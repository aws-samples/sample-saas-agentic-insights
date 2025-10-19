// Cost Analysis Dashboard Controller - Clean Two-Section Design
class CostAnalysisController {
    constructor() {
        this.data = {
            trends: [],
            predictions: [],
            optimizations: [],
            historicalData: [],
            predictedData: []
        };
        this.charts = {};
    }
    
    async init() {
        console.log('Initializing Cost Analysis Controller...');
        this.renderLayout();
        await this.loadInsightData();
        this.setupEventListeners();
        this.initializeCharts();
    }
    
    renderLayout() {
        const content = `
            <div class="cost-analysis-dashboard" id="cost-analysis-container">
                <!-- Header -->
                <div class="dashboard-header">
                    <h1>Cost Analysis Dashboard</h1>
                    <button id="refresh-btn" class="refresh-btn">Refresh Data</button>
                </div>

                <!-- Two Main Sections -->
                <div class="main-sections">
                    <!-- Trend Analysis Section -->
                    <div class="section trend-section">
                        <h2>📈 Trend Analysis</h2>
                        <div class="chart-container">
                            <canvas id="trend-chart"></canvas>
                        </div>
                        <div class="insights-list">
                            <ul id="trends-list">
                                <li>Loading trends...</li>
                            </ul>
                        </div>
                    </div>

                    <!-- AI Predictions Section -->
                    <div class="section prediction-section">
                        <h2>🔮 AI Predictions</h2>
                        <div class="chart-container">
                            <canvas id="prediction-chart"></canvas>
                        </div>
                        <div class="insights-list">
                            <ul id="predictions-list">
                                <li>Loading predictions...</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- AI Recommendations Section -->
                <div class="section optimizations-section">
                    <h2>🤖 AI Recommendations</h2>
                    <div class="insights-list">
                        <ul id="optimizations-list">
                            <li>Loading AI recommendations...</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('page-content').innerHTML = content;
    }
    
    async loadInsightData() {
        try {
            this.showLoading();
            console.log('Loading insight data from API...');
            const response = await fetch(`${window.APP_CONFIG.CONTROL_PLANE_API_URL}/insight-dashboard`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    analysis_type: 'simple-cost-analysis'
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Raw API Response:', result);
            
            if (!result.analysis) {
                throw new Error('No analysis data in response');
            }
            
            let analysisData;
            try {
                analysisData = JSON.parse(result.analysis);
                console.log('Parsed Analysis Data:', analysisData);
            } catch (parseError) {
                console.error('JSON Parse Error:', parseError);
                throw new Error(`Failed to parse analysis JSON: ${parseError.message}`);
            }
            
            // Store the AI insights and data
            this.data.trends = analysisData.trends || [];
            this.data.predictions = analysisData.predictions || [];
            this.data.optimizations = analysisData.optimizations || [];
            this.data.historicalData = analysisData.cost_per_tenant_averages || [];
            this.data.predictedData = analysisData.cost_per_tenant_predictions || [];
            
            // Update UI
            this.updateTrendsList();
            this.updatePredictionsList();
            this.updateOptimizationsList();
            this.updateCharts();
            
        } catch (error) {
            console.error('Error loading insight data:', error);
            this.showError(`Failed to load AI insights: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }
    
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }
    
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }
    
    updateTrendsList() {
        const trendsList = document.getElementById('trends-list');
        if (this.data.trends.length > 0) {
            trendsList.innerHTML = this.data.trends.map(trend => `<li>${trend}</li>`).join('');
        } else {
            trendsList.innerHTML = '<li>No trend data available</li>';
        }
    }
    
    updatePredictionsList() {
        const predictionsList = document.getElementById('predictions-list');
        if (this.data.predictions.length > 0) {
            predictionsList.innerHTML = this.data.predictions.map(prediction => `<li>${prediction}</li>`).join('');
        } else {
            predictionsList.innerHTML = '<li>No prediction data available</li>';
        }
    }
    
    updateOptimizationsList() {
        const optimizationsList = document.getElementById('optimizations-list');
        if (this.data.optimizations.length > 0) {
            optimizationsList.innerHTML = this.data.optimizations.map(optimization => `<li>${optimization}</li>`).join('');
        } else {
            optimizationsList.innerHTML = '<li>No AI recommendations available</li>';
        }
    }
    
    initializeCharts() {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }
        
        this.createTrendChart();
        this.createPredictionChart();
    }
    
    createTrendChart() {
        const canvas = document.getElementById('trend-chart');
        if (!canvas) return;
        
        // Destroy existing chart if it exists
        if (this.charts.trend) {
            this.charts.trend.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Prepare historical data
        const basicHistorical = this.data.historicalData.filter(d => d.tier === 'basic');
        const premiumHistorical = this.data.historicalData.filter(d => d.tier === 'premium');
        
        const months = [...new Set(this.data.historicalData.map(d => d.month))].sort();
        
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Basic Tier Cost',
                        data: months.map(month => {
                            const item = basicHistorical.find(d => d.month === month);
                            return item ? item.cost : null;
                        }),
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 3,
                        tension: 0.4
                    },
                    {
                        label: 'Premium Tier Cost',
                        data: months.map(month => {
                            const item = premiumHistorical.find(d => d.month === month);
                            return item ? item.cost : null;
                        }),
                        borderColor: '#8B5CF6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 3,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Historical Cost per Tenant Trends'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time (Month)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Cost per Tenant ($)'
                        }
                    }
                }
            }
        });
    }
    
    createPredictionChart() {
        const canvas = document.getElementById('prediction-chart');
        if (!canvas) return;
        
        // Destroy existing chart if it exists
        if (this.charts.prediction) {
            this.charts.prediction.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Prepare predicted data
        const basicPredicted = this.data.predictedData.filter(d => d.tier === 'basic');
        const premiumPredicted = this.data.predictedData.filter(d => d.tier === 'premium');
        
        const months = [...new Set(this.data.predictedData.map(d => d.month))].sort();
        
        this.charts.prediction = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Basic Tier Prediction',
                        data: months.map(month => {
                            const item = basicPredicted.find(d => d.month === month);
                            return item ? item.predicted_cost : null;
                        }),
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.4
                    },
                    {
                        label: 'Premium Tier Prediction',
                        data: months.map(month => {
                            const item = premiumPredicted.find(d => d.month === month);
                            return item ? item.predicted_cost : null;
                        }),
                        borderColor: '#8B5CF6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'AI-Predicted Cost per Tenant'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time (Month)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Cost per Tenant ($)'
                        }
                    }
                }
            }
        });
    }
    
    setupEventListeners() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadInsightData();
            });
        }
    }
    
    updateCharts() {
        // Recreate charts (destruction handled in create methods)
        this.createTrendChart();
        this.createPredictionChart();
    }
    
    showError(message) {
        const container = document.getElementById('cost-analysis-container');
        if (container) {
            container.innerHTML = `
                <div class="error-container" style="color: white;">
                    <h3 style="color: #EF4444;">Error Loading Data</h3>
                    <p style="color: white;">${message}</p>
                    <button onclick="window.CostAnalysisController.loadInsightData()" style="background: #EF4444; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer;">Retry</button>
                </div>
            `;
        }
    }
}

// Initialize Cost Analysis Controller
window.CostAnalysisController = new CostAnalysisController();
/* Updated: Sun 19 Oct 2025 15:37:36 +08 */
