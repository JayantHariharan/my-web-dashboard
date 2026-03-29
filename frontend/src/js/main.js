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

    init() {
        console.log("💎 PlayNexus Crystal Hub Initialized");
        this.setupPhysics();
        this.bindEvents();
    },

    setupPhysics() {
        const { Engine, Render, Runner, Bodies, Composite } = Matter;
        
        this.engine = Engine.create();
        this.engine.gravity.y = 1; // Start with normal gravity

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
        
        // FIX: Prevent the physics canvas from blocking UI clicks
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

        this.runner = Runner.create();
        Runner.run(this.runner, this.engine);
    },

    /**
     * Toggles the "Google Antigravity" effect
     */
    toggleGravity() {
        this.isGravityOn = !this.isGravityOn;
        this.engine.gravity.y = this.isGravityOn ? 1 : 0;
        
        if (!this.isGravityOn) {
            // Give everything a little kick when gravity turns off
            this.bodies.forEach(body => {
                Matter.Body.applyForce(body, body.position, {
                    x: (Math.random() - 0.5) * 0.1,
                    y: (Math.random() - 0.5) * 0.1
                });
            });
        }
        
        console.log(`🛸 Gravity: ${this.isGravityOn ? 'ON' : 'OFF'}`);
        return this.isGravityOn;
    },

    /**
     * Syncs a DOM element with a physics body
     */
    addPhysicsToElement(el) {
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const { Bodies, Composite } = Matter;

        const body = Bodies.rectangle(
            rect.left + rect.width / 2,
            rect.top + rect.height / 2,
            rect.width,
            rect.height,
            { restitution: 0.6, friction: 0.1 }
        );

        this.bodies.push(body);
        Composite.add(this.engine.world, body);

        // Sync loop
        const sync = () => {
            if (!this.isGravityOn || body.speed > 0.1) {
                el.style.transform = `translate(${body.position.x - rect.left - rect.width/2}px, ${body.position.y - rect.top - rect.height/2}px) rotate(${body.angle}rad)`;
            }
            requestAnimationFrame(sync);
        };
        sync();
    },

    bindEvents() {
        // Handle window resize
        window.addEventListener('resize', () => {
            // Update walls logic here if needed
        });
    }
};

// Global hook for the session manager
window.startGravity = () => {
    const cards = document.querySelectorAll('.crystal-card');
    cards.forEach(card => PlayNexus.addPhysicsToElement(card));
};

PlayNexus.init();
