// Admin Panel Application
const AdminApp = {
    // Configuration - Uses shared config generated during deployment
    config: window.APP_CONFIG || (() => {
        console.error('APP_CONFIG not found. Please ensure config.js is loaded.');
        return {};
    })(),

    // Application state
    state: {
        admin: null,
        tenants: []
    },

    // Initialize the application
    init() {
        console.log('Initializing Admin Panel...');
        
        // Check if admin is already logged in
        const token = localStorage.getItem('adminToken');
        if (token && !this.isTokenExpired(token)) {
            this.showApp();
            this.loadAdminInfo();
            
            // Load tenant page content directly
            this.loadTenantPageDirectly();
        } else {
            this.showLoginModal();
        }

        // Initialize event listeners
        this.initializeEventListeners();
    },

    // Initialize all event listeners
    initializeEventListeners() {
        // Login form
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', this.handleLogin.bind(this));
        }
        
        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', this.handleLogout.bind(this));
        }
        
        // Add tenant button
        const addTenantBtn = document.getElementById('add-tenant-btn');
        if (addTenantBtn) {
            addTenantBtn.addEventListener('click', this.showAddTenantModal.bind(this));
        }
        
        // Tenant form
        const tenantForm = document.getElementById('tenant-form');
        if (tenantForm) {
            tenantForm.addEventListener('submit', this.handleTenantSubmit.bind(this));
        }
        
        // Cancel tenant button
        const cancelTenantBtn = document.getElementById('cancel-tenant-btn');
        if (cancelTenantBtn) {
            cancelTenantBtn.addEventListener('click', this.closeTenantModal.bind(this));
        }
        
        // Modal close buttons
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            });
        });
    },

    // Handle admin login
    async handleLogin(event) {
        event.preventDefault();
        
        const email = document.getElementById('admin-email').value.trim();
        const password = document.getElementById('admin-password').value;
        const errorDiv = document.getElementById('login-error');
        const loginBtn = document.querySelector('#login-form button[type="submit"]');
        
        if (!email || !password) {
            this.showLoginError('Please enter both email and password');
            return;
        }
        
        loginBtn.disabled = true;
        loginBtn.textContent = 'Logging in...';
        
        try {
            const response = await fetch(`${this.config.CONTROL_PLANE_API_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Store tokens
                localStorage.setItem('adminToken', data.tokens.id_token);
                localStorage.setItem('adminAccessToken', data.tokens.access_token);
                localStorage.setItem('adminRefreshToken', data.tokens.refresh_token);
                
                // Clear form
                document.getElementById('login-form').reset();
                errorDiv.style.display = 'none';
                
                // Show app and initialize
                this.showApp();
                this.loadAdminInfo();
                
                // Load tenant page content directly
                this.loadTenantPageDirectly();
                
            } else {
                const errorData = await response.json();
                this.showLoginError(errorData.error || 'Login failed');
            }
            
        } catch (error) {
            console.error('Login error:', error);
            this.showLoginError('Network error. Please try again.');
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }
    },

    // Show login error
    showLoginError(message) {
        const errorDiv = document.getElementById('login-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    },

    // Handle logout
    handleLogout() {
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminAccessToken');
        localStorage.removeItem('adminRefreshToken');
        
        this.state.admin = null;
        this.state.tenants = [];
        
        this.showLoginModal();
    },

    // Show login modal
    showLoginModal() {
        document.getElementById('login-modal').style.display = 'block';
        document.getElementById('admin-dashboard').style.display = 'none';
    },

    // Show main app
    showApp() {
        document.getElementById('login-modal').style.display = 'none';
        document.getElementById('admin-dashboard').style.display = 'block';
    },

    // Load admin information
    loadAdminInfo() {
        const token = localStorage.getItem('adminToken');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                this.state.admin = {
                    email: payload.email
                };
                
                const adminEmailDisplay = document.getElementById('admin-email-display');
                if (adminEmailDisplay) {
                    adminEmailDisplay.textContent = this.state.admin.email;
                }
            } catch (error) {
                console.error('Error parsing admin token:', error);
                this.handleLogout();
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

    // Load dashboard data
    async loadDashboard() {
        await this.loadTenants();
        this.updateDashboardStats();
    },

    // Load tenants page with retry mechanism
    loadTenantsPageWithRetry(attempts = 0) {
        const pageContent = document.getElementById('page-content');
        if (!pageContent && attempts < 10) {
            setTimeout(() => this.loadTenantsPageWithRetry(attempts + 1), 100);
            return;
        }
        
        if (pageContent && window.navigationController) {
            window.navigationController.navigateToPage('tenants');
        } else {
            console.error('Failed to load tenants page - DOM not ready');
        }
    },

    // Load tenant page content directly
    loadTenantPageDirectly() {
        const pageContent = document.getElementById('page-content');
        if (!pageContent) return;
        
        // Set active nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active', 'bg-gray-700/50');
            if (item.getAttribute('data-page') === 'tenants') {
                item.classList.add('active', 'bg-gray-700/50');
            }
        });
        
        // Load content directly from navigation controller
        if (!window.navigationController) {
            window.navigationController = new NavigationController();
        }
        window.navigationController.loadTenantsPage();
    },

    // Load tenants
    async loadTenants() {
        const tenantList = document.getElementById('tenant-list');
        if (!tenantList) return;
        
        tenantList.innerHTML = '<div class="loading">Loading tenants...</div>';
        
        try {
            const response = await this.makeAuthenticatedRequest(`${this.config.CONTROL_PLANE_API_URL}/tenants`);
            
            if (response.ok) {
                const data = await response.json();
                this.state.tenants = data.tenants || [];
                this.renderTenants();
                this.updateDashboardStats(); // Update stats after tenants are loaded
            } else {
                throw new Error('Failed to load tenants');
            }
            
        } catch (error) {
            console.error('Error loading tenants:', error);
            tenantList.innerHTML = '<div class="empty-state">Failed to load tenants</div>';
        }
    },

    // Render tenants
    renderTenants() {
        const tenantList = document.getElementById('tenant-list');
        
        if (this.state.tenants.length === 0) {
            tenantList.innerHTML = `
                <div class="empty-state">
                    <h3>No tenants yet</h3>
                    <p>Start by adding your first tenant to the platform</p>
                </div>
            `;
            return;
        }
        
        // Filter out deleted tenants from the display
        const activeTenants = this.state.tenants.filter(tenant => tenant.status !== 'deleted');
        
        tenantList.innerHTML = activeTenants.map(tenant => `
            <div class="tenant-card">
                <div class="tenant-info">
                    <h4>${tenant.tenant_name}</h4>
                    <p><strong>Email:</strong> ${tenant.admin_email}</p>
                    <p><strong>ID:</strong> ${tenant.tenant_id}</p>
                    <p><strong>Created:</strong> ${new Date(tenant.created_at).toLocaleDateString()}</p>
                    <div style="margin-top: 0.5rem;">
                        <span class="tenant-tier ${tenant.tier}">${tenant.tier}</span>
                        <span class="tenant-status ${tenant.status}">${tenant.status}</span>
                    </div>
                </div>
                <div class="tenant-actions">
                    <button class="btn btn-sm btn-secondary view-tenant-btn" data-tenant-id="${tenant.tenant_id}">View</button>
                    <button class="btn btn-sm btn-danger delete-tenant-btn" data-tenant-id="${tenant.tenant_id}">Delete</button>
                </div>
            </div>
        `).join('');
        
        // Add event listeners
        this.addTenantEventListeners();
    },

    // Add event listeners to tenant cards
    addTenantEventListeners() {
        document.querySelectorAll('.view-tenant-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tenantId = e.target.getAttribute('data-tenant-id');
                this.showTenantDetails(tenantId);
            });
        });
        
        document.querySelectorAll('.delete-tenant-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tenantId = e.target.getAttribute('data-tenant-id');
                this.deleteTenant(tenantId);
            });
        });
    },

    // Update dashboard stats
    updateDashboardStats() {
        // Filter out deleted tenants for most statistics
        const activeAndProvisioningTenants = this.state.tenants.filter(t => t.status !== 'deleted');
        
        const totalTenants = activeAndProvisioningTenants.length;
        const basicTenants = activeAndProvisioningTenants.filter(t => t.tier === 'basic').length;
        const premiumTenants = activeAndProvisioningTenants.filter(t => t.tier === 'premium').length;
        const activeTenants = this.state.tenants.filter(t => t.status === 'active').length;
        const deletedTenants = this.state.tenants.filter(t => t.status === 'deleted').length;
        const monthlyRevenue = (basicTenants * 29) + (premiumTenants * 99);
        
        const totalTenantsEl = document.getElementById('total-tenants');
        const basicTenantsEl = document.getElementById('basic-tenants');
        const premiumTenantsEl = document.getElementById('premium-tenants');
        const activeTenantsEl = document.getElementById('active-tenants');
        const deletedTenantsEl = document.getElementById('deleted-tenants');
        const monthlyRevenueEl = document.getElementById('monthly-revenue');
        
        if (totalTenantsEl) totalTenantsEl.textContent = totalTenants;
        if (basicTenantsEl) basicTenantsEl.textContent = basicTenants;
        if (premiumTenantsEl) premiumTenantsEl.textContent = premiumTenants;
        if (activeTenantsEl) activeTenantsEl.textContent = activeTenants;
        if (deletedTenantsEl) deletedTenantsEl.textContent = deletedTenants;
        if (monthlyRevenueEl) monthlyRevenueEl.textContent = `$${monthlyRevenue}`;
    },

    // Show add tenant modal
    showAddTenantModal() {
        const tenantForm = document.getElementById('tenant-form');
        const tenantModal = document.getElementById('tenant-modal');
        
        if (tenantForm) {
            tenantForm.reset();
        }
        if (tenantModal) {
            tenantModal.style.display = 'flex';
        }
    },

    // Close tenant modal
    closeTenantModal() {
        document.getElementById('tenant-modal').style.display = 'none';
        document.getElementById('tenant-error').style.display = 'none';
    },

    // Handle tenant form submission
    async handleTenantSubmit(event) {
        event.preventDefault();
        
        const formData = {
            tenant_name: document.getElementById('tenant-name').value.trim(),
            admin_email: document.getElementById('tenant-email').value.trim(),
            tier: document.getElementById('tenant-tier').value
        };
        
        // Validate
        if (!formData.tenant_name || !formData.admin_email || !formData.tier) {
            this.showTenantError('Please fill in all required fields');
            return;
        }
        
        const saveBtn = document.getElementById('save-tenant-btn');
        saveBtn.disabled = true;
        saveBtn.textContent = 'Creating...';
        
        try {
            const response = await this.makeAuthenticatedRequest(`${this.config.CONTROL_PLANE_API_URL}/tenants`, {
                method: 'POST',
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                this.closeTenantModal();
                await this.loadDashboard();
            } else {
                const errorData = await response.json();
                this.showTenantError(errorData.error || 'Failed to create tenant');
            }
            
        } catch (error) {
            console.error('Create tenant error:', error);
            this.showTenantError('Network error. Please try again.');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Create Tenant';
        }
    },

    // Show tenant error
    showTenantError(message) {
        const errorDiv = document.getElementById('tenant-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    },

    // Show tenant details
    showTenantDetails(tenantId) {
        const tenant = this.state.tenants.find(t => t.tenant_id === tenantId);
        if (!tenant) return;
        
        const modal = document.getElementById('tenant-details-modal');
        const content = document.getElementById('tenant-details-content');
        
        content.innerHTML = `
            <div class="detail-row">
                <span class="detail-label">Company Name:</span>
                <span class="detail-value">${tenant.tenant_name}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Admin Email:</span>
                <span class="detail-value">${tenant.admin_email}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Tenant ID:</span>
                <span class="detail-value">${tenant.tenant_id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Tier:</span>
                <span class="detail-value">
                    <span class="tenant-tier ${tenant.tier}">${tenant.tier}</span>
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">
                    <span class="tenant-status ${tenant.status}">${tenant.status}</span>
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Created:</span>
                <span class="detail-value">${new Date(tenant.created_at).toLocaleString()}</span>
            </div>
            ${tenant.order_table_name ? `
                <div class="detail-row">
                    <span class="detail-label">Order Table:</span>
                    <span class="detail-value">${tenant.order_table_name}</span>
                </div>
            ` : ''}
        `;
        
        modal.style.display = 'block';
    },

    // Delete tenant
    async deleteTenant(tenantId) {
        const tenant = this.state.tenants.find(t => t.tenant_id === tenantId);
        if (!tenant) return;
        
        // Show custom confirmation modal
        const confirmed = await this.showDeleteConfirmation(tenant.tenant_name);
        if (!confirmed) return;
        
        try {
            const response = await this.makeAuthenticatedRequest(
                `${this.config.CONTROL_PLANE_API_URL}/tenants/${tenantId}`,
                { method: 'DELETE' }
            );
            
            if (response.ok) {
                await this.loadDashboard();
            } else {
                const errorData = await response.json();
                alert(errorData.error || 'Failed to delete tenant');
            }
            
        } catch (error) {
            console.error('Delete tenant error:', error);
            alert('Network error. Please try again.');
        }
    },

    // Show custom delete confirmation modal
    showDeleteConfirmation(tenantName) {
        return new Promise((resolve) => {
            // Create modal HTML
            const modalHtml = `
                <div id="delete-confirmation-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div class="bg-gray-800 rounded-lg p-6 max-w-md mx-4 border border-gray-700">
                        <div class="flex items-center mb-4">
                            <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mr-4">
                                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                                </svg>
                            </div>
                            <h3 class="text-lg font-semibold text-white">Delete Tenant</h3>
                        </div>
                        <p class="text-gray-300 mb-6">
                            Are you sure you want to delete tenant <strong class="text-white">"${tenantName}"</strong>? This action cannot be undone.
                        </p>
                        <div class="flex justify-end space-x-3">
                            <button id="cancel-delete" class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors">
                                Cancel
                            </button>
                            <button id="confirm-delete" class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
                                Delete Tenant
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to DOM
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            const modal = document.getElementById('delete-confirmation-modal');
            const cancelBtn = document.getElementById('cancel-delete');
            const confirmBtn = document.getElementById('confirm-delete');
            
            // Handle cancel
            const handleCancel = () => {
                modal.remove();
                resolve(false);
            };
            
            // Handle confirm
            const handleConfirm = () => {
                modal.remove();
                resolve(true);
            };
            
            // Add event listeners
            cancelBtn.addEventListener('click', handleCancel);
            confirmBtn.addEventListener('click', handleConfirm);
            
            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    handleCancel();
                }
            });
            
            // Close on Escape key
            const handleKeydown = (e) => {
                if (e.key === 'Escape') {
                    handleCancel();
                    document.removeEventListener('keydown', handleKeydown);
                }
            };
            document.addEventListener('keydown', handleKeydown);
        });
    },

    // Make authenticated API request
    async makeAuthenticatedRequest(url, options = {}) {
        const token = localStorage.getItem('adminToken');
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
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
                this.handleLogout();
                throw new Error('Session expired. Please log in again.');
            }
            
            return response;
            
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    },

    // Update configuration after deployment
    updateConfig(controlPlaneApiUrl) {
        this.config.CONTROL_PLANE_API_URL = controlPlaneApiUrl;
    }
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.AdminApp = AdminApp; // Expose AdminApp globally
    AdminApp.init();
});
