# Requirements Document

## Introduction

This document outlines the requirements for a multi-tenant Agentic Insights e-commerce SaaS platform designed as a reference solution for an AWS workshop. The platform enables vendors (tenants) to self-provision through a landing page with tier-based deployment strategies. The system consists of a control plane with shared microservices (registration, login, tenant management, tenant provisioning) and an application plane with 3 microservices (product, order, user). It supports Basic ($29) and Premium ($99) tiers with different resource allocation strategies and includes three web applications: SaaS admin panel, SaaS app, and landing page.

## Requirements

### Requirement 1: Tenant Self-Provisioning via Landing Page

**User Story:** As a vendor (tenant), I want to self-register for the SaaS platform through a landing page, so that I can start using the e-commerce functionality immediately.

#### Acceptance Criteria

1. WHEN a vendor visits the landing page THEN the system SHALL display tier details for Basic ($29) and Premium ($99) options
2. WHEN a vendor completes registration THEN the system SHALL create a new tenant with unique tenant_id and assign them as tenant_admin role
3. WHEN tenant registration is successful THEN the system SHALL create a Cognito user with tenant_id as custom attribute
4. WHEN tenant provisioning completes THEN the system SHALL provision tier-specific resources based on selected tier
5. IF registration fails THEN the system SHALL display appropriate error messages and allow retry

### Requirement 2: Tier-Based Resource Allocation

**User Story:** As a platform architect, I want different resource allocation strategies based on tenant tiers, so that I can optimize costs for Basic tenants and provide better isolation for Premium tenants.

#### Acceptance Criteria

1. WHEN a Basic tier tenant is provisioned THEN the system SHALL use shared Product and Order microservices with shared DynamoDB tables and shared Cognito User Pool across all Basic tenants
2. WHEN a Premium tier tenant is provisioned THEN the system SHALL use shared Product and Order Lambda microservices but create dedicated DynamoDB table for Order service and use shared Cognito User Pool for all Premium tenants
3. WHEN Premium tenant provisioning occurs THEN the TenantProvisionService SHALL create new Order DynamoDB table via EventBridge events
4. WHEN API requests are made THEN the system SHALL route to /basic/product, /basic/order for Basic tenants and /premium/product, /premium/order for Premium tenants
5. WHEN requests include tier_name header THEN the system SHALL use appropriate tier-specific resources

### Requirement 3: Authentication and Authorization

**User Story:** As a tenant user, I want to securely authenticate and access only my tenant's data, so that my business information remains isolated.

#### Acceptance Criteria

1. WHEN a user authenticates THEN the Cognito user pool SHALL return JWT token containing tenant_id as custom attribute
2. WHEN making API requests THEN the frontend SHALL include JWT token and tenant_id in HTTP headers
3. WHEN API requests are received THEN the Lambda authorizer SHALL verify JWT token and extract tenant_id
4. WHEN requests are processed THEN backend microservices SHALL use tenant_id for tenant-aware operations
5. IF JWT token is invalid or tenant_id is missing THEN the system SHALL return 401/403 error

### Requirement 4: Tenant User Management

**User Story:** As a tenant admin, I want to create and manage users within my organization, so that I can control access to our e-commerce store.

#### Acceptance Criteria

1. WHEN a tenant admin accesses the Users tab THEN the system SHALL display user management interface
2. WHEN creating a new user THEN the system SHALL allow assignment of tenant_admin or tenant_user roles
3. WHEN a user is created THEN the system SHALL create Cognito user with tenant_id custom attribute
4. WHEN tenant users access SaaS app THEN the system SHALL hide Users tab (only visible to tenant admins)
5. IF user creation fails THEN the system SHALL display validation errors and prevent duplicate emails

### Requirement 5: Product Management

**User Story:** As a tenant admin, I want to create and manage products, so that customers can browse and purchase items from my catalog.

#### Acceptance Criteria

1. WHEN a tenant admin creates a product THEN the system SHALL require name, description, and price
2. WHEN products are stored THEN the system SHALL associate them with tenant_id for isolation
3. WHEN products are retrieved THEN the system SHALL filter by tenant_id from request context
4. WHEN both tenant admins and users access products THEN the system SHALL display tenant-specific product list
5. IF product creation fails THEN the system SHALL validate required fields and display errors

### Requirement 6: Order Management and Shopping Experience

**User Story:** As a tenant user, I want to browse products and create orders, so that I can purchase items from the catalog.

#### Acceptance Criteria

1. WHEN users view the home page THEN the system SHALL display product list with name, price, and +/- buttons
2. WHEN users click +/- buttons THEN the system SHALL update cart state and show total count and value in upper right corner
3. WHEN users click "Create Order" button THEN the system SHALL create order via Order microservice and show success message
4. WHEN order is created THEN the system SHALL reset the page for new order creation
5. WHEN users click on a product THEN the system SHALL load product details page
6. WHEN users access Orders tab THEN the system SHALL display list of all past orders for that tenant

