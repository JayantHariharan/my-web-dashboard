/**
 * Toast Notification System
 *
 * Provides auto-dismissing, stackable notification toasts rendered in the
 * top-right corner of the viewport.  Toasts slide in from the right and
 * fade out after a configurable duration (or on click).
 *
 * Quick start
 * -----------
 * ```js
 * Toast.success('Account created!');
 * Toast.error('Invalid password', 6000);
 * Toast.info('Loading…');
 * Toast.warning('Rate limit approaching.');
 * ```
 *
 * @module toast
 */
const Toast = {
    container: null,
    init() {
        if (this.container) return;
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'true');
        Object.assign(this.container.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: '9999',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            maxWidth: '300px',
            pointerEvents: 'none',
            fontFamily: "'Outfit', sans-serif"
        });
        document.body.appendChild(this.container);
    },
    show(message, type = 'info', duration = 4000) {
        if (!this.container) this.init();
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.setAttribute('role', 'alert');
        const colors = {
            info: 'linear-gradient(135deg, #6d28d9, #2563eb)',
            success: 'linear-gradient(135deg, #10b981, #059669)',
            error: 'linear-gradient(135deg, #ef4444, #dc2626)',
            warning: 'linear-gradient(135deg, #f59e0b, #d97706)'
        };
        const bg = colors[type] || colors.info;
        Object.assign(toast.style, {
            padding: '12px 16px',
            borderRadius: '12px',
            background: bg,
            color: '#fff',
            fontSize: '0.9rem',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s cubic-bezier(0.19, 1, 0.22, 1)',
            pointerEvents: 'auto',
            cursor: 'pointer'
        });
        this.container.appendChild(toast);
        // Animate in
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });
        // Dismiss handlers
        const dismiss = () => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        };
        toast.addEventListener('click', dismiss);
        setTimeout(dismiss, duration);
    },
    success(msg, dur) { this.show(msg, 'success', dur); },
    error(msg, dur) { this.show(msg, 'error', dur); },
    info(msg, dur) { this.show(msg, 'info', dur); },
    warning(msg, dur) { this.show(msg, 'warning', dur); }
};

// Auto-init when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Toast.init());
} else {
    Toast.init();
}
