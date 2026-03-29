/**
 * PlayNexus Session Manager
 * 
 * Handles the "Who's exploring?" intro screen and persists
 * the user's name throughout the session.
 */

const SessionManager = {
  SESSION_KEY: 'playnexus_explorer_name',

  init() {
    const explorerName = sessionStorage.getItem(this.SESSION_KEY);
    
    if (!explorerName) {
      this.showIntro();
    } else {
      this.updateHUD(explorerName);
      this.revealHub();
    }
  },

  showIntro() {
    const introOverlay = document.createElement('div');
    introOverlay.id = 'crystal-intro-overlay';
    introOverlay.innerHTML = `
      <div class="crystal-intro-content">
        <h1 class="netflix-red">Who's exploring PlayNexus?</h1>
        <div class="crystal-input-group">
          <input type="text" id="explorer-input" placeholder="Enter your name..." maxlength="15">
          <button id="start-btn" class="crystal-btn">Start Exploration</button>
        </div>
      </div>
    `;
    document.body.appendChild(introOverlay);

    document.getElementById('start-btn').onclick = () => this.handleStart();
    document.getElementById('explorer-input').onkeypress = (e) => {
      if (e.key === 'Enter') this.handleStart();
    };
  },

  handleStart() {
    const input = document.getElementById('explorer-input');
    const name = input.value.trim() || 'Guest Explorer';
    
    sessionStorage.setItem(this.SESSION_KEY, name);
    
    // Animation out
    const overlay = document.getElementById('crystal-intro-overlay');
    overlay.classList.add('fade-out');
    
    setTimeout(() => {
      overlay.remove();
      this.updateHUD(name);
      this.revealHub();
    }, 800);
  },

  updateHUD(name) {
    const userDisplay = document.getElementById('user-display-name');
    if (userDisplay) {
      userDisplay.innerHTML = `<span class="neon-purple">Explorer:</span> <span class="crystal-text" style="color: white; margin-left: 5px;">${name}</span>`;
    }

    const gravityBtn = document.getElementById('gravity-toggle');
    if (gravityBtn && window.PlayNexus) {
      gravityBtn.onclick = () => {
        const isOn = window.PlayNexus.toggleGravity();
        gravityBtn.innerText = isOn ? '🛸 Gravity: ON' : '🛸 Zero-G: OFF';
        gravityBtn.style.color = isOn ? 'white' : 'var(--neon-blue)';
      };
    }
  },

  revealHub() {
    const hub = document.getElementById('main-hub-container');
    if (hub) hub.classList.remove('hidden');
    // Trigger Matter.js physics if initialized
    if (window.startGravity) window.startGravity();
  }
};

window.onload = () => SessionManager.init();
