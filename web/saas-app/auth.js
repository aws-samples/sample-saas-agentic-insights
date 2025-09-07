// Authentication module
const Auth = {
    // Handle login form submission
    async handleLogin(event) {
        event.preventDefault();
        
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const errorDiv = document.getElementById('login-error');
        const loginBtn = document.querySelector('#login-form button[type="submit"]');
        
        // Validate input
        if (!email || !password) {
            Auth.showLoginError('Please enter both email and password');
            return;
        }
        
        // Disable login button
        loginBtn.disabled = true;
        loginBtn.textContent = 'Logging in...';
        
        try {
            // Determine which user pool to use based on email domain or other logic
            // For now, we'll try both tiers (this could be optimized)
            const response = await Auth.attemptLogin(email, password);
            
            if (response.ok) {
                const data = await response.json();
                
                // Store tokens
                localStorage.setItem('authToken', data.tokens.id_token);
                localStorage.setItem('accessToken', data.tokens.access_token);
                localStorage.setItem('refreshToken', data.tokens.refresh_token);
                
                // Clear form
                document.getElementById('login-form').reset();
                errorDiv.style.display = 'none';
                
                // Show app and initialize
                App.showApp();
                App.loadUserInfo();
                App.initializeApp();
                
            } else {
                const errorData = await response.json();
                Auth.showLoginError(errorData.error || 'Login failed');
            }
            
        } catch (error) {
            console.error('Login error:', error);
            Auth.showLoginError('Network error. Please try again.');
        } finally {
            // Re-enable login button
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }
    },

    // Attempt login with the control plane API
    async attemptLogin(email, password) {
        return fetch(`${App.config.CONTROL_PLANE_API_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });
    },

    // Show login error message
    showLoginError(message) {
        const errorDiv = document.getElementById('login-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    },

    // Handle logout
    handleLogout() {
        // Clear stored tokens
        localStorage.removeItem('authToken');
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        
        // Clear app state
        App.state.user = null;
        App.state.tenant = null;
        App.state.cart.clear();
        App.state.products = [];
        App.state.orders = [];
        App.state.users = [];
        
        // Show login modal
        App.showLoginModal();
    },

    // Get authorization headers for API calls
    getAuthHeaders() {
        const token = localStorage.getItem('authToken');
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
            if (App.state.tenant) {
                headers['tenant-id'] = App.state.tenant.id;
                headers['tier-name'] = App.state.tenant.tier;
            }
        }
        
        return headers;
    },

    // Make authenticated API call
    async makeAuthenticatedRequest(url, options = {}) {
        const headers = Auth.getAuthHeaders();
        
        const requestOptions = {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        };
        
        try {
            const response = await fetch(url, requestOptions);
            
            // Handle token expiration
            if (response.status === 401) {
                Auth.handleLogout();
                throw new Error('Session expired. Please log in again.');
            }
            
            return response;
            
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    }
};
