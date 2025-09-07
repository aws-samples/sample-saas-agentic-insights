// Configuration - Uses shared config generated during deployment
const CONFIG = window.APP_CONFIG || (() => {
    console.error('APP_CONFIG not found. Please ensure config.js is loaded.');
    return {};
})();

// State management
let selectedTier = null;

// DOM elements
const pricingSection = document.querySelector('.pricing');
const registrationSection = document.getElementById('registration-section');
const registrationForm = document.getElementById('registration-form');
const selectedTierSpan = document.getElementById('selected-tier');
const errorMessage = document.getElementById('error-message');
const successMessage = document.getElementById('success-message');
const registerBtn = document.getElementById('register-btn');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Plan selection buttons
    document.querySelectorAll('.select-plan-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tier = this.getAttribute('data-tier');
            selectPlan(tier);
        });
    });

    // Change plan button
    document.getElementById('change-plan').addEventListener('click', function() {
        showPricingSection();
    });

    // Cancel button
    document.getElementById('cancel-btn').addEventListener('click', function() {
        showPricingSection();
    });

    // Registration form
    registrationForm.addEventListener('submit', handleRegistration);

    // Password confirmation validation
    document.getElementById('confirm-password').addEventListener('input', validatePasswordMatch);
});

function selectPlan(tier) {
    selectedTier = tier;
    selectedTierSpan.textContent = tier.charAt(0).toUpperCase() + tier.slice(1);
    
    // Hide pricing section and show registration form
    pricingSection.style.display = 'none';
    registrationSection.style.display = 'block';
    
    // Clear any previous messages
    hideMessages();
    
    // Reset form
    registrationForm.reset();
}

function showPricingSection() {
    pricingSection.style.display = 'block';
    registrationSection.style.display = 'none';
    selectedTier = null;
    hideMessages();
}

function validatePasswordMatch() {
    const password = document.getElementById('admin-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const confirmInput = document.getElementById('confirm-password');
    
    if (confirmPassword && password !== confirmPassword) {
        confirmInput.setCustomValidity('Passwords do not match');
    } else {
        confirmInput.setCustomValidity('');
    }
}

async function handleRegistration(event) {
    event.preventDefault();
    
    // Get form data
    const formData = new FormData(registrationForm);
    const tenantName = formData.get('tenant_name').trim();
    const adminEmail = formData.get('admin_email').trim().toLowerCase();
    const adminPassword = formData.get('admin_password');
    const confirmPassword = formData.get('confirm_password');
    
    // Validate form data
    if (!tenantName || !adminEmail || !adminPassword || !confirmPassword) {
        showError('Please fill in all required fields');
        return;
    }
    
    if (adminPassword !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }
    
    if (adminPassword.length < 6) {
        showError('Password must be at least 6 characters long');
        return;
    }
    
    if (!isValidEmail(adminEmail)) {
        showError('Please enter a valid email address');
        return;
    }
    
    // Disable submit button
    registerBtn.disabled = true;
    registerBtn.textContent = 'Creating Account...';
    
    try {
        // Call registration API
        const response = await fetch(`${CONFIG.CONTROL_PLANE_API_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tenant_name: tenantName,
                admin_email: adminEmail,
                admin_password: adminPassword,
                tier: selectedTier
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(`Account created successfully! Your tenant ID is: ${data.tenant_id}. You can now log in to your SaaS application.`);
            
            // Redirect to SaaS app after 3 seconds
            setTimeout(() => {
                window.location.href = CONFIG.SAAS_APP_URL;
            }, 3000);
            
        } else {
            showError(data.error || 'Registration failed. Please try again.');
        }
        
    } catch (error) {
        console.error('Registration error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        // Re-enable submit button
        registerBtn.disabled = false;
        registerBtn.textContent = 'Create Account';
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showError(message) {
    hideMessages();
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showSuccess(message) {
    hideMessages();
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    successMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideMessages() {
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';
}

// Update configuration after deployment
function updateConfig(controlPlaneApiUrl, saasAppUrl) {
    CONFIG.CONTROL_PLANE_API_URL = controlPlaneApiUrl;
    CONFIG.SAAS_APP_URL = saasAppUrl;
}
