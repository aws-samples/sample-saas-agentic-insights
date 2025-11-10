// Usage Insights Dashboard for Platform Admins (Control Plane)
// Provides TTV, CLTV, feature adoption, engagement, and at-risk analysis

const UsageInsightsDashboard = {
    // State management
    state: {
        currentAnalysis: null,
        selectedTenant: 'all',
        isLoading: false,
        charts: {}
    },

    // Initialize the usage insights dashboard
    init() {
        console.log('Initializing Usage Insights Dashboard...');

        // Check if UsageInsightsAPI is available
        if (typeof UsageInsightsAPI === 'undefined') {
            console.error('UsageInsightsAPI is not defined. Retrying in 1 second...');
            setTimeout(() => this.init(), 1000);
            return;
        }

        this.setupEventListeners();
        this.initializeManagers();
        this.renderDashboard();
    },

    // Initialize managers
    initializeManagers() {
        this.loadingManager = UsageInsightsAPI.createLoadingManager({
            overlay: document.getElementById('loading-overlay'),
            buttons: document.querySelectorAll('.insights-btn')
        });

        this.notificationManager = UsageInsightsAPI.createNotificationManager();
    },

    // Setup event listeners
    setupEventListeners() {
        // Use event delegation for analysis buttons
        document.body.addEventListener('click', (e) => {
            if (e.target.classList.contains('insights-btn') ||
                e.target.closest('.insights-btn')) {

                e.preventDefault();
                const button = e.target.classList.contains('insights-btn') ?
                    e.target : e.target.closest('.insights-btn');

                const analysisType = button.getAttribute('data-analysis-type');
                if (analysisType) {
                    this.loadAnalysis(analysisType);
                }
            }
        });
    },

    // Render main dashboard
    renderDashboard() {
        console.log('Rendering Usage Insights Dashboard...');
        const pageContent = document.getElementById('page-content');
        if (!pageContent) {
            console.error('Could not find page-content element');
            return;
        }
        console.log('Found page-content element, rendering HTML...');

        pageContent.innerHTML = `
            <div class="space-y-8" id="usage-insights-content">
                <div>
                    <h1 class="text-4xl font-bold text-white mb-2">Usage Insights Dashboard</h1>
                    <p class="text-gray-300">Advanced analytics: TTV, CLTV, engagement, and feature health</p>
                </div>

                <!-- Analysis Action Buttons -->
                <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <button class="insights-btn bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 px-4 py-3 rounded-lg transition-all text-white font-medium" data-analysis-type="ttv">
                        <div class="text-sm opacity-90">Time to Value</div>
                        <div class="text-xs mt-1">Onboarding Speed</div>
                    </button>
                    <button class="insights-btn bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 px-4 py-3 rounded-lg transition-all text-white font-medium" data-analysis-type="cltv">
                        <div class="text-sm opacity-90">CLTV Projection</div>
                        <div class="text-xs mt-1">Revenue Forecast</div>
                    </button>
                    <button class="insights-btn bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-600 hover:to-teal-600 px-4 py-3 rounded-lg transition-all text-white font-medium" data-analysis-type="adoption">
                        <div class="text-sm opacity-90">Feature Adoption</div>
                        <div class="text-xs mt-1">Usage Rates</div>
                    </button>
                    <button class="insights-btn bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 px-4 py-3 rounded-lg transition-all text-white font-medium" data-analysis-type="engagement">
                        <div class="text-sm opacity-90">User Engagement</div>
                        <div class="text-xs mt-1">Activity Scores</div>
                    </button>
                    <button class="insights-btn bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 px-4 py-3 rounded-lg transition-all text-white font-medium" data-analysis-type="at-risk">
                        <div class="text-sm opacity-90">At-Risk Features</div>
                        <div class="text-xs mt-1">Declining Usage</div>
                    </button>
                </div>
                
                <!-- Analysis Results Container -->
                <div id="insights-results" class="min-h-[400px]">
                    <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl p-8 text-center">
                        <svg class="w-16 h-16 mx-auto mb-4 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"></path>
                        </svg>
                        <h3 class="text-xl font-semibold text-white mb-2">Select an Analysis Type</h3>
                        <p class="text-gray-300">
                            Click one of the buttons above to generate AI-powered insights about your platform usage.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Loading Overlay -->
            <div id="loading-overlay" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" style="display: none;">
                <div class="bg-gray-800 rounded-lg p-6">
                    <div class="loading-content"></div>
                </div>
            </div>
        `;

        console.log('Dashboard HTML rendered successfully. Buttons available:', document.querySelectorAll('.insights-btn').length);

        // Ensure the page content is visible (in case it was faded out by navigation animation)
        pageContent.style.opacity = '1';
        console.log('Page content opacity set to 1');
        console.log('Page content first 100 chars:', pageContent.innerHTML.substring(0, 100));

        // Remove any loading divs that might still be present
        const loadingDiv = document.getElementById('usage-insights-loading');
        if (loadingDiv) {
            console.log('Removing usage-insights-loading div');
            loadingDiv.remove();
        }

        // Hide any loading overlays that might be visible
        const globalLoadingOverlay = document.getElementById('loading-overlay');
        if (globalLoadingOverlay) {
            globalLoadingOverlay.style.display = 'none';
            globalLoadingOverlay.classList.add('hidden');
            console.log('Hidden global loading overlay');
        }

        // Hide the dashboard's own loading overlay
        const dashboardLoadingOverlay = pageContent.querySelector('#loading-overlay');
        if (dashboardLoadingOverlay) {
            dashboardLoadingOverlay.style.display = 'none';
            console.log('Hidden dashboard loading overlay');
        }

        console.log('Dashboard should now be visible!');

        // Make the page content VERY visible with a bright background
        pageContent.style.backgroundColor = '#1a1a2e';
        pageContent.style.minHeight = '100vh';
        pageContent.style.display = 'block';
        pageContent.style.visibility = 'visible';

        // Scroll to top to ensure we're looking at the right place
        window.scrollTo(0, 0);
        pageContent.scrollIntoView({ behavior: 'smooth', block: 'start' });

        console.log('Applied visibility styles and scrolled to content');
    },

    // Update button states to show which analysis is selected
    updateButtonStates(selectedType) {
        const buttons = document.querySelectorAll('.insights-btn');
        buttons.forEach(button => {
            const buttonType = button.getAttribute('data-analysis-type');
            if (buttonType === selectedType) {
                // Add selected state styling
                button.classList.add('ring-2', 'ring-white', 'ring-offset-2', 'ring-offset-gray-900');
            } else {
                // Remove selected state styling
                button.classList.remove('ring-2', 'ring-white', 'ring-offset-2', 'ring-offset-gray-900');
            }
        });
    },

    // Load specific analysis
    async loadAnalysis(analysisType) {
        if (this.state.isLoading) return;

        this.state.isLoading = true;
        this.state.currentAnalysis = analysisType;

        // Update button states to show selection
        this.updateButtonStates(analysisType);

        const analysisNames = {
            'ttv': 'Time to Value Analysis',
            'cltv': 'Customer Lifetime Value Projection',
            'adoption': 'Feature Adoption Analysis',
            'engagement': 'User Engagement Analysis',
            'at-risk': 'At-Risk Features Identification'
        };

        this.loadingManager.show(`Generating ${analysisNames[analysisType]}...`);

        try {
            // Always analyze all tenants for platform-wide insights
            const params = {
                tenant_id: null
            };

            let data;
            switch (analysisType) {
                case 'ttv':
                    data = await UsageInsightsAPI.analyzeTTV({
                        baseUrl: window.AdminApp.config.CONTROL_PLANE_API_URL,
                        makeAuthenticatedRequest: window.AdminApp.makeAuthenticatedRequest.bind(window.AdminApp),
                        isControlPlane: true,
                        params
                    });
                    this.renderTTVAnalysis(data);
                    break;

                case 'cltv':
                    data = await UsageInsightsAPI.analyzeCLTV({
                        baseUrl: window.AdminApp.config.CONTROL_PLANE_API_URL,
                        makeAuthenticatedRequest: window.AdminApp.makeAuthenticatedRequest.bind(window.AdminApp),
                        isControlPlane: true,
                        params
                    });
                    this.renderCLTVAnalysis(data);
                    break;

                case 'adoption':
                    data = await UsageInsightsAPI.analyzeFeatureAdoption({
                        baseUrl: window.AdminApp.config.CONTROL_PLANE_API_URL,
                        makeAuthenticatedRequest: window.AdminApp.makeAuthenticatedRequest.bind(window.AdminApp),
                        isControlPlane: true,
                        params
                    });
                    this.renderAdoptionAnalysis(data);
                    break;

                case 'engagement':
                    data = await UsageInsightsAPI.analyzeEngagement({
                        baseUrl: window.AdminApp.config.CONTROL_PLANE_API_URL,
                        makeAuthenticatedRequest: window.AdminApp.makeAuthenticatedRequest.bind(window.AdminApp),
                        isControlPlane: true,
                        params
                    });
                    this.renderEngagementAnalysis(data);
                    break;

                case 'at-risk':
                    data = await UsageInsightsAPI.identifyAtRiskFeatures({
                        baseUrl: window.AdminApp.config.CONTROL_PLANE_API_URL,
                        makeAuthenticatedRequest: window.AdminApp.makeAuthenticatedRequest.bind(window.AdminApp),
                        isControlPlane: true,
                        params
                    });
                    this.renderAtRiskAnalysis(data);
                    break;
            }

            this.notificationManager.showSuccess(
                `${analysisNames[analysisType]} completed successfully!`,
                { duration: 4000 }
            );

        } catch (error) {
            console.error('Error loading analysis:', error);

            if (error.isApiError) {
                this.notificationManager.showApiError(error, {
                    retryCallback: `UsageInsightsDashboard.loadAnalysis('${analysisType}')`
                });
            } else {
                this.notificationManager.showError(
                    'Failed to load analysis',
                    { details: error.message }
                );
            }
        } finally {
            this.state.isLoading = false;
            this.loadingManager.hide();
        }
    },

    // Render TTV Analysis
    renderTTVAnalysis(data) {
        const resultsContainer = document.getElementById('insights-results');
        if (!resultsContainer) return;

        const tenantAnalysis = data.tenant_analysis || [];
        const platformBenchmark = data.summary?.platform_benchmark || {};
        const recommendations = data.recommendations || [];

        // Check if no TTV data is available
        if (!platformBenchmark.mean_ttv_days || platformBenchmark.mean_ttv_days === 0) {
            resultsContainer.innerHTML = `
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <div class="text-center py-8">
                        <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"></path>
                        </svg>
                        <p class="text-gray-300 text-lg">No Time to Value insights available</p>
                    </div>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = `
            <div class="space-y-6">
                <!-- Summary Stats -->
                <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Mean TTV</div>
                        <div class="text-2xl font-bold text-white">${UsageInsightsAPI.formatDays(platformBenchmark.mean_ttv_days || 0)}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Median TTV</div>
                        <div class="text-2xl font-bold text-white">${UsageInsightsAPI.formatDays(platformBenchmark.median_ttv_days || 0)}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">25th Percentile</div>
                        <div class="text-2xl font-bold text-white">${UsageInsightsAPI.formatDays(platformBenchmark.percentile_25 || 0)}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">75th Percentile</div>
                        <div class="text-2xl font-bold text-white">${UsageInsightsAPI.formatDays(platformBenchmark.percentile_75 || 0)}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">90th Percentile</div>
                        <div class="text-2xl font-bold text-white">${UsageInsightsAPI.formatDays(platformBenchmark.percentile_90 || 0)}</div>
                    </div>
                </div>

                <!-- Tenant Metrics -->
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <h3 class="text-lg font-semibold text-white mb-4">Tenant Time to Value</h3>
                    <div class="space-y-3">
                        ${tenantAnalysis.map(tenant => {
            const performanceColor = tenant.performance_vs_platform === 'above_average' ? 'text-green-400' :
                tenant.performance_vs_platform === 'below_average' ? 'text-red-400' :
                    tenant.performance_vs_platform === 'no_data' ? 'text-gray-400' : 'text-yellow-400';
            const performanceBg = tenant.performance_vs_platform === 'above_average' ? 'bg-green-900/20' :
                tenant.performance_vs_platform === 'below_average' ? 'bg-red-900/20' :
                    tenant.performance_vs_platform === 'no_data' ? 'bg-gray-800/50' : 'bg-yellow-900/20';

            return `
                            <div class="p-4 ${performanceBg} border border-gray-700/50 rounded-lg">
                                <div class="flex items-start justify-between mb-3">
                                    <div class="flex-1">
                                        <div class="font-semibold text-white text-lg mb-1">${tenant.tenant_name || tenant.tenant_id}</div>
                                        <div class="flex items-center space-x-2 mb-2">
                                            <span class="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300 capitalize">${tenant.tier}</span>
                                            <span class="text-xs px-2 py-1 rounded ${performanceBg} ${performanceColor} font-medium capitalize">
                                                ${tenant.performance_vs_platform.replace('_', ' ')}
                                            </span>
                                            ${tenant.status === 'no_interaction_yet' ? '<span class="text-xs px-2 py-1 rounded bg-orange-900/30 text-orange-400">Not yet active</span>' : ''}
                                        </div>
                                    </div>
                                    <div class="text-right">
                                        <div class="text-3xl font-bold ${performanceColor}">
                                            ${tenant.status === 'no_interaction_yet' ? 'N/A' : UsageInsightsAPI.formatDays(tenant.ttv_days)}
                                        </div>
                                        ${tenant.percentile_rank ? `<div class="text-xs text-gray-400 mt-1">Top ${tenant.percentile_rank}%</div>` : ''}
                                    </div>
                                </div>
                                
                                ${tenant.comparison_to_mean || tenant.comparison_to_tier ? `
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
                                        ${tenant.comparison_to_mean ? `
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">vs Platform Average</div>
                                                <div class="text-sm font-medium ${performanceColor}">${tenant.comparison_to_mean}</div>
                                            </div>
                                        ` : ''}
                                        ${tenant.comparison_to_tier ? `
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">vs Tier Average</div>
                                                <div class="text-sm font-medium ${performanceColor}">${tenant.comparison_to_tier}</div>
                                            </div>
                                        ` : ''}
                                    </div>
                                ` : ''}

                                ${tenant.insights && tenant.insights.length > 0 ? `
                                    <div class="bg-gray-800/50 rounded p-3">
                                        <div class="text-xs font-semibold text-gray-300 mb-2">Key Insights:</div>
                                        <ul class="space-y-1">
                                            ${tenant.insights.map(insight => `
                                                <li class="text-sm text-gray-400 flex items-start">
                                                    <svg class="w-4 h-4 mr-2 mt-0.5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                                                    </svg>
                                                    ${insight}
                                                </li>
                                            `).join('')}
                                        </ul>
                                    </div>
                                ` : ''}
                            </div>
                        `;
        }).join('')}
                    </div>
                </div>

                <!-- Recommendations -->
                ${this.renderRecommendations(recommendations)}
            </div>
        `;
    },

    // Render CLTV Analysis
    renderCLTVAnalysis(data) {
        const resultsContainer = document.getElementById('insights-results');
        if (!resultsContainer) return;

        const projections = data.data?.tenant_projections || [];
        const segments = data.data?.segments || {};
        const recommendations = data.recommendations || [];

        // Check if no CLTV data is available
        if (projections.length === 0) {
            resultsContainer.innerHTML = `
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <div class="text-center py-8">
                        <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"></path>
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clip-rule="evenodd"></path>
                        </svg>
                        <p class="text-gray-300 text-lg">No CLTV Projection insights available</p>
                    </div>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = `
            <div class="space-y-6">
                <!-- Segment Overview -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    ${Object.entries(segments).map(([segmentName, segment]) => `
                        <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                            <div class="text-gray-400 text-sm capitalize">${segmentName.replace('_', ' ')}</div>
                            <div class="text-2xl font-bold text-white">${UsageInsightsAPI.formatCurrency(segment.avg_cltv || 0)}</div>
                            <div class="text-sm text-gray-400 mt-1">${segment.count || 0} tenants</div>
                        </div>
                    `).join('')}
                </div>

                <!-- Tenant Projections -->
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <h3 class="text-lg font-semibold text-white mb-4">12-Month CLTV Projections</h3>
                    <div class="space-y-3">
                        ${projections.map(tenant => {
            const tierStyle = UsageInsightsAPI.getTierStyling(tenant.segment === 'high_value' ? 'high' : tenant.segment === 'at_risk' ? 'low' : 'medium');
            return `
                                <div class="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                                    <div class="flex-1">
                                        <div class="font-medium text-white">${tenant.tenant_name}</div>
                                        <div class="text-sm text-gray-400">
                                            ${tenant.tier} tier • Retention: ${UsageInsightsAPI.formatPercentage(tenant.retention_rate)}
                                        </div>
                                    </div>
                                    <div class="text-right">
                                        <div class="text-lg font-bold text-white">${UsageInsightsAPI.formatCurrency(tenant.projected_cltv_12m)}</div>
                                        <span class="${tierStyle.badge} text-xs px-2 py-1 rounded">${tenant.segment.replace('_', ' ')}</span>
                                    </div>
                                </div>
                            `;
        }).join('')}
                    </div>
                </div>

                <!-- Recommendations -->
                ${this.renderRecommendations(recommendations)}
            </div>
        `;
    },

    // Render Feature Adoption Analysis
    renderAdoptionAnalysis(data) {
        const resultsContainer = document.getElementById('insights-results');
        if (!resultsContainer) return;

        const features = data.data?.features || [];
        const recommendations = data.recommendations || [];

        resultsContainer.innerHTML = `
            <div class="space-y-6">
                ${features.length > 0 ? `
                    <!-- Feature Adoption Chart -->
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                        <h3 class="text-lg font-semibold text-white mb-4">Feature Adoption Rates</h3>
                        <div class="space-y-3">
                            ${features.map((feature, index) => {
                const adoptionRate = feature.adoption_rate || 0;
                const isLowAdoption = adoptionRate < 20;
                return `
                                    <div class="space-y-2">
                                        <div class="flex items-center justify-between">
                                            <div class="flex items-center space-x-3">
                                                <span class="text-gray-400 font-mono text-sm">#${index + 1}</span>
                                                <span class="font-medium text-white">${feature.feature_name}</span>
                                                ${isLowAdoption ? '<span class="bg-red-100 text-red-800 text-xs px-2 py-1 rounded">Low Adoption</span>' : ''}
                                            </div>
                                            <div class="text-right">
                                                <div class="text-lg font-bold ${isLowAdoption ? 'text-red-400' : 'text-green-400'}">
                                                    ${adoptionRate.toFixed(1)}%
                                                </div>
                                                <div class="text-xs text-gray-400">${feature.feature_users}/${feature.active_users} users</div>
                                            </div>
                                        </div>
                                        <div class="w-full bg-gray-700 rounded-full h-2">
                                            <div class="h-2 rounded-full ${isLowAdoption ? 'bg-red-500' : 'bg-green-500'}" style="width: ${adoptionRate}%"></div>
                                        </div>
                                    </div>
                                `;
            }).join('')}
                        </div>
                    </div>
                ` : `
                    <!-- No Features Message -->
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                        <div class="text-center py-8">
                            <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"></path>
                            </svg>
                            <p class="text-gray-300">No feature adoption data available.</p>
                        </div>
                    </div>
                `}

                <!-- Recommendations -->
                ${features.length > 0 ? this.renderRecommendations(recommendations) : ''}
            </div>
        `;
    },

    // Render Engagement Analysis
    renderEngagementAnalysis(data) {
        const resultsContainer = document.getElementById('insights-results');
        if (!resultsContainer) return;

        const tenantAnalysis = data.tenant_analysis || [];
        const summary = data.summary || {};
        const platformBenchmark = summary.platform_benchmark || {};
        const distribution = data.distribution || {};
        const tierBreakdown = data.tier_breakdown || {};
        const recommendations = data.recommendations || [];

        // Check if no engagement data is available
        if (!platformBenchmark.mean_engagement_score || platformBenchmark.mean_engagement_score === 0) {
            resultsContainer.innerHTML = `
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <div class="text-center py-8">
                        <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"></path>
                        </svg>
                        <p class="text-gray-300 text-lg">No User Engagement insights available</p>
                    </div>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = `
            <div class="space-y-6">
                <!-- Summary Stats -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Mean Engagement</div>
                        <div class="text-2xl font-bold text-white">${platformBenchmark.mean_engagement_score?.toFixed(1) || 'N/A'}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Median Engagement</div>
                        <div class="text-2xl font-bold text-white">${platformBenchmark.median_engagement_score?.toFixed(1) || 'N/A'}</div>
                    </div>
                </div>

                <!-- Tenant Engagement Analysis -->
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <h3 class="text-lg font-semibold text-white mb-4">Tenant Engagement Scores</h3>
                    <div class="space-y-3">
                        ${tenantAnalysis.map(tenant => {
            const performanceColor = tenant.performance_vs_platform === 'above_average' ? 'text-green-400' :
                tenant.performance_vs_platform === 'below_average' ? 'text-red-400' :
                    tenant.performance_vs_platform === 'no_activity' ? 'text-gray-400' : 'text-yellow-400';
            const performanceBg = tenant.performance_vs_platform === 'above_average' ? 'bg-green-900/20' :
                tenant.performance_vs_platform === 'below_average' ? 'bg-red-900/20' :
                    tenant.performance_vs_platform === 'no_activity' ? 'bg-gray-800/50' : 'bg-yellow-900/20';

            // Determine engagement tier from engagement_score if not provided
            let engagementTier = 'medium';
            if (tenant.engagement_score) {
                if (tenant.engagement_score > 70) engagementTier = 'high';
                else if (tenant.engagement_score < 40) engagementTier = 'low';
            }
            const tierColor = engagementTier === 'high' ? 'text-green-400' : engagementTier === 'medium' ? 'text-yellow-400' : 'text-red-400';
            const tierBadgeBg = engagementTier === 'high' ? 'bg-green-900/30' : engagementTier === 'medium' ? 'bg-yellow-900/30' : 'bg-red-900/30';
            const tierBadgeText = engagementTier === 'high' ? 'text-green-400' : engagementTier === 'medium' ? 'text-yellow-400' : 'text-red-400';

            return `
                                <div class="p-4 ${performanceBg} border border-gray-700/50 rounded-lg">
                                    <div class="flex items-start justify-between mb-3">
                                        <div class="flex-1">
                                            <div class="font-semibold text-white text-lg mb-1">${tenant.tenant_name || tenant.tenant_id}</div>
                                            <div class="flex items-center space-x-2 mb-2">
                                                <span class="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300 capitalize">${tenant.tier} tier</span>
                                                <span class="text-xs px-2 py-1 rounded ${tierBadgeBg} ${tierBadgeText} font-medium capitalize">
                                                    ${engagementTier} engagement
                                                </span>
                                                <span class="text-xs px-2 py-1 rounded ${performanceBg} ${performanceColor} font-medium capitalize">
                                                    ${tenant.performance_vs_platform?.replace('_', ' ') || 'average'}
                                                </span>
                                                ${tenant.status === 'no_activity' ? '<span class="text-xs px-2 py-1 rounded bg-orange-900/30 text-orange-400">No activity</span>' : ''}
                                            </div>
                                        </div>
                                        <div class="text-right">
                                            <div class="text-3xl font-bold ${tierColor}">
                                                ${tenant.status === 'no_activity' ? 'N/A' : tenant.engagement_score?.toFixed(1) || 'N/A'}
                                            </div>
                                            ${tenant.percentile_rank ? `<div class="text-xs text-gray-400 mt-1">Top ${tenant.percentile_rank}%</div>` : ''}
                                        </div>
                                    </div>
                                    
                                    ${tenant.metrics ? `
                                        <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Total Requests</div>
                                                <div class="text-sm font-medium text-white">${tenant.metrics.total_requests?.toLocaleString() || 0}</div>
                                            </div>
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Unique Users</div>
                                                <div class="text-sm font-medium text-white">${tenant.metrics.unique_users || 0}</div>
                                            </div>
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Activity Frequency</div>
                                                <div class="text-sm font-medium text-white">${tenant.metrics.activity_frequency?.toFixed(1) || 0}%</div>
                                            </div>
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Feature Diversity</div>
                                                <div class="text-sm font-medium text-white">${tenant.metrics.feature_diversity?.toFixed(1) || 0}%</div>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-2 gap-2 mb-3">
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Days Active</div>
                                                <div class="text-sm font-medium text-white">${tenant.metrics.unique_days_active || 0} / 30</div>
                                            </div>
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Avg Requests/Day</div>
                                                <div class="text-sm font-medium text-white">${tenant.metrics.avg_requests_per_day?.toFixed(1) || 0}</div>
                                            </div>
                                        </div>
                                    ` : ''}

                                    ${tenant.comparison_to_mean || tenant.comparison_to_tier ? `
                                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
                                            ${tenant.comparison_to_mean ? `
                                                <div class="bg-gray-800/50 rounded p-2">
                                                    <div class="text-xs text-gray-400">vs Platform Average</div>
                                                    <div class="text-sm font-medium ${performanceColor}">${tenant.comparison_to_mean}</div>
                                                </div>
                                            ` : ''}
                                            ${tenant.comparison_to_tier ? `
                                                <div class="bg-gray-800/50 rounded p-2">
                                                    <div class="text-xs text-gray-400">vs Tier Average</div>
                                                    <div class="text-sm font-medium ${performanceColor}">${tenant.comparison_to_tier}</div>
                                                </div>
                                            ` : ''}
                                        </div>
                                    ` : ''}

                                    ${tenant.insights && tenant.insights.length > 0 ? `
                                        <div class="bg-gray-800/50 rounded p-3">
                                            <div class="text-xs font-semibold text-gray-300 mb-2">Key Insights:</div>
                                            <ul class="space-y-1">
                                                ${tenant.insights.map(insight => `
                                                    <li class="text-sm text-gray-400 flex items-start">
                                                        <svg class="w-4 h-4 mr-2 mt-0.5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                                                        </svg>
                                                        ${insight}
                                                    </li>
                                                `).join('')}
                                            </ul>
                                        </div>
                                    ` : ''}

                                    ${tenant.metrics?.features_list && tenant.metrics.features_list.length > 0 ? `
                                        <div class="bg-gray-800/50 rounded p-3 mt-3">
                                            <div class="text-xs font-semibold text-gray-300 mb-2">Features Used:</div>
                                            <div class="flex flex-wrap gap-1">
                                                ${tenant.metrics.features_list.map(feature => `
                                                    <span class="text-xs px-2 py-1 rounded bg-blue-900/30 text-blue-300">${feature}</span>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            `;
        }).join('')}
                    </div>
                </div>

                <!-- Tier Breakdown -->
                ${Object.keys(tierBreakdown).length > 0 ? `
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                        <h3 class="text-lg font-semibold text-white mb-4">Engagement by Tier</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            ${Object.entries(tierBreakdown).map(([tier, stats]) => `
                                <div class="bg-gray-700/30 rounded-lg p-4">
                                    <div class="text-sm text-gray-400 capitalize mb-2">${tier} Tier</div>
                                    <div class="space-y-2">
                                        <div class="flex justify-between">
                                            <span class="text-xs text-gray-400">Tenants:</span>
                                            <span class="text-sm font-medium text-white">${stats.count || 0}</span>
                                        </div>
                                        <div class="flex justify-between">
                                            <span class="text-xs text-gray-400">Mean Engagement:</span>
                                            <span class="text-sm font-medium text-white">${stats.mean_engagement?.toFixed(1) || 'N/A'}</span>
                                        </div>
                                        <div class="flex justify-between">
                                            <span class="text-xs text-gray-400">Median Engagement:</span>
                                            <span class="text-sm font-medium text-white">${stats.median_engagement?.toFixed(1) || 'N/A'}</span>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Recommendations -->
                ${this.renderRecommendations(recommendations)}
            </div>
        `;
    },

    // Render At-Risk Features Analysis
    renderAtRiskAnalysis(data) {
        const resultsContainer = document.getElementById('insights-results');
        if (!resultsContainer) return;

        const summary = data.summary || {};
        const atRiskFeatures = data.at_risk_features || [];
        const recommendations = data.recommendations || [];

        // Check if no features were analyzed
        if (!summary.total_features_analyzed || summary.total_features_analyzed === 0) {
            resultsContainer.innerHTML = `
                <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                    <div class="text-center py-8">
                        <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"></path>
                        </svg>
                        <p class="text-gray-300 text-lg">No At-Risk Features insights available</p>
                    </div>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = `
            <div class="space-y-6">
                <!-- Summary Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Features Analyzed</div>
                        <div class="text-2xl font-bold text-white">${summary.total_features_analyzed || 0}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">At-Risk Features</div>
                        <div class="text-2xl font-bold text-orange-400">${summary.at_risk_features_count || 0}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Critical Risk</div>
                        <div class="text-2xl font-bold text-red-400">${summary.critical_risk_count || 0}</div>
                    </div>
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                        <div class="text-gray-400 text-sm">Moderate Risk</div>
                        <div class="text-2xl font-bold text-yellow-400">${summary.moderate_risk_count || 0}</div>
                    </div>
                </div>

                <!-- At-Risk Features Details -->
                ${atRiskFeatures.length > 0 ? `
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                        <h3 class="text-lg font-semibold text-white mb-4">At-Risk Features</h3>
                        <div class="space-y-3">
                            ${atRiskFeatures.map(feature => {
            const riskColor = feature.risk_level === 'critical' ? 'text-red-400' : 'text-yellow-400';
            const riskBg = feature.risk_level === 'critical' ? 'bg-red-900/30' : 'bg-yellow-900/30';
            const riskBorder = feature.risk_level === 'critical' ? 'border-red-500/50' : 'border-yellow-500/50';
            return `
                                    <div class="bg-gray-700/30 border ${riskBorder} rounded-lg p-4">
                                        <div class="flex items-start justify-between mb-3">
                                            <div class="flex-1">
                                                <div class="font-semibold text-white text-lg mb-1">${feature.feature_name}</div>
                                                <span class="${riskBg} ${riskColor} text-xs px-2 py-1 rounded capitalize">${feature.risk_level} Risk</span>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-sm text-gray-400">Decline Rate</div>
                                                <div class="text-xl font-bold ${riskColor}">${feature.decline_rate?.toFixed(1)}%</div>
                                            </div>
                                        </div>
                                        
                                        <div class="grid grid-cols-2 gap-3 mb-3">
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Adoption Rate</div>
                                                <div class="text-sm font-medium text-white">${feature.adoption_rate?.toFixed(1)}%</div>
                                            </div>
                                            <div class="bg-gray-800/50 rounded p-2">
                                                <div class="text-xs text-gray-400">Current Users</div>
                                                <div class="text-sm font-medium text-white">${feature.current_period_summary?.unique_users || 0}</div>
                                            </div>
                                        </div>

                                        ${feature.trend_analysis ? `
                                            <div class="bg-gray-800/50 rounded p-3 mb-3">
                                                <div class="text-xs font-semibold text-gray-300 mb-1">Trend Analysis:</div>
                                                <div class="text-sm text-gray-400">${feature.trend_analysis}</div>
                                            </div>
                                        ` : ''}

                                        ${feature.key_insights && feature.key_insights.length > 0 ? `
                                            <div class="bg-gray-800/50 rounded p-3">
                                                <div class="text-xs font-semibold text-gray-300 mb-2">Key Insights:</div>
                                                <ul class="space-y-1">
                                                    ${feature.key_insights.map(insight => `
                                                        <li class="text-sm text-gray-400 flex items-start">
                                                            <svg class="w-4 h-4 mr-2 mt-0.5 ${riskColor} flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                                                            </svg>
                                                            ${insight}
                                                        </li>
                                                    `).join('')}
                                                </ul>
                                            </div>
                                        ` : ''}
                                    </div>
                                `;
        }).join('')}
                        </div>
                    </div>
                ` : summary.at_risk_features_count === 0 ? `
                    <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
                        <div class="text-center py-8">
                            <svg class="w-16 h-16 mx-auto mb-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            <p class="text-gray-300">No features are currently at risk. All features show healthy usage patterns.</p>
                        </div>
                    </div>
                ` : ''}

                <!-- Recommendations -->
                ${recommendations.length > 0 ? `
                    <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-lg p-6">
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
                            <svg class="w-5 h-5 mr-2 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                            </svg>
                            AI Recommendations
                        </h3>
                        <div class="space-y-3">
                            ${recommendations.map(rec => {
            const priorityStyle = UsageInsightsAPI.getPriorityStyling(rec.priority);
            return `
                                    <div class="bg-gray-800/50 rounded-lg p-4">
                                        <div class="flex items-start space-x-3 mb-3">
                                            <span class="${priorityStyle.badge} text-xs px-2 py-1 rounded border capitalize flex-shrink-0">${rec.priority}</span>
                                            <div class="flex-1">
                                                ${rec.feature_name ? `<div class="text-xs text-gray-400 mb-1">Feature: <span class="font-medium text-gray-300">${rec.feature_name}</span></div>` : ''}
                                                <div class="font-medium text-white mb-2">${rec.action}</div>
                                                ${rec.rationale ? `<div class="text-sm text-gray-300 mb-3">${rec.rationale}</div>` : ''}
                                                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                                                    ${rec.expected_impact ? `
                                                        <div class="bg-gray-700/50 rounded p-2">
                                                            <span class="text-gray-400">Impact:</span>
                                                            <span class="font-medium text-green-400">${rec.expected_impact}</span>
                                                        </div>
                                                    ` : ''}
                                                    ${rec.timeline ? `
                                                        <div class="bg-gray-700/50 rounded p-2">
                                                            <span class="text-gray-400">Timeline:</span>
                                                            <span class="font-medium text-blue-400">${rec.timeline}</span>
                                                        </div>
                                                    ` : ''}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `;
        }).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    },

    // Render recommendations section
    renderRecommendations(recommendations) {
        if (!recommendations || recommendations.length === 0) {
            return '';
        }

        return `
            <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-lg p-6">
                <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
                    <svg class="w-5 h-5 mr-2 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                    </svg>
                    AI Recommendations
                </h3>
                <div class="space-y-3">
                    ${recommendations.map(rec => {
            const priorityStyle = UsageInsightsAPI.getPriorityStyling(rec.priority);
            return `
                            <div class="bg-gray-800/50 rounded-lg p-4">
                                <div class="flex items-start space-x-3">
                                    <span class="${priorityStyle.badge} text-xs px-2 py-1 rounded border capitalize">${rec.priority}</span>
                                    <div class="flex-1">
                                        <div class="font-medium text-white mb-1">${rec.action}</div>
                                        <div class="text-sm text-gray-300">${rec.rationale}</div>
                                    </div>
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Don't auto-initialize - let navigation controller handle it
    window.UsageInsightsDashboard = UsageInsightsDashboard;
});