// Navigation Controller with GSAP animations
class NavigationController {
    constructor() {
        this.currentPage = 'dashboard';
        this.pages = {
            'dashboard': () => this.loadDashboardPage(),
            'tenants': () => this.loadTenantsPage(),
            'cost-analysis': () => this.loadCostAnalysisPage()
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
        
        // Load initial page
        this.navigateToPage('dashboard');
    }
    
    navigateToPage(page) {
        if (this.currentPage === page) return;
        
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
    
    loadDashboardPage() {
        const content = `
            <div class="space-y-8">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-4xl font-bold text-white mb-2">Admin Dashboard</h1>
                        <p class="text-gray-300">Platform overview and tenant management</p>
                    </div>
                </div>
                
                <!-- Quick Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Total Tenants</h3>
                        <p class="text-3xl font-bold text-white" id="total-tenants">-</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Basic Tier</h3>
                        <p class="text-3xl font-bold text-blue-400" id="basic-tenants">-</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Premium Tier</h3>
                        <p class="text-3xl font-bold text-purple-400" id="premium-tenants">-</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Monthly Revenue</h3>
                        <p class="text-3xl font-bold text-green-400" id="monthly-revenue">-</p>
                    </div>
                </div>
                
                <!-- Tenant List -->
                <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                    <h3 class="text-xl font-semibold text-white mb-4">Recent Tenants</h3>
                    <div id="tenant-list">Loading...</div>
                </div>
            </div>
        `;
        
        this.updatePageContent(content);
        // Load dashboard data
        if (window.loadTenants) {
            window.loadTenants();
        }
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
                
                <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                    <div id="tenants-container">Loading tenants...</div>
                </div>
            </div>
        `;
        
        this.updatePageContent(content);
        // Load existing tenant management functionality
        if (window.loadTenants) {
            window.loadTenants();
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

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.navigationController = new NavigationController();
});
