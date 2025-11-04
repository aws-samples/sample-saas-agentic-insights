import { useState, useEffect, useRef } from 'react';
import { RefreshCw } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function CostAnalysis() {
  const [loading, setLoading] = useState(true);
  const [trends, setTrends] = useState<string[]>(['Loading trends...']);
  const [predictions, setPredictions] = useState<string[]>(['Loading predictions...']);
  const [recommendations, setRecommendations] = useState<string[]>(['Loading AI recommendations...']);
  const trendChartRef = useRef<HTMLCanvasElement>(null);
  const predictionChartRef = useRef<HTMLCanvasElement>(null);
  const tierComparisonChartRef = useRef<HTMLCanvasElement>(null);
  const growthHeatmapChartRef = useRef<HTMLCanvasElement>(null);
  const efficiencyChartRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    loadInsightData();
  }, []);

  const loadInsightData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_CONTROL_PLANE_API_URL}/insight-dashboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ analysis_type: 'simple-cost-analysis' })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      
      const result = await response.json();
      if (!result.analysis) throw new Error('No analysis data in response');
      
      const analysisData = JSON.parse(result.analysis);
      
      setTrends(analysisData.trends || []);
      setPredictions(analysisData.predictions || []);
      setRecommendations(analysisData.recommendations || []);
      
      // Initialize charts after data loads
      setTimeout(initializeCharts, 100);
    } catch (error) {
      console.error('Error loading insights:', error);
      setTrends(['Failed to load AI insights']);
      setPredictions(['Error loading predictions']);
      setRecommendations(['Error loading recommendations']);
    } finally {
      setLoading(false);
    }
  };

  const initializeCharts = () => {
    if (!window.Chart) return;

    // Trend Chart
    if (trendChartRef.current) {
      new window.Chart(trendChartRef.current, {
        type: 'line',
        data: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Monthly Costs ($)',
            data: [1200, 1350, 1500, 1650, 1800, 2000],
            borderColor: '#8B5CF6',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: '#fff' } } },
          scales: {
            x: { ticks: { color: '#fff' } },
            y: { ticks: { color: '#fff' } }
          }
        }
      });
    }

    // Prediction Chart
    if (predictionChartRef.current) {
      new window.Chart(predictionChartRef.current, {
        type: 'bar',
        data: {
          labels: ['Basic Tier', 'Premium Tier', 'AI Features'],
          datasets: [{
            label: 'Projected Costs ($)',
            data: [800, 1200, 150],
            backgroundColor: ['#06B6D4', '#8B5CF6', '#F59E0B']
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: '#fff' } } },
          scales: {
            x: { ticks: { color: '#fff' } },
            y: { ticks: { color: '#fff' } }
          }
        }
      });
    }

    // Tier Comparison Chart
    if (tierComparisonChartRef.current) {
      new window.Chart(tierComparisonChartRef.current, {
        type: 'line',
        data: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
          datasets: [{
            label: 'Basic Tier ($29)',
            data: [15, 16, 14, 17, 15, 18, 16, 19, 17, 20, 18, 21],
            borderColor: '#06B6D4',
            backgroundColor: 'rgba(6, 182, 212, 0.1)'
          }, {
            label: 'Premium Tier ($99)',
            data: [45, 48, 42, 50, 47, 52, 49, 55, 51, 58, 54, 60],
            borderColor: '#8B5CF6',
            backgroundColor: 'rgba(139, 92, 246, 0.1)'
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: '#fff' } } },
          scales: {
            x: { ticks: { color: '#fff' } },
            y: { ticks: { color: '#fff' } }
          }
        }
      });
    }

    // Growth Heatmap Chart
    if (growthHeatmapChartRef.current) {
      new window.Chart(growthHeatmapChartRef.current, {
        type: 'bar',
        data: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
          datasets: [{
            label: 'Margin Change ($)',
            data: [2, -1, 3, 1, -2, 4, 2, 3, -1, 5, 2, 3],
            backgroundColor: (ctx: any) => ctx.parsed.y >= 0 ? '#10B981' : '#EF4444'
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: '#fff' } } },
          scales: {
            x: { ticks: { color: '#fff' } },
            y: { ticks: { color: '#fff' } }
          }
        }
      });
    }

    // Efficiency Chart
    if (efficiencyChartRef.current) {
      new window.Chart(efficiencyChartRef.current, {
        type: 'line',
        data: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
          datasets: [{
            label: 'Basic Tier Efficiency',
            data: [0.65, 0.63, 0.67, 0.62, 0.65, 0.60, 0.64, 0.59, 0.63, 0.58, 0.62, 0.57],
            borderColor: '#06B6D4'
          }, {
            label: 'Premium Tier Efficiency',
            data: [0.55, 0.53, 0.57, 0.52, 0.55, 0.50, 0.54, 0.49, 0.53, 0.48, 0.52, 0.47],
            borderColor: '#8B5CF6'
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: '#fff' } } },
          scales: {
            x: { ticks: { color: '#fff' } },
            y: { ticks: { color: '#fff' } }
          }
        }
      });
    }
  };

  if (loading) {
    return (
      <div className="cost-analysis-dashboard">
        {/* Header */}
        <div className="dashboard-header flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Cost Analysis Dashboard</h1>
          <Button disabled>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Data
          </Button>
        </div>

        {/* Two Main Sections */}
        <div className="main-sections grid lg:grid-cols-2 gap-8 mb-8">
          <Card className="section">
            <CardHeader>
              <CardTitle>📈 Trend Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full mb-6" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            </CardContent>
          </Card>
          <Card className="section">
            <CardHeader>
              <CardTitle>🔮 AI Predictions</CardTitle>
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full mb-6" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-4/5" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Advanced Analytics Grid */}
        <div className="advanced-charts-grid space-y-8 mb-8">
          {[
            '📊 Tier Profitability Comparison (12 Months)',
            '📈 Month-over-Month Margin Variation',
            '⚖️ Revenue Efficiency Index (12 Months)'
          ].map((title, i) => (
            <Card key={i} className="chart-row-full">
              <CardHeader>
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-64 w-full mb-4" />
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>

        {/* AI Recommendations */}
        <Card className="section">
          <CardHeader>
            <CardTitle>🤖 AI Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/5" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="cost-analysis-dashboard">
      {/* Header */}
      <div className="dashboard-header flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Cost Analysis Dashboard</h1>
        <Button
          onClick={loadInsightData}
          className="refresh-btn"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh Data
        </Button>
      </div>

      {/* Two Main Sections */}
      <div className="main-sections grid lg:grid-cols-2 gap-8 mb-8">
        {/* Trend Analysis Section */}
        <Card className="section trend-section">
          <CardHeader>
            <CardTitle>📈 Trend Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container mb-6">
              <canvas ref={trendChartRef} className="w-full h-64"></canvas>
            </div>
            <div className="insights-list">
              <ul className="space-y-2">
                {trends.map((trend, index) => (
                  <li key={index} className="flex items-start">
                    <span className="w-2 h-2 bg-purple-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                    <span className="text-gray-300">{trend}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* AI Predictions Section */}
        <Card className="section prediction-section">
          <CardHeader>
            <CardTitle>🔮 AI Predictions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container mb-6">
              <canvas ref={predictionChartRef} className="w-full h-64"></canvas>
            </div>
            <div className="insights-list">
              <ul className="space-y-2">
                {predictions.map((prediction, index) => (
                  <li key={index} className="flex items-start">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                    <span className="text-gray-300">{prediction}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Advanced Analytics Grid */}
      <div className="advanced-charts-grid space-y-8 mb-8">
        {/* Row 1: Full Width Tier Comparison */}
        <Card className="chart-row-full section chart-widget-full">
          <CardHeader>
            <CardTitle>📊 Tier Profitability Comparison (12 Months)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container mb-4">
              <canvas ref={tierComparisonChartRef} className="w-full h-64"></canvas>
            </div>
            <div className="chart-explanation text-sm text-muted-foreground">
              Shows profit margins for Basic ($29) and Premium ($99) tiers over time. Higher lines mean better profitability. Example: $15 margin means $15 profit per customer.
            </div>
          </CardContent>
        </Card>

        {/* Row 2: Full Width Margin Variation */}
        <Card className="chart-row-full section chart-widget-full">
          <CardHeader>
            <CardTitle>📈 Month-over-Month Margin Variation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container mb-4">
              <canvas ref={growthHeatmapChartRef} className="w-full h-64"></canvas>
            </div>
            <div className="chart-explanation text-sm text-muted-foreground">
              Shows monthly profit changes in dollars. Green bars mean profit increased, red bars mean profit decreased. Example: +$5 means $5 more profit than last month.
            </div>
          </CardContent>
        </Card>

        {/* Row 3: Full Width Revenue Efficiency Index */}
        <Card className="chart-row-full section chart-widget-full">
          <CardHeader>
            <CardTitle>⚖️ Revenue Efficiency Index (12 Months)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="chart-container mb-4">
              <canvas ref={efficiencyChartRef} className="w-full h-64"></canvas>
            </div>
            <div className="chart-explanation text-sm text-muted-foreground">
              Shows how much it costs to generate a dollar of revenue tier-wise. Keep below 1.0 for profit. Example: 0.65 means 65¢ cost per $1 revenue, so 35¢ profit.
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI Recommendations Section */}
      <Card className="section optimizations-section">
        <CardHeader>
          <CardTitle>🤖 AI Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="insights-list">
            <ul className="space-y-2">
              {recommendations.map((recommendation, index) => (
                <li key={index} className="flex items-start">
                  <span className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <span className="text-gray-300">{recommendation}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
