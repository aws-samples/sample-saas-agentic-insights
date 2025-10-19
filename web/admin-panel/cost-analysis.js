// Cost Analysis Dashboard Controller - Clean Two-Section Design
class CostAnalysisController {
    constructor() {
        this.data = {
            trends: [],
            predictions: [],
            recommendations: [],
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

                <!-- Advanced Analytics Grid -->
                <div class="advanced-charts-grid">
                    <!-- Row 1: Full Width Tier Comparison -->
                    <div class="chart-row-full">
                        <div class="section chart-widget-full">
                            <h2>📊 Tier Profitability Comparison (12 Months)</h2>
                            <div class="chart-container">
                                <canvas id="tier-comparison-chart"></canvas>
                            </div>
                            <div class="chart-explanation">
                                Shows profit margins for Basic ($29) and Premium ($99) tiers over time. Higher lines mean better profitability. Example: $15 margin means $15 profit per customer.
                            </div>
                        </div>
                    </div>

                    <!-- Row 2: Full Width Margin Variation -->
                    <div class="chart-row-full">
                        <div class="section chart-widget-full">
                            <h2>📈 Month-over-Month Margin Variation</h2>
                            <div class="chart-container">
                                <canvas id="growth-heatmap-chart"></canvas>
                            </div>
                            <div class="chart-explanation">
                                Shows monthly profit changes in dollars. Green bars mean profit increased, red bars mean profit decreased. Example: +$5 means $5 more profit than last month.
                            </div>
                        </div>
                    </div>

                    <!-- Row 3: Full Width Revenue Efficiency Index -->
                    <div class="chart-row-full">
                        <div class="section chart-widget-full">
                            <h2>⚖️ Revenue Efficiency Index </h2>
                            <div class="chart-container">
                                <canvas id="efficiency-chart"></canvas>
                            </div>
                            <div class="chart-explanation">
                                Shows how much it costs to generate a dollar of revenue tier-wise. Keep below 1.0 for profit. Example: 0.65 means 65¢ cost per $1 revenue, so 35¢ profit.
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
            this.data.recommendations = analysisData.recommendations || [];
            this.data.historicalData = analysisData.cost_per_tenant_averages || [];
            this.data.predictedData = analysisData.cost_per_tenant_predictions || [];
            
            // Update UI
            this.updateTrendsList();
            this.updatePredictionsList();
            this.updateRecommendationsList();
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
    
    updateRecommendationsList() {
        const optimizationsList = document.getElementById('optimizations-list');
        if (this.data.recommendations.length > 0) {
            optimizationsList.innerHTML = this.data.recommendations.map(recommendation => `<li>${recommendation}</li>`).join('');
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
        this.createTierComparisonChart();
        this.createGrowthHeatmapChart();
        this.createEfficiencyChart();
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
    
    // Advanced Chart 2: Tier Profitability Comparison (12 Months)
    createTierComparisonChart() {
        const canvas = document.getElementById('tier-comparison-chart');
        if (!canvas) return;
        
        if (this.charts.tierComparison) {
            this.charts.tierComparison.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Get last 6 months of historical data
        const historicalMonths = [...new Set(this.data.historicalData.map(d => d.month))].sort().slice(-6);
        
        // Get 6 months of prediction data
        const predictionMonths = [...new Set(this.data.predictedData.map(d => d.month))].sort().slice(0, 6);
        
        // Combine all 12 months
        const allMonths = [...historicalMonths, ...predictionMonths];
        
        // Prepare data for both tiers
        const basicData = allMonths.map(month => {
            // Check historical first
            const historical = this.data.historicalData.find(d => d.month === month && d.tier === 'basic');
            if (historical) return historical.margin;
            
            // Then check predictions
            const predicted = this.data.predictedData.find(d => d.month === month && d.tier === 'basic');
            return predicted ? predicted.predicted_margin : null;
        });
        
        const premiumData = allMonths.map(month => {
            // Check historical first
            const historical = this.data.historicalData.find(d => d.month === month && d.tier === 'premium');
            if (historical) return historical.margin;
            
            // Then check predictions
            const predicted = this.data.predictedData.find(d => d.month === month && d.tier === 'premium');
            return predicted ? predicted.predicted_margin : null;
        });
        
        this.charts.tierComparison = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allMonths,
                datasets: [
                    {
                        label: 'Basic Tier Margin (Historical)',
                        data: basicData.slice(0, 6), // First 6 months (historical)
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 4,
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: '#3B82F6',
                        pointRadius: 6
                    },
                    {
                        label: 'Basic Tier Margin (Predicted)',
                        data: [null, null, null, null, null, ...basicData.slice(6)], // Last 6 months (predicted)
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 4,
                        borderDash: [10, 5],
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: '#3B82F6',
                        pointRadius: 6,
                        pointStyle: 'triangle'
                    },
                    {
                        label: 'Premium Tier Margin (Historical)',
                        data: premiumData.slice(0, 6), // First 6 months (historical)
                        borderColor: '#8B5CF6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 4,
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: '#8B5CF6',
                        pointRadius: 6
                    },
                    {
                        label: 'Premium Tier Margin (Predicted)',
                        data: [null, null, null, null, null, ...premiumData.slice(6)], // Last 6 months (predicted)
                        borderColor: '#8B5CF6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 4,
                        borderDash: [10, 5],
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: '#8B5CF6',
                        pointRadius: 6,
                        pointStyle: 'triangle'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Historical vs Predicted Tier Profitability (12 Months)'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time Period'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Margin ($)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
    
    // Advanced Chart 4: Month-over-Month Margin Variation (12 Months)
    createGrowthHeatmapChart() {
        const canvas = document.getElementById('growth-heatmap-chart');
        if (!canvas) return;
        
        if (this.charts.growthHeatmap) {
            this.charts.growthHeatmap.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Get last 6 months of historical data
        const historicalMonths = [...new Set(this.data.historicalData.map(d => d.month))].sort().slice(-6);
        
        // Get 6 months of prediction data
        const predictionMonths = [...new Set(this.data.predictedData.map(d => d.month))].sort().slice(0, 6);
        
        // Combine all 12 months
        const allMonths = [...historicalMonths, ...predictionMonths];
        
        const basicGrowthValues = [];
        const premiumGrowthValues = [];
        
        // Calculate historical changes for Basic tier
        const basicHistorical = this.data.historicalData
            .filter(d => d.tier === 'basic')
            .sort((a, b) => a.month.localeCompare(b.month))
            .slice(-6);
        
        for (let i = 1; i < basicHistorical.length; i++) {
            const current = basicHistorical[i];
            const previous = basicHistorical[i - 1];
            basicGrowthValues.push(current.margin - previous.margin);
        }
        
        // Add predicted changes for Basic tier
        const basicPredicted = this.data.predictedData
            .filter(d => d.tier === 'basic')
            .sort((a, b) => a.month.localeCompare(b.month))
            .slice(0, 6);
        
        // Connect last historical to first predicted
        if (basicHistorical.length > 0 && basicPredicted.length > 0) {
            const lastHistorical = basicHistorical[basicHistorical.length - 1];
            const firstPredicted = basicPredicted[0];
            basicGrowthValues.push(firstPredicted.predicted_margin - lastHistorical.margin);
        }
        
        // Add predicted month-over-month changes
        for (let i = 1; i < basicPredicted.length; i++) {
            const current = basicPredicted[i];
            const previous = basicPredicted[i - 1];
            basicGrowthValues.push(current.predicted_margin - previous.predicted_margin);
        }
        
        // Calculate historical changes for Premium tier
        const premiumHistorical = this.data.historicalData
            .filter(d => d.tier === 'premium')
            .sort((a, b) => a.month.localeCompare(b.month))
            .slice(-6);
        
        for (let i = 1; i < premiumHistorical.length; i++) {
            const current = premiumHistorical[i];
            const previous = premiumHistorical[i - 1];
            premiumGrowthValues.push(current.margin - previous.margin);
        }
        
        // Add predicted changes for Premium tier
        const premiumPredicted = this.data.predictedData
            .filter(d => d.tier === 'premium')
            .sort((a, b) => a.month.localeCompare(b.month))
            .slice(0, 6);
        
        // Connect last historical to first predicted
        if (premiumHistorical.length > 0 && premiumPredicted.length > 0) {
            const lastHistorical = premiumHistorical[premiumHistorical.length - 1];
            const firstPredicted = premiumPredicted[0];
            premiumGrowthValues.push(firstPredicted.predicted_margin - lastHistorical.margin);
        }
        
        // Add predicted month-over-month changes
        for (let i = 1; i < premiumPredicted.length; i++) {
            const current = premiumPredicted[i];
            const previous = premiumPredicted[i - 1];
            premiumGrowthValues.push(current.predicted_margin - previous.predicted_margin);
        }
        
        // Use months starting from second month (since we're showing changes)
        const changeMonths = allMonths.slice(1);
        
        this.charts.growthHeatmap = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: changeMonths,
                datasets: [
                    {
                        label: 'Basic Tier Margin Change ($)',
                        data: basicGrowthValues,
                        backgroundColor: basicGrowthValues.map(value => {
                            return value >= 0 ? '#10B981' : '#EF4444'; // Green for positive, Red for negative
                        }),
                        borderColor: '#F59E0B', // Yellow outline for Basic
                        borderWidth: 3
                    },
                    {
                        label: 'Premium Tier Margin Change ($)',
                        data: premiumGrowthValues,
                        backgroundColor: premiumGrowthValues.map(value => {
                            return value >= 0 ? '#10B981' : '#EF4444'; // Green for positive, Red for negative
                        }),
                        borderColor: '#3B82F6', // Blue outline for Premium
                        borderWidth: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Historical vs Predicted Margin Changes (12 Months)'
                    },
                    legend: {
                        display: true,
                        labels: {
                            generateLabels: function(chart) {
                                return [
                                    {
                                        text: 'Basic Tier Margin Change ($)',
                                        fillStyle: 'transparent',
                                        strokeStyle: '#F59E0B', // Yellow outline
                                        lineWidth: 3
                                    },
                                    {
                                        text: 'Premium Tier Margin Change ($)',
                                        fillStyle: 'transparent',
                                        strokeStyle: '#3B82F6', // Blue outline
                                        lineWidth: 3
                                    }
                                ];
                            }
                        }
                    },
                    legend: {
                        display: true,
                        labels: {
                            generateLabels: function(chart) {
                                return [
                                    {
                                        text: 'Basic Tier Margin Change ($)',
                                        fillStyle: 'transparent',
                                        strokeStyle: '#F59E0B', // Yellow outline
                                        lineWidth: 3
                                    },
                                    {
                                        text: 'Premium Tier Margin Change ($)',
                                        fillStyle: 'transparent',
                                        strokeStyle: '#3B82F6', // Blue outline
                                        lineWidth: 3
                                    }
                                ];
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const value = ctx.parsed.y;
                                const sign = value >= 0 ? '+' : '';
                                const tier = ctx.datasetIndex === 0 ? 'Basic' : 'Premium';
                                return `${tier}: ${sign}$${value.toFixed(1)}`;
                            }
                        }
                    },
                    datalabels: {
                        display: true,
                        anchor: (ctx) => {
                            return ctx.parsed.y >= 0 ? 'end' : 'start';
                        },
                        align: (ctx) => {
                            return ctx.parsed.y >= 0 ? 'top' : 'bottom';
                        },
                        formatter: (value, ctx) => {
                            const tier = ctx.datasetIndex === 0 ? 'Basic' : 'Premium';
                            return tier;
                        },
                        color: '#FFFFFF',
                        font: {
                            size: 10,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Margin Change ($)'
                        }
                    }
                }
            }
        });
    }
    
    // Advanced Chart 5: Volatility Index
    createVolatilityChart() {
        const canvas = document.getElementById('volatility-chart');
        if (!canvas) return;
        
        if (this.charts.volatility) {
            this.charts.volatility.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Calculate volatility (standard deviation) for each tier
        const basicCosts = this.data.historicalData.filter(d => d.tier === 'basic').map(d => d.cost);
        const premiumCosts = this.data.historicalData.filter(d => d.tier === 'premium').map(d => d.cost);
        
        const calculateVolatility = (values) => {
            const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
            const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
            return Math.sqrt(variance);
        };
        
        const basicVolatility = calculateVolatility(basicCosts);
        const premiumVolatility = calculateVolatility(premiumCosts);
        
        this.charts.volatility = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Basic Tier Risk', 'Premium Tier Risk'],
                datasets: [{
                    data: [basicVolatility, premiumVolatility],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(139, 92, 246, 0.8)'
                    ],
                    borderColor: [
                        '#3B82F6',
                        '#8B5CF6'
                    ],
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Cost Volatility Index by Tier'
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                return `${ctx.label}: $${ctx.parsed.toFixed(2)} volatility`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Advanced Chart 8: Revenue Efficiency Index
    createEfficiencyChart() {
        const canvas = document.getElementById('efficiency-chart');
        if (!canvas) return;
        
        if (this.charts.efficiency) {
            this.charts.efficiency.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Get last 6 months of historical data
        const historicalMonths = [...new Set(this.data.historicalData.map(d => d.month))].sort().slice(-6);
        
        // Get 6 months of prediction data
        const predictionMonths = [...new Set(this.data.predictedData.map(d => d.month))].sort().slice(0, 6);
        
        // Combine all 12 months
        const allMonths = [...historicalMonths, ...predictionMonths];
        
        // Calculate efficiency for Basic tier (historical + predicted)
        const basicEfficiency = allMonths.map(month => {
            // Check historical first
            const historical = this.data.historicalData.find(d => d.month === month && d.tier === 'basic');
            if (historical) {
                return historical.cost / historical.revenue;
            }
            
            // Then check predictions
            const predicted = this.data.predictedData.find(d => d.month === month && d.tier === 'basic');
            return predicted ? (predicted.predicted_cost / predicted.revenue) : null;
        });
        
        // Calculate efficiency for Premium tier (historical + predicted)
        const premiumEfficiency = allMonths.map(month => {
            // Check historical first
            const historical = this.data.historicalData.find(d => d.month === month && d.tier === 'premium');
            if (historical) {
                return historical.cost / historical.revenue;
            }
            
            // Then check predictions
            const predicted = this.data.predictedData.find(d => d.month === month && d.tier === 'premium');
            return predicted ? (predicted.predicted_cost / predicted.revenue) : null;
        });
        
        this.charts.efficiency = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: allMonths,
                datasets: [
                    {
                        label: 'Basic Tier Efficiency (Historical)',
                        data: basicEfficiency.slice(0, 6), // First 6 months (historical)
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: '#3B82F6',
                        borderWidth: 2
                    },
                    {
                        label: 'Basic Tier Efficiency (Predicted)',
                        data: [null, null, null, null, null, null, ...basicEfficiency.slice(6)], // Last 6 months (predicted)
                        backgroundColor: 'rgba(59, 130, 246, 0.4)',
                        borderColor: '#3B82F6',
                        borderWidth: 2,
                        borderDash: [5, 5]
                    },
                    {
                        label: 'Premium Tier Efficiency (Historical)',
                        data: premiumEfficiency.slice(0, 6), // First 6 months (historical)
                        backgroundColor: 'rgba(139, 92, 246, 0.7)',
                        borderColor: '#8B5CF6',
                        borderWidth: 2
                    },
                    {
                        label: 'Premium Tier Efficiency (Predicted)',
                        data: [null, null, null, null, null, null, ...premiumEfficiency.slice(6)], // Last 6 months (predicted)
                        backgroundColor: 'rgba(139, 92, 246, 0.4)',
                        borderColor: '#8B5CF6',
                        borderWidth: 2,
                        borderDash: [5, 5]
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Historical vs Predicted Cost per $ Revenue (12 Months)'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time Period'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Efficiency Ratio (Cost/Revenue)'
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
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
        this.createTierComparisonChart();
        this.createGrowthHeatmapChart();
        this.createEfficiencyChart();
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
