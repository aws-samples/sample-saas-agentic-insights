# Bedrock Agent Deployment Troubleshooting

## Issue Summary
During test-agent deployment in us-east-2, encountered model validation error that was resolved by deleting and recreating the agent.

## Timeline
- **Working Agent**: Product description agent (ZZQXX1QVQN) created Sept 13, 2025 - works perfectly
- **Failed Agent**: Test agent (SYACXCFUQO) created Oct 6, 2025 - model validation error
- **Working Agent**: Test agent (VABRFMUZZK) created Oct 6, 2025 (after deletion) - works perfectly

## Error Details
```
validationException: Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 
with on-demand throughput isn't supported. Retry your request with the ID or ARN 
of an inference profile that contains this model.
```

## Investigation Findings

### What We Tried
1. ✅ **Model ID Verification**: Both working and failing agents used identical model ID
2. ✅ **Agent Preparation**: Manually prepared failing agent - still failed
3. ✅ **IAM Permissions**: Updated Lambda permissions - still failed
4. ✅ **Agent Status**: Both agents showed "PREPARED" status
5. ✅ **Delete/Recreate**: This fixed the issue

### Root Cause Analysis
- **Not a model availability issue**: Same model ID worked for both agents
- **Not a preparation issue**: Manual preparation didn't fix it
- **Not a timing issue**: Agents created 40 minutes apart, both failed/succeeded immediately
- **Likely AWS service state**: Some transient backend configuration issue

## Troubleshooting Guide

### For New Region Deployments

#### Step 1: Check Model Availability
```bash
aws bedrock list-foundation-models --region <region> \
  --query 'modelSummaries[?contains(modelId, `claude-3-haiku`)]' --output table
```

#### Step 2: Verify Inference Profile
```bash
aws bedrock list-inference-profiles --region <region> \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `claude-3-haiku`)]'
```

#### Step 3: Test Agent Invocation
```bash
# Test via insight dashboard API
curl -X POST <API_URL>/insight-dashboard \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "simple-cost-analysis"}'
```

#### Step 4: If Model Validation Error Occurs
```bash
# Nuclear option - delete and recreate
cdk destroy AgenticInsightsTestAgent --force
./scripts/deploy-test-agent.sh
```

#### Step 5: Manual Preparation (Last Resort)
```bash
# Only if CDK doesn't auto-prepare
aws bedrock-agent prepare-agent --region <region> --agent-id <AGENT_ID>
```

## Recommendations

### ❌ Don't Add to Deployment Script
- Agent preparation should be automatic via CDK
- Adding manual preparation suggests working around CDK issues
- Increases deployment time and complexity
- May cause race conditions

### ✅ Document Manual Fix
- Keep troubleshooting steps in documentation
- Use manual preparation only when automatic fails
- Monitor if this becomes a pattern across regions

### ✅ Test After Deployment
Consider adding simple test to deployment script:
```bash
# Optional: Test agent after deployment
print_status "Testing agent invocation..."
curl -s -X POST $API_URL/insight-dashboard \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "simple-cost-analysis"}' | jq .success
```

## Model Configuration Notes

### Working Configuration (us-east-2)
```yaml
# agent-config.yaml
model: us.anthropic.claude-3-haiku-20240307-v1:0
```

### Available Inference Profile
```
inferenceProfileId: us.anthropic.claude-3-haiku-20240307-v1:0
description: Routes requests to Anthropic Claude 3 Haiku in us-east-1, us-west-2 and us-east-2
status: ACTIVE
```

## Action Items

- [ ] Monitor if this issue occurs in other regions
- [ ] Test deployment in us-west-2 and eu-west-1
- [ ] Consider adding automated test to verify agent works post-deployment
- [ ] Document region-specific model ID variations if found

## Related Files
- `scripts/deploy-test-agent.sh` - Deployment script
- `infra/test-agent-stack.ts` - CDK infrastructure
- `src/control-plane/agents/test-agent/` - Agent configuration
- `src/control-plane/insight-dashboard-api/handler.py` - API integration

---
**Created**: Oct 7, 2025  
**Status**: Resolved (delete/recreate worked)  
**Priority**: Low (monitor for patterns)
