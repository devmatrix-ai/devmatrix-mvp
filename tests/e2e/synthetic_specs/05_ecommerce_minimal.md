# E-commerce Minimal - Level 3 Synthetic Spec

## Overview
Minimal but production-ready e-commerce platform with Next.js 14 frontend, FastAPI backend, PostgreSQL database, Stripe payment processing (test mode), product catalog, shopping cart, checkout flow, and order management.

## Tech Stack
- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS, shadcn/ui, Zustand
- **Backend**: FastAPI (Python 3.10+), SQLAlchemy 2.0, Alembic
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Payments**: Stripe (test mode with webhooks)
- **Auth**: JWT (httponly cookies)
- **Email**: SendGrid or Resend (transactional emails)
- **Images**: Cloudinary or S3-compatible storage
- **Deployment**: Docker Compose
- **Testing**: Vitest + Testing Library (frontend), pytest (backend), Playwright (E2E)

## Features

### F1: User Authentication
- User registration with email verification
- Login with JWT (httponly cookies)
- Password reset via email
- OAuth login (Google, optional)
- User roles: customer, admin
- Profile management (name, email, shipping address)
- Order history view

### F2: Product Catalog
- Product listing page (grid view, paginated 12 per page)
- Product detail page with:
  - Image gallery (multiple images)
  - Title, description, price
  - Stock availability
  - Variant selection (size, color)
  - Quantity selector
  - Add to cart button
  - Related products
- Category filtering (Electronics, Clothing, Home, etc.)
- Search by product name/description
- Sort by: price (low-high, high-low), newest, popularity
- Product reviews and ratings (optional bonus)

### F3: Shopping Cart
- Add/remove products
- Update quantity (with stock validation)
- Cart persistence (localStorage for guests, database for authenticated)
- Cart summary (subtotal, tax, shipping, total)
- Cart badge with item count in header
- Apply discount code
- Stock validation before checkout
- Cart abandonment email (optional bonus)

### F4: Checkout Flow
- Multi-step checkout:
  1. **Shipping**: Address form (autocomplete with Google Places API optional)
  2. **Payment**: Stripe Elements (card input)
  3. **Review**: Order summary, edit options
  4. **Confirmation**: Order placed, email sent
- Guest checkout (email required)
- Saved addresses for authenticated users
- Shipping methods (standard, express)
- Tax calculation (simple percentage by state/country)
- Order notes field (optional)
- Loading states during payment processing

### F5: Payment Processing (Stripe)
- Stripe Checkout integration (hosted page)
- OR Stripe Elements (embedded card form)
- Test mode cards:
  - Success: 4242 4242 4242 4242
  - Decline: 4000 0000 0000 0002
  - 3D Secure: 4000 0025 0000 3155
- Webhook handling:
  - payment_intent.succeeded
  - payment_intent.payment_failed
  - checkout.session.completed
- Idempotency for payment processing
- Refund support (admin only)

### F6: Order Management
- Order statuses: pending, processing, shipped, delivered, cancelled
- Order detail page:
  - Order number (unique)
  - Items list with images
  - Shipping address
  - Payment method
  - Status timeline
  - Tracking number (optional)
- Order status updates (admin)
- Email notifications on status change
- Invoice generation (PDF, optional)
- Return/refund request (optional bonus)

### F7: Admin Dashboard
- Product management:
  - Create/edit/delete products
  - Upload multiple images
  - Manage variants (size, color)
  - Stock tracking
  - Bulk operations (enable/disable, price update)
- Order management:
  - Orders table (filterable, sortable)
  - Order status updates
  - Refund processing
  - Export to CSV
- Analytics:
  - Revenue chart (daily, weekly, monthly)
  - Top-selling products
  - Conversion rate
  - Average order value
- User management (view users, orders per user)

### F8: Inventory Management
- Stock tracking per product variant
- Low stock warnings (< 10 items)
- Out-of-stock indicators
- Stock reservation during checkout (30-minute hold)
- Stock adjustment history (audit log)
- Prevent overselling (concurrency handling)

### F9: Email Notifications
- Order confirmation email
- Shipping notification email
- Order status updates
- Password reset email
- Email verification
- Cart abandonment (optional)
- Templates with order details and branding

