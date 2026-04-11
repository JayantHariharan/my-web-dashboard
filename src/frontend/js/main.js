/**
 * PlayNexus Crystal Portal - Main Logic & Physics
 *
 * Matter.js is lazy-loaded when the signed-in hub starts physics, so the auth
 * portal stays lightweight on first paint (important for free-tier hosting).
 */

const MATTER_CDN =
    "https://cdnjs.cloudflare.com/ajax/libs/matter-js/0.19.0/matter.min.js";

function loadMatterScript() {
    return new Promise((resolve, reject) => {
        if (typeof Matter !== "undefined") {
            resolve();
            return;
        }
        const existing = document.querySelector('script[data-playnexus="matter"]');
        if (existing) {
            existing.addEventListener("load", () => resolve());
            existing.addEventListener("error", () =>
                reject(new Error("Matter.js load failed"))
            );
            return;
        }
        const s = document.createElement("script");
        s.src = MATTER_CDN;
        s.async = true;
        s.dataset.playnexus = "matter";
        s.onload = () => resolve();
        s.onerror = () => reject(new Error("Matter.js load failed"));
        document.head.appendChild(s);
    });
}

const PlayNexus = {
    engine: null,
    render: null,
    runner: null,
    bodies: [],
    isGravityOn: true,
    isActive: false, // Track if physics is actively running
    animationFrameId: null,
    matterLoadAttempted: false,

    init() {
        console.log("💎 PlayNexus Crystal Hub Initialized (physics deferred)");
        this.bindEvents();
    },

    setupPhysics() {
        if (typeof Matter === "undefined") {
            console.warn("Matter.js not available; physics disabled");
            return;
        }
        const { Engine, Render, Runner, Bodies, Composite } = Matter;

        this.engine = Engine.create();
        this.engine.gravity.y = 1;

        // Create a hidden renderer just for the world bounds
        this.render = Render.create({
            element: document.body,
            engine: this.engine,
            options: {
                width: window.innerWidth,
                height: window.innerHeight,
                wireframes: false,
                background: 'transparent'
            }
        });

        // Prevent the physics canvas from blocking UI clicks
        if (this.render && this.render.canvas) {
            this.render.canvas.style.pointerEvents = 'none';
            this.render.canvas.style.position = 'fixed';
            this.render.canvas.style.zIndex = '-1';
        }

        // Add invisible walls
        const wallOptions = { isStatic: true, render: { visible: false } };
        const ground = Bodies.rectangle(window.innerWidth/2, window.innerHeight + 50, window.innerWidth, 100, wallOptions);
        const leftWall = Bodies.rectangle(-50, window.innerHeight/2, 100, window.innerHeight, wallOptions);
        const rightWall = Bodies.rectangle(window.innerWidth + 50, window.innerHeight/2, 100, window.innerHeight, wallOptions);
        const ceiling = Bodies.rectangle(window.innerWidth/2, -50, window.innerWidth, 100, wallOptions);

        Composite.add(this.engine.world, [ground, leftWall, rightWall, ceiling]);

        // Don't start runner yet - wait for startPhysics()
    },

    /**
     * Start the physics simulation (call when hub is active).
     * Loads Matter.js from CDN on first use.
     */
    async startPhysics() {
        if (this.isActive) return;

        try {
            await loadMatterScript();
        } catch (e) {
            console.warn("Skipping hub physics:", e && e.message);
            return;
        }

        if (!this.engine) {
            this.setupPhysics();
        }
        if (!this.engine) return;

        this.isActive = true;
        this.runner = Matter.Runner.create();
        Matter.Runner.run(this.runner, this.engine);
        console.log("🎮 Physics engine started");
    },

    /**
     * Stop the physics simulation to save CPU (call when leaving hub)
     */
    stopPhysics() {
        if (!this.isActive) return;

        if (this.runner) {
            Runner.stop(this.runner);
            this.runner = null;
        }
        this.isActive = false;
        console.log("⏸️ Physics engine stopped");
    },

    /**
     * Toggle gravity on/off
     */
    toggleGravity() {
        this.isGravityOn = !this.isGravityOn;
        this.engine.gravity.y = this.isGravityOn ? 1 : 0;

        if (!this.isGravityOn && this.bodies.length > 0) {
            // Give elements a random push when gravity turns off
            this.bodies.forEach(body => {
                Matter.Body.applyForce(body, body.position, {
                    x: (Math.random() - 0.5) * 0.05, // Reduced force for lighter effect
                    y: (Math.random() - 0.5) * 0.05
                });
            });
        }

        console.log(`🛸 Gravity: ${this.isGravityOn ? 'ON' : 'OFF'}`);
        return this.isGravityOn;
    },

    /**
     * Add physics to a DOM element
     */
    addPhysicsToElement(el) {
        if (!el || !this.isActive) return;

        const rect = el.getBoundingClientRect();
        const { Bodies, Composite } = Matter;

        // Skip if too small
        if (rect.width < 20 || rect.height < 20) return;

        const body = Bodies.rectangle(
            rect.left + rect.width / 2,
            rect.top + rect.height / 2,
            rect.width,
            rect.height,
            {
                restitution: 0.4, // Reduced bounce for more stable
                friction: 0.1,
                frictionAir: 0.01, // Add air resistance for damping
                density: 0.001 // Lightweight
            }
        );

        this.bodies.push(body);
        Composite.add(this.engine.world, body);

        // Sync loop - only update if element still exists and physics is active
        const sync = () => {
            if (!this.isActive) return;

            try {
                // Only update if moved significantly or rotating
                if (body.speed > 0.05 || Math.abs(body.angle) > 0.01) {
                    const newX = body.position.x - rect.left - rect.width/2;
                    const newY = body.position.y - rect.top - rect.height/2;
                    el.style.transform = `translate(${newX}px, ${newY}px) rotate(${body.angle}rad)`;
                }

                // Continue loop only if body still in world
                if (Composite.get(this.engine.world, body.id, 'body')) {
                    this.animationFrameId = requestAnimationFrame(sync);
                }
            } catch (e) {
                // Element might have been removed, stop syncing
                console.debug("Physics sync stopped for element");
            }
        };

        // Start sync loop
        if (this.isActive) {
            this.animationFrameId = requestAnimationFrame(sync);
        }
    },

    bindEvents() {
        // Handle window resize - update walls
        window.addEventListener('resize', () => {
            // Could rebuild walls here, but skip for performance
        });

        // Reduce physics when tab is not visible
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                this.stopPhysics();
                return;
            }
            const hub = document.getElementById("master-hub-container");
            if (hub && !hub.classList.contains("hidden")) {
                this.startPhysics();
            }
        });
    }
};

// Global hooks
window.startGravity = () => {
    const cards = document.querySelectorAll('.crystal-card');
    cards.forEach(card => PlayNexus.addPhysicsToElement(card));
};

// Expose for testing/debugging
window.PlayNexus = PlayNexus;

PlayNexus.init();
