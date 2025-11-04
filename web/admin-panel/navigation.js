// Navigation Controller with GSAP animations
class NavigationController {
    constructor() {
        this.currentPage = 'tenants';
        this.pages = {
            'tenants': () => this.loadTenantsPage(),
            'cost-analysis': () => this.loadCostAnalysisPage(),
            'usage-insights': () => this.loadUsageInsightsPage()

        };
        
        this.init();
    }
    
    init() {
        // Add click listeners to navigation items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.getAttribute('data-page');
                if (page && this.pages[page]) {
                    this.navigateToPage(page);
                }
            });
        });
        
        // Don't load initial page here - let AdminApp control when to load it
        // this.navigateToPage('dashboard');
    }
    
    navigateToPage(page) {
        if (this.currentPage === page) return;
        
        // Check if page-content exists before proceeding
        const pageContent = document.getElementById('page-content');
        if (!pageContent) {
            console.warn('page-content element not found, deferring navigation');
            return;
        }
        
        // Update active navigation item
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active', 'bg-gray-700/50');
            if (item.getAttribute('data-page') === page) {
                item.classList.add('active', 'bg-gray-700/50');
            }
        });
        
        // Load page content
        this.currentPage = page;
        this.pages[page]();
    }
    
    loadTenantsPage() {
        const content = `
            <div class="space-y-8">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-4xl font-bold text-white mb-2">Tenant Management</h1>
                        <p class="text-gray-300">Manage platform tenants and subscriptions</p>
                    </div>
                    <button id="add-tenant-btn" class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-4 py-2 rounded-lg transition-all">
                        Add Tenant
                    </button>
                </div>
                
                <!-- Stats Section -->
                <div class="space-y-6">
                    <!-- Tenant Stats Group -->
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
                            <svg class="w-5 h-5 mr-2 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            Tenants Overview
                        </h3>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="text-center">
                                <p class="text-2xl font-bold text-white" id="total-tenants">-</p>
                                <p class="text-sm text-gray-400">Total</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold text-blue-400" id="basic-tenants">-</p>
                                <p class="text-sm text-gray-400">Basic</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold text-purple-400" id="premium-tenants">-</p>
                                <p class="text-sm text-gray-400">Premium</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold text-red-400" id="deleted-tenants">-</p>
                                <p class="text-sm text-gray-400">Deleted</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Revenue Stats -->
                    <div class="bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
                            <svg class="w-5 h-5 mr-2 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            Monthly Revenue
                        </h3>
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-3xl font-bold text-green-400" id="monthly-revenue">$0</p>
                                <p class="text-sm text-gray-400">Recurring monthly revenue from active tenants</p>
                            </div>
                            <div class="text-right text-sm text-gray-400">
                                <p>Basic: $29/month</p>
                                <p>Premium: $99/month</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                    <h3 class="text-xl font-semibold text-white mb-4">Tenants</h3>
                    <div id="tenant-list">Loading tenants...</div>
                </div>
                
                <!-- Add Tenant Modal -->
                <div id="tenant-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" style="display: none;">
                    <div class="bg-gray-800 rounded-lg p-6 w-96 max-w-md mx-4">
                        <h3 class="text-xl font-bold text-white mb-4">Add New Tenant</h3>
                        <form id="tenant-form">
                            <div class="mb-4">
                                <label for="tenant-name" class="block text-sm font-medium text-gray-300 mb-2">Company Name</label>
                                <input type="text" id="tenant-name" required class="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none text-white">
                            </div>
                            <div class="mb-4">
                                <label for="tenant-email" class="block text-sm font-medium text-gray-300 mb-2">Admin Email</label>
                                <input type="email" id="tenant-email" required class="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none text-white">
                            </div>
                            <div class="mb-4">
                                <label for="tenant-password" class="block text-sm font-medium text-gray-300 mb-2">Admin Password</label>
                                <input type="password" id="tenant-password" required class="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none text-white" placeholder="Minimum 8 characters">
                            </div>
                            <div class="mb-4">
                                <label for="tenant-tier" class="block text-sm font-medium text-gray-300 mb-2">Tier</label>
                                <select id="tenant-tier" required class="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none text-white">
                                    <option value="">Select Tier</option>
                                    <option value="basic">Basic ($29/month)</option>
                                    <option value="premium">Premium ($99/month)</option>
                                </select>
                            </div>
                            <div id="tenant-error" class="text-red-400 text-sm mb-4" style="display: none;"></div>
                            <div class="flex gap-3">
                                <button type="submit" id="save-tenant-btn" class="flex-1 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 p-3 rounded-lg transition-all text-white">
                                    Create Tenant
                                </button>
                                <button type="button" id="cancel-tenant-btn" class="flex-1 bg-gray-600 hover:bg-gray-700 p-3 rounded-lg transition-all text-white">
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                
                <!-- Tenant Details Modal -->
                <div id="tenant-details-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" style="display: none;">
                    <div class="flex items-center justify-center min-h-screen p-4">
                        <div class="bg-gray-800 rounded-lg p-6 w-96 max-w-md">
                            <h3 class="text-xl font-bold text-white mb-4">Tenant Details</h3>
                            <div id="tenant-details-content" class="space-y-3 text-gray-300">
                                <!-- Content populated by JavaScript -->
                            </div>
                            <div class="mt-6">
                                <button type="button" class="close-btn w-full bg-gray-600 hover:bg-gray-700 p-3 rounded-lg transition-all text-white">
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const pageContent = document.getElementById('page-content');
        if (!pageContent) {
            console.error('page-content element not found');
            return;
        }
        
        pageContent.innerHTML = content;
        
        // Load tenant data and stats
        if (window.AdminApp) {
            window.AdminApp.loadTenants();
            
            // Re-attach event listeners for tenant functionality
            setTimeout(() => {
                const addTenantBtn = document.getElementById('add-tenant-btn');
                const tenantForm = document.getElementById('tenant-form');
                const cancelTenantBtn = document.getElementById('cancel-tenant-btn');
                
                if (addTenantBtn) {
                    addTenantBtn.addEventListener('click', window.AdminApp.showAddTenantModal.bind(window.AdminApp));
                }
                if (tenantForm) {
                    tenantForm.addEventListener('submit', window.AdminApp.handleTenantSubmit.bind(window.AdminApp));
                }
                if (cancelTenantBtn) {
                    cancelTenantBtn.addEventListener('click', window.AdminApp.closeTenantModal.bind(window.AdminApp));
                }
                
                // Add event listeners for view and delete buttons
                document.querySelectorAll('.view-tenant-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const tenantId = e.target.getAttribute('data-tenant-id');
                        window.AdminApp.showTenantDetails(tenantId);
                    });
                });
                
                document.querySelectorAll('.delete-tenant-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const tenantId = e.target.getAttribute('data-tenant-id');
                        window.AdminApp.deleteTenant(tenantId);
                    });
                });
                
                // Add close button listener for tenant details modal
                document.querySelectorAll('.close-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const modal = e.target.closest('.modal, #tenant-details-modal');
                        if (modal) {
                            modal.style.display = 'none';
                        }
                    });
                });
            }, 100);
        }
    }
    
    loadCostAnalysisPage() {
        if (window.CostAnalysisController) {
            window.CostAnalysisController.init();
        } else {
            const content = `
                <div class="space-y-8">
                    <div class="flex items-center justify-between">
                        <div>
                            <h1 class="text-4xl font-bold text-white mb-2">Cost Analysis Dashboard</h1>
                            <p class="text-gray-300">AI-powered insights into your SaaS platform economics</p>
                        </div>
                        <button id="refresh-btn" class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-4 py-2 rounded-lg transition-all flex items-center">
                            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                            </svg>
                            Refresh Data
                        </button>
                    </div>
                    
                    <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl p-6">
                        <h3 class="text-xl font-semibold text-white mb-4 flex items-center">
                            <svg class="w-5 h-5 mr-2 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                            </svg>
                            AI-Powered Cost Analysis
                        </h3>
                        <p class="text-gray-300 mb-4">
                            The Cost Analysis feature is being deployed. Once metrics collection begins, 
                            you'll see comprehensive cost insights, tenant profitability analysis, and 
                            AI-powered recommendations here.
                        </p>
                        <div class="text-sm text-gray-400">
                            <p>• Real-time cost tracking with 90-day retention</p>
                            <p>• Tenant profitability analysis (Basic: $29/month, Premium: $99/month)</p>
                            <p>• AI-powered cost predictions and optimization recommendations</p>
                            <p>• Service breakdown: Lambda, DynamoDB, API Gateway, Bedrock AI</p>
                        </div>
                    </div>
                </div>
            `;
            
            this.updatePageContent(content);
        }
    }
    
    loadUsageInsightsPage() {
        // Don't use updatePageContent with GSAP animation - it conflicts with dashboard rendering
        const pageContent = document.getElementById('page-content');
        if (pageContent) {
            pageContent.innerHTML = '';
            pageContent.style.opacity = '1';
        }

        // Initialize usage insights dashboard immediately
        console.log('Attempting to initialize UsageInsightsDashboard...');

        if (window.UsageInsightsDashboard && typeof window.UsageInsightsDashboard.init === 'function') {
            console.log('Initializing UsageInsightsDashboard...');
            window.UsageInsightsDashboard.init();
        } else {
            console.error('UsageInsightsDashboard not available or init method missing');
            // Try again after a short delay
            setTimeout(() => {
                if (window.UsageInsightsDashboard && typeof window.UsageInsightsDashboard.init === 'function') {
                    console.log('Retrying UsageInsightsDashboard initialization...');
                    window.UsageInsightsDashboard.init();
                } else {
                    console.error('UsageInsightsDashboard still not available after retry');
                    if (pageContent) {
                        pageContent.innerHTML = '<div class="text-red-500 p-8">Error: Usage Insights Dashboard failed to load. Please refresh the page.</div>';
                    }
                }
            }, 1000);
        }
    }

    updatePageContent(content) {
        const pageContent = document.getElementById('page-content');
        
        // Fade out
        gsap.to(pageContent, {
            opacity: 0,
            duration: 0.2,
            onComplete: () => {
                pageContent.innerHTML = content;
                
                // Fade in
                gsap.to(pageContent, {
                    opacity: 1,
                    duration: 0.3
                });
            }
        });
    }
}

// Initialize navigation when DOM is loaded (but don't load initial page)
document.addEventListener('DOMContentLoaded', () => {
    window.navigationController = new NavigationController();
});

