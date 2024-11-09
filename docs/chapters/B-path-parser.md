# Path Parser

RESTest's Path Parser is a powerful tool for navigating and extracting data from complex JSON structures. This chapter provides a complete guide to its syntax and capabilities.

## Basic Syntax

The path parser uses a dot notation with special syntax for arrays and conditions:

```
field.nested_field[array_index].further_nested.field[condition]
```

## Core Concepts

### Direct Field Access
```json
{
    "name": "John",
    "age": 30
}
```
Path: `name` -> Returns: `"John"`

### Nested Fields
```json
{
    "user": {
        "profile": {
            "name": "John",
            "age": 30
        }
    }
}
```
Path: `user.profile.name` -> Returns: `"John"`

### Array Access
```json
{
    "items": [
        {"id": 1, "name": "First"},
        {"id": 2, "name": "Second"}
    ]
}
```
Path: `items[0].name` -> Returns: `"First"`

## Advanced Features

### Conditional Access

#### Equality Condition
```json
{
    "users": [
        {"role": "admin", "name": "John"},
        {"role": "user", "name": "Jane"}
    ]
}
```
Path: `users.[role=admin].name` -> Returns: `"John"`

#### Inequality Condition
```json
{
    "items": [
        {"status": "active", "id": 1},
        {"status": "deleted", "id": 2}
    ]
}
```
Path: `items.[status!=deleted].id` -> Returns: `1`

### Multiple Conditions
```json
{
    "products": [
        {"type": "book", "price": 20, "inStock": true},
        {"type": "book", "price": 30, "inStock": false},
        {"type": "electronics", "price": 100, "inStock": true}
    ]
}
```
Path: `products.[type=book].[inStock=true].price` -> Returns: `20`

### Numeric Comparisons
```json
{
    "orders": [
        {"id": 1, "total": 50},
        {"id": 2, "total": 150},
        {"id": 3, "total": 200}
    ]
}
```
```plaintext
Path: orders.[total>100].id      -> Returns: [2, 3]
Path: orders.[total<=150].id     -> Returns: [1, 2]
```

## Path Parser Syntax Reference

### Basic Elements

| Syntax | Description | Example |
|--------|-------------|---------|
| `.` | Object property accessor | `user.name` |
| `[n]` | Array index accessor | `items[0]` |
| `.[condition]` | Conditional accessor | `users.[role=admin]` |

### Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equality | `[status=active]` |
| `!=` | Inequality | `[status!=deleted]` |
| `>` | Greater than | `[price>100]` |
| `>=` | Greater than or equal | `[age>=18]` |
| `<` | Less than | `[stock<10]` |
| `<=` | Less than or equal | `[priority<=3]` |

## Common Use Cases

### Data Extraction

#### Basic Field Extraction
```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/users/1",
            "fields": [
                ["user.profile.id", "profile_id"],
                ["user.settings.theme", "user_theme"]
            ]
        }
    ]
}
```

#### Conditional Extraction
```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/teams",
            "fields": [
                ["members.[role=leader].id", "leader_id"],
                ["projects.[status=active].name", "active_projects"]
            ]
        }
    ]
}
```

### Response Testing

#### Array Testing
```json
{
    "tests": [
        {
            "field": "users.[status=active]",
            "mode": "SIZE-GT",
            "value": 0
        },
        {
            "field": "orders.[total>1000].[status=paid].id",
            "mode": "EXISTS"
        }
    ]
}
```

#### Nested Object Testing
```json
{
    "tests": [
        {
            "field": "user.addresses.[type=primary].country",
            "value": "USA"
        },
        {
            "field": "settings.notifications.[priority>=high]",
            "mode": "SIZE-LTE",
            "value": 5
        }
    ]
}
```

## Complex Examples

### E-commerce Order Processing
```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/orders",
            "fields": [
                ["orders.[status=pending].[total>100].id", "high_value_orders"],
                ["orders.[items.[category=electronics]].id", "electronics_orders"],
                ["customers.[orders>10].id", "vip_customers"]
            ],
            "tests": [
                {
                    "field": "orders.[payment_status=failed]",
                    "mode": "SIZE",
                    "value": 0
                },
                {
                    "field": "orders.[status=processing].estimated_delivery",
                    "mode": "EXISTS"
                }
            ]
        }
    ]
}
```

### User Management System
```json
{
    "actions": [
        {
            "method": "get",
            "url": "/api/organization/%(org_id)s",
            "fields": [
                ["departments.[manager.status=active].id", "active_departments"],
                ["users.[permissions.[name=admin]].email", "admin_emails"],
                ["projects.[status!=completed].[priority=high].id", "urgent_projects"]
            ],
            "tests": [
                {
                    "field": "users.[role=admin].[status=active]",
                    "mode": "SIZE-GT",
                    "value": 0,
                    "title": "At least one active admin exists"
                },
                {
                    "field": "departments.[budget>1000000].name",
                    "mode": "EXISTS",
                    "title": "High-budget department exists"
                }
            ]
        }
    ]
}
```

## Best Practices

1. **Path Construction**
   - Use descriptive field names
   - Keep paths as simple as possible
   - Break complex paths into multiple steps

2. **Error Handling**
   - Always test path existence before accessing nested values
   - Use appropriate test modes for validation
   - Handle array bounds properly

3. **Performance**
   - Avoid overly complex nested conditions
   - Use specific paths instead of searching entire structures
   - Cache frequently accessed values

4. **Maintenance**
   - Document complex path patterns
   - Use variables for repeated paths
   - Keep paths consistent across tests

## Common Pitfalls

### Invalid Path Syntax
```json
// ❌ Wrong
{
    "field": "users[role=admin]",  // Missing dot before condition
    "value": "admin"
}

// ✅ Correct
{
    "field": "users.[role=admin]",
    "value": "admin"
}
```

### Incorrect Quotation
```json
// ❌ Wrong
{
    "field": "users.[email=user@example.com]",  // Unquoted email
    "value": "active"
}

// ✅ Correct
{
    "field": "users.[email='user@example.com']",
    "value": "active"
}
```

### Missing Array Index
```json
// ❌ Wrong
{
    "field": "items.price",  // Attempting to access price directly from array
    "value": 100
}

// ✅ Correct
{
    "field": "items[0].price",
    "value": 100
}
```

### Invalid Condition Operators
```json
// ❌ Wrong
{
    "field": "users.[age=>18]",  // Invalid operator syntax
    "mode": "EXISTS"
}

// ✅ Correct
{
    "field": "users.[age>=18]",
    "mode": "EXISTS"
}
```
