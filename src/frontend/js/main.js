/**
 * PlayNexus Crystal Portal - Main Logic & Physics
 * 
 * Features:
 * 1. Matter.js Physics (Google Antigravity)
 * 2. Navigation & Hub Interactions
 */

const PlayNexus = {
    engine: null,
    render: null,
    runner: null,
    bodies: [],
    isGravityOn: true,
    isActive: false, // Track if physics is actively running
    animationFrameId: null,

    init() {
        console.log("💎 PlayNexus Crystal Hub Initialized");
        this.setupPhysics();
        this.bindEvents();
    },

    setupPhysics() {
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
     * Start the physics simulation (call when hub is active)
     */
    startPhysics() {
        if (this.isActive) return; // Already running

        this.isActive = true;
        this.runner = Runner.create();
        Runner.run(this.runner, this.engine);
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
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPhysics();
            } else if (document.querySelector('.crystal-card')) {
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
