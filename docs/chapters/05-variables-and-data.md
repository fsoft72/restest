# Variables and Data

This chapter covers variable management, data extraction from responses, and using RESTest's powerful path parser for accessing nested data structures.

## Variable Basics

RESTest uses Python's string formatting syntax `%(variable_name)s` for variable references.

### Setting Variables

There are several ways to set variables:

#### 1. Command Line
```bash
restest --key user_id:123 --key token:abc123 test.json
```

#### 2. Using the Set Action
```json
{
    "action": "set",
    "key": "base_path",
    "value": "/api/v2"
}
```

#### 3. Extracting from Responses
```json
{
    "method": "post",
    "url": "/auth/login",
    "fields": [
        ["token", "auth_token"],
        ["user.id", "user_id"]
    ]
}
```

### Variable Scope

Variables in RESTest are:
- Global across all test files
- Persistent throughout test execution
- Case-sensitive
- String-based (numbers are converted to strings)

## Data Extraction

### Basic Field Extraction
```json
{
    "method": "get",
    "url": "/users/1",
    "fields": [
        "id",                    // Same name extraction  (a new variable named 'id' is created)
        ["email", "user_email"] // Renamed extraction  (a new variable named 'user_email' is created from 'email')
    ]
}
```

### Nested Data Extraction
```json
{
    "fields": [
        ["user.profile.id", "profile_id"],
        ["settings.preferences.theme", "user_theme"]
    ]
}
```

### Array Data Extraction
```json
{
    "fields": [
        ["items[0].id", "first_item_id"],
        ["users.[role=admin].id", "admin_id"]
    ]
}
```

## Path Parser

RESTest's path parser provides powerful ways to access nested data.

### Basic Path Notation

#### Direct Field Access
```json
{
    "fields": [
        "id",              // Root level field
        "user.name",       // Nested field
        "deeply.nested.value"  // Multiple levels
    ]
}
```

#### Array Access
```json
{
    "fields": [
        "[0]",            // First element of root array
        "items[0]",       // First element of items array
        "items[1].name"   // Name of second item
    ]
}
```

#### Conditional Access
```json
{
    "fields": [
        "users.[status=active]",     // First active user
        "items.[price>100].name",    // Names of expensive items
        "data.[type!=deleted].id"    // IDs of non-deleted items
    ]
}
```

### Advanced Path Parser Examples

#### Multiple Conditions
```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/search",
            "fields": [
                ["results.[type=user].[status=active].name", "active_users"],
                ["results.[price>=100].[stock>0].id", "available_premium_items"]
            ]
        }
    ]
}
```

#### Nested Array Navigation
```json
{
    "fields": [
        ["categories[0].products[0].variants[0].sku", "first_sku"],
        ["orders.[status=completed].items.[quantity>1].product_id", "bulk_order_products"]
    ]
}
```

## Complete Examples

### User Authentication Flow
```json
{
    "actions": [
        {
            "title": "Set API Version",
            "action": "set",
            "key": "api_version",
            "value": "v2"
        },
        {
            "title": "Login",
            "method": "post",
            "url": "/api/%(api_version)s/auth/login",
            "params": {
                "email": "user@example.com",
                "password": "secret123"
            },
            "fields": [
                ["token", "auth_token"],
                ["user.id", "user_id"],
                ["user.permissions", "user_perms"]
            ]
        },
        {
            "title": "Get User Profile",
            "method": "get",
            "url": "/api/%(api_version)s/users/%(user_id)s",
            "headers": {
                "Authorization": "Bearer %(auth_token)s"
            },
            "fields": [
                ["profile.settings.*", "user_settings"],
                ["profile.preferences", "user_prefs"]
            ]
        }
    ]
}
```

### Complex Data Processing
```json
{
    "actions": [
        {
            "title": "Search Products",
            "method": "get",
            "url": "/api/products/search",
            "params": {
                "category": "electronics",
                "min_price": 100
            },
            "fields": [
                ["results.[price>=500].[stock>0].id", "premium_products"],
                ["facets.categories.[count>10].name", "popular_categories"],
                ["metadata.total_count", "total_results"]
            ],
            "tests": [
                {
                    "field": "results.[price>=500]",
                    "mode": "SIZE-GT",
                    "value": 0
                }
            ]
        },
        {
            "title": "Process Premium Products",
            "method": "post",
            "url": "/api/batch/process",
            "params": {
                "product_ids": "%(premium_products)s",
                "action": "discount",
                "amount": 10
            }
        }
    ]
}
```

## Environment Variables

### Loading Environment Variables
```bash
restest --env test.json
```

### Environment File Example
```json
{
    "API_KEY": "your-api-key",
    "API_SECRET": "your-api-secret",
    "ENVIRONMENT": "staging"
}
```

### Saving Variables
```bash
restest --env-save vars.json test.json
```

## Variable Manipulation

### String Concatenation
```json
{
    "action": "set",
    "key": "full_name",
    "value": "%(first_name)s %(last_name)s"
}
```

### Using in URLs
```json
{
    "method": "get",
    "url": "/api/%(version)s/users/%(user_id)s/profile"
}
```

### Headers and Authentication
```json
{
    "headers": {
        "X-API-Key": "%(api_key)s",
        "X-Request-ID": "%(request_id)s"
    }
}
```

## Best Practices

1. **Naming Conventions**
   - Use descriptive variable names
   - Follow a consistent naming pattern
   - Indicate variable type in name when useful

2. **Data Extraction**
   - Extract only needed data
   - Use meaningful variable names
   - Document expected data structures

3. **Path Parser**
   - Use appropriate conditions
   - Handle missing data gracefully
   - Test complex paths separately

4. **Variable Management**
   - Clean up temporary variables
   - Document required variables
   - Use environment variables for sensitive data

## Troubleshooting

### Common Issues

1. **Variable Not Found**
```json
// ❌ Wrong
{
    "url": "/api/%(UserID)s"  // Variable is case-sensitive
}

// ✅ Correct
{
    "url": "/api/%(user_id)s"
}
```

2. **Wrong Path Syntax**
```json
// ❌ Wrong
{
    "fields": [
        ["users.{role=admin}", "admin"]  // Invalid syntax
    ]
}

// ✅ Correct
{
    "fields": [
        ["users.[role=admin]", "admin"]
    ]
}
```

3. **Missing Variable Type Specifier**
```json
// ❌ Wrong
{
    "url": "/api/%(user_id)"  // Missing 's' type specifier
}

// ✅ Correct
{
    "url": "/api/%(user_id)s"
}
```
