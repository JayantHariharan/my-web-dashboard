/**
 * PlayNexus Cinematic Gateway – Dark Elegance & AI Identity (v8.0)
 *
 * Renders the animated canvas background seen on the auth portal.
 *
 * Features:
 * - Robust Logo-Bloom logic (fixed selector / timing)
 * - Cinematic God Rays & Bokeh (v8.0)
 * - Accessible: honours `prefers-reduced-motion` and `saveData` hints
 * - Lightweight mobile path (fewer particles, shorter reveal delay)
 *
 * @module cinematic-startup
 */

const CinematicGateway = {
    canvas: null,
    ctx: null,
    particles: [],
    blobs: [],
    startTime: 0,
    DURATION: 12000, 

    init() {
        this.canvas = document.getElementById('cinematic-bg');
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        this.resize();
        window.addEventListener('resize', () => this.resize());

        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduceMotion) {
            this.paintStaticBackdrop();
            this.revealAuthCard();
            return;
        }

        const saveData = navigator.connection && navigator.connection.saveData;
        const isMobile = window.innerWidth < 768;
        this._liteBackdrop = !!(saveData || isMobile);

        this.spawnParticles();
        this.spawnBlobs();

        requestAnimationFrame((t) => this.animate(t));

        // Reveal auth portal (slightly faster when saving data / mobile)
        const delay = this._liteBackdrop ? 900 : 2000;
        setTimeout(() => this.revealAuthCard(), delay);
    },

    /** One-shot frame for accessibility and lighter CPU on auth screen */
    paintStaticBackdrop() {
        this.ctx.fillStyle = '#030308';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGodRays();
    },

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    },

    spawnParticles() {
        // ✨ Golden Bokeh Particles (Refined for v8.0)
        // Reduce particle count on mobile for better performance
        const isMobile = window.innerWidth < 768;
        const particleCount = this._liteBackdrop
            ? (isMobile ? 28 : 40)
            : isMobile
              ? 60
              : 120;

        for (let i = 0; i < particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: 3 + Math.random() * 15,
                color: i % 10 === 0 ? '#FFFFFF' : '#FFD700', 
                vx: (Math.random() - 0.5) * 0.1,
                vy: -0.05 - Math.random() * 0.15, 
                alpha: 0.1 + Math.random() * 0.3,
                pulse: Math.random() * Math.PI,
                pulseSpeed: 0.005 + Math.random() * 0.015
            });
        }
    },

    spawnBlobs() {
        const colors = ['#BB86FC', '#03DAC6', '#0a0a0f', '#060608'];
        const count = this._liteBackdrop ? 3 : 6;
        for (let i = 0; i < count; i++) {
            this.blobs.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: 500 + Math.random() * 500,
                color: colors[i % colors.length],
                vx: (Math.random() - 0.5) * 0.4, 
                vy: (Math.random() - 0.5) * 0.4,
                opacity: 0.02 + Math.random() * 0.05
            });
        }
    },

    drawGodRays() {
        // 🔦 Top-Left Cinematic Light Optics
        const gradient = this.ctx.createRadialGradient(
            0, 0, 0,
            0, 0, this.canvas.width * 1.5
        );
        gradient.addColorStop(0, 'rgba(255, 255, 255, 0.03)');
        gradient.addColorStop(0.3, 'rgba(255, 215, 0, 0.01)');
        gradient.addColorStop(0.6, 'transparent');
        
        this.ctx.globalCompositeOperation = 'screen';
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    },

    drawBlob(blob) {
        const gradient = this.ctx.createRadialGradient(
            blob.x, blob.y, 0,
            blob.x, blob.y, blob.radius
        );
        gradient.addColorStop(0, blob.color);
        gradient.addColorStop(1, 'transparent');
        
        this.ctx.globalAlpha = blob.opacity;
        this.ctx.fillStyle = gradient;
        this.ctx.beginPath();
        this.ctx.arc(blob.x, blob.y, blob.radius, 0, Math.PI * 2);
        this.ctx.fill();
    },

    generateAvatar(seed) {
        // 👤 DiceBear Identity Randomizer
        return `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}&backgroundColor=b6e3f4,c0aede,d1d4f9&mood=happy`;
    },

    animate(time) {
        if (!this.startTime) this.startTime = time;
        const elapsed = time - this.startTime;

        // 🌌 PITCH DARK DEPTH
        this.ctx.globalCompositeOperation = 'source-over';
        this.ctx.fillStyle = '#020202';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // 🔦 GOD RAY Optics
        this.drawGodRays();

        // 🌀 LIQUID NEBULA
        this.ctx.globalCompositeOperation = 'screen';
        this.blobs.forEach(b => {
            b.x += b.vx;
            b.y += b.vy;
            if (b.x < -b.radius || b.x > this.canvas.width + b.radius) b.vx *= -1;
            if (b.y < -b.radius || b.y > this.canvas.height + b.radius) b.vy *= -1;
            this.drawBlob(b);
        });

        // ✨ GOLDEN BOKEH Field
        this.ctx.globalCompositeOperation = 'lighter';
        this.particles.forEach((p) => {
            p.x += p.vx;
            p.y += p.vy;
            p.pulse += p.pulseSpeed;

            const pAlpha = p.alpha * (0.5 + Math.abs(Math.sin(p.pulse) * 0.5));
            const pRadius = p.radius * (0.9 + Math.abs(Math.sin(p.pulse) * 0.2));
            
            this.ctx.beginPath();
            const pGrad = this.ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, pRadius);
            pGrad.addColorStop(0, p.color);
            pGrad.addColorStop(1, 'transparent');

            this.ctx.fillStyle = pGrad;
            this.ctx.globalAlpha = pAlpha;
            this.ctx.arc(p.x, p.y, pRadius, 0, Math.PI * 2);
            this.ctx.fill();
            
            if (p.y < -p.radius) p.y = this.canvas.height + p.radius;
            if (p.x < -p.radius) p.x = this.canvas.width + p.radius;
            if (p.x > this.canvas.width + p.radius) p.x = -p.radius;
        });

        // 🪐 PHASE 2: LOGO CENTER-BLOOM (2-7s)
        const logo = document.getElementById('logo-bloom');
        if (logo && elapsed > 2000 && elapsed < 7000) {
            logo.style.opacity = (elapsed - 2000) / 4000;
        }

        requestAnimationFrame((t) => this.animate(t));
    },

    revealAuthCard() {
        const auth = document.getElementById('crystal-auth-portal');
        const logo = document.getElementById('logo-bloom');
        
        if (auth) {
            auth.classList.remove('hidden');
            auth.style.transition = 'opacity 1.5s ease-out, transform 1.5s cubic-bezier(0.19, 1, 0.22, 1)';
            auth.style.opacity = '1';
            auth.style.transform = 'scale(1)';
        }

        if (logo) {
            logo.style.transition = 'all 2.5s cubic-bezier(0.19, 1, 0.22, 1)';
            logo.style.transform = 'scale(1) translateY(0)';
            logo.style.opacity = '1';
        }
    }
};

/**
 * Bootstrap the cinematic gateway once all page resources have loaded.
 *
 * Using `addEventListener` instead of assigning `window.onload` directly
 * prevents this handler from accidentally overwriting any other `load`
 * listeners registered elsewhere in the page.
 */
window.addEventListener('load', () => CinematicGateway.init());
