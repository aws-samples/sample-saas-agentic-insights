# Implementation Plan

- [ ] 1. Set up project structure and CDK foundation
  - Create directory structure for infra, src, web, and scripts folders
  - Initialize CDK project with TypeScript configuration
  - Set up package.json with latest AWS CDK dependencies
  - _Requirements: 10.1, 10.2, 10.3_

- [ ] 2. Implement Control Plane Stack infrastructure
  - Create control-plane-stack.ts with API Gateway, Lambda functions, and DynamoDB
  - Configure EventBridge custom bus for tenant provisioning events
  - Set up Cognito User Pool for SaaS admins
  - _Requirements: 10.1, 10.4, 7.1_

- [ ] 3. Implement Application Plane Stack infrastructure
  - Create app-plane-stack.ts with API Gateway and Lambda functions
  - Configure shared DynamoDB tables for Basic tier (products, orders)
  - Set up shared Cognito User Pools for Basic and Premium tiers
  - Configure S3 buckets and CloudFront distributions for web hosting
  - _Requirements: 10.1, 10.4, 2.1, 2.2_

- [ ] 4. Create Lambda authorizer for JWT validation
  - Implement Python Lambda function to validate JWT tokens
  - Extract tenant_id from Cognito custom attributes
  - Add tier-based routing logic for API requests
  - _Requirements: 3.3, 3.4, 2.5_

- [ ] 5. Implement Registration Service
  - Create Python Lambda function for tenant self-registration
  - Handle tier selection and tenant_id generation
  - Integrate with Cognito to create tenant admin users
  - Trigger EventBridge events for tenant provisioning
  - _Requirements: 1.2, 1.3, 1.4, 9.1_

- [ ] 6. Implement Login Service
  - Create Python Lambda function for user authentication
  - Integrate with Cognito for JWT token generation
  - Ensure tenant_id is included as custom attribute in tokens
  - _Requirements: 3.1, 3.2_

- [ ] 7. Implement Tenant Management Service
  - Create Python Lambda function for tenant CRUD operations
  - Add admin-only endpoints for manual tenant provisioning
  - Implement tenant deprovisioning with resource cleanup
  - _Requirements: 7.2, 7.3, 7.4_

- [ ] 8. Implement Tenant Provisioning Service
  - Create Python Lambda function to handle EventBridge events
  - Implement dynamic DynamoDB table creation for Premium tenants
  - Update Lambda environment variables for table routing
  - _Requirements: 2.3, 9.2_

- [ ] 9. Implement Product Service
  - Create Python Lambda function for product CRUD operations
  - Add tenant_id filtering for data isolation
  - Implement endpoints for both Basic and Premium tiers
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 10. Implement Order Service
  - Create Python Lambda function for order management
  - Add tier-specific DynamoDB table routing logic
  - Implement sequential order processing without EventBridge
  - _Requirements: 6.3, 6.6, 9.3, 2.2_

- [ ] 11. Implement User Service
  - Create Python Lambda function for tenant user management
  - Add role-based access control (tenant_admin vs tenant_user)
  - Integrate with Cognito for user creation and management
  - _Requirements: 4.2, 4.3, 13.1, 13.2_

- [ ] 12. Create Landing Page web application
  - Build HTML/CSS/JS for tier selection and registration
  - Implement modern UI/UX with vanilla JavaScript
  - Add form validation and error handling
  - Integrate with Registration Service API
  - _Requirements: 1.1, 8.1, 8.4_

- [ ] 13. Create Control Plane Admin Panel
  - Build HTML/CSS/JS for tenant management interface
  - Implement dashboard with insights and metrics
  - Add manual tenant provisioning and deprovisioning features
  - Integrate with Tenant Management Service API
  - _Requirements: 7.1, 7.4, 8.1, 8.4_

- [ ] 14. Create Application Plane SaaS App
  - Build HTML/CSS/JS with left panel navigation (Products, Orders, Users)
  - Implement role-based UI (hide Users tab for tenant_users)
  - Add JWT token handling and API integration
  - _Requirements: 8.2, 8.3, 4.4, 3.2_

- [ ] 15. Implement Product Management UI
  - Create product list view with name, price, and +/- buttons
  - Add product details page for individual products
  - Implement product creation form for tenant admins
  - Add cart state management with total display in upper right
  - _Requirements: 6.1, 6.5, 5.1, 6.2_

- [ ] 16. Implement Order Management UI
  - Create order creation flow with "Create Order" button
  - Add success message and page reset after order creation
  - Implement order history view for past orders
  - _Requirements: 6.3, 6.4, 6.6_

- [ ] 17. Implement User Management UI
  - Create user management interface for tenant admins
  - Add user creation form with role assignment
  - Implement user list view with tenant_id filtering
  - _Requirements: 4.1, 4.2, 4.5_

- [ ] 18. Create deployment scripts
  - Write deploy.sh script to deploy full baseline architecture
  - Write delete-all.sh script to remove entire solution
  - Add error handling and clear success/failure messages
  - _Requirements: 11.1, 11.2, 11.5_

- [ ] 19. Configure dynamic Premium tenant provisioning
  - Implement CDK code for runtime DynamoDB table creation
  - Add Lambda environment variable updates for new tables
  - Test EventBridge integration for Premium tenant events
  - _Requirements: 2.3, 9.2_

- [ ] 20. Implement data isolation and security
  - Add tenant_id validation in all Lambda functions
  - Implement cross-tenant access prevention
  - Add security logging for unauthorized access attempts
  - _Requirements: 12.1, 12.4, 12.5_

- [ ] 21. Wire up complete application flow
  - Connect all frontend applications to backend APIs
  - Test end-to-end tenant registration and provisioning
  - Verify tier-based resource allocation works correctly
  - Ensure all components integrate properly
  - _Requirements: 1.4, 2.4, 8.5_