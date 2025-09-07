// Main application entry point
// Import all modules
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    App.init();
});

// Main App object
const App = {
    // Configuration - Uses shared config generated during deployment
    config: window.APP_CONFIG || (() => {
        console.error('APP_CONFIG not found. Please ensure config.js is loaded.');
        return {};
    })(),

    // Application state
    state: {
        user: null,
        tenant: null,
        currentSection: 'products',
        cart: new Map(), // productId -> quantity
        products: [],
        orders: [],
        users: []
    },

    // Initialize the application
    init() {
        console.log('Initializing Agentic Insights SaaS App...');
        
        // Check if user is already logged in
        const token = localStorage.getItem('authToken');
        if (token && !this.isTokenExpired(token)) {
            this.showApp();
            this.loadUserInfo();
            this.initializeApp();
        } else {
            this.showLoginModal();
        }

        // Initialize event listeners
        this.initializeEventListeners();
    },

    // Initialize all event listeners
    initializeEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', Auth.handleLogin);
        
        // Logout button
        document.getElementById('logout-btn').addEventListener('click', Auth.handleLogout);
        
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.showSection(section);
            });
        });

        // Modal close buttons
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                modal.style.display = 'none';
            });
        });

        // Product management
        document.getElementById('add-product-btn').addEventListener('click', ProductManager.showAddProductModal.bind(ProductManager));
        document.getElementById('product-form').addEventListener('submit', ProductManager.handleProductSubmit.bind(ProductManager));
        document.getElementById('cancel-product-btn').addEventListener('click', ProductManager.closeProductModal.bind(ProductManager));

        // User management
        document.getElementById('add-user-btn').addEventListener('click', UserManager.showAddUserModal);
        document.getElementById('user-form').addEventListener('submit', UserManager.handleUserSubmit);
        document.getElementById('cancel-user-btn').addEventListener('click', UserManager.closeUserModal);

        // Cart actions
        document.getElementById('create-order-btn').addEventListener('click', OrderManager.createOrder);
        document.getElementById('clear-cart-btn').addEventListener('click', CartManager.clearCart);

        // Product details modal
        document.getElementById('close-product-details').addEventListener('click', () => {
            document.getElementById('product-details-modal').style.display = 'none';
        });
    },

    // Show login modal
    showLoginModal() {
        document.getElementById('login-modal').style.display = 'block';
        document.getElementById('app').style.display = 'none';
    },

    // Show main app
    showApp() {
        document.getElementById('login-modal').style.display = 'none';
        document.getElementById('app').style.display = 'block';
    },

    // Initialize app after login
    initializeApp() {
        this.showSection('products');
        this.loadData();
    },

    // Load all necessary data
    async loadData() {
        await Promise.all([
            ProductManager.loadProducts(),
            OrderManager.loadOrders(),
            this.state.user.role === 'tenant_admin' ? UserManager.loadUsers() : Promise.resolve()
        ]);
    },

    // Load user information from token
    loadUserInfo() {
        const token = localStorage.getItem('authToken');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                this.state.user = {
                    email: payload.email,
                    role: payload['custom:role'] || 'tenant_user',
                    tenant_id: payload['custom:tenant_id']
                };
                this.state.tenant = {
                    id: payload['custom:tenant_id'],
                    tier: payload['custom:tier']
                };

                // Update UI
                document.getElementById('current-user-email').textContent = this.state.user.email;
                
                // Show/hide admin features
                if (this.state.user.role === 'tenant_admin') {
                    document.getElementById('add-product-btn').style.display = 'block';
                    document.getElementById('users-nav').style.display = 'block';
                } else {
                    document.getElementById('add-product-btn').style.display = 'none';
                    document.getElementById('users-nav').style.display = 'none';
                }

            } catch (error) {
                console.error('Error parsing token:', error);
                Auth.handleLogout();
            }
        }
    },

    // Check if token is expired
    isTokenExpired(token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return Date.now() >= payload.exp * 1000;
        } catch {
            return true;
        }
    },

    // Show specific section
    showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        // Update content sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`${sectionName}-section`).classList.add('active');

        this.state.currentSection = sectionName;

        // Load section-specific data if needed
        switch (sectionName) {
            case 'products':
                ProductManager.loadProducts();
                break;
            case 'orders':
                OrderManager.loadOrders();
                break;
            case 'users':
                if (this.state.user.role === 'tenant_admin') {
                    UserManager.loadUsers();
                }
                break;
        }
    },

    // Update configuration after deployment
    updateConfig(appPlaneApiUrl, controlPlaneApiUrl) {
        this.config.APP_PLANE_API_URL = appPlaneApiUrl;
        this.config.CONTROL_PLANE_API_URL = controlPlaneApiUrl;
    }
};
