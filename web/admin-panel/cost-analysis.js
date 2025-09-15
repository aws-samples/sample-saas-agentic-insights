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
            console.log('🔄 Starting cost analysis data load...');
            this.showLoading();
            
            // Debug: Check if API URL is configured
            console.log('🔗 API URL:', window.APP_CONFIG?.COST_ANALYSIS_API_URL);
            
            if (!window.APP_CONFIG?.COST_ANALYSIS_API_URL) {
                throw new Error('COST_ANALYSIS_API_URL not configured in APP_CONFIG');
            }
            
            // Call Cost Analysis API for complete dashboard data
            console.log('📡 Making API call to cost analysis endpoint...');
            const response = await fetch(window.APP_CONFIG.COST_ANALYSIS_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    analysis_type: 'dashboard_complete'
                })
            });
            
            console.log('📥 API Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📊 API Response data:', result);
            console.log('📝 Analysis text:', result.analysis);
            
            // Parse AI response and extract structured data
            this.data = this.parseAIResponse(result.analysis);
            console.log('🎯 Parsed data:', this.data);
            
            this.renderQuickStats();
            this.renderCharts();
            this.renderAIRecommendations();
            
            console.log('✅ Cost analysis data loaded successfully');
            
        } catch (error) {
            console.error('❌ Failed to load cost analysis data:', error);
            
            // Show raw error details for debugging
            const errorContainer = document.getElementById('page-content');
            errorContainer.innerHTML = `
                <div class="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-8">
                    <div class="max-w-4xl mx-auto">
                        <h1 class="text-4xl font-bold text-white mb-8">Cost Analysis API Error</h1>
                        <div class="bg-red-900/50 border border-red-500/50 rounded-xl p-6">
                            <h2 class="text-xl font-semibold text-red-300 mb-4">API Call Failed</h2>
                            <div class="space-y-4">
                                <div>
                                    <h3 class="text-lg font-medium text-white mb-2">Error Details:</h3>
                                    <pre class="bg-gray-800 p-4 rounded-lg text-red-300 text-sm overflow-auto">${error.message}</pre>
                                </div>
                                <div>
                                    <h3 class="text-lg font-medium text-white mb-2">API Endpoint:</h3>
                                    <code class="bg-gray-800 p-2 rounded text-blue-300">${window.APP_CONFIG.COST_ANALYSIS_API_URL}</code>
                                </div>
                                <div>
                                    <h3 class="text-lg font-medium text-white mb-2">Request Payload:</h3>
                                    <pre class="bg-gray-800 p-4 rounded-lg text-yellow-300 text-sm">{"analysis_type": "dashboard_complete"}</pre>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            return;
        } finally {
            this.hideLoading();
        }
    }
    
    parseAIResponse(analysisText) {
        // Parse AI response text and extract structured data
        // This is a simplified parser - in production, you might want more robust parsing
        const data = {
            overview: {
                total_cost: this.extractNumber(analysisText, /total.*cost.*\$?([\d.]+)/i) || 0,
                avg_cost_per_tenant: this.extractNumber(analysisText, /average.*tenant.*\$?([\d.]+)/i) || 0,
                platform_margin: this.extractNumber(analysisText, /margin.*?([\d.]+)%/i) || 0,
                ai_usage: this.extractNumber(analysisText, /ai.*usage.*?([\d]+)/i) || 0
            },
            service_breakdown: {
                lambda_cost: this.extractNumber(analysisText, /lambda.*\$?([\d.]+)/i) || 0,
                dynamodb_cost: this.extractNumber(analysisText, /dynamodb.*\$?([\d.]+)/i) || 0,
                api_gateway_cost: this.extractNumber(analysisText, /api.*gateway.*\$?([\d.]+)/i) || 0,
                bedrock_cost: this.extractNumber(analysisText, /bedrock.*\$?([\d.]+)/i) || 0
            },
            cost_trends: this.extractCostTrends(analysisText),
            ai_recommendations: this.extractRecommendations(analysisText)
        };
        
        return data;
    }
    
    extractNumber(text, regex) {
        const match = text.match(regex);
        return match ? parseFloat(match[1]) : 0;
    }
    
    extractCostTrends(text) {
        // Extract daily cost trends for the last 7 days
        const trends = [];
        const today = new Date();
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            trends.push({
                date: date.toISOString().split('T')[0],
                cost: Math.random() * 10 + 5 // Placeholder - would extract from AI response
            });
        }
        
        return trends;
    }
    
    extractRecommendations(text) {
        // Extract AI recommendations from the response
        const recommendations = [];
        
        // Look for numbered recommendations or bullet points
        const lines = text.split('\n');
        let currentRec = null;
        
        for (const line of lines) {
            if (line.match(/^\d+\.|^[-*]\s/)) {
                if (currentRec) {
                    recommendations.push(currentRec);
                }
                currentRec = {
                    type: line.toLowerCase().includes('optim') ? 'optimization' : 'forecasting',
                    title: line.replace(/^\d+\.|^[-*]\s/, '').trim().substring(0, 50) + '...',
                    description: line.replace(/^\d+\.|^[-*]\s/, '').trim(),
                    impact: 'Medium'
                };
            } else if (currentRec && line.trim()) {
                currentRec.description += ' ' + line.trim();
            }
        }
        
        if (currentRec) {
            recommendations.push(currentRec);
        }
        
        // Ensure we have exactly 5 recommendations
        while (recommendations.length < 5) {
            recommendations.push({
                type: 'optimization',
                title: 'Cost optimization opportunity identified',
                description: 'Additional cost optimization recommendations will be available as more data is collected.',
                impact: 'Low'
            });
        }
        
        return recommendations.slice(0, 5);
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
    
    renderAIRecommendations() {
        const container = document.getElementById('ai-recommendations');
        const recommendations = this.data.ai_recommendations || [];
        
        if (recommendations.length === 0) {
            container.innerHTML = `
                <p class="text-gray-300 text-sm">
                    AI-powered cost optimization recommendations will appear here once sufficient metrics data is collected.
                </p>
            `;
            return;
        }
        
        const recommendationsHtml = recommendations.map((rec, index) => `
            <div class="mb-4 p-3 bg-gray-800/30 rounded-lg border border-gray-600/30">
                <div class="flex items-start justify-between mb-2">
                    <h4 class="text-sm font-medium text-white">${rec.title}</h4>
                    <span class="text-xs px-2 py-1 rounded-full ${
                        rec.impact === 'High' ? 'bg-red-500/20 text-red-300' :
                        rec.impact === 'Medium' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-green-500/20 text-green-300'
                    }">${rec.impact}</span>
                </div>
                <p class="text-xs text-gray-400 leading-relaxed">${rec.description}</p>
                <div class="mt-2 flex items-center text-xs text-purple-400">
                    <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                    </svg>
                    ${rec.type === 'optimization' ? 'Cost Optimization' : 'Forecasting'}
                </div>
            </div>
        `).join('');
        
        container.innerHTML = recommendationsHtml;
    }
    
    renderServiceBreakdownChart() {
        const ctx = document.getElementById('service-breakdown-chart').getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Lambda', 'DynamoDB', 'API Gateway', 'Bedrock AI'],
                datasets: [{
                    data: [
                        this.data.service_breakdown?.lambda_cost || 0,
                        this.data.service_breakdown?.dynamodb_cost || 0,
                        this.data.service_breakdown?.api_gateway_cost || 0,
                        this.data.service_breakdown?.bedrock_cost || 0
                    ],
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
        const trends = this.data.cost_trends || [];
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: trends.map(trend => trend.date),
                datasets: [{
                    label: 'Daily Costs',
                    data: trends.map(trend => trend.cost),
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
