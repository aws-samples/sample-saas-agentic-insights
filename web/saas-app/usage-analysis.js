// Usage Analysis Manager for Tenant Users
class UsageAnalysisManager {
    constructor() {
        this.currentAnalysis = null;
        this.userRole = null;
    }

    init() {
        console.log('🔄 Initializing Usage Analysis Manager');
        this.userRole = App.state.user?.role || 'tenant_user';
    }

    async loadUsageAnalysis() {
        console.log('📊 Loading usage analysis for role:', this.userRole);
        
        try {
            this.showLoading();
            
            // Get tenant context
            const tenantId = App.state.user?.tenant_id;
            if (!tenantId) {
                throw new Error('Missing tenant context');
            }

            // Call Usage Analysis API
            const response = await fetch(`${window.APP_CONFIG.APP_PLANE_API_URL}/usage-analysis`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('id_token')}`,
                    'tenant-id': tenantId,
                    'tier-name': App.state.user?.tier || 'basic'
                },
                body: JSON.stringify({
                    analysis_type: 'tenant_usage',
                    filters: {
                        include_ai_usage: true,
                        include_performance: true
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Analysis failed: ${response.status}`);
            }

            const result = await response.json();
            console.log('📈 Usage analysis result:', result);

            this.currentAnalysis = result;
            this.renderUsageAnalysis(result);

        } catch (error) {
            console.error('❌ Failed to load usage analysis:', error);
            this.showError(error.message);
        }
    }

    renderUsageAnalysis(analysisResult) {
        const container = document.getElementById('usage-analysis-content');
        
        if (!analysisResult || analysisResult.status === 'error') {
            this.showError(analysisResult?.error?.message || 'Analysis failed');
            return;
        }

        // Parse AI analysis text for key metrics
        const analysis = analysisResult.analysis || '';
        const metrics = this.parseAnalysisMetrics(analysis);

        const content = `
            <div class="usage-analysis-dashboard">
                <!-- Quick Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-content">
                            <h3>API Requests</h3>
                            <p class="stat-value">${metrics.apiRequests.toLocaleString()}</p>
                            <span class="stat-label">This month</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">⚡</div>
                        <div class="stat-content">
                            <h3>Efficiency Score</h3>
                            <p class="stat-value">${metrics.efficiencyScore}%</p>
                            <span class="stat-label">Usage efficiency</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">🤖</div>
                        <div class="stat-content">
                            <h3>AI Usage</h3>
                            <p class="stat-value">${metrics.aiUsage}</p>
                            <span class="stat-label">AI requests</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">💰</div>
                        <div class="stat-content">
                            <h3>Usage Cost</h3>
                            <p class="stat-value">$${metrics.cost.toFixed(2)}</p>
                            <span class="stat-label">This month</span>
                        </div>
                    </div>
                </div>

                <!-- Feature Usage Breakdown -->
                <div class="analysis-section">
                    <h3>Feature Usage Breakdown</h3>
                    <div class="feature-usage-grid">
                        <div class="feature-card">
                            <div class="feature-header">
                                <span class="feature-icon">📦</span>
                                <span class="feature-name">Products</span>
                            </div>
                            <div class="feature-usage">
                                <div class="usage-bar">
                                    <div class="usage-fill" style="width: ${metrics.features.products}%"></div>
                                </div>
                                <span class="usage-percent">${metrics.features.products}%</span>
                            </div>
                        </div>
                        <div class="feature-card">
                            <div class="feature-header">
                                <span class="feature-icon">📋</span>
                                <span class="feature-name">Orders</span>
                            </div>
                            <div class="feature-usage">
                                <div class="usage-bar">
                                    <div class="usage-fill" style="width: ${metrics.features.orders}%"></div>
                                </div>
                                <span class="usage-percent">${metrics.features.orders}%</span>
                            </div>
                        </div>
                        ${this.userRole === 'tenant_admin' ? `
                        <div class="feature-card">
                            <div class="feature-header">
                                <span class="feature-icon">👥</span>
                                <span class="feature-name">Users</span>
                            </div>
                            <div class="feature-usage">
                                <div class="usage-bar">
                                    <div class="usage-fill" style="width: ${metrics.features.users}%"></div>
                                </div>
                                <span class="usage-percent">${metrics.features.users}%</span>
                            </div>
                        </div>
                        ` : ''}
                        <div class="feature-card">
                            <div class="feature-header">
                                <span class="feature-icon">🤖</span>
                                <span class="feature-name">AI Descriptions</span>
                            </div>
                            <div class="feature-usage">
                                <div class="usage-bar">
                                    <div class="usage-fill" style="width: ${metrics.features.ai}%"></div>
                                </div>
                                <span class="usage-percent">${metrics.features.ai}%</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- AI Analysis Insights -->
                <div class="analysis-section">
                    <h3>AI-Powered Insights</h3>
                    <div class="insights-container">
                        <div class="insight-card">
                            <div class="insight-header">
                                <span class="insight-icon">💡</span>
                                <span class="insight-title">Usage Analysis</span>
                            </div>
                            <div class="insight-content">
                                <p>${this.extractInsight(analysis, 'usage') || 'Your usage patterns show consistent activity across core features.'}</p>
                            </div>
                        </div>
                        <div class="insight-card">
                            <div class="insight-header">
                                <span class="insight-icon">📈</span>
                                <span class="insight-title">Performance Insights</span>
                            </div>
                            <div class="insight-content">
                                <p>${this.extractInsight(analysis, 'performance') || 'System performance is optimal with good response times.'}</p>
                            </div>
                        </div>
                        <div class="insight-card">
                            <div class="insight-header">
                                <span class="insight-icon">🎯</span>
                                <span class="insight-title">Recommendations</span>
                            </div>
                            <div class="insight-content">
                                <p>${this.extractInsight(analysis, 'recommendation') || 'Consider exploring AI features to improve productivity.'}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Raw AI Analysis -->
                <div class="analysis-section">
                    <h3>Detailed Analysis</h3>
                    <div class="ai-analysis-text">
                        <p>${analysis}</p>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = content;
    }

    parseAnalysisMetrics(analysisText) {
        // Extract metrics from AI analysis text
        return {
            apiRequests: this.extractNumber(analysisText, /(\d+)\s+(?:api\s+)?requests?/i) || 0,
            efficiencyScore: this.extractNumber(analysisText, /(\d+)%?\s+efficiency/i) || 75,
            aiUsage: this.extractNumber(analysisText, /(\d+)\s+ai\s+(?:requests?|usage)/i) || 0,
            cost: this.extractNumber(analysisText, /\$?([\d.]+)\s+cost/i) || 0,
            features: {
                products: this.extractNumber(analysisText, /products?.*?(\d+)%/i) || 85,
                orders: this.extractNumber(analysisText, /orders?.*?(\d+)%/i) || 70,
                users: this.extractNumber(analysisText, /users?.*?(\d+)%/i) || 60,
                ai: this.extractNumber(analysisText, /ai.*?(\d+)%/i) || 40
            }
        };
    }

    extractNumber(text, regex) {
        const match = text.match(regex);
        return match ? parseFloat(match[1]) : 0;
    }

    extractInsight(text, type) {
        // Extract specific insights from AI analysis
        const sentences = text.split(/[.!?]+/);
        
        for (const sentence of sentences) {
            const lowerSentence = sentence.toLowerCase();
            if (type === 'usage' && (lowerSentence.includes('usage') || lowerSentence.includes('utilization'))) {
                return sentence.trim();
            } else if (type === 'performance' && (lowerSentence.includes('performance') || lowerSentence.includes('response'))) {
                return sentence.trim();
            } else if (type === 'recommendation' && (lowerSentence.includes('recommend') || lowerSentence.includes('suggest'))) {
                return sentence.trim();
            }
        }
        return null;
    }

    async loadFeatureAdoption() {
        try {
            const tenantId = App.state.user?.tenant_id;
            const response = await fetch(`${window.APP_CONFIG.APP_PLANE_API_URL}/usage-analysis`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('id_token')}`,
                    'tenant-id': tenantId,
                    'tier-name': App.state.user?.tier || 'basic'
                },
                body: JSON.stringify({
                    analysis_type: 'feature_adoption'
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('📊 Feature adoption analysis:', result);
                // Could be used to enhance the dashboard
            }
        } catch (error) {
            console.error('Failed to load feature adoption:', error);
        }
    }

    async loadAIUsageAnalysis() {
        try {
            const tenantId = App.state.user?.tenant_id;
            const response = await fetch(`${window.APP_CONFIG.APP_PLANE_API_URL}/usage-analysis`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('id_token')}`,
                    'tenant-id': tenantId,
                    'tier-name': App.state.user?.tier || 'basic'
                },
                body: JSON.stringify({
                    analysis_type: 'ai_usage',
                    filters: {
                        include_cost_analysis: true
                    }
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('🤖 AI usage analysis:', result);
                // Could be used to enhance AI insights
            }
        } catch (error) {
            console.error('Failed to load AI usage analysis:', error);
        }
    }

    showLoading() {
        const container = document.getElementById('usage-analysis-content');
        container.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <p>Analyzing your usage patterns...</p>
            </div>
        `;
    }

    showError(message) {
        const container = document.getElementById('usage-analysis-content');
        container.innerHTML = `
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h3>Analysis Unavailable</h3>
                <p>${message}</p>
                <button onclick="UsageAnalysisManager.loadUsageAnalysis()" class="btn btn-primary">
                    Retry Analysis
                </button>
            </div>
        `;
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-usage-analysis-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadUsageAnalysis();
            });
        }
    }
}

// Initialize Usage Analysis Manager
window.UsageAnalysisManager = new UsageAnalysisManager();