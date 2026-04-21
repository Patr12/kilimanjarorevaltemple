// ================= PAGE TRANSITION ANIMATION =================
class PageTransition {
    constructor() {
        this.transitionElement = document.querySelector('.page-transition');
        this.pageContent = document.querySelector('.page-content');
        this.curtains = document.querySelectorAll('.curtain');
        this.logo = document.querySelector('.transition-logo');

        if (!this.transitionElement || !this.pageContent) {
            return;
        }
        
        this.init();
    }
    
    init() {
        // Anza na page zote zimefungua
        this.transitionElement.classList.add('curtain-close');
        
        // Baada ya muda mfupi, futa animation na onyesha content
        setTimeout(() => {
            this.animateOut();
        }, 100);
        
        // Add event listener kwa internal links
        this.bindLinks();
    }
    
    animateOut() {
        // Anza animation ya kufungua
        this.transitionElement.classList.remove('curtain-close');
        this.transitionElement.classList.add('curtain-open');
        
        // Onyesha content baada ya animation
        setTimeout(() => {
            document.body.classList.add('page-ready');
            this.transitionElement.style.pointerEvents = 'none';
        }, 800);

        setTimeout(() => {
            this.transitionElement.style.display = 'none';
        }, 1200);
    }
    
    animateIn(url) {
        return new Promise((resolve) => {
            this.transitionElement.style.display = 'flex';
            this.transitionElement.style.pointerEvents = 'auto';

            // Funga curtains tena
            this.transitionElement.classList.remove('curtain-open');
            this.transitionElement.classList.add('curtain-close');
            
            // Ficha content
            document.body.classList.remove('page-ready');
            
            // Nenda kwenye url baada ya animation
            setTimeout(() => {
                resolve();
                if (url) {
                    window.location.href = url;
                }
            }, 1200);
        });
    }
    
    bindLinks() {
        // Bind all internal links
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            
            if (link && 
                link.href && 
                !link.href.includes('#') && 
                !link.target && 
                link.href.indexOf(window.location.origin) === 0 &&
                !link.classList.contains('no-transition') &&
                !link.hasAttribute('data-bs-toggle') &&
                link.getAttribute('href') !== 'javascript:void(0)') {
                
                e.preventDefault();
                this.animateIn(link.href);
            }
        });
        
        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            this.animateOut();
        });
    }
}

// ================= BACK TO TOP BUTTON =================
const backToTopButton = document.getElementById('backToTop');

if (backToTopButton) {
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTopButton.style.display = 'block';
        } else {
            backToTopButton.style.display = 'none';
        }
    });

    backToTopButton.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ================= AUTO-CLOSE ALERTS =================
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Initialize page transition
    if (document.querySelector('.page-transition')) {
        new PageTransition();
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
