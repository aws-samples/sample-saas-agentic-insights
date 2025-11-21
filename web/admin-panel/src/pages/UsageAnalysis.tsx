import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, DollarSign, TrendingUp, Users, AlertTriangle, CheckCircle, XCircle, ArrowUp, ArrowRight, ArrowDown } from 'lucide-react';

type AnalysisType = 'ttv' | 'cltv' | 'feature_adoption' | 'engagement' | 'at_risk' | null;

export default function UsageAnalysis() {
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisType>(null);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadAnalysis = async (analysisType: AnalysisType) => {
    if (!analysisType) return;
    
    setLoading(true);
    setCurrentAnalysis(analysisType);
    
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(
        `${import.meta.env.VITE_CONTROL_PLANE_API_URL}/ai/usage-insights`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ analysis_type: analysisType })
        }
      );
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Failed to load analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const analysisButtons = [
    { type: 'ttv' as const, label: 'Time to Value', subtitle: 'Onboarding Speed', icon: Clock, gradient: 'from-blue-500 to-cyan-500' },
    { type: 'cltv' as const, label: 'CLTV Projection', subtitle: 'Revenue Forecast', icon: DollarSign, gradient: 'from-purple-500 to-pink-500' },
    { type: 'feature_adoption' as const, label: 'Feature Adoption', subtitle: 'Usage Rates', icon: TrendingUp, gradient: 'from-green-500 to-teal-500' },
    { type: 'engagement' as const, label: 'User Engagement', subtitle: 'Activity Scores', icon: Users, gradient: 'from-orange-500 to-red-500' },
    { type: 'at_risk' as const, label: 'At-Risk Features', subtitle: 'Declining Usage', icon: AlertTriangle, gradient: 'from-red-500 to-rose-500' },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent mb-2">
          Usage Insights Dashboard
        </h1>
        <p className="text-slate-300">Advanced analytics: TTV, CLTV, engagement, and feature health</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {analysisButtons.map(({ type, label, subtitle, icon: Icon, gradient }) => (
          <Button
            key={type}
            onClick={() => loadAnalysis(type)}
            disabled={loading}
            className={`h-auto py-4 bg-gradient-to-r ${gradient} hover:opacity-90 transition-all ${
              currentAnalysis === type 
                ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-900 scale-105 shadow-2xl shadow-white/20' 
                : 'hover:scale-102'
            }`}
          >
            <div className="flex flex-col items-center gap-2">
              <Icon className="w-5 h-5" />
              <div className="text-sm font-medium">{label}</div>
              <div className="text-xs opacity-90">{subtitle}</div>
            </div>
          </Button>
        ))}
      </div>

      <div className="min-h-[400px]">
        {!currentAnalysis ? (
          <Card className="p-8 text-center bg-gradient-to-r from-purple-500/10 to-blue-500/10 border-purple-500/20">
            <TrendingUp className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h3 className="text-xl font-semibold mb-2">Select an Analysis Type</h3>
            <p className="text-slate-300">
              Click one of the buttons above to generate AI-powered insights about your platform usage.
            </p>
          </Card>
        ) : loading ? (
          <Card className="p-8 text-center bg-slate-800/50 border-slate-700">
            <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-slate-300">Generating {currentAnalysis.toUpperCase()} analysis...</p>
          </Card>
        ) : (
          <div className="space-y-6">
            {currentAnalysis === 'ttv' && (
              <>
                {data?.summary?.tenants_analyzed === 0 ? (
                  <Card className="p-8 bg-slate-800/50 border-slate-700">
                    <div className="text-center mb-6">
                      <Clock className="w-16 h-16 mx-auto mb-4 text-blue-400" />
                      <h3 className="text-xl font-semibold mb-2">No Time to Value Data Available</h3>
                      <p className="text-slate-300">
                        No tenant activity found in the specified date range. Please ensure tenants have interacted with the platform.
                      </p>
                    </div>
                    {data?.recommendations && data.recommendations.length > 0 && (
                      <div className="mt-6 pt-6 border-t border-slate-700">
                        <h4 className="text-lg font-semibold mb-3 flex items-center gap-2">
                          <AlertTriangle className="w-5 h-5 text-yellow-400" />
                          Recommendations
                        </h4>
                        <div className="space-y-3">
                          {data.recommendations.map((rec: any, i: number) => (
                            <div key={i} className="p-4 bg-slate-700/30 rounded-lg text-left">
                              <div className="flex items-start gap-3">
                                <Badge variant={rec.priority === 'high' ? 'destructive' : 'secondary'}>
                                  {rec.priority}
                                </Badge>
                                <div className="flex-1">
                                  <div className="font-medium mb-1">{rec.action}</div>
                                  <div className="text-sm text-slate-400">{rec.rationale}</div>
                                  {rec.expected_impact && (
                                    <div className="text-xs text-slate-500 mt-1">Impact: {rec.expected_impact}</div>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                      <Card className="p-4 bg-slate-800/50 border-slate-700">
                        <div className="text-slate-400 text-sm">Mean TTV</div>
                        <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.mean_ttv_days?.toFixed(1) || '0.0'} days</div>
                      </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700">
                    <div className="text-slate-400 text-sm">Median TTV</div>
                    <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.median_ttv_days?.toFixed(1) || '0.0'} days</div>
                  </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700">
                    <div className="text-slate-400 text-sm">25th Percentile</div>
                    <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.percentile_25?.toFixed(1) || '0.0'} days</div>
                  </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700">
                    <div className="text-slate-400 text-sm">75th Percentile</div>
                    <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.percentile_75?.toFixed(1) || '0.0'} days</div>
                  </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700">
                    <div className="text-slate-400 text-sm">90th Percentile</div>
                    <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.percentile_90?.toFixed(1) || '0.0'} days</div>
                  </Card>
                </div>

                {data?.tenant_analysis && data.tenant_analysis.length > 0 && (
                  <Card className="p-6 bg-slate-800/50 border-slate-700">
                    <h3 className="text-lg font-semibold mb-4">Tenant Time to Value</h3>
                    <div className="space-y-3">
                      {data.tenant_analysis.filter((t: any) => t.ttv_days != null).map((tenant: any) => {
                        const performance = tenant.performance_vs_platform;
                        const performanceColor = performance === 'above_average' ? 'text-green-400' : performance === 'average' ? 'text-amber-400' : 'text-red-400';
                        const performanceBadgeVariant = performance === 'above_average' ? 'default' : performance === 'average' ? 'secondary' : 'destructive';
                        const performanceBadgeClass = performance === 'above_average' ? 'bg-green-600' : performance === 'average' ? 'bg-amber-600' : 'bg-red-600';
                        
                        return (
                        <div key={tenant.tenant_id} className="p-4 bg-slate-700/30 rounded-lg">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <div className="font-semibold text-lg">{tenant.tenant_name || tenant.tenant_id}</div>
                              <div className="flex gap-2 mt-1">
                                <Badge variant="secondary">{tenant.tier}</Badge>
                                <Badge variant={performanceBadgeVariant} className={performanceBadgeClass}>
                                  {tenant.performance_vs_platform?.replace('_', ' ')}
                                </Badge>
                                {tenant.status === 'no_interaction_yet' && (
                                  <Badge variant="outline" className="bg-orange-900/30 text-orange-400">Not yet active</Badge>
                                )}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className={`text-3xl font-bold ${performanceColor}`}>
                                {tenant.status === 'no_interaction_yet' ? 'N/A' : `${tenant.ttv_days?.toFixed(1)} days`}
                              </div>
                              {tenant.percentile_rank && (
                                <div className="text-xs text-slate-400 mt-1">Top {tenant.percentile_rank}%</div>
                              )}
                            </div>
                          </div>
                          
                          {(tenant.comparison_to_mean || tenant.comparison_to_tier) && (
                            <div className="grid grid-cols-2 gap-2 mb-3">
                              {tenant.comparison_to_mean && (
                                <div className="bg-slate-800/50 rounded p-2">
                                  <div className="text-xs text-slate-400">vs Platform Average</div>
                                  <div className={`text-sm font-medium ${performanceColor}`}>{tenant.comparison_to_mean}</div>
                                </div>
                              )}
                              {tenant.comparison_to_tier && (
                                <div className="bg-slate-800/50 rounded p-2">
                                  <div className="text-xs text-slate-400">vs Tier Average</div>
                                  <div className={`text-sm font-medium ${performanceColor}`}>{tenant.comparison_to_tier}</div>
                                </div>
                              )}
                            </div>
                          )}

                          {tenant.insights && tenant.insights.length > 0 && (
                            <div className="bg-slate-800/50 rounded p-3">
                              <div className="text-xs font-semibold text-slate-300 mb-2">Key Insights:</div>
                              <ul className="space-y-1">
                                {tenant.insights.map((insight: string, idx: number) => (
                                  <li key={idx} className="text-sm text-slate-400 flex items-start">
                                    <span className="text-blue-400 mr-2">•</span>
                                    {insight}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                        );
                      })}
                    </div>
                  </Card>
                )}
                  </>
                )}
              </>
            )}

            {currentAnalysis === 'cltv' && (() => {
              const tenants = data?.data?.tenant_projections || [];

              const getSegmentLabel = (segment: string) => {
                return segment.replace('_', ' ');
              };

              if (tenants.length === 0) {
                return (
                  <Card className="p-8 text-center bg-slate-800/50 border-slate-700">
                    <DollarSign className="w-16 h-16 mx-auto mb-4 text-purple-400" />
                    <h3 className="text-xl font-semibold mb-2">No CLTV Projections Available</h3>
                    <p className="text-slate-300">
                      There are no CLTV projections available yet. Data will appear once tenant usage patterns are established.
                    </p>
                  </Card>
                );
              }

              return (
                <Card className="p-6 bg-slate-800/50 border-slate-700">
                  <h3 className="text-lg font-semibold mb-4">12-Month CLTV Projections</h3>
                  <div className="space-y-3">
                    {tenants.map((tenant: any) => (
                      <div key={tenant.tenant_id} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                        <div className="flex-1">
                          <div className="font-medium">{tenant.tenant_name}</div>
                          <div className="text-sm text-slate-400">
                            {tenant.tier} tier • Retention: {(tenant.retention_rate * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-white">${tenant.projected_cltv_12m?.toFixed(2)}</div>
                          <Badge variant="secondary" className="text-xs capitalize">
                            {getSegmentLabel(tenant.segment)}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              );
            })()}

            {currentAnalysis === 'engagement' && (
              <>
                {!data?.summary?.platform_benchmark?.mean_engagement_score || data.summary.platform_benchmark.mean_engagement_score === 0 ? (
                  <Card className="p-8 text-center bg-slate-800/50 border-slate-700">
                    <Users className="w-16 h-16 mx-auto mb-4 text-orange-400" />
                    <h3 className="text-xl font-semibold mb-2">No User Engagement Data Available</h3>
                    <p className="text-slate-300">
                      There is no user engagement data available yet. Data will appear once users start interacting with the platform.
                    </p>
                  </Card>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card className="p-4 bg-slate-800/50 border-slate-700">
                        <div className="text-slate-400 text-sm">Mean Engagement</div>
                        <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.mean_engagement_score?.toFixed(1) || '0.0'}</div>
                      </Card>
                      <Card className="p-4 bg-slate-800/50 border-slate-700">
                        <div className="text-slate-400 text-sm">Median Engagement</div>
                        <div className="text-2xl font-bold">{data?.summary?.platform_benchmark?.median_engagement_score?.toFixed(1) || '0.0'}</div>
                      </Card>
                    </div>

                {data?.tenant_analysis && data.tenant_analysis.length > 0 && (
                  <Card className="p-6 bg-slate-800/50 border-slate-700">
                    <h3 className="text-lg font-semibold mb-4">Tenant Engagement Scores</h3>
                    <div className="space-y-3">
                      {data.tenant_analysis.map((tenant: any) => {
                        const engagementTier = tenant.engagement_score > 70 ? 'high' : tenant.engagement_score < 40 ? 'low' : 'medium';
                        const tierColor = engagementTier === 'high' ? 'text-blue-400' : engagementTier === 'medium' ? 'text-cyan-400' : 'text-orange-400';
                        const TierIcon = engagementTier === 'high' ? ArrowUp : engagementTier === 'medium' ? ArrowRight : ArrowDown;
                        
                        return (
                          <div key={tenant.tenant_id} className="p-4 bg-slate-700/30 rounded-lg">
                            <div className="flex justify-between items-start mb-3">
                              <div>
                                <div className="font-semibold text-lg">{tenant.tenant_name || tenant.tenant_id}</div>
                                <div className="flex gap-2 mt-1">
                                  <Badge variant="secondary">{tenant.tier} tier</Badge>
                                  <Badge variant={engagementTier === 'high' ? 'default' : 'secondary'} className="flex items-center gap-1">
                                    <TierIcon className="w-3 h-3" />
                                    {engagementTier} engagement
                                  </Badge>
                                  {tenant.status === 'no_activity' && (
                                    <Badge variant="outline" className="bg-orange-900/30 text-orange-400">No activity</Badge>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className={`text-3xl font-bold ${tierColor} flex items-center justify-end gap-2`}>
                                  {tenant.status === 'no_activity' ? 'N/A' : (
                                    <>
                                      <TierIcon className="w-6 h-6" />
                                      {tenant.engagement_score?.toFixed(1) || '0.0'}
                                    </>
                                  )}
                                </div>
                                {tenant.percentile_rank && (
                                  <div className="text-xs text-slate-400 mt-1">Top {tenant.percentile_rank}%</div>
                                )}
                              </div>
                            </div>
                            
                            {tenant.metrics && (
                              <>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                                  <div className="bg-slate-800/50 rounded p-2">
                                    <div className="text-xs text-slate-400">Total Requests</div>
                                    <div className="text-sm font-medium">{tenant.metrics.total_requests?.toLocaleString() || 0}</div>
                                  </div>
                                  <div className="bg-slate-800/50 rounded p-2">
                                    <div className="text-xs text-slate-400">Unique Users</div>
                                    <div className="text-sm font-medium">{tenant.metrics.unique_users || 0}</div>
                                  </div>
                                  <div className="bg-slate-800/50 rounded p-2">
                                    <div className="text-xs text-slate-400">Activity Frequency</div>
                                    <div className="text-sm font-medium">{tenant.metrics.activity_frequency?.toFixed(1) || 0}%</div>
                                  </div>
                                  <div className="bg-slate-800/50 rounded p-2">
                                    <div className="text-xs text-slate-400">Feature Diversity</div>
                                    <div className="text-sm font-medium">{tenant.metrics.feature_diversity?.toFixed(1) || 0}%</div>
                                  </div>
                                </div>
                                <div className="grid grid-cols-2 gap-2 mb-3">
                                  <div className="bg-slate-800/50 rounded p-2">
                                    <div className="text-xs text-slate-400">Days Active</div>
                                    <div className="text-sm font-medium">{tenant.metrics.unique_days_active || 0} / 30</div>
                                  </div>
                                  <div className="bg-slate-800/50 rounded p-2">
                                    <div className="text-xs text-slate-400">Avg Requests/Day</div>
                                    <div className="text-sm font-medium">{tenant.metrics.avg_requests_per_day?.toFixed(1) || 0}</div>
                                  </div>
                                </div>
                              </>
                            )}

                            {tenant.insights && tenant.insights.length > 0 && (
                              <div className="bg-slate-800/50 rounded p-3">
                                <div className="text-xs font-semibold text-slate-300 mb-2">Key Insights:</div>
                                <ul className="space-y-1">
                                  {tenant.insights.map((insight: string, idx: number) => (
                                    <li key={idx} className="text-sm text-slate-400 flex items-start">
                                      <span className="text-blue-400 mr-2">•</span>
                                      {insight}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {tenant.metrics?.features_list && tenant.metrics.features_list.length > 0 && (
                              <div className="bg-slate-800/50 rounded p-3 mt-3">
                                <div className="text-xs font-semibold text-slate-300 mb-2">Features Used:</div>
                                <div className="flex flex-wrap gap-1">
                                  {tenant.metrics.features_list.map((feature: string, idx: number) => (
                                    <span key={idx} className="text-xs px-2 py-1 rounded bg-blue-900/30 text-blue-300">{feature}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                )}
                  </>
                )}
              </>
            )}

            {currentAnalysis === 'feature_adoption' && (
              <>
                {!data?.data?.features || data.data.features.length === 0 ? (
                  <Card className="p-8 text-center bg-slate-800/50 border-slate-700">
                    <TrendingUp className="w-16 h-16 mx-auto mb-4 text-green-400" />
                    <h3 className="text-xl font-semibold mb-2">No Feature Adoption Data Available</h3>
                    <p className="text-slate-300">
                      There is no feature adoption data available yet. Data will appear once features are being used.
                    </p>
                  </Card>
                ) : (
                  <Card className="p-6 bg-slate-800/50 border-slate-700">
                    <h3 className="text-lg font-semibold mb-4">Feature Adoption Rates</h3>
                    <div className="space-y-3">
                      {data?.data?.features?.map((feature: any, index: number) => {
                    const adoptionRate = feature.adoption_rate || 0;
                    const isLowAdoption = adoptionRate < 20;
                    const AdoptionIcon = isLowAdoption ? XCircle : CheckCircle;
                    return (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="text-slate-400 font-mono text-sm">#{index + 1}</span>
                            <span className="font-medium">{feature.feature_name}</span>
                            {isLowAdoption && (
                              <Badge variant="destructive" className="text-xs flex items-center gap-1">
                                <XCircle className="w-3 h-3" />
                                Low Adoption
                              </Badge>
                            )}
                            {!isLowAdoption && (
                              <Badge variant="default" className="text-xs flex items-center gap-1 bg-blue-600">
                                <CheckCircle className="w-3 h-3" />
                                Good Adoption
                              </Badge>
                            )}
                          </div>
                          <div className="text-right">
                            <div className={`text-lg font-bold flex items-center justify-end gap-1 ${isLowAdoption ? 'text-orange-400' : 'text-blue-400'}`}>
                              <AdoptionIcon className="w-5 h-5" />
                              {adoptionRate.toFixed(1)}%
                            </div>
                            <div className="text-xs text-slate-400">{feature.feature_users}/{feature.active_users} users</div>
                          </div>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2 relative overflow-hidden">
                          <div 
                            className={`h-2 rounded-full ${isLowAdoption ? 'bg-orange-500' : 'bg-blue-500'}`} 
                            style={{ width: `${adoptionRate}%` }} 
                          />
                          {isLowAdoption && (
                            <div 
                              className="absolute inset-0 bg-gradient-to-r from-transparent via-orange-300/20 to-transparent"
                              style={{ 
                                backgroundSize: '20px 100%',
                                backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(251, 146, 60, 0.1) 10px, rgba(251, 146, 60, 0.1) 20px)',
                                width: `${adoptionRate}%`
                              }}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })}
                    </div>
                  </Card>
                )}
              </>
            )}

            {currentAnalysis === 'at_risk' && (
              <>
                {!data?.summary?.total_features_analyzed || data.summary.total_features_analyzed === 0 ? (
                  <Card className="p-8 text-center bg-slate-800/50 border-slate-700">
                    <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-red-400" />
                    <h3 className="text-xl font-semibold mb-2">No At-Risk Features Available</h3>
                    <p className="text-slate-300">
                      There are no at-risk features available yet. Data will appear once feature usage patterns are established.
                    </p>
                  </Card>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <Card className="p-4 bg-slate-800/50 border-slate-700">
                        <div className="text-slate-400 text-sm">Features Analyzed</div>
                        <div className="text-2xl font-bold">{data?.summary?.total_features_analyzed || 0}</div>
                      </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700">
                    <div className="text-slate-400 text-sm">At-Risk Features</div>
                    <div className="text-2xl font-bold text-orange-400 flex items-center gap-2">
                      <AlertTriangle className="w-6 h-6" />
                      {data?.summary?.at_risk_features_count || 0}
                    </div>
                  </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700 border-l-4 border-l-red-500">
                    <div className="text-slate-400 text-sm flex items-center gap-1">
                      <XCircle className="w-4 h-4" />
                      Critical Risk
                    </div>
                    <div className="text-2xl font-bold text-red-400">{data?.summary?.critical_risk_count || 0}</div>
                  </Card>
                  <Card className="p-4 bg-slate-800/50 border-slate-700 border-l-4 border-l-yellow-500">
                    <div className="text-slate-400 text-sm flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4" />
                      Moderate Risk
                    </div>
                    <div className="text-2xl font-bold text-yellow-400">{data?.summary?.moderate_risk_count || 0}</div>
                  </Card>
                </div>

                {data?.at_risk_features && data.at_risk_features.length > 0 && (
                  <Card className="p-6 bg-slate-800/50 border-slate-700">
                    <h3 className="text-lg font-semibold mb-4">At-Risk Features</h3>
                    <div className="space-y-3">
                      {data.at_risk_features.map((feature: any, index: number) => {
                        const riskColor = feature.risk_level === 'critical' ? 'text-red-400' : 'text-yellow-400';
                        const riskBg = feature.risk_level === 'critical' ? 'bg-red-900/30' : 'bg-yellow-900/30';
                        const riskBorder = feature.risk_level === 'critical' ? 'border-l-red-500 border-l-4' : 'border-l-yellow-500 border-l-4';
                        const RiskIcon = feature.risk_level === 'critical' ? XCircle : AlertTriangle;
                        
                        return (
                          <div key={index} className={`${riskBg} border border-slate-700/50 ${riskBorder} rounded-lg p-4`}>
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex-1">
                                <div className="font-semibold text-lg mb-1 flex items-center gap-2">
                                  <RiskIcon className="w-5 h-5" />
                                  {feature.feature_name}
                                </div>
                                <Badge variant={feature.risk_level === 'critical' ? 'destructive' : 'secondary'} className="capitalize flex items-center gap-1 w-fit">
                                  <RiskIcon className="w-3 h-3" />
                                  {feature.risk_level} Risk
                                </Badge>
                              </div>
                              <div className="text-right">
                                <div className="text-sm text-slate-400">Decline Rate</div>
                                <div className={`text-xl font-bold ${riskColor} flex items-center justify-end gap-1`}>
                                  <ArrowDown className="w-5 h-5" />
                                  {feature.decline_rate?.toFixed(1)}%
                                </div>
                              </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-3 mb-3">
                              <div className="bg-slate-800/50 rounded p-2">
                                <div className="text-xs text-slate-400">Adoption Rate</div>
                                <div className="text-sm font-medium">{feature.adoption_rate?.toFixed(1)}%</div>
                              </div>
                              <div className="bg-slate-800/50 rounded p-2">
                                <div className="text-xs text-slate-400">Current Users</div>
                                <div className="text-sm font-medium">{feature.current_period_summary?.unique_users || 0}</div>
                              </div>
                            </div>

                            {feature.trend_analysis && (
                              <div className="bg-slate-800/50 rounded p-3 mb-3">
                                <div className="text-xs font-semibold text-slate-300 mb-1">Trend Analysis:</div>
                                <div className="text-sm text-slate-400">{feature.trend_analysis}</div>
                              </div>
                            )}

                            {feature.key_insights && feature.key_insights.length > 0 && (
                              <div className="bg-slate-800/50 rounded p-3">
                                <div className="text-xs font-semibold text-slate-300 mb-2">Key Insights:</div>
                                <ul className="space-y-1">
                                  {feature.key_insights.map((insight: string, idx: number) => (
                                    <li key={idx} className="text-sm text-slate-400 flex items-start gap-2">
                                      <RiskIcon className={`${riskColor} w-4 h-4 flex-shrink-0 mt-0.5`} />
                                      {insight}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                )}
                  </>
                )}
              </>
            )}

            {data?.recommendations && data.recommendations.length > 0 && (() => {
              // Don't show recommendations if we're in a "no data" state
              const hasNoData = (
                (currentAnalysis === 'ttv' && (!data?.summary?.platform_benchmark?.mean_ttv_days || data.summary.platform_benchmark.mean_ttv_days === 0)) ||
                (currentAnalysis === 'cltv' && (!data?.data?.tenant_projections || data.data.tenant_projections.length === 0)) ||
                (currentAnalysis === 'engagement' && (!data?.summary?.platform_benchmark?.mean_engagement_score || data.summary.platform_benchmark.mean_engagement_score === 0)) ||
                (currentAnalysis === 'feature_adoption' && (!data?.data?.features || data.data.features.length === 0)) ||
                (currentAnalysis === 'at_risk' && (!data?.summary?.total_features_analyzed || data.summary.total_features_analyzed === 0))
              );
              
              if (hasNoData) return null;
              
              return (
                <Card className="p-6 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border-purple-500/20">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-purple-400" />
                    AI Recommendations
                  </h3>
                  <div className="space-y-3">
                    {data.recommendations.map((rec: any, i: number) => (
                      <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                        <div className="flex items-start gap-3">
                          <Badge variant={rec.priority === 'high' ? 'destructive' : 'secondary'}>
                            {rec.priority}
                          </Badge>
                          <div className="flex-1">
                            <div className="font-medium mb-1">{rec.action?.replace(/_/g, ' ') || rec.action}</div>
                            <div className="text-sm text-slate-300">{rec.description || rec.rationale}</div>
                            {rec.expected_impact && (
                              <div className="text-xs text-slate-400 mt-1">Impact: {rec.expected_impact}</div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
