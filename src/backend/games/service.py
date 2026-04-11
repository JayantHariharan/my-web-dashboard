# src/backend/games/service.py
import random
import logging
from typing import List, Optional, Tuple, Dict, Any
from ..shared.database import game_repo, game_player_repo, game_move_repo, leaderboard_repo
from ..config import settings

logger = logging.getLogger(__name__)

class GameService:
    @staticmethod
    def get_board_state(game_id: int) -> Tuple[List[Optional[str]], str, str]:
        """Calculates the current board state and status."""
        moves = game_move_repo.find_by_game(game_id)
        board = [None] * 9
        for m in moves:
            board[m['position']] = m['symbol']
        
        # Win patterns
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        
        status = 'playing'
        for w in wins:
            if board[w[0]] and board[w[0]] == board[w[1]] == board[w[2]]:
                status = f"{board[w[0]]}_wins"
                break
        
        if status == 'playing' and all(board):
            status = 'draw'
            
        # Determine current turn
        current_turn = 'X' if len(moves) % 2 == 0 else 'O'
        
        return board, status, current_turn

    @staticmethod
    def get_ai_move(board: List[Optional[str]], symbol: str, level: str) -> int:
        """Returns the next move for the AI agent."""
        empty_indices = [i for i, x in enumerate(board) if x is None]
        
        if level == 'easy':
            return random.choice(empty_indices)
        
        if level == 'god' and settings.openai_api_key:
            return GameService._get_openai_move(board, symbol)
            
        # Default to Minimax for medium/hard
        return GameService._minimax_move(board, symbol)

    @staticmethod
    def _minimax_move(board: List[Optional[str]], symbol: str) -> int:
        """Standard Minimax algorithm for Tic-Tac-Toe."""
        def check_status(b):
            wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
            for w in wins:
                if b[w[0]] and b[w[0]] == b[w[1]] == b[w[2]]:
                    return b[w[0]]
            if all(b): return 'draw'
            return None

        def minimax(b, depth, is_max, ai_sym, hu_sym):
            res = check_status(b)
            if res == ai_sym: return 10 - depth
            if res == hu_sym: return depth - 10
            if res == 'draw': return 0
            
            if is_max:
                best = -100
                for i in range(9):
                    if b[i] is None:
                        b[i] = ai_sym
                        best = max(best, minimax(b, depth+1, False, ai_sym, hu_sym))
                        b[i] = None
                return best
            else:
                best = 100
                for i in range(9):
                    if b[i] is None:
                        b[i] = hu_sym
                        best = min(best, minimax(b, depth+1, True, ai_sym, hu_sym))
                        b[i] = None
                return best

        hu_sym = 'O' if symbol == 'X' else 'X'
        best_val = -100
        best_move = -1
        
        # If board is empty, take a corner instead of calculating
        if all(x is None for x in board):
            return random.choice([0, 2, 6, 8, 4])

        for i in range(9):
            if board[i] is None:
                board[i] = symbol
                move_val = minimax(board, 0, False, symbol, hu_sym)
                board[i] = None
                if move_val > best_val:
                    best_val = move_val
                    best_move = i
        return best_move

    @staticmethod
    def _get_openai_move(board: List[Optional[str]], symbol: str) -> int:
        """Call OpenAI to get the next move for 'God' level."""
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        
        board_str = ", ".join([x if x else str(i) for i, x in enumerate(board)])
        prompt = f"Tic-Tac-Toe board state (0-8 indices if empty): {board_str}. You are playing as {symbol}. What is your next best move? Respond ONLY with the index number (0-8)."
        
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "system", "content": "You are a professional Tic-Tac-Toe player."},
                          {"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0
            )
            move = response.choices[0].message.content.strip()
            return int(move)
        except Exception as e:
            logger.error(f"OpenAI Move Error: {e}")
            return GameService._minimax_move(board, symbol)
