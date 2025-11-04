# Agentic Insights SaaS - Detailed Solution Architecture

## High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              WEB APPLICATIONS                                   │
├─────────────────┬─────────────────────┬─────────────────────────────────────────┤
│   Landing Page  │  Control Plane      │    Application Plane                    │
│   (Registration)│  Admin Panel        │    SaaS App                             │
│                 │  (Tenant Mgmt)      │    (Products/Orders/Users + AI)         │
└─────────────────┴─────────────────────┴─────────────────────────────────────────┘
         │                    │                           │
         │                    │                           │
         ▼                    ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                       │
├─────────────────────────────┬───────────────────────────────────────────────────┤
│      Control Plane APIs     │           Application Plane APIs                 │
│   /register, /login,        │  /basic/*, /premium/*, /user, /ai/*               │
│   /tenants                  │                                                   │
└─────────────────────────────┴───────────────────────────────────────────────────┘
         │                                        │
         │                                        │
         ▼                                        ▼
┌─────────────────────────────┐    ┌─────────────────────────────────────────────┐
│      CONTROL PLANE          │    │           APPLICATION PLANE                 │
│                             │    │                                             │
│  ┌─────────────────────┐    │    │  ┌─────────────────────────────────────────┐│
│  │ Registration Service│    │    │  │         Product Service                ││
│  │ Login Service       │    │    │  │    (Shared Lambda + Shared DDB)        ││
│  │ Tenant Management   │    │    │  └─────────────────────────────────────────┘│
│  │ Tenant Provisioning │    │    │                                             │
│  └─────────────────────┘    │    │  ┌─────────────────────────────────────────┐│
│                             │    │  │         Order Service                   ││
│           │                 │    │  │  Basic: Shared Lambda + Shared DDB     ││
│           │                 │    │  │  Premium: Shared Lambda + Dedicated DDB││
│           ▼                 │    │  └─────────────────────────────────────────┘│
│  ┌─────────────────────┐    │    │                                             │
│  │    EventBridge      │────┼────┤  ┌─────────────────────────────────────────┐│
│  │   (Provisioning)    │    │    │  │         User Service                    ││
│  └─────────────────────┘    │    │  │    (Common for both tiers)              ││
└─────────────────────────────┘    │  └─────────────────────────────────────────┘│
                                   │                                             │
                                   │  ┌─────────────────────────────────────────┐│
                                   │  │      AI Description Service             ││
                                   │  │  • Amazon Bedrock Agent (Claude 3)     ││
                                   │  │  • Standalone Lambda Function          ││
                                   │  │  • Usage Tracking & Cost Monitoring    ││
                                   │  └─────────────────────────────────────────┘│
                                   └─────────────────────────────────────────────┘
```

## Detailed Component Architecture

### 1. Web Applications Layer

#### Landing Page
- **Purpose**: Tenant self-registration
- **Technology**: Static HTML/CSS/JS hosted on S3 + CloudFront
- **Features**:
  - Tier selection (Basic $29 vs Premium $99)
  - Registration form
  - Integration with Registration Service

#### Control Plane Admin Panel
- **Purpose**: SaaS provider tenant management
- **Technology**: Static HTML/CSS/JS hosted on S3 + CloudFront
- **Features**:
  - Tenant dashboard and insights
  - Manual tenant provisioning/deprovisioning
  - Admin authentication via dedicated Cognito User Pool

#### Application Plane SaaS App
- **Purpose**: Tenant e-commerce application
- **Technology**: Static HTML/CSS/JS hosted on S3 + CloudFront
- **Features**:
  - Left navigation: Products, Orders, Users tabs
  - Role-based UI (Users tab hidden for tenant_user role)
  - Shopping cart with +/- buttons for multiple products
  - Product details page for individual products
  - Cart total display in upper right corner
  - Multi-product order creation
  - Form validation and error handling
  - JWT-based authentication

### 2. Control Plane Services

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE SERVICES                               │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│ Registration    │ Login Service   │ Tenant Mgmt     │ Tenant Provisioning     │
│ Service         │                 │ Service         │ Service                 │
│                 │                 │                 │                         │
│ • Tenant signup │ • JWT auth      │ • CRUD tenants  │ • EventBridge listener  │
│ • Tier selection│ • Cognito       │ • Admin ops     │ • Dynamic DDB creation  │
│ • Cognito user  │   integration   │ • Status mgmt   │ • Premium provisioning  │
│ • EventBridge   │                 │                 │                         │
│   trigger       │                 │                 │                         │
└─────────────────┴─────────────────┴─────────────────┴─────────────────────────┘
         │                                                          ▲
         │                                                          │
         ▼                                                          │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EventBridge                                       │
│                         (Tenant Provisioning Events)                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3. Application Plane Services

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION PLANE SERVICES                              │
├─────────────────────────┬─────────────────────────┬─────────────────────────────┤
│    Product Service      │     Order Service       │      User Service           │
│                         │                         │                             │
│ • Shared Lambda         │ • Shared Lambda         │ • Common Lambda             │
│ • Shared DDB table      │ • Basic: Shared DDB     │ • Cognito integration       │
│ • Tenant_id filtering   │ • Premium: Dedicated    │ • Role management           │
│ • CRUD operations       │   DDB per tenant        │ • Both tiers                │
│                         │ • Multi-product orders  │                             │
│                         │ • Cart state handling   │                             │
│                         │ • Tenant_id filtering   │                             │
└─────────────────────────┴─────────────────────────┴─────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AI DESCRIPTION SERVICE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Standalone AI Agent Stack                            │   │
│  │                                                                         │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │   │
│  │  │ Lambda Function │───▶│ Bedrock Agent   │───▶│ Claude Haiku 4.5    │  │   │
│  │  │ (Python 3.11)   │    │ (Inference      │    │ Foundation Model    │  │   │
│  │  │                 │    │  Profile)       │    │                     │  │   │
│  │  │ • Input validation│    │                 │    │ • Cost optimized    │  │   │
│  │  │ • Usage tracking │    │ • Expert prompt │    │ • Fast generation   │  │   │
│  │  │ • Error handling │    │ • 3-4 sentences │    │ • Professional tone │  │   │
│  │  │ • Cost calculation│    │ • E-commerce    │    │                     │  │   │
│  │  └─────────────────┘    │   focused       │    └─────────────────────┘  │   │
│  │                         └─────────────────┘                            │   │
│  │                                                                         │   │
│  │  API Endpoint: POST /ai/generate-description                            │   │
│  │  • JWT Authentication via existing authorizer                           │   │
│  │  • Tenant isolation with tenant-id header                               │   │
│  │  • CORS support for web application                                     │   │
│  │  • Structured logging for usage analytics                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4. Tier-Based Resource Allocation

#### Basic Tier ($29/month)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BASIC TIER                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│  API Routes: /basic/product, /basic/order, /user                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │ Product Service │  │ Order Service   │  │ User Service                    │  │
│  │ Shared Lambda   │  │ Shared Lambda   │  │ Common Lambda                   │  │
│  │       │         │  │       │         │  │       │                         │  │
│  │       ▼         │  │       ▼         │  │       ▼                         │  │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────────────────────┐ │  │
│  │ │ Shared DDB  │ │  │ │ Shared DDB  │ │  │ │ Shared Cognito User Pool    │ │  │
│  │ │ Products    │ │  │ │ Orders      │ │  │ │ (All Basic Tenants)         │ │  │
│  │ │ Table       │ │  │ │ Table       │ │  │ └─────────────────────────────┘ │  │
│  │ └─────────────┘ │  │ └─────────────┘ │  │                                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Premium Tier ($99/month)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             PREMIUM TIER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│  API Routes: /premium/product, /premium/order, /user                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │ Product Service │  │ Order Service   │  │ User Service                    │  │
│  │ Shared Lambda   │  │ Shared Lambda   │  │ Common Lambda                   │  │
│  │       │         │  │       │         │  │       │                         │  │
│  │       ▼         │  │       ▼         │  │       ▼                         │  │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────────────────────┐ │  │
│  │ │ Shared DDB  │ │  │ │ Dedicated   │ │  │ │ Shared Cognito User Pool    │ │  │
│  │ │ Products    │ │  │ │ DDB Table   │ │  │ │ (All Premium Tenants)       │ │  │
│  │ │ Table       │ │  │ │ per Tenant  │ │  │ └─────────────────────────────┘ │  │
│  │ └─────────────┘ │  │ └─────────────┘ │  │                                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5. Authentication & Authorization Flow

#### User Pool Selection Strategy
The login service uses a sequential "try all pools" approach for user authentication:

**Current Behavior**

The login service tries pools in this order:
1. **Admin User Pool** (for SaaS admins)
2. **Basic Tier User Pool** 
3. **Premium Tier User Pool**

*Note: If the same email exists in multiple pools, authentication succeeds against the first matching pool, which could cause tier mismatches.*

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

1. User Login
   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐
   │   Web App   │───▶│Login Service│───▶│   Cognito User Pool │
   └─────────────┘    └─────────────┘    └─────────────────────┘
                             │                       │
                             ▼                       ▼
                      ┌─────────────┐    ┌─────────────────────┐
                      │JWT Token    │◀───│ Custom Attributes:  │
                      │with         │    │ - tenant_id         │
                      │tenant_id    │    │ - role              │
                      └─────────────┘    └─────────────────────┘

2. API Request Authorization
   ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────┐
   │   Web App   │───▶│ Lambda          │───▶│   Backend Service   │
   │             │    │ Authorizer      │    │                     │
   │ Headers:    │    │                 │    │ Context:            │
   │ - JWT Token │    │ • Validate JWT  │    │ - tenant_id         │
   │ - tenant_id │    │ • Extract       │    │ - role              │
   │ - tier_name │    │   tenant_id     │    │ - tier              │
   │             │    │ • Route by tier │    │                     │
   └─────────────┘    └─────────────────┘    └─────────────────────┘
```

### 6. Data Models & Storage

#### Tenant Data Model
```
DynamoDB Table: Tenants
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ tenant_id (PK) │ tenant_name │ tier    │ status      │ admin_email │ order_table_name │ created_at │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ uuid-1234      │ Acme Corp   │ basic   │ active      │ admin@acme  │ null             │ timestamp  │
│ uuid-5678      │ Tech Store  │ premium │ active      │ admin@tech  │ Orders-uuid-5678 │ timestamp  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Product Data Model
```
DynamoDB Table: Products (Shared)
┌─────────────────────────────────────────────────────────────────────────────────┐
│ tenant_id (PK) │ product_id (SK) │ name      │ description │ price │ created_at │
├─────────────────────────────────────────────────────────────────────────────────┤
│ uuid-1234      │ prod-001        │ Laptop    │ Gaming...   │ 1200  │ timestamp  │
│ uuid-5678      │ prod-002        │ Phone     │ Smart...    │ 800   │ timestamp  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Order Data Models
```
Basic Tier - Shared Orders Table:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ tenant_id (PK) │ order_id (SK) │ items (Multi-Product Array) │ total │ status  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ uuid-1234      │ order-001     │ [                           │ 2000  │ complete│
│                │               │   {product_id: "p1",        │       │         │
│                │               │    name: "Laptop",          │       │         │
│                │               │    price: 1200, qty: 1},    │       │         │
│                │               │   {product_id: "p2",        │       │         │
│                │               │    name: "Mouse",           │       │         │
│                │               │    price: 25, qty: 2}       │       │         │
│                │               │ ]                           │       │         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ uuid-5678      │ order-002     │ [                           │ 800   │ pending │
│                │               │   {product_id: "p3",        │       │         │
│                │               │    name: "Phone",           │       │         │
│                │               │    price: 800, qty: 1}      │       │         │
│                │               │ ]                           │       │         │
└─────────────────────────────────────────────────────────────────────────────────┘

Premium Tier - Dedicated Tables per Tenant:
Table: Orders-uuid-5678
┌─────────────────────────────────────────────────────────────────────────────────┐
│ tenant_id (PK) │ order_id (SK) │ items (Multi-Product Array) │ total │ status  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ uuid-5678      │ order-001     │ [                           │ 3200  │ complete│
│                │               │   {product_id: "p1",        │       │         │
│                │               │    name: "Laptop",          │       │         │
│                │               │    price: 1200, qty: 2},    │       │         │
│                │               │   {product_id: "p4",        │       │         │
│                │               │    name: "Monitor",         │       │         │
│                │               │    price: 400, qty: 2}      │       │         │
│                │               │ ]                           │       │         │
└─────────────────────────────────────────────────────────────────────────────────┘

Shopping Cart Flow:
1. User browses products with +/- buttons
2. Cart state managed client-side (multiple products)
3. Cart total displayed in upper right corner
4. "Create Order" sends entire cart as items array
5. Order Service stores multi-product order in appropriate table
```

### 7. Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EVENT FLOW                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

Tenant Registration Flow:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────┐
│ Landing Page    │───▶│ Registration    │───▶│ EventBridge                     │
│ (Tier Selection)│    │ Service         │    │ Events:                         │
└─────────────────┘    └─────────────────┘    │ 1. tenant.created               │
                                              │ 2. admin.user.creation.requested│
                                              └─────────────────────────────────┘
                                                             │
                                                             ▼
                                              ┌─────────────────────────────────┐
                                              │ Application Plane Handlers      │
                                              │                                 │
                                              │ Tenant Provisioning Service:   │
                                              │ IF tier == "premium":           │
                                              │   • Create dedicated DDB table  │
                                              │   • Update Lambda env vars      │
                                              │ ELSE:                           │
                                              │   • Use shared resources        │
                                              │                                 │
                                              │ User Creation Service:          │
                                              │ • Create Cognito user in        │
                                              │   appropriate tier user pool    │
                                              │ • Set tenant_id custom attr     │
                                              │ • Assign role (tenant_admin)    │
                                              └─────────────────────────────────┘

EventBridge-Driven User Creation Benefits:
• Clean separation of concerns between Control and Application planes
• Appropriate user pool selection based on tenant tier
• Resilient user creation with retry mechanisms
• Decoupled architecture for better maintainability
```

### 8. API Gateway Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY ROUTES                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Control Plane APIs:                                                           │
│  ├── POST /register          (Tenant self-registration)                        │
│  ├── POST /login             (User authentication)                             │
│  ├── GET  /tenants           (List tenants - admin only)                       │
│  ├── POST /tenants           (Create tenant - admin only)                      │
│  └── DELETE /tenants/{id}    (Delete tenant - admin only)                      │
│                                                                                 │
│  Application Plane APIs:                                                       │
│  ├── Basic Tier Routes:                                                        │
│  │   ├── GET    /basic/products        (Product catalog for cart)              │
│  │   ├── POST   /basic/products        (Create product)                        │
│  │   ├── PUT    /basic/products/{id}   (Update product)                        │
│  │   ├── DELETE /basic/products/{id}   (Delete product)                        │
│  │   ├── GET    /basic/orders          (Order history)                         │
│  │   └── POST   /basic/orders          (Create multi-product order)            │
│  │                                                                             │
│  ├── Premium Tier Routes:                                                      │
│  │   ├── GET    /premium/products      (Product catalog for cart)              │
│  │   ├── POST   /premium/products      (Create product)                        │
│  │   ├── PUT    /premium/products/{id} (Update product)                        │
│  │   ├── DELETE /premium/products/{id} (Delete product)                        │
│  │   ├── GET    /premium/orders        (Order history)                         │
│  │   └── POST   /premium/orders        (Create multi-product order)            │
│  │                                                                             │
│  └── Common Routes:                                                            │
│      ├── GET    /user                  (List tenant users)                     │
│      ├── POST   /user                  (Create tenant user)                    │
│      ├── PUT    /user/{id}             (Update tenant user)                    │
│      └── DELETE /user/{id}             (Delete tenant user)                    │
│                                                                                 │
│  AI-Powered Routes:                                                             │
│  └── POST /ai/generate-description     (Generate AI product descriptions)      │
│      • Requires: product_name (required), short_description (optional)         │
│      • Returns: generated_description, usage metrics, cost tracking            │
│      • Authentication: JWT token via existing authorizer                       │
│      • Tenant isolation: tenant-id and tier-name headers                       │
│                                                                                 │
│  Note: Cart state managed client-side, order creation sends items array       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 9. Error Handling & Validation

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ERROR HANDLING STRATEGY                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Frontend Validation & Error Display:                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Registration: Display errors and allow retry                          │   │
│  │ • User Creation: Validate fields, prevent duplicate emails              │   │
│  │ • Product Creation: Validate required fields (name, description, price) │   │
│  │ • Form Validation: Clear feedback on all forms                          │   │
│  │ • User-Friendly: Convert technical errors to readable messages          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Backend Error Handling:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • 400: Bad Request (validation errors)                                  │   │
│  │ • 401: Unauthorized (invalid JWT)                                       │   │
│  │ • 403: Forbidden (insufficient permissions)                             │   │
│  │ • 404: Not Found (resource not found)                                   │   │
│  │ • 500: Internal Server Error (system errors)                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  EventBridge Error Handling:                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Reliable delivery with retry mechanisms                               │   │
│  │ • Error logging for failed provisioning events                          │   │
│  │ • Dead letter queues for unprocessable events                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 10. Security & Multi-Tenancy

### 10. Security & Multi-Tenancy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        SECURITY & ISOLATION                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Data Isolation Strategy:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ 1. All API requests include tenant_id in headers                        │   │
│  │ 2. Lambda authorizer validates JWT and extracts tenant_id               │   │
│  │ 3. All DynamoDB operations filter by tenant_id                          │   │
│  │ 4. Cross-tenant access blocked at application layer                     │   │
│  │ 5. Premium tenants get dedicated Order tables for better isolation      │   │
│  │ 6. Security logging for unauthorized cross-tenant access attempts       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Role-Based Access Control:                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • tenant_admin: Full access to Products, Orders, Users                  │   │
│  │ • tenant_user:  Access to Products, Orders only (Users tab hidden)     │   │
│  │ • saas_admin:   Platform-wide tenant management                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 11. Dynamic CDK Resource Creation

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    PREMIUM TENANT PROVISIONING                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  EventBridge Trigger Flow:                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │ Registration    │───▶│ EventBridge     │───▶│ Tenant Provisioning         │  │
│  │ Service         │    │ Event:          │    │ Service                     │  │
│  │                 │    │ tenant.created  │    │                             │  │
│  │ tier="premium"  │    │ {tenant_id,     │    │ IF tier == "premium":       │  │
│  └─────────────────┘    │  tier}          │    │ • Create DDB table          │  │
│                         └─────────────────┘    │ • Update Lambda env vars    │  │
│                                                │ • Store table name in       │  │
│                                                │   tenant record             │  │
│                                                └─────────────────────────────┘  │
│                                                                                 │
│  Technical Implementation:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Use AWS CDK programmatically within Lambda                            │   │
│  │ • Create DynamoDB table: "Orders-{tenant_id}"                           │   │
│  │ • Update Order Service Lambda environment variables                     │   │
│  │ • Store order_table_name in Tenant DynamoDB record                      │   │
│  │ • Handle provisioning failures with retry logic                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 12. AI Product Description Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AI PRODUCT DESCRIPTION AGENT                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Standalone CDK Stack: AgenticInsightsAIDescription                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  Frontend Integration:                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │ Product Form (Add/Edit)                                         │   │   │
│  │  │ ├── Product Name Input (required for Generate button)           │   │   │
│  │  │ ├── Description Textarea (populated by AI)                      │   │   │
│  │  │ └── Generate Button                                              │   │   │
│  │  │     • Enabled when product name entered                         │   │   │
│  │  │     • Loading states with spinner                               │   │   │
│  │  │     • Error handling with user-friendly messages               │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                    │   │
│  │                                    ▼                                    │   │
│  │  API Request Flow:                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │ POST /ai/generate-description                                   │   │   │
│  │  │ Headers:                                                        │   │   │
│  │  │ • Authorization: Bearer <jwt-token>                             │   │   │
│  │  │ • Content-Type: application/json                                │   │   │
│  │  │ • tenant-id: <tenant-uuid>                                      │   │   │
│  │  │ • tier-name: basic|premium                                      │   │   │
│  │  │                                                                 │   │   │
│  │  │ Body:                                                           │   │   │
│  │  │ {                                                               │   │   │
│  │  │   "product_name": "Smart Fitness Watch",                       │   │   │
│  │  │   "short_description": "Heart rate, GPS" // Optional           │   │   │
│  │  │ }                                                               │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                    │   │
│  │                                    ▼                                    │   │
│  │  Lambda Function (Python 3.11):                                        │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │ handler.py                                                      │   │   │
│  │  │ ├── Input validation (product name required, length limits)     │   │   │
│  │  │ ├── JWT token extraction (tenant_id, user_id, tier)             │   │   │
│  │  │ ├── Bedrock agent invocation                                    │   │   │
│  │  │ ├── Response processing and formatting                          │   │   │
│  │  │ ├── Usage tracking (tokens, costs, response time)               │   │   │
│  │  │ └── Structured logging to CloudWatch                            │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                    │   │
│  │                                    ▼                                    │   │
│  │  Amazon Bedrock Agent:                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │ Agent ID: DRYUFFAST2                                            │   │   │
│  │  │ Alias ID: YHU9F5JYCE                                            │   │   │
│  │  │ Model: us.anthropic.claude-3-haiku-20240307-v1:0               │   │   │
│  │  │                                                                 │   │   │
│  │  │ Instructions:                                                   │   │   │
│  │  │ "You are an expert e-commerce product description writer.       │   │   │
│  │  │  Generate compelling 3-4 sentence product descriptions that     │   │   │
│  │  │  highlight key features, benefits, and emotional appeal.        │   │   │
│  │  │  Use professional language suitable for online retail.          │   │   │
│  │  │  Return only the description text, no additional formatting."   │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                    │   │
│  │                                    ▼                                    │   │
│  │  Response & Usage Tracking:                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │ {                                                               │   │   │
│  │  │   "generated_description": "Stay on top of your fitness...",    │   │   │
│  │  │   "usage": {                                                    │   │   │
│  │  │     "input_tokens": 45,                                         │   │   │
│  │  │     "output_tokens": 120,                                       │   │   │
│  │  │     "total_tokens": 165,                                        │   │   │
│  │  │     "input_cost": 0.0001125,                                    │   │   │
│  │  │     "output_cost": 0.00015,                                     │   │   │
│  │  │     "total_cost": 0.0002625,                                    │   │   │
│  │  │     "response_time_seconds": 7.37                               │   │   │
│  │  │   },                                                            │   │   │
│  │  │   "status": "success"                                           │   │   │
│  │  │ }                                                               │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  CloudWatch Logging:                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ USAGE_LOG: {                                                            │   │
│  │   "timestamp": "2025-08-28T18:23:45.142215",                           │   │
│  │   "tenant_id": "26cb31f9-4d40-4e5c-aade-2278478f6301",                 │   │
│  │   "tier": "basic",                                                      │   │
│  │   "user_id": "04085438-30f1-7044-f9bb-52aec8eebaa0",                   │   │
│  │   "product_name": "Smart Watch",                                        │   │
│  │   "service": "ai-product-description",                                  │   │
│  │   "usage": { /* token and cost details */ },                           │   │
│  │   "response_time_seconds": 7.37                                         │   │
│  │ }                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Deployment:                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Standalone deployment: ./scripts/lab-01.2-deploy-product-description-ai-agent.sh │   │
│  │ • Configuration-driven: No hardcoded values                             │   │
│  │ • Integrates with existing API Gateway and authorizer                   │   │
│  │ • IAM permissions: bedrock-agent-runtime:InvokeAgent, bedrock:InvokeAgent│   │
│  │ • CORS configuration: Manual OPTIONS method for web app compatibility   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 13. Testing Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TESTING APPROACH                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Unit Testing:                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Python Lambda functions with pytest                                   │   │
│  │ • Mock AWS services (DynamoDB, Cognito, EventBridge)                    │   │
│  │ • Test tenant isolation logic                                            │   │
│  │ • Validate data models and business logic                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Integration Testing:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • API Gateway endpoint testing                                           │   │
│  │ • Lambda authorizer integration                                          │   │
│  │ • EventBridge event processing                                           │   │
│  │ • Cognito authentication flows                                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  End-to-End Testing:                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Complete tenant registration and provisioning                          │   │
│  │ • Multi-tenant data isolation verification                               │   │
│  │ • Tier-specific resource allocation testing                              │   │
│  │ • Web application user flows                                             │   │
│  │ • Cross-tenant access prevention                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 13. Monitoring & Logging

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY STRATEGY                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  CloudWatch Logging:                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • All Lambda functions log to CloudWatch                                │   │
│  │ • Structured logging with tenant_id context                             │   │
│  │ • Error logging for failed operations                                    │   │
│  │ • Security event logging for unauthorized access                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  X-Ray Tracing:                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • End-to-end request tracing                                             │   │
│  │ • Performance monitoring across services                                │   │
│  │ • Identify bottlenecks in multi-service flows                           │   │
│  │ • Track tenant provisioning workflows                                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Metrics & Alarms:                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • API Gateway request metrics                                            │   │
│  │ • Lambda function duration and error rates                              │   │
│  │ • DynamoDB throttling and capacity metrics                              │   │
│  │ • EventBridge event processing success/failure rates                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 14. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT STRUCTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Project Structure:                                                             │
│  ├── infra/                    (CDK TypeScript infrastructure)                 │
│  │   ├── control-plane-stack.ts                                               │
│  │   ├── app-plane-stack.ts                                                   │
│  │   ├── ai-description-stack.ts                                              │
│  │   └── main.ts                                                              │
│  │                                                                             │
│  ├── src/                      (Python Lambda functions)                      │
│  │   ├── control-plane/                                                       │
│  │   │   ├── registration/                                                     │
│  │   │   ├── login/                                                           │
│  │   │   ├── tenant-management/                                               │
│  │   │   └── tenant-provisioning/                                             │
│  │   │                                                                        │
│  │   └── app-plane/                                                           │
│  │       ├── product/                                                         │
│  │       ├── product-desc/        (AI description generation)                 │
│  │       ├── order/                                                           │
│  │       ├── user/                                                            │
│  │       └── authorizer/                                                      │
│  │                                                                             │
│  ├── web/                      (Frontend applications)                        │
│  │   ├── landing-page/                                                        │
│  │   ├── admin-panel/                                                         │
│  │   └── saas-app/             (Enhanced with AI Generate button)             │
│  │                                                                             │
│  └── scripts/                  (Deployment scripts)                           │
│      ├── lab1.1-deploy-base-architecture.sh                                 │
│      ├── lab-01.2-deploy-product-description-ai-agent.sh                      │
│      └── delete-all.sh                                                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

This architecture provides:
- **Cost Optimization**: Shared resources for Basic tier, selective isolation for Premium
- **Scalability**: Serverless components that scale automatically
- **Security**: Multi-layer tenant isolation and JWT-based authentication
- **Maintainability**: Clean separation of control plane and application plane
- **Workshop Ready**: Simple deployment scripts for easy setup/teardown
