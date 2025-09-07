# TODO List - Agentic Insights SaaS Platform

## 🚀 Performance Optimizations

### 1. Authorizer Caching
- **Status**: Disabled for functionality
- **Issue**: Cache conflicts between HTTP methods (GET vs POST)
- **Solution**: Re-enable with method-aware cache key
- **Implementation**: 
  ```typescript
  identitySource: 'method.request.header.Authorization,method.request.httpMethod'
  resultsCacheTtl: cdk.Duration.minutes(5)
  ```
- **Impact**: Reduces Lambda invocations and improves API response times
- **Priority**: Medium

## 📧 Email & Notifications

### 2. Custom Admin User Email Notifications
- **Status**: Currently using Cognito's default "Your temporary password" email
- **Issue**: Default Cognito email template doesn't match desired branding/content
- **Current**: Cognito sends standard welcome email + failed SES custom email attempt
- **Required**: Suppress Cognito email + Only send custom SES email
- **Implementation**:
  1. **Add `--message-action SUPPRESS`** back to `admin-create-user` command
  2. **Configure SES** with verified sender domain/email
  3. **Custom email template**:
     - Subject: "Admin user created in the Agentic Insights SaaS Platform"
     - Body: "The admin user is created. Here is the admin panel URL: {URL}, Username: {email}, Password: {password}. Thank you!"
  4. **Error handling**: Fallback to console output if SES fails
- **Benefits**: Branded email experience, consistent messaging, professional appearance
- **Priority**: Medium

## 🤖 AI Features

### 3. AI Product Description Token Counting
- **Status**: Currently returns zero token counts due to architecture mismatch
- **Issue**: tiktoken/regex dependencies fail with `No module named 'regex._regex'` - macOS ARM64 vs Linux x86_64 architecture difference
- **Current**: Simple word-based estimation workaround (`words / 0.75 ≈ tokens`)
- **Required**: Accurate token counting for proper cost calculations
- **Implementation**: Use CDK bundling with Docker for correct Lambda architecture:
  ```typescript
  code: lambda.Code.fromAsset('src/app-plane/product-desc', {
    bundling: {
      image: lambda.Runtime.PYTHON_3_11.bundlingImage,
      command: [
        'bash', '-c',
        'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
      ],
    },
  }),
  ```
- **Benefits**: Accurate token counting with tiktoken (Claude-compatible), proper cost calculations, cross-platform compatibility
- **Alternative**: Use Anthropic's official library for 100% accurate Claude token counting
- **Priority**: Medium

## 🛡️ Security Enhancements

### 4. Order Privacy - User-Specific Filtering
- **Status**: Orders show all tenant orders, not user-specific
- **Issue**: Users can see orders created by other users in the same tenant
- **Current**: Filters by `tenant_id` only in `list_orders()` function
- **Required**: Filter by both `tenant_id` AND `created_by` (current user's ID)
- **Implementation Options**:
  1. **Backend Filtering** (Recommended): Add GSI on `created_by` field for efficient DynamoDB querying
  2. **Frontend Filtering** (Quick fix): Filter in JavaScript after receiving all orders
- **Impact**: Improves user privacy and data security within tenant
- **Priority**: High

### 5. User Pool Selection Strategy
- **Status**: Sequential "try all pools" approach has potential conflicts
- **Issue**: If same email exists in multiple user pools, authentication succeeds against first matching pool (Admin → Basic → Premium order)
- **Risk**: User could get wrong tier access or authenticate to incorrect tenant context
- **Solutions**:
  0. **Share one user pool**: Have only one user pool to store basic tier, premium tier and admin users with Role based separation 
  1. **Unique Email Enforcement**: Prevent duplicate emails across pools during user creation
  2. **Pool Hint**: Include tier information in login request
  3. **User Lookup First**: Query all pools to find correct one before authentication
  4. **Single User Pool**: Architectural change to use one pool with tier as attribute
- **Impact**: Prevents authentication conflicts and ensures correct tier access
- **Priority**: Medium

