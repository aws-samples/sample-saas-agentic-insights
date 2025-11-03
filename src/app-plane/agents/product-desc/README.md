# Product Description Agent

AI agent for generating compelling e-commerce product descriptions using Amazon Bedrock.

## Configuration

- **Model**: Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **Purpose**: Generate 3-4 sentence product descriptions
- **Input**: Product name and short description
- **Output**: Professional, engaging product description

## Files

- `agent-config.yaml` - Agent configuration
- `instructions.txt` - Agent prompt/instructions
- `iam-policies/` - IAM policies for agent execution role

## Deployment

The agent is deployed automatically via `scripts/lab-01.2-deploy-product-description-ai-agent.sh`.

## Usage

The agent is invoked via the Lambda function in the API Gateway endpoint:
`POST /ai/generate-description`

## Costs

Claude Sonnet 4.5 pricing (as of deployment):
