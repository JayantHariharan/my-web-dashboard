/**
 * PlayNexus Splash & Auth Transition
 * 
 * Handles the 3-second cinematic Logo Splash, 
 * then transitions to the Crystal Login Portal.
 */

const PortalIntro = {
  SPLASH_TIME: 3000,

  init() {
    this.createSplash();
    
    // Auto-transition after SPLASH_TIME
    setTimeout(() => {
      this.transitionToAuth();
    }, this.SPLASH_TIME);
  },

  createSplash() {
    const splash = document.createElement('div');
    splash.id = 'playnexus-splash';
    splash.innerHTML = `
      <div class="splash-logo-container">
        <!-- Geometric Crystal Logo Placeholder (CSS animated) -->
        <div class="crystal-nexus-logo"></div>
        <h1 class="logo-text-fade">Play<span>Nexus</span></h1>
      </div>
    `;
    document.body.appendChild(splash);
  },

  transitionToAuth() {
    const splash = document.getElementById('playnexus-splash');
    const authPortal = document.getElementById('crystal-auth-portal');
    
    if (splash) splash.classList.add('fade-out');
    
    setTimeout(() => {
      if (splash) splash.remove();
      if (authPortal) {
        authPortal.classList.remove('hidden');
        authPortal.classList.add('fade-in');
      }
    }, 1000);
  }
};

window.onload = () => PortalIntro.init();
