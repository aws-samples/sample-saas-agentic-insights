# Implementation Plan

- [ ] 1. Set up project structure and shared utilities
  - Create the complete folder structure as specified in the requirements including scripts/0.baseline/
  - Set up package.json files for infra and web applications
  - Create shared Python utilities for Lambda layers (auth, database, events, utils)
  - _Requirements: 9.1, 9.2_

- [ ] 2. Implement CDK infrastructure foundation
  - [ ] 2.1 Create CDK app entry point and basic stack structure
    - Set up CDK app.ts with stack imports
    - Create base stack classes for shared, control-plane, application-plane, and frontend
    - Configure CDK context and deployment settings
    - _Requirements: 9.1, 9.2_

  - [ ] 2.2 Implement shared infrastructure stack
    - Create EventBridge custom bus for inter-plane communication
    - Set up API Gateway with CORS and custom domain configuration
    - Create CloudWatch log groups and basic monitoring dashboards
    - _Requirements: 7.2, 9.3_

  - [ ] 2.3 Create CDK constructs for reusable components
    - Build Lambda service construct with common configuration
    - Create DynamoDB construct for both shared and silo table patterns
    - Implement Cognito construct with custom tenant_id attribute
    - Build API Gateway construct with authorizer integration
    - _Requirements: 2.1, 8.2, 9.2_

- [ ] 3. Implement authentication and authorization system
  - [ ] 3.1 Create tier-specific Cognito User Pools with custom attributes
    - Configure Basic Tier User Pool with tenant_id and tier custom attributes
    - Configure Premium Tier User Pool with tenant_id and tier custom attributes
    - Set up user groups for role-based access control in both pools
    - Create User Pool Clients with appropriate OAuth settings for both tiers
    - _Requirements: 2.1, 2.2, 10.1_

  - [ ] 3.2 Implement Lambda authorizer for tier-aware tenant context
    - Write JWT validation logic with tier-specific Cognito integration
    - Extract tenant_id and tier from custom claims and validate
    - Implement service endpoint routing based on tenant tier
    - Generate IAM policy with tenant and tier context in authorizer response
    - Create unit tests for tier-based authorization scenarios
    - _Requirements: 2.3, 2.4, 8.3, 10.4_

  - [ ] 3.3 Create shared authentication utilities
    - Build Python auth module for tenant context extraction
    - Implement Cognito client wrapper for user operations
    - Create authentication decorators for Lambda functions
    - Write unit tests for auth utilities
    - _Requirements: 2.1, 2.4_

- [ ] 4. Build control plane services
  - [ ] 4.1 Implement tenant management service
    - Create tenant data models and validation schemas
    - Build tenant repository with DynamoDB operations
    - Implement tenant creation, update, and retrieval handlers
    - Write unit tests for tenant management operations
    - _Requirements: 1.2, 1.3, 7.1_

  - [ ] 4.2 Implement user management service
    - Create user data models and Cognito integration
    - Build user repository for tenant-scoped operations
    - Implement user creation, invitation, and role management handlers
    - Write unit tests for user management operations
    - _Requirements: 3.1, 3.2, 3.4_

  - [ ] 4.3 Implement tier-based tenant provisioning service
    - Create EventBridge event handlers for tenant lifecycle
    - Build Basic tier provisioning logic (user group creation only)
    - Build Premium tier provisioning logic (user group + silo Payment infrastructure creation)
    - Implement tier-specific Cognito user group creation
    - Write unit tests for both Basic and Premium provisioning workflows
    - _Requirements: 1.3, 1.4, 7.1, 10.1, 10.2_

  - [ ] 4.5 Implement tier-based tenant deprovisioning service
    - Create admin-only API endpoint for tenant deprovisioning
    - Build Basic tier deprovisioning logic (user group cleanup only)
    - Build Premium tier deprovisioning logic (silo Payment infrastructure + user group cleanup)
    - Implement tier-specific Cognito user group and user cleanup
    - Add S3 object cleanup for Premium tier tenant-specific resources
    - Write unit tests for both Basic and Premium deprovisioning workflows
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ] 4.4 Implement billing management service
    - Create billing data models for tier tracking
    - Build billing repository with usage metrics
    - Implement billing event handlers and tier validation
    - Write unit tests for billing operations
    - _Requirements: 1.1, 7.3_

- [ ] 5. Build tier-based application plane services
  - [ ] 5.1 Implement Basic tier shared services
    - Create Basic tier product service with shared database operations
    - Create Basic tier order service with shared database operations
    - Create Basic tier payment service with shared database operations
    - Implement tenant filtering for all Basic tier operations
    - Add S3 integration for Basic tier product image uploads
    - Write unit tests for Basic tier shared operations
    - _Requirements: 4.1, 4.2, 4.3, 8.1, 10.1_

  - [ ] 5.2 Implement Premium tier services
    - Create Premium tier shared product service with dedicated database
    - Create Premium tier shared order service with dedicated database
    - Create Premium tier silo payment service template for per-tenant deployment
    - Implement tenant isolation for Premium tier operations
    - Add S3 integration for Premium tier product image uploads
    - Write unit tests for Premium tier shared and silo operations
    - _Requirements: 5.1, 5.3, 6.1, 6.2, 8.2, 10.2_

  - [ ] 5.3 Implement tier-aware service routing
    - Create service discovery logic based on tenant tier
    - Implement API Gateway routing appropriate tier services
    - Add fallback mechanisms for service routing failures
    - Write unit tests for tier-based routing logic
    - _Requirements: 2.4, 10.4_

