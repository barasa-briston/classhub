document.addEventListener('alpine:init', () => {
    Alpine.data('toast', () => ({
        toasts: [],
        nextId: 1,

        add(message, type = 'info') {
            const id = this.nextId++;
            this.toasts.push({
                id,
                message,
                type,
                visible: true
            });

            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                this.remove(id);
            }, 5000);
        },

        remove(id) {
            const toastIndex = this.toasts.findIndex(t => t.id === id);
            if (toastIndex > -1) {
                this.toasts[toastIndex].visible = false;
                // Wait for transition to finish before removing from array
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 300);
            }
        },

        // Helper to get classes based on type
        getTypeClasses(type) {
            switch (type) {
                case 'success':
                    return 'bg-emerald-500/90 text-white border-emerald-400';
                case 'error':
                    return 'bg-rose-500/90 text-white border-rose-400';
                case 'warning':
                    return 'bg-amber-500/90 text-white border-amber-400';
                default:
                    return 'bg-blue-500/90 text-white border-blue-400';
            }
        },

        // Helper to get icon based on type
        getIcon(type) {
            switch (type) {
                case 'success':
                    return 'fas fa-check-circle';
                case 'error':
                    return 'fas fa-exclamation-circle';
                case 'warning':
                    return 'fas fa-exclamation-triangle';
                default:
                    return 'fas fa-info-circle';
            }
        }
    }));
});