### F10: Discount System
- Discount codes:
  - Percentage off (e.g., SAVE20 = 20% off)
  - Fixed amount (e.g., FLAT10 = $10 off)
  - Free shipping
  - Minimum order value requirement
  - Single-use vs multi-use
  - Expiry date
- Apply discount at checkout
- Validation (expired, invalid, minimum not met)

## Architecture

### Frontend Structure
```
src/
├── app/
│   ├── (shop)/
│   │   ├── page.tsx (homepage/product listing)
│   │   ├── products/[slug]/page.tsx
│   │   ├── cart/page.tsx
│   │   ├── checkout/
│   │   │   ├── page.tsx (multi-step wizard)
│   │   │   └── success/page.tsx
│   │   ├── orders/
│   │   │   ├── page.tsx (order history)
│   │   │   └── [id]/page.tsx (order detail)
│   │   └── search/page.tsx
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── forgot-password/page.tsx
│   │   └── reset-password/page.tsx
│   ├── admin/
│   │   ├── layout.tsx
│   │   ├── page.tsx (dashboard)
│   │   ├── products/page.tsx
│   │   ├── products/new/page.tsx
│   │   ├── products/[id]/edit/page.tsx
│   │   ├── orders/page.tsx
│   │   ├── orders/[id]/page.tsx
│   │   └── analytics/page.tsx
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── shop/
│   │   ├── ProductCard.tsx
│   │   ├── ProductGrid.tsx
│   │   ├── ProductGallery.tsx
│   │   ├── VariantSelector.tsx
│   │   ├── AddToCartButton.tsx
│   │   └── RelatedProducts.tsx
│   ├── cart/
│   │   ├── CartItem.tsx
│   │   ├── CartSummary.tsx
│   │   ├── DiscountCodeInput.tsx
│   │   └── CartBadge.tsx
│   ├── checkout/
│   │   ├── CheckoutWizard.tsx
│   │   ├── ShippingForm.tsx
│   │   ├── PaymentForm.tsx (Stripe Elements)
│   │   └── OrderReview.tsx
│   ├── orders/
│   │   ├── OrderCard.tsx
│   │   ├── OrderStatus.tsx
│   │   └── OrderTimeline.tsx
│   ├── admin/
│   │   ├── ProductForm.tsx
│   │   ├── OrdersTable.tsx
│   │   ├── StatsCard.tsx
│   │   ├── RevenueChart.tsx
│   │   └── ImageUpload.tsx
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Sidebar.tsx
│   └── ui/ (shadcn/ui)
├── lib/
│   ├── api.ts (axios client)
│   ├── stripe.ts (Stripe client)
│   ├── auth.ts
│   └── utils.ts
├── stores/
│   ├── cartStore.ts (Zustand)
│   ├── authStore.ts
│   └── checkoutStore.ts
└── types/
    └── index.ts
```

### Backend Structure
```
src/
├── api/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── products.py
│   │   ├── cart.py
│   │   ├── orders.py
│   │   ├── payments.py (Stripe webhooks)
│   │   ├── admin.py
│   │   └── discounts.py
│   ├── dependencies/
│   │   ├── auth.py (JWT + role validation)
│   │   └── database.py
│   └── main.py
├── models/
│   ├── user.py
│   ├── product.py
│   ├── cart.py
│   ├── order.py
│   ├── payment.py
│   └── discount.py
├── schemas/
│   ├── user.py (Pydantic)
│   ├── product.py
│   ├── cart.py
│   ├── order.py
│   └── discount.py
├── services/
│   ├── auth_service.py
│   ├── product_service.py
│   ├── cart_service.py
│   ├── order_service.py
│   ├── payment_service.py (Stripe integration)
│   ├── email_service.py
│   ├── discount_service.py
│   └── inventory_service.py
├── database/
│   ├── database.py
│   └── session.py
├── alembic/
│   └── versions/
└── config.py
```

