# Validation Rules Summary

## Endpoint:create_product
- **body** (presence): Request body is required for POST {path}
- **body** (format): Request body must be valid JSON

## Endpoint:create_user
- **body** (presence): Request body is required for POST {path}
- **body** (format): Request body must be valid JSON

## Endpoint:get_product
- **id** (presence): ID parameter is required
- **id** (format): ID parameter must be a valid UUID

## Product
- **id** (format): id must be a valid UUID (RFC 4122)
- **id** (presence): id is required
- **sku** (format): sku cannot be empty
- **sku** (presence): sku is required
- **name** (format): name cannot be empty
- **name** (presence): name is required
- **price** (presence): price is required
- **quantity** (presence): quantity is required
- **status** (format): status must be one of the allowed values
- **status** (presence): status status is required
- **created_at** (format): created_at must be a valid ISO 8601 datetime
- **created_at** (presence): created_at is required
- **is_active** (format): is_active must be true or false
- **is_active** (presence): is_active is required
- **id** (uniqueness): id must be unique
- **price** (range): price must be greater than 0
- **price** (format): price must be a valid decimal with 2 decimal places
- **quantity** (range): quantity must be greater than or equal to 0
- **quantity** (stock_constraint): quantity quantity cannot exceed available stock

## User
- **id** (format): id must be a valid UUID (RFC 4122)
- **id** (presence): id is required
- **email** (format): email must be a valid email address
- **email** (presence): email is required
- **password** (format): password must be at least 8 characters with uppercase, lowercase, and numbers
- **password** (presence): password is required
- **created_at** (format): created_at must be a valid ISO 8601 datetime
- **created_at** (presence): created_at is required
- **id** (uniqueness): id must be unique
- **email** (uniqueness): email must be unique
- **password** (range): password must be between 8 and 128 characters
