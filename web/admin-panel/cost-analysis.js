// Cost Analysis Dashboard Controller
class CostAnalysisController {
    constructor() {
        this.data = {
            overview: null,
            tenants: null,
            predictions: null
        };
    }
    
    async init() {
        this.renderLayout();
        await this.loadData();
        this.setupEventListeners();
    }
    
    renderLayout() {
        const content = `
            <div class="space-y-8" id="cost-analysis-container">
                <!-- Header -->
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
                
                <!-- Quick Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6" id="quick-stats">
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Total Platform Cost</h3>
                        <p class="text-3xl font-bold text-white" id="total-cost">$0.00</p>
                        <p class="text-sm text-gray-400 mt-1">This month</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Average Cost/Tenant</h3>
                        <p class="text-3xl font-bold text-blue-400" id="avg-cost">$0.00</p>
                        <p class="text-sm text-gray-400 mt-1">Per month</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">Platform Margin</h3>
                        <p class="text-3xl font-bold text-green-400" id="platform-margin">0%</p>
                        <p class="text-sm text-gray-400 mt-1">Profit margin</p>
                    </div>
                    <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-gray-300 mb-2">AI Usage</h3>
                        <p class="text-3xl font-bold text-purple-400" id="ai-usage">0</p>
                        <p class="text-sm text-gray-400 mt-1">Bedrock calls</p>
                    </div>
                </div>
                
                <!-- Main Content Grid -->
                <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
                    <!-- Left Column (2/3 width) -->
                    <div class="xl:col-span-2 space-y-8">
                        <!-- Service Breakdown -->
                        <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4">Service Cost Breakdown</h3>
                            <div class="h-80">
                                <canvas id="service-breakdown-chart"></canvas>
                            </div>
                        </div>
                        
                        <!-- Tenant Analysis -->
                        <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4">Tenant Cost Ranking</h3>
                            <div class="overflow-x-auto">
                                <table class="w-full" id="tenant-ranking-table">
                                    <thead>
                                        <tr class="border-b border-gray-700">
                                            <th class="text-left py-3 text-gray-300">Tenant ID</th>
                                            <th class="text-left py-3 text-gray-300">Tier</th>
                                            <th class="text-left py-3 text-gray-300">Cost</th>
                                            <th class="text-left py-3 text-gray-300">Revenue</th>
                                            <th class="text-left py-3 text-gray-300">Margin</th>
                                            <th class="text-left py-3 text-gray-300">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody id="tenant-ranking-body">
                                        <tr>
                                            <td colspan="6" class="text-center py-8 text-gray-400">
                                                No metrics data available yet. Start using the platform to see cost analysis.
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Right Column (1/3 width) -->
                    <div class="space-y-8">
                        <!-- AI Recommendations -->
                        <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4 flex items-center">
                                <svg class="w-5 h-5 mr-2 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                                </svg>
                                AI Recommendations
                            </h3>
                            <div id="ai-recommendations">
                                <p class="text-gray-300 text-sm">
                                    AI-powered cost optimization recommendations will appear here once sufficient metrics data is collected.
                                </p>
                            </div>
                        </div>
                        
                        <!-- Cost Forecast -->
                        <div class="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6">
                            <h3 class="text-xl font-semibold text-white mb-4">3-Month Forecast</h3>
                            <div class="h-64">
                                <canvas id="cost-trend-chart"></canvas>
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
            this.showLoading();
            
            // Mock data for now - in real implementation, call Cost Analysis API
            this.data = {
                overview: {
                    total_cost: 0,
                    avg_cost_per_tenant: 0,
                    platform_margin: 0,
                    ai_usage: 0
                },
                tenants: [],
                predictions: {}
            };
            
            this.renderQuickStats();
            this.renderCharts();
            
        } catch (error) {
            console.error('Failed to load cost analysis data:', error);
            this.showError('Failed to load dashboard data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    renderQuickStats() {
        const data = this.data.overview;
        document.getElementById('total-cost').textContent = `$${data.total_cost.toFixed(2)}`;
        document.getElementById('avg-cost').textContent = `$${data.avg_cost_per_tenant.toFixed(2)}`;
        document.getElementById('platform-margin').textContent = `${data.platform_margin.toFixed(1)}%`;
        document.getElementById('ai-usage').textContent = data.ai_usage.toString();
    }
    
    renderCharts() {
        this.renderServiceBreakdownChart();
        this.renderCostTrendChart();
    }
    
    renderServiceBreakdownChart() {
        const ctx = document.getElementById('service-breakdown-chart').getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Lambda', 'DynamoDB', 'API Gateway', 'Bedrock AI'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#8B5CF6', '#06B6D4', '#10B981', '#F59E0B'],
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
                        labels: {
                            color: '#D1D5DB',
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    renderCostTrendChart() {
        const ctx = document.getElementById('cost-trend-chart').getContext('2d');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Current', 'Month 1', 'Month 2', 'Month 3'],
                datasets: [{
                    label: 'Predicted Costs',
                    data: [0, 0, 0, 0],
                    borderColor: '#8B5CF6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#D1D5DB'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#D1D5DB' },
                        grid: { color: '#374151' }
                    },
                    y: {
                        ticks: { color: '#D1D5DB' },
                        grid: { color: '#374151' }
                    }
                }
            }
        });
    }
    
    setupEventListeners() {
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
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
        // Simple error display - could be enhanced
        console.error(message);
    }
}

// Initialize Cost Analysis Controller
window.CostAnalysisController = new CostAnalysisController();
