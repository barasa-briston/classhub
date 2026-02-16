
document.addEventListener('DOMContentLoaded', function () {
    console.log("Admin Tab Fix Loaded");

    function setupTabs() {
        const tabs = document.querySelectorAll('.nav-tabs .nav-link');
        const contents = document.querySelectorAll('.tab-content .tab-pane');

        if (tabs.length > 0) {
            tabs.forEach(tab => {
                tab.addEventListener('click', function (e) {
                    // If it's a Jazzmin tab, it might already have a listener, 
                    // but we can force the classes if needed.
                    const targetId = this.getAttribute('href');
                    if (targetId && targetId.startsWith('#')) {
                        // Standard Bootstrap tab behavior
                        tabs.forEach(t => t.classList.remove('active'));
                        contents.forEach(c => c.classList.remove('active', 'show'));

                        this.classList.add('active');
                        const targetContent = document.querySelector(targetId);
                        if (targetContent) {
                            targetContent.classList.add('active', 'show');
                        }
                    }
                });
            });
        }
    }

    // Run once and also after a short delay to account for Jazzmin's dynamic loading
    setupTabs();
    setTimeout(setupTabs, 1000);
});
