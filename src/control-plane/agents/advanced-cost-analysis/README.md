# Advanced Cost Analysis Agent

## Overview
Expert SaaS cost analyst agent for the Agentic Insights platform, specializing in financial forecasting and optimization insights.

## Capabilities
- Historical cost usage analysis
- Monthly usage data exploration
- Core SaaS metrics calculation (Cost per tenant, Margin, margin %)
- Financial forecasting and predictions
- Tenant profitability analysis
- Infrastructure optimization recommendations

## Model
- **Engine**: Claude 3 Haiku
- **Pricing**: $0.25/M input tokens, $1.25/M output tokens
- **Action Groups**: None (relies on built-in knowledge)

## Integration
- Called via insight-dashboard-api with `analysis_type: 'cost-analysis'`
- Frontend: Cost Analysis dashboard in admin panel

## Usage
The agent provides actionable recommendations with specific cost impact estimates for SaaS profitability optimization.
