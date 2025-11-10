// Shared Usage Insights API Integration Module
// Provides API client for TTV, CLTV, feature adoption, engagement, and at-risk analysis

const UsageInsightsAPI = {
    // API endpoints configuration
    endpoints: {
        controlPlane: '/ai/usage-insights',  // For platform admins
        appPlane: '/ai/usage-insights'       // For tenant users
    },

    // Make usage insights API request
    async makeUsageInsightsRequest(config) {
        const {
            baseUrl,
            analysisType,
            params = {},
            makeAuthenticatedRequest,
            isControlPlane = false
        } = config;

        if (!makeAuthenticatedRequest) {
            throw new Error('makeAuthenticatedRequest function is required');
        }

        if (!analysisType) {
            throw new Error('analysisType is required');
        }

        const endpoint = isControlPlane ? this.endpoints.controlPlane : this.endpoints.appPlane;
        const url = `${baseUrl}${endpoint}`;

        const requestBody = {
            analysis_type: analysisType,
            ...params
        };

        try {
            const response = await makeAuthenticatedRequest(url, {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw await this.createApiError(response);
            }

        } catch (error) {
            if (error.isApiError) {
                throw error;
            }

            // Handle network errors
            const errorDetails = [];
            errorDetails.push(`Failed to connect to ${url}`);
            errorDetails.push(`Analysis: ${analysisType}`);

            if (error.message) {
                errorDetails.push(`Reason: ${error.message}`);
            }

            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorDetails.push('This may be caused by: network connectivity issues, CORS restrictions, or the server being unavailable');
            } else if (error.name === 'AbortError') {
                errorDetails.push('The request timed out. The server may be slow or unresponsive');
            }

            const networkError = new Error(`Network error: ${errorDetails.join('. ')}. Please check your connection and try again.`);
            networkError.isApiError = true;
            networkError.code = 'NETWORK_ERROR';
            networkError.status = 0;
            networkError.retryable = true;
            networkError.originalError = error;

            throw networkError;
        }
    },

    // Specific analysis methods
    async analyzeTTV(config) {
        return await this.makeUsageInsightsRequest({
            ...config,
            analysisType: 'ttv'
        });
    },

    async analyzeCLTV(config) {
        return await this.makeUsageInsightsRequest({
            ...config,
            analysisType: 'cltv'
        });
    },

    async analyzeFeatureAdoption(config) {
        return await this.makeUsageInsightsRequest({
            ...config,
            analysisType: 'feature_adoption'
        });
    },

    async analyzeEngagement(config) {
        return await this.makeUsageInsightsRequest({
            ...config,
            analysisType: 'engagement'
        });
    },

    async identifyAtRiskFeatures(config) {
        return await this.makeUsageInsightsRequest({
            ...config,
            analysisType: 'at_risk'
        });
    },

    // Create enhanced API error with structured error handling
    async createApiError(response) {
        let errorMessage = 'An error occurred while loading usage insights.';
        let errorCode = 'UNKNOWN_ERROR';
        let errorDetails = {};
        let retryable = false;
        
        try {
            const errorData = await response.json();
            const error = errorData.error || {};
            
            errorCode = error.code || 'UNKNOWN_ERROR';
            errorDetails = error.details || {};
            
            switch (response.status) {
                case 400:
                    errorMessage = error.message || 'Invalid request parameters';
                    break;
                    
                case 401:
                    errorMessage = 'Authentication failed. Please log in again.';
                    break;
                    
                case 403:
                    errorMessage = error.message || 'Access denied. You do not have permission to view this data.';
                    break;
                    
                case 404:
                    errorMessage = error.message || 'No data found for the selected criteria.';
                    break;
                    
                case 429:
                    errorMessage = 'Too many requests. Please wait a moment and try again.';
                    retryable = true;
                    break;
                    
                case 500:
                    errorMessage = error.message || 'Service temporarily unavailable. Please try again later.';
                    retryable = errorDetails.retryable !== false;
                    break;
                    
                default:
                    errorMessage = error.message || errorMessage;
                    retryable = true;
            }
        } catch (parseError) {
            console.error('Error parsing error response:', parseError);
            errorMessage = 'Unable to process server response. Please try again.';
            retryable = true;
        }
        
        const apiError = new Error(errorMessage);
        apiError.isApiError = true;
        apiError.code = errorCode;
        apiError.status = response.status;
        apiError.details = errorDetails;
        apiError.retryable = retryable;
        apiError.requestId = errorDetails.request_id;
        
        return apiError;
    },

    // Format numbers for display
    formatNumber(num) {
        if (typeof num !== 'number') return '0';
        
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    },

    // Format percentage for display
    formatPercentage(value, decimals = 1) {
        if (typeof value !== 'number') return '0%';
        return `${(value * 100).toFixed(decimals)}%`;
    },

    // Format currency for display
    formatCurrency(value, decimals = 2) {
        if (typeof value !== 'number') return '$0.00';
        return `$${value.toFixed(decimals)}`;
    },

    // Format days for display
    formatDays(days) {
        if (typeof days !== 'number') return '0 days';
        if (days === 1) return '1 day';
        return `${days.toFixed(1)} days`;
    },

    // Get priority styling classes
    getPriorityStyling(priority) {
        const styles = {
            critical: {
                badge: 'bg-red-100 text-red-800 border-red-200',
                border: 'border-red-400',
                text: 'text-red-700'
            },
            high: {
                badge: 'bg-orange-100 text-orange-800 border-orange-200',
                border: 'border-orange-400',
                text: 'text-orange-700'
            },
            medium: {
                badge: 'bg-yellow-100 text-yellow-800 border-yellow-200',
                border: 'border-yellow-400',
                text: 'text-yellow-700'
            },
            low: {
                badge: 'bg-green-100 text-green-800 border-green-200',
                border: 'border-green-400',
                text: 'text-green-700'
            }
        };

        return styles[priority] || styles.low;
    },

    // Get tier styling classes
    getTierStyling(tier) {
        const styles = {
            high: {
                badge: 'bg-purple-100 text-purple-800',
                text: 'text-purple-700'
            },
            medium: {
                badge: 'bg-blue-100 text-blue-800',
                text: 'text-blue-700'
            },
            low: {
                badge: 'bg-gray-100 text-gray-800',
                text: 'text-gray-700'
            }
        };

        return styles[tier] || styles.medium;
    },

    // Create loading manager
    createLoadingManager(elements = {}) {
        let startTime = null;
        
        return {
            show(message = 'Analyzing insights...') {
                startTime = Date.now();
                
                if (elements.overlay) {
                    elements.overlay.style.display = 'flex';
                    const loadingContent = elements.overlay.querySelector('.loading-content');
                    if (loadingContent) {
                        loadingContent.innerHTML = `
                            <div class="flex items-center space-x-4">
                                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                                <div class="text-white">
                                    <div class="font-medium">${message}</div>
                                    <div class="text-sm text-gray-300 mt-1" id="insights-loading-progress">Processing...</div>
                                </div>
                            </div>
                        `;
                    }
                }

                if (elements.buttons) {
                    elements.buttons.forEach(btn => {
                        btn.disabled = true;
                        btn.classList.add('opacity-50', 'cursor-not-allowed');
                    });
                }
            },

            hide() {
                if (elements.overlay) {
                    elements.overlay.style.display = 'none';
                }

                if (elements.buttons) {
                    elements.buttons.forEach(btn => {
                        btn.disabled = false;
                        btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    });
                }
            },

            updateProgress(message) {
                const progressElement = document.getElementById('insights-loading-progress');
                if (progressElement) {
                    progressElement.textContent = message;
                }
            }
        };
    },

    // Create notification manager
    createNotificationManager(containerId = 'usage-insights-notifications') {
        return {
            show(message, type = 'error', options = {}) {
                this.clear();

                const { 
                    autoHide = true, 
                    duration = 8000, 
                    actions = [], 
                    details = null
                } = options;

                const notificationContainer = document.createElement('div');
                notificationContainer.id = containerId;
                
                const typeStyles = {
                    error: {
                        container: 'bg-red-50 border-red-200 text-red-700',
                        icon: `<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>`
                    },
                    success: {
                        container: 'bg-green-50 border-green-200 text-green-700',
                        icon: `<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>`
                    },
                    warning: {
                        container: 'bg-yellow-50 border-yellow-200 text-yellow-700',
                        icon: `<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>`
                    },
                    info: {
                        container: 'bg-blue-50 border-blue-200 text-blue-700',
                        icon: `<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>`
                    }
                };

                const style = typeStyles[type] || typeStyles.error;
                notificationContainer.className = `${style.container} border rounded-lg p-4 mb-6 shadow-sm`;
                
                const detailsHtml = details ? `<div class="text-sm mt-2 opacity-90">${details}</div>` : '';
                const actionsHtml = actions.length > 0 ? `
                    <div class="flex space-x-2 mt-3">
                        ${actions.map(action => `
                            <button onclick="${action.onClick}" class="text-xs px-3 py-1 rounded border border-current hover:bg-current hover:text-white transition-colors">
                                ${action.label}
                            </button>
                        `).join('')}
                    </div>
                ` : '';
                
                notificationContainer.innerHTML = `
                    <div class="flex items-start justify-between">
                        <div class="flex items-start space-x-3 flex-1">
                            <svg class="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                ${style.icon}
                            </svg>
                            <div class="flex-1">
                                <div class="font-medium">${message}</div>
                                ${detailsHtml}
                                ${actionsHtml}
                            </div>
                        </div>
                        <button onclick="this.parentElement.parentElement.remove()" class="hover:opacity-70 ml-4 flex-shrink-0">
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                            </svg>
                        </button>
                    </div>
                `;
                
                const targetContainer = document.getElementById('usage-insights-content') || 
                                     document.getElementById('page-content') || 
                                     document.body;
                
                targetContainer.insertBefore(notificationContainer, targetContainer.firstChild);
                
                if (autoHide) {
                    setTimeout(() => {
                        this.clear();
                    }, duration);
                }

                return notificationContainer;
            },

            showSuccess(message, options = {}) {
                return this.show(message, 'success', {
                    duration: 5000,
                    ...options
                });
            },

            showError(message, options = {}) {
                return this.show(message, 'error', {
                    duration: 10000,
                    ...options
                });
            },

            showApiError(apiError, options = {}) {
                const actions = [];
                
                if (apiError.retryable && options.retryCallback) {
                    actions.push({
                        label: 'Retry',
                        onClick: options.retryCallback
                    });
                }
                
                let details = options.details || '';
                if (apiError.requestId) {
                    details += details ? `\n\nRequest ID: ${apiError.requestId}` : `Request ID: ${apiError.requestId}`;
                }
                
                return this.showError(apiError.message, {
                    actions,
                    details,
                    duration: apiError.retryable ? 8000 : 12000,
                    ...options
                });
            },

            clear() {
                const existingNotification = document.getElementById(containerId);
                if (existingNotification) {
                    existingNotification.remove();
                }
            }
        };
    }
};

// Export for use in both admin panel and SaaS app
if (typeof window !== 'undefined') {
    window.UsageInsightsAPI = UsageInsightsAPI;
    console.log('UsageInsightsAPI loaded and available globally');
}

// Also support module exports for potential future use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UsageInsightsAPI;
}