- [ ] 6. Create database infrastructure
  - [ ] 6.1 Define tier-based DynamoDB table schemas
    - Create Basic tier shared tables (products, orders, payments) with tenant filtering
    - Create Premium tier shared tables (products, orders) with tenant filtering
    - Define Premium tier silo table patterns for payments only
    - Implement control plane tables for tenants with tier and service endpoint information
    - Add proper indexes and capacity configuration for all tier-specific tables
    - _Requirements: 8.1, 8.2, 10.1, 10.2_

  - [ ] 6.2 Deploy control plane infrastructure
    - Deploy Basic and Premium tier Cognito User Pools and related resources
    - Create control plane Lambda functions and API routes
    - Set up EventBridge rules and targets for tier-based provisioning
    - Configure CloudWatch monitoring for control plane with tier tagging
    - _Requirements: 7.1, 7.2, 9.3, 10.1_

  - [ ] 6.3 Deploy Basic tier application plane infrastructure
    - Create Basic tier shared Lambda functions and API routes
    - Deploy Basic tier shared DynamoDB tables
    - Set up S3 bucket for Basic tier product images with CloudFront
    - Configure CloudWatch monitoring for Basic tier with tenant and tier tagging
    - _Requirements: 4.4, 5.4, 6.4, 9.3, 10.1_

  - [ ] 6.4 Deploy Premium tier application plane infrastructure
    - Create Premium tier shared Product and Order Service Lambda functions and API routes
    - Deploy Premium tier shared Product and Order DynamoDB tables
    - Set up template resources for Premium tier silo Payment services
    - Set up S3 bucket for Premium tier product images with CloudFront
    - Configure CloudWatch monitoring for Premium tier with tenant and tier tagging
    - _Requirements: 4.4, 5.4, 6.4, 9.3, 10.2_

- [ ] 7. Build frontend applications
  - [ ] 7.1 Create landing page application
    - Build HTML structure with tier selection forms
    - Implement JavaScript for tenant registration API calls
    - Add CSS styling for professional appearance
    - Create form validation and error handling
    - _Requirements: 1.1, 1.5_

  - [ ] 7.2 Implement SaaS application frontend
    - Create authentication flow with Cognito integration
    - Build product catalog browsing with tenant filtering
    - Implement shopping cart functionality with local storage
    - Add checkout process with order placement
    - Create tenant admin panel with role-based access
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 5.2_

  - [ ] 7.3 Build system admin application
    - Create system dashboard with tenant metrics
    - Implement tenant management interface with deprovisioning controls
    - Add billing overview and analytics views
    - Build system health monitoring displays
    - _Requirements: 7.4, 10.1_

  - [ ] 7.4 Deploy frontend applications
    - Set up S3 buckets for static website hosting
    - Configure CloudFront distributions for each app
    - Implement build and deployment scripts
    - Add environment configuration for API endpoints
    - _Requirements: 9.4_

- [ ] 8. Create workshop seeding and setup tools
  - [ ] 8.1 Build tenant seeding script
    - Create shell script to provision demo tenant via API
    - Add error handling and validation for tenant creation
    - Implement cleanup functionality for workshop resets
    - _Requirements: 10.1, 10.5_

  - [ ] 8.2 Implement product seeding functionality
    - Create JSON data files with sample products
    - Build script to load products via product service API
    - Add product images to S3 and reference in product data
    - Implement batch loading with progress indicators
    - _Requirements: 10.2, 10.4_

  - [ ] 8.3 Create deployment automation scripts
    - Create scripts/0.baseline/ folder structure
    - Build deploy-baseline.sh script for fresh AWS account deployment
    - Build master deployment script for complete stack
    - Add environment-specific configuration management
    - Implement health checks and validation after deployment
    - Create rollback procedures for failed deployments
    - _Requirements: 9.5, 10.3_

- [ ] 9. Implement comprehensive testing
  - [ ] 9.1 Create unit tests for all services
    - Write unit tests for control plane service functions
    - Create unit tests for application plane service functions
    - Add unit tests for shared utilities and auth components
    - Implement mock objects for external dependencies
    - _Requirements: All service requirements_

  - [ ] 9.2 Build integration tests
    - Create end-to-end API testing for tenant provisioning and deprovisioning workflows
    - Test EventBridge communication between planes
    - Validate tenant isolation across all operations
    - Add database integration testing with test data
    - _Requirements: 2.4, 7.2, 8.3, 8.4, 10.4_

  - [ ] 9.3 Implement frontend testing
    - Create unit tests for JavaScript components
    - Add integration tests for API communication
    - Test authentication flows and error handling
    - Validate responsive design and cross-browser compatibility
    - _Requirements: 1.5, 2.5, 3.5_

- [ ] 10. Add monitoring and operational features
  - [ ] 10.1 Configure CloudWatch monitoring
    - Set up custom metrics for business operations
    - Create dashboards for tenant activity and system health
    - Implement log aggregation and structured logging
    - Add performance monitoring for Lambda functions
    - _Requirements: 9.3_

  - [ ] 10.2 Implement security monitoring
    - Add logging for tenant isolation violations
    - Create alerts for suspicious cross-tenant access attempts
    - Implement audit trails for sensitive operations
    - Add security scanning and vulnerability monitoring
    - _Requirements: 8.4, 8.5_

  - [ ] 10.3 Create operational documentation
    - Write deployment and configuration guides
    - Create troubleshooting documentation
    - Add API reference documentation
    - Build workshop participant guides
    - _Requirements: 10.3_