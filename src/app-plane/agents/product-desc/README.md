# Product Description Agent

AI agent for generating compelling e-commerce product descriptions using Amazon Bedrock.

## Configuration

- **Model**: Claude 3 Haiku (via inference profile)
- **Purpose**: Generate 3-4 sentence product descriptions
- **Input**: Product name and short description
- **Output**: Professional, engaging product description

## Files

- `agent-config.yaml` - Agent configuration
- `instructions.txt` - Agent prompt/instructions
- `iam-policies/` - IAM policies for agent execution role

## Deployment

The agent is deployed automatically via `scripts/deploy-ai-desc-agent.sh`.

## Usage

The agent is invoked via the Lambda function in the API Gateway endpoint:
`POST /ai/generate-description`

## Costs

Claude 3 Haiku pricing (as of deployment):
- Input tokens: $0.00025 per 1K tokens
- Output tokens: $0.00125 per 1K tokens
