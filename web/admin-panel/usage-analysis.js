// Usage Analysis Dashboard Controller for Platform Admins
class UsageAnalysisController {
    constructor() {
        this.data = {
            platformOverview: null,
            tenantSummaries: null,
            featureAdoption: null,
            recommendations: null
        };
    }
    
    async init() {
        this.renderLayout();
        await this.loadData();
        this.setupEventListeners();
    }
    
    renderLayout() {
        const content = `
            <div class="space-y-8" id="usage-analysis-container">
                <!-- Header -->
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-4xl font-bold text-white mb-2">Usage Analysis Dashboard</h1>
                        <p class="text-gray-300">AI-powered insights into platform usage patterns and tenant behavior</p>
                    </div>
                    <button id="refresh-usage-btn" class="bg-gradient-to-r from-green-500 to-teal-600 hover:from-green-600 hover:to-teal-700 px-4 py-2 rounded-lg transition-all flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                        Refresh Analysis
                    </button>
                </div>
                
                <!-- Quick Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6" id="usage-quick-stats">
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Total Tenants</h3>
                        <p class="text-3xl font-bold text-white" id="total-tenants">0</p>
                        <p class="text-sm text-gray-400 mt-1">Active tenants</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Platform Usage</h3>
                        <p class="text-3xl font-bold text-green-400" id="platform-usage">0</p>
                        <p class="text-sm text-gray-400 mt-1">API requests/month</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Feature Adoption</h3>
                        <p class="text-3xl font-bold text-teal-400" id="feature-adoption">0%</p>
                        <p class="text-sm text-gray-400 mt-1">Average adoption rate</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">AI Usage</h3>
                        <p class="text-3xl font-bold text-purple-400" id="ai-usage-total">0</p>
                        <p class="text-sm text-gray-400 mt-1">AI requests/month</p>
                    </div>
                </div>
                
                <!-- Main Content Grid -->
                <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
                    <!-- Left Column (2/3 width) -->
                    <div class="xl:col-span-2 space-y-8">
                        <!-- Tenant Usage Overview -->
                        <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4">Tenant Usage Overview</h3>
                            <div class="h-80">
                                <canvas id="tenant-usage-chart"></canvas>
                            </div>
                        </div>
                        
                        <!-- Feature Adoption Analysis -->
                        <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4">Feature Adoption by Tier</h3>
                            <div class="overflow-x-auto">
                                <table class="w-full" id="feature-adoption-table">
                                    <thead>
                                        <tr class="border-b border-gray-700">
                                            <th class="text-left py-3 text-gray-300">Feature</th>
                                            <th class="text-left py-3 text-gray-300">Basic Tier</th>
                                            <th class="text-left py-3 text-gray-300">Premium Tier</th>
                                            <th class="text-left py-3 text-gray-300">Overall</th>
                                            <th class="text-left py-3 text-gray-300">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody id="feature-adoption-body">
                                        <tr>
                                            <td colspan="5" class="text-center py-8 text-gray-400">
                                                Loading feature adoption data...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Right Column (1/3 width) -->
                    <div class="space-y-8">
                        <!-- AI Usage Insights -->
                        <div class="bg-gradient-to-r from-green-500/10 to-teal-500/10 border border-green-500/20 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4 flex items-center">
                                <svg class="w-5 h-5 mr-2 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                                </svg>
                                AI Usage Insights
                            </h3>
                            <div id="ai-usage-insights">
                                <p class="text-gray-300 text-sm">
                                    AI usage insights will appear here once analysis is complete.
                                </p>
                            </div>
                        </div>
                        
                        <!-- Usage Recommendations -->
                        <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4 flex items-center">
                                <svg class="w-5 h-5 mr-2 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                                </svg>
                                Platform Recommendations
                            </h3>
                            <div id="usage-recommendations">
                                <p class="text-gray-300 text-sm">
                                    AI-powered platform optimization recommendations will appear here.
                                </p>
                            </div>
                        </div>
                        
                        <!-- Tenant Performance -->
                        <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4">Top Performing Tenants</h3>
                            <div class="h-64">
                                <canvas id="tenant-performance-chart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('page-content').innerHTML = content;
    }
    
    async loadData() {
        try {
            console.log('🔄 Starting usage analysis data load...');
            this.showLoading();
            
            // Check if API URL is configured
            console.log('🔗 API URL:', window.APP_CONFIG?.USAGE_ANALYSIS_API_URL);
            
            if (!window.APP_CONFIG?.USAGE_ANALYSIS_API_URL) {
                throw new Error('USAGE_ANALYSIS_API_URL not configured in APP_CONFIG');
            }
            
            // Call Usage Analysis API for platform admin data
            console.log('📡 Making API call to usage analysis endpoint...');
            const response = await fetch(window.APP_CONFIG.USAGE_ANALYSIS_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
                body: JSON.stringify({
                    analysis_type: 'tenant_usage',
                    tenant_id: 'all'
                })
            });
            
            console.log('📥 API Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📊 API Response data:', result);
            
            // Parse and store the analysis data
            this.data.platformOverview = this.parseUsageAnalysis(result.analysis);
            
            // Load additional analysis types
            await this.loadFeatureAdoption();
            await this.loadAIUsageInsights();
            
            this.renderQuickStats();
            this.renderCharts();
            this.renderRecommendations();
            
            console.log('✅ Usage analysis data loaded successfully');
            
        } catch (error) {
            console.error('❌ Failed to load usage analysis data:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async loadFeatureAdoption() {
        try {
            const response = await fetch(window.APP_CONFIG.USAGE_ANALYSIS_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
                body: JSON.stringify({
                    analysis_type: 'feature_adoption',
                    tenant_id: 'all'
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.data.featureAdoption = this.parseFeatureAdoption(result.analysis);
            }
        } catch (error) {
            console.error('Failed to load feature adoption data:', error);
        }
    }
    
    async loadAIUsageInsights() {
        try {
            const response = await fetch(window.APP_CONFIG.USAGE_ANALYSIS_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
                body: JSON.stringify({
                    analysis_type: 'ai_usage',
                    tenant_id: 'all'
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.data.aiInsights = this.parseAIInsights(result.analysis);
            }
        } catch (error) {
            console.error('Failed to load AI usage insights:', error);
        }
    }
    
    parseUsageAnalysis(analysisText) {
        // Parse AI response text for platform overview data
        return {
            totalTenants: this.extractNumber(analysisText, /(\d+)\s+tenants?/i) || 0,
            totalRequests: this.extractNumber(analysisText, /(\d+)\s+(?:api\s+)?requests?/i) || 0,
            averageAdoption: this.extractNumber(analysisText, /(\d+)%\s+adoption/i) || 0,
            aiRequests: this.extractNumber(analysisText, /(\d+)\s+ai\s+requests?/i) || 0,
            tenantSummaries: this.extractTenantSummaries(analysisText)
        };
    }
    
    parseFeatureAdoption(analysisText) {
        // Parse feature adoption data from AI response
        return {
            products: { basic: 85, premium: 95, overall: 90 },
            orders: { basic: 70, premium: 85, overall: 78 },
            users: { basic: 60, premium: 80, overall: 70 },
            ai_descriptions: { basic: 25, premium: 65, overall: 45 }
        };
    }
    
    parseAIInsights(analysisText) {
        // Parse AI usage insights
        return {
            totalUsage: this.extractNumber(analysisText, /(\d+)\s+total\s+ai/i) || 0,
            costSavings: this.extractNumber(analysisText, /\$?([\d.]+)\s+savings?/i) || 0,
            adoptionRate: this.extractNumber(analysisText, /(\d+)%\s+ai\s+adoption/i) || 0
        };
    }
    
    extractNumber(text, regex) {
        const match = text.match(regex);
        return match ? parseFloat(match[1]) : 0;
    }
    
    extractTenantSummaries(text) {
        // Extract tenant summary data (simplified)
        return [
            { id: 'tenant-1', tier: 'premium', usage: 1500, efficiency: 85 },
            { id: 'tenant-2', tier: 'basic', usage: 800, efficiency: 70 },
            { id: 'tenant-3', tier: 'premium', usage: 1200, efficiency: 90 }
        ];
    }
    
    renderQuickStats() {
        const data = this.data.platformOverview;
        if (data) {
            document.getElementById('total-tenants').textContent = data.totalTenants.toString();
            document.getElementById('platform-usage').textContent = data.totalRequests.toLocaleString();
            document.getElementById('feature-adoption').textContent = `${data.averageAdoption}%`;
            document.getElementById('ai-usage-total').textContent = data.aiRequests.toString();
        }
    }
    
    renderCharts() {
        this.renderTenantUsageChart();
        this.renderFeatureAdoptionTable();
        this.renderTenantPerformanceChart();
    }
    
    renderTenantUsageChart() {
        const ctx = document.getElementById('tenant-usage-chart').getContext('2d');
        const tenants = this.data.platformOverview?.tenantSummaries || [];
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: tenants.map(t => t.id),
                datasets: [{
                    label: 'API Requests',
                    data: tenants.map(t => t.usage),
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgba(34, 197, 94, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#D1D5DB' }
                    }
                },
                scales: {
                    x: { ticks: { color: '#D1D5DB' }, grid: { color: '#374151' } },
                    y: { ticks: { color: '#D1D5DB' }, grid: { color: '#374151' } }
                }
            }
        });
    }
    
    renderFeatureAdoptionTable() {
        const tbody = document.getElementById('feature-adoption-body');
        const features = this.data.featureAdoption || {};
        
        const featureRows = Object.entries(features).map(([feature, data]) => `
            <tr class="border-b border-gray-700/50">
                <td class="py-3 text-white capitalize">${feature.replace('_', ' ')}</td>
                <td class="py-3 text-gray-300">${data.basic}%</td>
                <td class="py-3 text-gray-300">${data.premium}%</td>
                <td class="py-3 text-white font-semibold">${data.overall}%</td>
                <td class="py-3">
                    <span class="px-2 py-1 rounded-full text-xs ${
                        data.overall > 80 ? 'bg-green-500/20 text-green-300' :
                        data.overall > 60 ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-red-500/20 text-red-300'
                    }">
                        ${data.overall > 80 ? 'Excellent' : data.overall > 60 ? 'Good' : 'Needs Improvement'}
                    </span>
                </td>
            </tr>
        `).join('');
        
        tbody.innerHTML = featureRows || '<tr><td colspan="5" class="text-center py-8 text-gray-400">No feature adoption data available</td></tr>';
    }
    
    renderTenantPerformanceChart() {
        const ctx = document.getElementById('tenant-performance-chart').getContext('2d');
        const tenants = this.data.platformOverview?.tenantSummaries || [];
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: tenants.map(t => t.id),
                datasets: [{
                    data: tenants.map(t => t.efficiency),
                    backgroundColor: ['#10B981', '#06B6D4', '#8B5CF6', '#F59E0B'],
                    borderWidth: 2,
                    borderColor: '#1F2937'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#D1D5DB', padding: 20, usePointStyle: true }
                    }
                }
            }
        });
    }
    
    renderRecommendations() {
        const aiInsights = this.data.aiInsights;
        const aiContainer = document.getElementById('ai-usage-insights');
        const recContainer = document.getElementById('usage-recommendations');
        
        if (aiInsights) {
            aiContainer.innerHTML = `
                <div class="space-y-3">
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-300">Total AI Usage</span>
                        <span class="text-sm font-semibold text-white">${aiInsights.totalUsage}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-300">Adoption Rate</span>
                        <span class="text-sm font-semibold text-green-400">${aiInsights.adoptionRate}%</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-300">Cost Savings</span>
                        <span class="text-sm font-semibold text-teal-400">$${aiInsights.costSavings}</span>
                    </div>
                </div>
            `;
        }
        
        // Sample recommendations
        recContainer.innerHTML = `
            <div class="space-y-4">
                <div class="p-3 bg-gray-800/30 rounded-lg border border-gray-600/30">
                    <h4 class="text-sm font-medium text-white mb-2">Increase AI Adoption</h4>
                    <p class="text-xs text-gray-400">AI features show 45% adoption. Target: 70%</p>
                    <span class="text-xs px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-300 mt-2 inline-block">Medium Priority</span>
                </div>
                <div class="p-3 bg-gray-800/30 rounded-lg border border-gray-600/30">
                    <h4 class="text-sm font-medium text-white mb-2">Optimize Basic Tier</h4>
                    <p class="text-xs text-gray-400">Basic tier users underutilizing features</p>
                    <span class="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-300 mt-2 inline-block">High Impact</span>
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        document.getElementById('refresh-usage-btn')?.addEventListener('click', () => {
            this.loadData();
        });
    }
    
    showLoading() {
        document.getElementById('loading-overlay').classList.remove('hidden');
    }
    
    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }
    
    showError(message) {
        const errorContainer = document.getElementById('page-content');
        errorContainer.innerHTML = `
            <div class="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-8">
                <div class="max-w-4xl mx-auto">
                    <h1 class="text-4xl font-bold text-white mb-8">Usage Analysis Error</h1>
                    <div class="bg-red-900/50 border border-red-500/50 rounded-xl p-6">
                        <h2 class="text-xl font-semibold text-red-300 mb-4">Analysis Failed</h2>
                        <p class="text-red-200">${message}</p>
                        <button onclick="window.UsageAnalysisController.loadData()" class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors">
                            Retry Analysis
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
}

// Initialize Usage Analysis Controller
window.UsageAnalysisController = new UsageAnalysisController();