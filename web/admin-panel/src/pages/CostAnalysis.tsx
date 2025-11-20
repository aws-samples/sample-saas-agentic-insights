import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { RefreshCw, TrendingUp, Sparkles, Lightbulb } from 'lucide-react';

interface CostData {
  trends: string[];
  predictions: string[];
  recommendations: string[];
  cost_per_tenant_averages: Array<{
    month: string;
    tier: string;
    cost: number;
    revenue: number;
    margin: number;
  }>;
  cost_per_tenant_predictions: Array<{
    month: string;
    tier: string;
    predicted_cost: number;
    revenue: number;
    predicted_margin: number;
  }>;
  enable_advanced_insights?: boolean;
}

export default function CostAnalysis() {
  const [data, setData] = useState<CostData>({
    trends: [],
    predictions: [],
    recommendations: [],
    cost_per_tenant_averages: [],
    cost_per_tenant_predictions: [],
  });
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('adminToken');
      console.log('Cost Analysis - API URL:', import.meta.env.VITE_CONTROL_PLANE_API_URL);
      console.log('Cost Analysis - Token:', token ? 'exists' : 'missing');
      
      const response = await fetch(
        `${import.meta.env.VITE_CONTROL_PLANE_API_URL}/insight-dashboard`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ analysis_type: 'cost-analysis' })
        }
      );
      
      console.log('Cost Analysis - Response status:', response.status);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Cost Analysis - API Error:', errorText);
        throw new Error(`API Error: ${response.status} - ${errorText}`);
      }
      
      const result = await response.json();
      console.log('Cost Analysis - Full response:', result);
      const analysis = result.analysis || {};
      setData({
        trends: analysis.trends || [],
        predictions: analysis.predictions || [],
        recommendations: analysis.recommendations || [],
        cost_per_tenant_averages: analysis.cost_per_tenant_averages || [],
        cost_per_tenant_predictions: analysis.cost_per_tenant_predictions || [],
        enable_advanced_insights: analysis.enable_advanced_insights
      });
    } catch (error) {
      console.error('Failed to load cost analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Transform data for charts
  const historicalChartData = data.cost_per_tenant_averages.reduce((acc, item) => {
    const existing = acc.find(d => d.month === item.month);
    if (existing) {
      existing[`${item.tier}_cost`] = item.cost;
      existing[`${item.tier}_margin`] = item.margin;
    } else {
      acc.push({
        month: item.month,
        [`${item.tier}_cost`]: item.cost,
        [`${item.tier}_margin`]: item.margin,
      });
    }
    return acc;
  }, [] as any[]);

  const predictionChartData = data.cost_per_tenant_predictions.reduce((acc, item) => {
    const existing = acc.find(d => d.month === item.month);
    if (existing) {
      existing[`${item.tier}_predicted_cost`] = item.predicted_cost;
      existing[`${item.tier}_predicted_margin`] = item.predicted_margin;
    } else {
      acc.push({
        month: item.month,
        [`${item.tier}_predicted_cost`]: item.predicted_cost,
        [`${item.tier}_predicted_margin`]: item.predicted_margin,
      });
    }
    return acc;
  }, [] as any[]);

  // Combined chart data - merge and bridge historical to predictions
  const combinedChartData = [...historicalChartData, ...predictionChartData]
    .reduce((acc: any[], item: any) => {
      const existing = acc.find((d: any) => d.month === item.month);
      if (existing) {
        Object.assign(existing, item);
      } else {
        acc.push({ ...item });
      }
      return acc;
    }, [])
    .sort((a: any, b: any) => a.month.localeCompare(b.month))
    .map((item: any, i: number, arr: any[]) => {
      // Bridge: extend historical line to first prediction point
      if (i > 0 && !arr[i-1].basic_predicted_margin && item.basic_predicted_margin) {
        item.basic_margin = item.basic_predicted_margin;
        item.premium_margin = item.premium_predicted_margin;
      }
      return item;
    });

  return (
    <>
      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 flex items-center space-x-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            <span className="text-white">Loading insights...</span>
          </div>
        </div>
      )}
      
      <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            Cost Analysis Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">v2.0.1 - {new Date().toLocaleString()}</p>
        </div>
        <Button 
          onClick={loadData} 
          disabled={loading}
          className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh Data
        </Button>
      </div>

      {/* Main Sections - Conditional rendering based on data availability */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Analysis */}
        <Card className="p-6 bg-slate-800/50 border-slate-700">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-semibold">Trend Analysis</h2>
          </div>
          <div className="text-center text-sm text-slate-300 mb-1 mt-1">Historical Cost per Tenant Trends</div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={historicalChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" stroke="#9CA3AF" label={{ value: 'Time (Month)', position: 'insideBottom', offset: -5 }} />
              <YAxis stroke="#9CA3AF" label={{ value: 'Cost per Tenant ($)', angle: -90, position: 'insideLeft' }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#F3F4F6' }}
              />
              <Legend verticalAlign="top" height={36} />
              <Line type="monotone" dataKey="basic_cost" stroke="#3B82F6" name="Basic Cost" strokeWidth={2} connectNulls />
              <Line type="monotone" dataKey="premium_cost" stroke="#8B5CF6" name="Premium Cost" strokeWidth={2} connectNulls />
            </LineChart>
          </ResponsiveContainer>
          {/* Only show trends text when sufficient data */}
          {data.cost_per_tenant_averages.length > 3 && (
            <div className="mt-4 space-y-2">
              {data.trends.map((trend, i) => (
                <div key={i} className="p-3 bg-slate-700/30 rounded-lg text-sm text-slate-200">
                  {trend}
                </div>
              ))}
            </div>
          )}
        </Card>

          {/* AI Predictions */}
          {data.predictions.length > 0 && (
            <Card className="p-6 bg-slate-800/50 border-slate-700">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <h2 className="text-xl font-semibold">AI Predictions</h2>
              </div>
              <div className="text-center text-sm text-slate-300 mb-1 mt-1">AI-Predicted Cost per Tenant</div>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={predictionChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="month" stroke="#9CA3AF" label={{ value: 'Time (Month)', position: 'insideBottom', offset: -5 }} />
                  <YAxis stroke="#9CA3AF" label={{ value: 'Cost per Tenant ($)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    labelStyle={{ color: '#F3F4F6' }}
                  />
                  <Legend verticalAlign="top" height={36} />
                  <Line type="monotone" dataKey="basic_predicted_cost" stroke="#3B82F6" strokeDasharray="5 5" name="Basic Predicted" strokeWidth={2} connectNulls />
                  <Line type="monotone" dataKey="premium_predicted_cost" stroke="#8B5CF6" strokeDasharray="5 5" name="Premium Predicted" strokeWidth={2} connectNulls />
                </LineChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {data.predictions.map((prediction, i) => (
                  <div key={i} className="p-3 bg-slate-700/30 rounded-lg text-sm text-slate-200">
                    {prediction}
                  </div>
                ))}
              </div>
            </Card>
          )}
      </div>

      {/* Advanced Insights */}
      {data.enable_advanced_insights && (
        <div className="space-y-6">
          {/* Tier Profitability Comparison */}
          <Card className="p-6 bg-slate-800/50 border-slate-700">
            <h2 className="text-xl font-semibold mb-1">📊 Tier Profitability Comparison</h2>
            <div className="text-center text-sm text-slate-300 mb-1 mt-1">Historical vs Predicted Tier Profitability (12 Months)</div>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={combinedChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" stroke="#9CA3AF" label={{ value: 'Time Period', position: 'insideBottom', offset: -5 }} />
                <YAxis stroke="#9CA3AF" label={{ value: 'Margin ($)', angle: -90, position: 'insideLeft' }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                />
                <Legend verticalAlign="top" height={36} />
                <Line type="natural" dataKey="basic_margin" stroke="#3B82F6" name="Basic Margin" strokeWidth={3} connectNulls />
                <Line type="natural" dataKey="premium_margin" stroke="#8B5CF6" name="Premium Margin" strokeWidth={3} connectNulls />
                <Line type="natural" dataKey="basic_predicted_margin" stroke="#3B82F6" strokeDasharray="5 5" name="Basic Predicted" strokeWidth={2} connectNulls />
                <Line type="natural" dataKey="premium_predicted_margin" stroke="#8B5CF6" strokeDasharray="5 5" name="Premium Predicted" strokeWidth={2} connectNulls />
              </LineChart>
            </ResponsiveContainer>
            <p className="text-sm text-slate-400 mt-2">
              Shows profit margins for Basic ($29) and Premium ($99) tiers over time. Higher lines mean better profitability.
            </p>
          </Card>

          {/* Month-over-Month Margin Variation */}
          <Card className="p-6 bg-slate-800/50 border-slate-700">
            <h2 className="text-xl font-semibold mb-1">📈 Month-over-Month Margin Variation</h2>
            <div className="text-center text-sm text-slate-300 mb-1 mt-1">Historical vs Predicted Margin Changes (12 Months)</div>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={combinedChartData.slice(1).map((item: any, i: number) => {
                const prev = combinedChartData[i];
                return {
                  month: item.month,
                  basic_change: (item.basic_margin || item.basic_predicted_margin || 0) - (prev.basic_margin || prev.basic_predicted_margin || 0),
                  premium_change: (item.premium_margin || item.premium_predicted_margin || 0) - (prev.premium_margin || prev.premium_predicted_margin || 0)
                };
              })}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" stroke="#9CA3AF" label={{ value: 'Month', position: 'insideBottom', offset: -5 }} />
                <YAxis stroke="#9CA3AF" label={{ value: 'Margin Change ($)', angle: -90, position: 'insideLeft' }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                />
                <Legend verticalAlign="top" height={36} />
                <Bar dataKey="basic_change" fill="#3B82F6" name="Basic Tier Margin Change ($)" />
                <Bar dataKey="premium_change" fill="#8B5CF6" name="Premium Tier Margin Change ($)" />
              </BarChart>
            </ResponsiveContainer>
            <p className="text-sm text-slate-400 mt-2">
              Shows monthly profit changes in dollars. Green bars mean profit increased, red bars mean profit decreased.
            </p>
          </Card>

          {/* Revenue Efficiency Index */}
          <Card className="p-6 bg-slate-800/50 border-slate-700">
            <h2 className="text-xl font-semibold mb-1">⚖️ Revenue Efficiency Index</h2>
            <div className="text-center text-sm text-slate-300 mb-1 mt-1">Historical vs Predicted Cost Efficiency (Cost per $ Revenue)</div>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={combinedChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" stroke="#9CA3AF" label={{ value: 'Time Period', position: 'insideBottom', offset: -5 }} />
                <YAxis stroke="#9CA3AF" label={{ value: 'Efficiency Ratio (Cost/Revenue)', angle: -90, position: 'insideLeft' }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                />
                <Legend verticalAlign="top" height={36} />
                <Bar dataKey="basic_cost" fill="#3B82F6" name="Basic Cost" />
                <Bar dataKey="basic_predicted_cost" fill="rgba(59, 130, 246, 0.4)" name="Basic Predicted Cost" />
                <Bar dataKey="premium_cost" fill="#8B5CF6" name="Premium Cost" />
                <Bar dataKey="premium_predicted_cost" fill="rgba(139, 92, 246, 0.4)" name="Premium Predicted Cost" />
              </BarChart>
            </ResponsiveContainer>
            <p className="text-sm text-slate-400 mt-2">
              Shows how much it costs to generate a dollar of revenue tier-wise. Keep below 1.0 for profit.
            </p>
          </Card>
        </div>
      )}

      {/* AI Recommendations */}
      {data.recommendations.length > 0 && (
        <Card className="p-6 bg-slate-800/50 border-slate-700">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="w-5 h-5 text-yellow-400" />
            <h2 className="text-xl font-semibold">AI Recommendations</h2>
          </div>
          <ul className="space-y-3">
            {data.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-3 p-3 bg-slate-700/50 rounded-lg">
                <Badge variant="secondary" className="mt-1">{i + 1}</Badge>
                <span className="text-slate-200">{rec}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      </div>
    </>
  );
}
