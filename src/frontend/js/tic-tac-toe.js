/**
 * Tic-Tac-Toe Crystal – Client Logic
 * Handles state sync, AI turn triggers, and cinematic animations.
 */

const TicTacToe = {
    gameId: null,
    userId: null,
    username: null,
    mode: 'single', // 'single' or 'multi'
    isMyTurn: false,
    mySymbol: 'X',
    board: Array(9).fill(null),
    status: 'playing',
    polling: null,

    // 🔊 Web Audio Sound Engine
    sounds: {
        ctx: null,
        init() {
            try {
                this.ctx = new (window.AudioContext || window.webkitAudioContext)();
            } catch(e) { console.warn("Audio Context blocked."); }
        },
        play(freq, type = 'sine', duration = 0.1, vol = 0.1) {
            if (!this.ctx) return;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            gain.gain.setValueAtTime(vol, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        },
        move() { this.play(440, 'triangle', 0.15, 0.05); },
        win() { 
            this.play(523.25, 'sine', 0.5, 0.1); 
            setTimeout(() => this.play(659.25, 'sine', 0.5, 0.1), 100);
            setTimeout(() => this.play(783.99, 'sine', 0.8, 0.1), 200);
        },
        error() { this.play(110, 'sawtooth', 0.3, 0.05); }
    },

    async init() {
        // 1. Get user session (Robust check for user_id or id)
        const sessionRaw = sessionStorage.getItem('playnexus_session') || localStorage.getItem('playnexus_session') || '{}';
        const session = JSON.parse(sessionRaw);
        this.userId = session.user_id || session.id;
        this.username = session.username;

        if (!this.userId) {
            console.error("No active session found. Redirecting to login...");
            window.location.replace('../index.html');
            return;
        }

        // Apply profile visuals to the game UI
        const p1Avatar = document.querySelector('#player-p1 .avatar');
        if (p1Avatar && session.avatar_url) {
            p1Avatar.style.backgroundImage = `url('${session.avatar_url}')`;
        }
        const p1Name = document.getElementById('p1-name');
        if (p1Name) p1Name.innerText = this.username;

        // 2. Determine mode from URL
        const params = new URLSearchParams(window.location.search);
        this.mode = params.get('mode') || 'single';
        this.level = params.get('level') || 'medium';

        // 3. Setup UI listeners
        this.sounds.init();
        document.querySelectorAll('.cell').forEach(cell => {
            cell.addEventListener('click', (e) => this.handleCellClick(e.target.dataset.index));
        });

        // 4. Create or Join Game
        await this.bootstrapGame();
        
        // 5. Initial Draw
        this.startPolling();
        this.fetchLeaderboard();
    },

    async bootstrapGame() {
        try {
            const apiBase = (window.location.protocol === 'file:') ? 'http://localhost:8000' : '';
            const response = await fetch(`${apiBase}/api/games/tic-tac-toe/create?user_id=${this.userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    game_type: this.mode,
                    level: this.level,
                    capacity: 2
                })
            });

            const game = await response.json();
            this.gameId = game.id;
            
            if (this.mode === 'multi') {
                document.getElementById('multiplayer-info').style.display = 'block';
                document.getElementById('game-join-code').innerText = game.join_code;
                document.getElementById('game-status-label').style.opacity = 1;
                document.getElementById('p2-name').innerText = "WAITING...";
            }

            console.log(`🎮 Game bootstrapped: ID ${this.gameId}`);
            this.updateUI(game);
        } catch (e) {
            Toast.error("Connection link failed. Retrying...");
        }
    },

    async handleCellClick(index) {
        if (!this.isMyTurn || this.board[index] || this.status !== 'playing') return;

        try {
            const apiBase = (window.location.protocol === 'file:') ? 'http://localhost:8000' : '';
            const response = await fetch(`${apiBase}/api/games/tic-tac-toe/move?user_id=${this.userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    game_id: this.gameId,
                    position: parseInt(index)
                })
            });

            if (!response.ok) {
                const err = await response.json();
                Toast.warning(err.detail || "Tactical error.");
                return;
            }

            // Immediately fetch state to update UI
            await this.syncState();
            this.playMoveSound();
        } catch (e) {
            console.error(e);
        }
    },

    async syncState() {
        if (!this.gameId) return;

        try {
            const apiBase = (window.location.protocol === 'file:') ? 'http://localhost:8000' : '';
            const response = await fetch(`${apiBase}/api/games/tic-tac-toe/state/${this.gameId}`);
            const state = await response.json();
            
            this.board = state.board;
            this.status = state.status;
            const oldTurn = this.currentTurn;
            this.currentTurn = state.current_turn;
            this.isMyTurn = (state.current_turn === this.mySymbol);

            // New: Play effect on change
            if (oldTurn && oldTurn !== state.current_turn) {
                this.triggerMoveEffect();
            }

            this.renderBoard();
            this.updateStatusUI(state);

            if (this.status !== 'playing') {
                this.stopPolling();
                this.handleGameOver();
            }
        } catch (e) {
            console.warn("Nexus sync interrupted.");
        }
    },

    renderBoard() {
        const winningLine = this.getWinningLine();
        document.querySelectorAll('.cell').forEach((cell, i) => {
            const val = this.board[i];
            if (val && !cell.classList.contains('occupied')) {
                cell.classList.add('occupied');
                cell.innerHTML = `<span class="symbol-${val.toLowerCase()}">${val}</span>`;
            }
            // Highlight winning line
            if (winningLine && winningLine.includes(i)) {
                cell.style.background = "rgba(187, 134, 252, 0.2)";
                cell.style.borderColor = "var(--nexus-purple)";
            }
        });
    },

    getWinningLine() {
        const b = this.board;
        const wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
        for (let w of wins) {
            if (b[w[0]] && b[w[0]] === b[w[1]] && b[w[0]] === b[w[2]]) return w;
        }
        return null;
    },

    updateStatusUI(state) {
        const turnLabel = document.getElementById('turn-indicator');
        const thinkingBar = document.getElementById('thinking-bar');

        if (state.status === 'playing') {
            const isAiTurn = !this.isMyTurn;
            const currentSym = state.current_turn;
            if (turnLabel) {
                 turnLabel.innerText = currentSym === this.mySymbol ? "YOUR STRIKE (PIECE: X)" : "AGENT PROCESSING...";
            }
            
            // UI Feedback for AI thinking
            if (thinkingBar) {
                thinkingBar.style.width = isAiTurn ? "100%" : "0%";
            }

            const p1Node = document.getElementById('player-p1');
            const p2Node = document.getElementById('player-p2');
            if (p1Node) p1Node.classList.toggle('active', state.current_turn === 'X');
            if (p2Node) p2Node.classList.toggle('active', state.current_turn === 'O');
        } else {
            if (turnLabel) {
                turnLabel.innerText = "MATCH CONCLUDED";
                turnLabel.style.color = "var(--nexus-cyan)";
            }
            if (thinkingBar) thinkingBar.style.width = "0%";
        }
    },

    triggerMoveEffect() {
        const board = document.querySelector('.board-container');
        if (board) {
            board.classList.remove('shake');
            void board.offsetWidth; // trigger reflow
            board.classList.add('shake');
        }
        this.sounds.move();
    },

    async handleGameOver() {
        const result = this.status;
        let achievementType = 'draw';
        
        if (result === 'draw') {
            Toast.info("STALEMATE. Data inconclusive.");
            this.sounds.error();
            achievementType = 'draw';
        } else if (result.includes(this.mySymbol)) {
            Toast.success("VICTORY. Nexus rating increased.");
            this.sounds.win();
            this.triggerVictoryEffect();
            achievementType = 'win';
        } else {
            Toast.error("DEFEAT. AI processing superior.");
            this.sounds.error();
            achievementType = 'loss';
        }

        // 🛰️ Broadcast Achievement to Nexus Hub
        try {
            const apiBase = (window.location.protocol === 'file:') ? 'http://localhost:8000' : '';
            await fetch(`${apiBase}/api/auth/me/activity`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    activity_type: 'game_concluded',
                    game_id: 'tic-tac-toe',
                    details: `Result: ${achievementType.toUpperCase()} | Mode: ${this.mode}`
                })
            });
        } catch (e) {
            console.warn("Nexus Transmission failed, but victory recorded locally.");
        }
    },

    triggerVictoryEffect() {
        // Simple visual flair
        document.querySelector('.board-container').style.boxShadow = "0 0 100px var(--nexus-cyan)";
        setTimeout(() => {
            document.querySelector('.board-container').style.boxShadow = "";
        }, 1000);
    },

    updateUI(game) {
        // Handle player names in multi
        const p2 = game.players.find(p => p.symbol === 'O');
        if (p2 && !p2.is_ai) {
            document.getElementById('p2-name').innerText = p2.username || "GUEST";
        }
    },

    startPolling() {
        this.polling = setInterval(() => this.syncState(), 1000);
    },

    stopPolling() {
        if (this.polling) clearInterval(this.polling);
    },

    async fetchLeaderboard() {
        try {
            const apiBase = (window.location.protocol === 'file:') ? 'http://localhost:8000' : '';
            const response = await fetch(`${apiBase}/api/games/leaderboard?limit=3`);
            const data = await response.json();
            const list = document.getElementById('leaderboard-list');
            list.innerHTML = data.map((entry, i) => `
                <li><span>${i+1}. ${entry.username}</span> <span>${entry.elo_rating} ELO</span></li>
            `).join('') || "<li><span>No ratings recorded...</span></li>";
        } catch (e) { /* silent fail */ }
    },

    playMoveSound() {
        // Optional: Implement tiny beep
    }
};

window.addEventListener('DOMContentLoaded', () => TicTacToe.init());