## Database Schema

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    role VARCHAR(20) DEFAULT 'customer',
    is_verified BOOLEAN DEFAULT false,
    verification_token VARCHAR(255),
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (role IN ('customer', 'admin'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_verification_token ON users(verification_token);
CREATE INDEX idx_users_reset_token ON users(reset_token);
```

### addresses
```sql
CREATE TABLE addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_addresses_user_id ON addresses(user_id);
```

### products
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    compare_at_price DECIMAL(10, 2), -- Original price for sale display
    category VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    featured BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_products_slug ON products(slug);
CREATE INDEX idx_products_category ON products(category) WHERE is_active = true;
CREATE INDEX idx_products_featured ON products(featured) WHERE is_active = true;
```

### product_images
```sql
CREATE TABLE product_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    alt_text VARCHAR(255),
    position INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_product_images_product_id ON product_images(product_id);
```

### product_variants
```sql
CREATE TABLE product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(100) UNIQUE NOT NULL,
    size VARCHAR(50),
    color VARCHAR(50),
    stock INT NOT NULL DEFAULT 0,
    price_adjustment DECIMAL(10, 2) DEFAULT 0, -- Variant price difference
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_variants_product_id ON product_variants(product_id);
CREATE INDEX idx_variants_sku ON product_variants(sku);
```

### cart_items
```sql
CREATE TABLE cart_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255), -- For guest carts
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT user_or_session CHECK (user_id IS NOT NULL OR session_id IS NOT NULL)
);

CREATE INDEX idx_cart_items_user_id ON cart_items(user_id);
CREATE INDEX idx_cart_items_session_id ON cart_items(session_id);
```

### orders
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) UNIQUE NOT NULL, -- ORD-20240115-XXXX
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    guest_email VARCHAR(255), -- For guest checkout
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    subtotal DECIMAL(10, 2) NOT NULL,
    tax DECIMAL(10, 2) NOT NULL,
    shipping DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    shipping_address_id UUID REFERENCES addresses(id),
    shipping_method VARCHAR(50),
    tracking_number VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'))
);

CREATE INDEX idx_orders_order_number ON orders(order_number);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

### order_items
```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    product_name VARCHAR(255) NOT NULL, -- Snapshot
    variant_details VARCHAR(255), -- Snapshot (size, color)
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
```

### payments
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(50), -- card, paypal, etc.
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded'))
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_stripe_id ON payments(stripe_payment_intent_id);
```

### discount_codes
```sql
CREATE TABLE discount_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL, -- percentage, fixed_amount, free_shipping
    value DECIMAL(10, 2) NOT NULL, -- 20 for 20%, or $10 for fixed
    min_order_value DECIMAL(10, 2),
    max_uses INT,
    current_uses INT DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (type IN ('percentage', 'fixed_amount', 'free_shipping'))
);

CREATE INDEX idx_discount_codes_code ON discount_codes(code);
```

### stock_history
```sql
CREATE TABLE stock_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    change INT NOT NULL, -- +10, -5
    reason VARCHAR(100), -- restock, sale, return, adjustment
    previous_stock INT NOT NULL,
    new_stock INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stock_history_variant_id ON stock_history(variant_id);