### Requirement 7: SaaS Admin Panel

**User Story:** As a SaaS provider admin, I want to manage tenants and view insights, so that I can monitor platform health and manually provision/deprovision tenants.

#### Acceptance Criteria

1. WHEN SaaS admin accesses admin panel THEN the system SHALL display tenant management interface
2. WHEN admin provisions tenant manually THEN the system SHALL create tenant with selected tier
3. WHEN admin deprovisions tenant THEN the system SHALL remove tenant and associated resources
4. WHEN admin views dashboard THEN the system SHALL display insights and metrics
5. IF admin operations fail THEN the system SHALL display error messages and allow retry

### Requirement 8: Web Application UI/UX

**User Story:** As a user of any web application, I want a modern and intuitive interface, so that I can efficiently complete my tasks.

#### Acceptance Criteria

1. WHEN users access any web app THEN the system SHALL display slick and modern UI using vanilla JS/HTML
2. WHEN users navigate the SaaS app THEN the system SHALL show left panel with Products, Orders, and Users tabs
3. WHEN tenant users access the app THEN the system SHALL hide Users tab (only visible to tenant admins)
4. WHEN users interact with forms THEN the system SHALL provide clear validation and feedback
5. IF users encounter errors THEN the system SHALL display user-friendly error messages

### Requirement 9: Control Plane and Application Plane Communication

**User Story:** As a system architect, I want proper communication between control plane and application plane, so that tenant provisioning events are handled correctly.

#### Acceptance Criteria

1. WHEN tenant provisioning occurs THEN control plane SHALL communicate with application plane via EventBridge
2. WHEN Premium tenant is created THEN EventBridge SHALL trigger creation of dedicated Order DynamoDB table
3. WHEN application plane actions occur (order.placed) THEN the system SHALL use sequential execution without EventBridge
4. WHEN EventBridge events are processed THEN the system SHALL ensure reliable delivery and error handling
5. IF EventBridge communication fails THEN the system SHALL log errors and provide retry mechanisms

### Requirement 10: Infrastructure and Technology Stack

**User Story:** As a developer, I want to use modern AWS serverless technologies with proper project structure, so that the solution is scalable and maintainable.

#### Acceptance Criteria

1. WHEN deploying infrastructure THEN the system SHALL use AWS CDK with TypeScript in ./infra/ folder
2. WHEN implementing business logic THEN the system SHALL use Python for all Lambda functions
3. WHEN organizing code THEN the system SHALL follow structure: ./src/control-plane/, ./src/app-plane/, ./web/
4. WHEN using AWS services THEN the system SHALL implement API Gateway, Cognito, Lambda, DynamoDB, EventBridge
5. WHEN using libraries THEN the system SHALL use latest versions with no vulnerabilities

### Requirement 11: Deployment and Management Scripts

**User Story:** As a workshop participant, I want simple deployment and cleanup scripts, so that I can easily set up and tear down the entire solution.

#### Acceptance Criteria

1. WHEN running deploy.sh THEN the system SHALL deploy the full baseline architecture to AWS account
2. WHEN running delete-all.sh THEN the system SHALL remove the entire solution from AWS account
3. WHEN scripts execute THEN all generated code SHALL compile without errors
4. WHEN deployment completes THEN the system SHALL be ready for immediate use
5. IF script execution fails THEN the system SHALL provide clear error messages and exit gracefully

### Requirement 12: Data Isolation and Security

**User Story:** As a tenant, I want my business data to be completely isolated from other tenants, so that my information remains secure and private.

#### Acceptance Criteria

1. WHEN storing data THEN the system SHALL use tenant_id for all database operations
2. WHEN Basic tier tenants access data THEN the system SHALL use shared DynamoDB tables with tenant_id filtering
3. WHEN Premium tier tenants access orders THEN the system SHALL use dedicated DynamoDB tables per tenant
4. WHEN processing requests THEN the system SHALL validate tenant context at all API layers
5. IF cross-tenant data access is attempted THEN the system SHALL block access and log security events

### Requirement 13: Common User Service

**User Story:** As a system architect, I want a unified user service for both tiers, so that user management is consistent across the platform.

#### Acceptance Criteria

1. WHEN accessing user endpoints THEN the system SHALL use /user API for both Basic and Premium tiers
2. WHEN creating tenant users THEN the system SHALL use common User microservice regardless of tier
3. WHEN user operations occur THEN the system SHALL maintain tenant isolation through tenant_id
4. WHEN users authenticate THEN the system SHALL work with tier-specific shared Cognito user pools (one for Basic, one for Premium)
5. IF user operations fail THEN the system SHALL provide consistent error handling across tiers