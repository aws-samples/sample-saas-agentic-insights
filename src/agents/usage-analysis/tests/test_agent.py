import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add the tools directory to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from tenant_usage_analyzer import analyze_tenant_usage
from feature_adoption_analyzer import analyze_feature_adoption
from performance_analyzer import analyze_performance_metrics
from ai_usage_analyzer import analyze_ai_usage


class TestUsageAnalysisAgent:
    """Test suite for Usage Analysis Agent tools"""
    
    def setup_method(self):
        """Set up test environment"""
        # Mock environment variables
        os.environ['METRICS_AGGREGATION_TABLE_NAME'] = 'test-metrics-table'
    
    @patch('tenant_usage_analyzer.boto3.resource')
    def test_analyze_tenant_usage_basic(self, mock_boto3):
        """Test basic tenant usage analysis"""
        
        # Mock DynamoDB response
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'api_gateway_requests',
                    'total_count': 100,
                    'estimated_cost': 0.05,
                    'tier_name': 'basic'
                },
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'lambda_executions',
                    'total_count': 50,
                    'estimated_cost': 0.02,
                    'tier_name': 'basic'
                }
            ]
        }
        
        # Test tenant admin analysis
        result = analyze_tenant_usage(
            tenant_id='test-tenant-123',
            user_role='tenant_admin'
        )
        
        assert result['tenant_id'] == 'test-tenant-123'
        assert result['user_role'] == 'tenant_admin'
        assert 'usage_summary' in result
        assert 'insights' in result
        assert result['usage_summary']['api_requests'] == 100
        assert result['usage_summary']['lambda_executions'] == 50
    
    @patch('tenant_usage_analyzer.boto3.resource')
    def test_analyze_tenant_usage_platform_admin(self, mock_boto3):
        """Test platform admin usage analysis"""
        
        # Mock DynamoDB response for platform-wide data
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'tenant_id': 'tenant-1',
                    'metric_name': 'api_gateway_requests',
                    'total_count': 100,
                    'estimated_cost': 0.05,
                    'tier_name': 'basic'
                },
                {
                    'tenant_id': 'tenant-2',
                    'metric_name': 'api_gateway_requests',
                    'total_count': 200,
                    'estimated_cost': 0.10,
                    'tier_name': 'premium'
                }
            ]
        }
        
        # Test platform admin analysis
        result = analyze_tenant_usage(
            tenant_id='all',
            user_role='platform_admin'
        )
        
        assert result['tenant_id'] == 'all'
        assert result['user_role'] == 'platform_admin'
        assert 'usage_summary' in result
        assert 'platform_totals' in result['usage_summary']
        assert result['usage_summary']['platform_totals']['tenant_count'] == 2
    
    @patch('feature_adoption_analyzer.boto3.resource')
    def test_analyze_feature_adoption(self, mock_boto3):
        """Test feature adoption analysis"""
        
        # Mock DynamoDB response
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'product_operations',
                    'total_count': 50,
                    'estimated_cost': 0.02
                },
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'bedrock_invocations',
                    'total_count': 10,
                    'estimated_cost': 0.15
                }
            ]
        }
        
        result = analyze_feature_adoption(
            tenant_id='test-tenant-123',
            scope='tenant',
            user_role='tenant_admin'
        )
        
        assert result['tenant_id'] == 'test-tenant-123'
        assert result['scope'] == 'tenant'
        assert 'adoption_summary' in result
        assert 'recommendations' in result
    
    @patch('performance_analyzer.boto3.resource')
    def test_analyze_performance_metrics(self, mock_boto3):
        """Test performance metrics analysis"""
        
        # Mock DynamoDB response
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'api_gateway_requests',
                    'total_count': 1000,
                    'estimated_cost': 0.50
                },
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'lambda_executions',
                    'total_count': 500,
                    'estimated_cost': 0.25
                }
            ]
        }
        
        result = analyze_performance_metrics(
            tenant_id='test-tenant-123',
            metrics_type=['response_time', 'throughput']
        )
        
        assert result['tenant_id'] == 'test-tenant-123'
        assert 'performance_summary' in result
        assert 'optimization_opportunities' in result
        assert 'recommendations' in result
    
    @patch('ai_usage_analyzer.boto3.resource')
    def test_analyze_ai_usage(self, mock_boto3):
        """Test AI usage analysis"""
        
        # Mock DynamoDB response
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'bedrock_input_tokens',
                    'total_count': 5000,
                    'estimated_cost': 0.10
                },
                {
                    'tenant_id': 'test-tenant-123',
                    'metric_name': 'bedrock_output_tokens',
                    'total_count': 3000,
                    'estimated_cost': 0.15
                }
            ]
        }
        
        result = analyze_ai_usage(
            tenant_id='test-tenant-123',
            include_cost_analysis=True
        )
        
        assert result['tenant_id'] == 'test-tenant-123'
        assert 'ai_usage_summary' in result
        assert 'cost_analysis' in result
        assert 'recommendations' in result
    
    def test_tenant_user_role_validation(self):
        """Test that tenant_user role requires user_id"""
        
        result = analyze_tenant_usage(
            tenant_id='test-tenant-123',
            user_role='tenant_user'
            # Missing user_id
        )
        
        assert 'error' in result['usage_summary']
        assert 'User ID required' in result['usage_summary']['error']
    
    @patch('tenant_usage_analyzer.boto3.resource')
    def test_error_handling(self, mock_boto3):
        """Test error handling in usage analysis"""
        
        # Mock DynamoDB exception
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.query.side_effect = Exception("DynamoDB error")
        
        result = analyze_tenant_usage(
            tenant_id='test-tenant-123',
            user_role='tenant_admin'
        )
        
        assert 'usage_summary' in result
        assert 'error' in result['usage_summary']
        assert 'Failed to retrieve tenant usage' in result['usage_summary']['error']


if __name__ == '__main__':
    pytest.main([__file__])