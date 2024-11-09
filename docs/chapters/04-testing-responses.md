# Testing Responses

This chapter covers all aspects of testing API responses with RESTest, including status codes, response body validation, header checking, and different test modes.

## Basic Response Testing

Every request can include tests to validate the response:

```json
{
    "method": "get",
    "url": "/api/users/1",
    "tests": [
        {
            "field": "name",
            "value": "John Doe"
        },
        {
            "field": "email",
            "mode": "EXISTS"
        }
    ]
}
```

## Status Code Validation

### Default Status Codes
By default, RESTest expects a 200 status code. You can override this:

```json
{
    "method": "post",
    "url": "/api/users",
    "status_code": 201,
    "body": {
        "name": "John Doe"
    }
}
```

### Common Status Code Scenarios

#### Created Resource (201)
```json
{
    "method": "post",
    "url": "/api/resources",
    "status_code": 201,
    "tests": [
        {
            "field": "id",
            "mode": "EXISTS"
        }
    ]
}
```

#### Not Found (404)

If you specifically expect a 404 status code, you can ignore the error and in this case `ignore_error` directive can be omitted.

```json
{
    "method": "get",
    "url": "/api/users/999999",
    "status_code": 404,
    "ignore_error": true
}
```

#### Validation Error (400)
```json
{
    "method": "post",
    "url": "/api/users",
    "status_code": 400,
    "params": {
        "email": "invalid-email"
    },
    "tests": [
        {
            "field": "errors.email",
            "mode": "EXISTS"
        }
    ]
}
```

## Test Modes

RESTest supports various test modes for different validation scenarios:

### Equality Tests
```json
{
    "tests": [
        {
            "field": "status",
            "mode": "EQUALS",  // or "==" or "="
            "value": "active"
        }
    ]
}
```

### Existence Tests
```json
{
    "tests": [
        {
            "field": "id",
            "mode": "EXISTS"  // or "!!" or "NOT_NULL"
        }
    ]
}
```

### Non-Existence Tests
```json
{
    "tests": [
        {
            "field": "deleted_at",
            "mode": "EMPTY"  // or "IS_NULL" or "NULL"
        }
    ]
}
```

### Inequality Tests
```json
{
    "tests": [
        {
            "field": "status",
            "mode": "NOT_EQUAL",  // or "!=" or "<>"
            "value": "deleted"
        }
    ]
}
```

### Containment Tests

Suppose that the value of `tags` is an array field of strings, like: `[ "admin", "user" ]`.

```json
{
    "tests": [
        {
            "field": "tags",
            "mode": "CONTAINS",  // or "->"
            "value": "admin"
        }
    ]
}
```

### Size Tests
```json
{
    "tests": [
        {
            "field": "items",
            "mode": "SIZE",  // or "LEN" or "LENGTH"
            "value": 10
        }
    ]
}
```

### Numeric Comparisons

`GT` (greater than), `GTE` (greater than or equal), `LT` (less than), `LTE` (less than or equal)

```json
{
    "tests": [
        {
            "field": "count",
            "mode": "GT",  // or ">"
            "value": 0
        },
        {
            "field": "price",
            "mode": "LTE",  // or "<="
            "value": 100
        }
    ]
}
```

### Array Size Comparisons

To test for array sizes, use `SIZE-GT` (size greater than) and `SIZE-LTE` (size less than or equal).

```json
{
    "tests": [
        {
            "field": "users",
            "mode": "SIZE-GT",  // or "()>"
            "value": 5
        },
        {
            "field": "products",
            "mode": "SIZE-LTE",  // or "()<="
            "value": 20
        }
    ]
}
```

## Path-Based Testing

RESTest provides powerful path-based testing for complex JSON responses:

### Array Element Testing
```json
{
    "tests": [
        {
            "field": "[0].id",  // First element's ID
            "value": 1
        },
        {
            "field": "users[2].name",  // Third user's name
            "value": "Alice"
        }
    ]
}
```

### Nested Object Testing
```json
{
    "tests": [
        {
            "field": "user.address.city",
            "value": "New York"
        },
        {
            "field": "metadata.settings.theme",
            "value": "dark"
        }
    ]
}
```