```

## API Endpoints

### Authentication
**POST /api/v1/auth/register**
- Request: `{email, username, password}`
- Response: `{user, message: "Verification email sent"}`
- Sends verification email

**POST /api/v1/auth/verify**
- Request: `{token}`
- Response: `{message: "Email verified"}`

**POST /api/v1/auth/login**
- Request: `{email, password}`
- Response: Sets httponly cookie, returns user
- Requires verified email

**POST /api/v1/auth/logout**
- Clears cookie

**POST /api/v1/auth/forgot-password**
- Request: `{email}`
- Sends reset email

**POST /api/v1/auth/reset-password**
- Request: `{token, new_password}`

### Products (Public)
**GET /api/v1/products**
- Query: `?page=1&limit=12&category=electronics&search=laptop&sort=price&order=asc&featured=true`
- Response: `{products: [...], total, page, totalPages}`

**GET /api/v1/products/{slug}**
- Response: Full product with images and variants

**GET /api/v1/categories**
- Response: `[{name, count}, ...]`

### Cart
**GET /api/v1/cart**
- Headers: Cookie (if authenticated) OR session_id (guest)
- Response: `{items: [...], subtotal, total_items}`

**POST /api/v1/cart/items**
- Request: `{product_id, variant_id, quantity}`
- Validates stock availability

**PUT /api/v1/cart/items/{id}**
- Request: `{quantity}`
- Validates stock

**DELETE /api/v1/cart/items/{id}**

**POST /api/v1/cart/apply-discount**
- Request: `{code}`
- Validates and applies discount

### Orders
**POST /api/v1/orders**
- Auth: Optional (guest checkout with email)
- Request: `{shipping_address, shipping_method, payment_method, notes?, discount_code?}`
- Creates order + Stripe PaymentIntent
- Response: `{order_id, client_secret (for Stripe)}`

**GET /api/v1/orders**
- Auth: Required
- Response: User's orders (paginated)

**GET /api/v1/orders/{id}**
- Auth: Required (own orders) or Admin
- Response: Full order details

### Payments (Webhooks)
**POST /api/v1/payments/webhook**
- Stripe webhook endpoint
- Handles: payment_intent.succeeded, payment_intent.failed
- Updates order status, sends confirmation email

**POST /api/v1/payments/refund**
- Auth: Admin
- Request: `{order_id, amount?}` (full refund if no amount)

### Admin - Products
**POST /api/v1/admin/products**
- Auth: Admin
- Request: `{name, description, price, category, variants: [{sku, size, color, stock}], images: [...]}`

**PUT /api/v1/admin/products/{id}**
- Auth: Admin

**DELETE /api/v1/admin/products/{id}**
- Auth: Admin

### Admin - Orders
**GET /api/v1/admin/orders**
- Auth: Admin
- Query: `?status=processing&page=1`

**PUT /api/v1/admin/orders/{id}/status**
- Auth: Admin
- Request: `{status, tracking_number?}`
- Sends email notification

### Admin - Analytics
**GET /api/v1/admin/analytics/revenue**
- Auth: Admin
- Query: `?period=week|month|year`
- Response: `{revenue_by_day: [...], total}`

**GET /api/v1/admin/analytics/top-products**
- Auth: Admin
- Response: `[{product, revenue, units_sold}, ...]`

## Validation Rules

### Product
- Name: 1-255 chars
- Description: Max 5000 chars
- Price: > 0, max 2 decimal places
- Category: One of predefined list
- Variant SKU: Unique, 3-50 chars

### Order
- Shipping address: All fields required
- Items: Min 1 item, stock available
- Tax: Calculated based on shipping state
- Shipping: Selected method valid

### Payment
- Stripe card: Valid card number, expiry, CVC
- Amount: Matches order total
- Idempotency: Prevent duplicate charges

### Discount
- Code: Uppercase, alphanumeric, 3-20 chars
- Expiry: Future date
- Min order value: >= 0
- Max uses: > 0 if limited

## Error Handling

### Frontend
- Form validation inline
- Toast notifications for errors
- Payment errors: Display Stripe error message
- Network errors: Retry button
- Loading states: Skeleton UI

### Backend
- 400: Validation errors
- 401: Unauthorized
- 403: Forbidden (admin only)
- 404: Product/Order not found
- 409: Conflict (insufficient stock, duplicate order)
- 422: Invalid request
- 500: Internal server error

### Payment Errors
- Card declined: Show user-friendly message
- Insufficient funds: Prompt different payment method
- 3D Secure required: Redirect to auth flow
- Network error: Retry payment

## Email Templates

### Order Confirmation
- Order number, items list, total
- Shipping address
- Payment method (last 4 digits)
- Track order link

### Shipping Notification
- Tracking number
- Carrier name
- Estimated delivery date
- Track shipment link

### Password Reset
- Reset link (expires in 1 hour)
- Security notice

## Performance Requirements

### Frontend
- Product listing: < 2s (LCP)
- Product detail: < 1.5s
- Cart operations: < 300ms
- Checkout: < 3s per step
- Stripe payment: < 2s (network dependent)

### Backend
- List products: < 150ms
- Product detail: < 100ms
- Cart operations: < 100ms
- Order creation: < 500ms
- Payment webhook: < 1s (must respond quickly to Stripe)

### Database
- Indexes on foreign keys
- Pagination for large result sets
- Optimistic locking for stock updates
- Connection pooling

## Security Requirements

### Payment Security
- PCI compliance: Never store card details
- Stripe Elements: Client-side card tokenization
- HTTPS only for checkout
- Webhook signature verification

### Data Protection
- Passwords: bcrypt hashing (cost factor 12)
- JWT: HttpOnly cookies, secure flag in production
- CSRF protection
- Rate limiting on auth endpoints
- SQL injection prevention (parameterized queries)

## Stripe Test Mode

### Test Cards
- Success: 4242 4242 4242 4242
- Decline (generic): 4000 0000 0000 0002
- Decline (insufficient funds): 4000 0000 0000 9995
- 3D Secure required: 4000 0025 0000 3155

### Webhook Testing
- Use Stripe CLI for local webhook testing
- `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`

## Docker Compose

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: pk_test_xxx
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/ecommerce
      REDIS_URL: redis://redis:6379
      SECRET_KEY: your-secret-key
      STRIPE_SECRET_KEY: sk_test_xxx
      STRIPE_WEBHOOK_SECRET: whsec_xxx
      SENDGRID_API_KEY: your-api-key
      FRONTEND_URL: http://localhost:3000
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: ecommerce
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Test Coverage Requirements

### Frontend
- Unit tests: ≥ 90%
- Components: ProductCard, Cart, Checkout wizard
- Store: cartStore, checkoutStore
- Utils: Price formatting, tax calculation

### Backend
- Unit tests: ≥ 95%
- Services: payment_service, inventory_service, order_service
- Routers: All endpoints
- Stripe webhook handling

### E2E Tests (40 scenarios)
1. Browse product catalog
2. Filter by category
3. Search products
4. Sort by price
5. View product detail
6. Select variant (size, color)
7. Add to cart (guest)
8. Add to cart (authenticated)
9. Update cart quantity
10. Remove from cart
11. Apply valid discount code
12. Apply invalid discount code
13. Cart persistence (localStorage)
14. Cart persistence (database)
15. Guest checkout flow
16. Authenticated checkout flow
17. Checkout - shipping form validation
18. Checkout - payment with test card (success)
19. Checkout - payment with test card (decline)
20. Checkout - payment with 3D Secure
21. Order confirmation email sent
22. View order history (authenticated)
23. View order detail
24. Admin login
25. Admin - create product
26. Admin - upload product images
27. Admin - create variant
28. Admin - update stock
29. Admin - view orders
30. Admin - update order status
31. Admin - shipping notification email sent
32. Admin - process refund
33. Admin - view revenue analytics
34. Admin - view top products
35. Stock validation (prevent overselling)
36. Stock reservation during checkout (30-min hold)
37. Webhook handling (payment succeeded)
38. Webhook handling (payment failed)
39. Password reset flow
40. Email verification flow

## Success Criteria

1. ✅ User authentication complete (register, login, verify, reset)
2. ✅ Product catalog with categories, search, filter, sort
3. ✅ Shopping cart functional (add, update, remove, persist)
4. ✅ Checkout flow complete (3 steps, validation)
5. ✅ Stripe payment integration working (test cards)
6. ✅ Webhook handling functional (payment events)
7. ✅ Order management complete (create, view, status updates)
8. ✅ Email notifications sent (order confirmation, shipping)
9. ✅ Discount code system working (percentage, fixed, validation)
10. ✅ Inventory management with stock validation
11. ✅ Stock reservation prevents overselling
12. ✅ Admin dashboard functional (products, orders, analytics)
13. ✅ All E2E tests passing (40 scenarios)
14. ✅ Test coverage ≥90% (frontend), ≥95% (backend)
15. ✅ Performance requirements met
16. ✅ Security requirements met (PCI, bcrypt, JWT)
17. ✅ Docker Compose up and running (4 services)
18. ✅ Database migrations applied
19. ✅ Responsive design (mobile, tablet, desktop)
20. ✅ Error handling comprehensive (payment, stock, validation)
