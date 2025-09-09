// Main JavaScript for SubService

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page transitions
    document.body.classList.add('page-transition');
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.textContent;
                submitBtn.innerHTML = '<span class="spinner"></span> Processing...';
                submitBtn.disabled = true;
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                }, 10000);
            }
        });
    });
    
    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add hover effects to cards
    const cards = document.querySelectorAll('.card-hover');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Initialize tooltips (if using any tooltip library)
    initializeTooltips();
    
    // Initialize modals
    initializeModals();
});

// Utility functions
function showLoading(element) {
    if (element) {
        element.innerHTML = '<span class="spinner"></span> Loading...';
        element.disabled = true;
    }
}

function hideLoading(element, originalText) {
    if (element) {
        element.textContent = originalText;
        element.disabled = false;
    }
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} bg-${type === 'error' ? 'red' : 'green'}-100 border border-${type === 'error' ? 'red' : 'green'}-400 text-${type === 'error' ? 'red' : 'green'}-700 px-4 py-3 rounded mb-4`;
    alertDiv.textContent = message;
    
    // Insert at the top of the main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        }, 5000);
    }
}

function initializeTooltips() {
    // Simple tooltip implementation
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute z-50 px-2 py-1 text-sm text-white bg-gray-800 rounded shadow-lg';
            tooltip.textContent = this.getAttribute('data-tooltip');
            tooltip.style.top = (this.offsetTop - 30) + 'px';
            tooltip.style.left = this.offsetLeft + 'px';
            
            document.body.appendChild(tooltip);
            this.tooltipElement = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this.tooltipElement) {
                this.tooltipElement.remove();
                this.tooltipElement = null;
            }
        });
    });
}

function initializeModals() {
    // Simple modal implementation
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    const modalCloses = document.querySelectorAll('[data-modal-close]');
    
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal-target');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            }
        });
    });
    
    modalCloses.forEach(close => {
        close.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.classList.add('hidden');
                document.body.style.overflow = 'auto';
            }
        });
    });
    
    // Close modal on backdrop click
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-backdrop')) {
            e.target.classList.add('hidden');
            document.body.style.overflow = 'auto';
        }
    });
}

// Stripe integration helpers
function redirectToStripeCheckout(checkoutUrl) {
    if (checkoutUrl) {
        window.location.href = checkoutUrl;
    }
}

// API helpers
async function makeApiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'An error occurred');
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Export functions for global use
window.SubService = {
    showLoading,
    hideLoading,
    showAlert,
    redirectToStripeCheckout,
    makeApiRequest,
    getCookie
};