### Conditional Path Testing
```json
{
    "tests": [
        {
            "field": "items.[type=book].price",  // Price of items of type 'book'
            "mode": "LT",
            "value": 100
        }
    ]
}
```

## Response Size Testing

RESTest introduces also some *meta* fields that can be used for testing.
At the moment, the only meta field available is `rt:size` which represents the size of the response in bytes.

Test the size of the response:

```json
{
    "tests": [
        {
            "field": "rt:size",
            "mode": "LT",
            "value": 1024  // Response must be less than 1KB
        }
    ]
}
```

## Complex Testing Examples

### User Registration Flow
```json
{
    "actions": [
        {
            "title": "Register User",
            "method": "post",
            "url": "/api/register",
            "params": {
                "email": "test@example.com",
                "password": "secret123"
            },
            "status_code": 201,
            "tests": [
                {
                    "field": "id",
                    "mode": "EXISTS"
                },
                {
                    "field": "email",
                    "value": "test@example.com"
                },
                {
                    "field": "roles",
                    "mode": "SIZE",
                    "value": 1
                },
                {
                    "field": "roles[0]",
                    "value": "user"
                },
                {
                    "field": "created_at",
                    "mode": "EXISTS"
                }
            ],
            "fields": [
                ["id", "user_id"],
                ["token", "auth_token"]
            ]
        },
        {
            "title": "Verify User Profile",
            "method": "get",
            "url": "/api/users/%(user_id)s",
            "headers": {
                "Authorization": "Bearer %(auth_token)s"
            },
            "tests": [
                {
                    "field": "email",
                    "value": "test@example.com"
                },
                {
                    "field": "status",
                    "value": "active"
                },
                {
                    "field": "password",
                    "mode": "NOT_EXISTS"
                }
            ]
        }
    ]
}
```

### Product Search Validation
```json
{
    "method": "get",
    "url": "/api/products/search",
    "params": {
        "q": "phone",
        "min_price": 100
    },
    "tests": [
        {
            "field": "total",
            "mode": "GT",
            "value": 0
        },
        {
            "field": "products",
            "mode": "SIZE-GT",
            "value": 0
        },
        {
            "field": "products.[price<100]",
            "mode": "SIZE",
            "value": 0
        },
        {
            "field": "products[0]",
            "mode": "OBJECT",
            "value": {
                "id": "EXISTS",
                "name": "EXISTS",
                "price": "GT:100"
            }
        },
        {
            "field": "facets.categories",
            "mode": "EXISTS"
        },
        {
            "field": "rt:size",
            "mode": "LT",
            "value": 10240  // Response should be under 10KB
        }
    ]
}
```

## Best Practices

1. **Test Organization**
   - Group related tests logically
   - Test most important aspects first
   - Include both positive and negative tests

2. **Path Testing**
   - Use meaningful path expressions
   - Handle nested data carefully
   - Test array elements systematically

3. **Error Testing**
   - Validate error responses thoroughly
   - Check error message formats
   - Verify appropriate status codes

4. **Performance Testing**
   - Use `max_exec_time` for timing constraints
   - Test response sizes when relevant
   - Monitor response times consistently

5. **Data Validation**
   - Verify data types
   - Check data ranges
   - Validate data relationships

## Troubleshooting Tests

### Common Issues

1. **Path Not Found**
```json
// ❌ Wrong
{
    "field": "user.firstName",  // JSON has "first_name"
    "value": "John"
}

// ✅ Correct
{
    "field": "user.first_name",
    "value": "John"
}
```

2. **Array Index Out of Bounds**
```json
// ❌ Wrong
{
    "field": "items[5]",  // Array has only 3 items
    "value": "something"
}

// ✅ Correct
{
    "field": "items",
    "mode": "SIZE-GT",
    "value": 0
}
```

3. **Type Mismatches**
```json
// ❌ Wrong
{
    "field": "age",
    "value": "25"  // Number stored as string
}

// ✅ Correct
{
    "field": "age",
    "value": 25
}
```