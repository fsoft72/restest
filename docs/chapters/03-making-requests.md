# Making Requests

This chapter covers everything you need to know about making HTTP requests with RESTest, including methods, parameters, authentication, headers, and file uploads.

## HTTP Methods

RESTest supports all standard HTTP methods:

### GET Requests
```json
{
    "method": "get",
    "url": "/api/users",
    "params": {
        "page": 1,
        "limit": 10,
        "sort": "name"
    }
}
```
GET parameters are automatically encoded and appended to the URL.

### POST Requests
```json
{
    "method": "post",
    "url": "/api/users",
    "body": {
        "name": "John Doe",
        "email": "john@example.com",
        "roles": ["user", "admin"]
    }
}
```

### PUT Requests
```json
{
    "method": "put",
    "url": "/api/users/%(user_id)s",
    "body": {
        "name": "John Smith",
        "email": "john.smith@example.com"
    }
}
```

### PATCH Requests
```json
{
    "method": "patch",
    "url": "/api/users/%(user_id)s",
    "body": {
        "name": "John Smith"
    }
}
```

### DELETE Requests
```json
{
    "method": "delete",
    "url": "/api/users/%(user_id)s"
}
```

## Request Parameters

### Query Parameters (GET)
Parameters in GET requests are automatically URL-encoded:

```json
{
    "method": "get",
    "url": "/search",
    "params": {
        "q": "search term",
        "filters": ["active", "verified"],
        "date_range": "2023-01-01,2024-01-01"
    }
}
```
Becomes: `/search?q=search%20term&filters=%5B%22active%22%2C%22verified%22%5D&date_range=2023-01-01%2C2024-01-01`

### Request Body (POST/PUT/PATCH)
You can send data in different formats:

#### JSON Content (Default)
```json
{
    "method": "post",
    "url": "/api/users",
    "body": {
        "name": "John Doe",
        "metadata": {
            "age": 30,
            "location": "New York"
        },
        "tags": ["developer", "manager"]
    }
}
```

#### Form Data
```json
{
    "method": "post",
    "url": "/api/form",
    "content": "form",
    "body": {
        "name": "John Doe",
        "email": "john@example.com"
    }
}
```

## Headers and Cookies

### Custom Headers
Headers can be set at different levels:

#### Global Headers (in system config)
```json
{
    "system": {
        "global_headers": {
            "X-API-Version": "1.0",
            "Accept-Language": "en-US"
        }
    }
}
```

#### Request-Specific Headers
```json
{
    "method": "get",
    "url": "/api/protected",
    "headers": {
        "X-Custom-Header": "value",
        "X-Request-ID": "%(request_id)s"
    }
}
```

### Cookies

Since RESTest is based on the Python `requests` library, cookies are handled automatically, but you can also set them explicitly:

```json
{
    "method": "get",
    "url": "/api/dashboard",
    "cookies": {
        "session_id": "%(session_cookie)s",
        "preference": "dark_mode"
    }
}
```

## Authentication

RESTest supports different authentication approaches:

### Bearer Token Authentication
```json
{
    "system": {
        "headers": {
            "Authorization": "Bearer %(token)s"
        }
    }
}
```

### Per-Request Authentication Control
```json
{
    "method": "get",
    "url": "/api/public",
    "auth": false  // Disable authentication for this request
}
```

### Authentication Flow Example
```json
{
    "actions": [
        {
            "title": "Login",
            "method": "post",
            "url": "/auth/login",
            "auth": false,
            "body": {
                "username": "admin",
                "password": "secret"
            },
            "fields": [
                ["token", "auth_token"]
            ]
        },
        {
            "title": "Get Protected Resource",
            "method": "get",
            "url": "/api/protected",
            "headers": {
                "Authorization": "Bearer %(auth_token)s"
            }
        }
    ]
}
```

## File Uploads

RESTest supports various file upload scenarios:

### Single File Upload
```json
{
    "method": "post",
    "url": "/api/upload",
    "content": "form",
    "files": {
        "document": "./path/to/document.pdf"
    }
}
```

### Multiple Files with Same Field
```json
{
    "method": "post",
    "url": "/api/upload-multiple",
    "content": "form",
    "files": {
        "documents": [
            "./path/to/doc1.pdf",
            "./path/to/doc2.pdf"
        ]
    }
}
```

### Multiple Files with Different Fields
```json
{
    "method": "post",
    "url": "/api/upload-profile",
    "content": "form",
    "files": {
        "avatar": "./path/to/avatar.jpg",
        "resume": "./path/to/resume.pdf"
    },
    "body": {
        "user_id": "%(user_id)s"
    }
}
```

## Advanced Request Features

### Request Timing Control
```json
{
    "method": "get",
    "url": "/api/slow-endpoint",
    "max_exec_time": 1000  // Fail if request takes more than 1000ms
}
```

### Error Handling
```json
{
    "method": "post",
    "url": "/api/users",
    "ignore_error": true,  // Continue even if request fails
    "status_code": 409     // Expect a conflict response
}
```

### Request Repetition
```json
{
    "method": "get",
    "url": "/api/status",
    "repeat": 3  // Execute this request 3 times
}
```

## Working Examples

### Complete API Test Suite
```json
{
    "system": {
        "base_url": "https://api.example.com",
        "log_file": "./api-test.log",
        "authorization_template": "Bearer %(token)s",
        "global_headers": {
            "Accept": "application/json",
            "X-Client-Version": "1.0"
        }
    },
    "actions": [
        {
            "title": "Authentication",
            "method": "post",
            "url": "/auth/login",
            "auth": false,
            "body": {
                "username": "testuser",
                "password": "testpass"
            },
            "fields": [
                ["token", "api_token"]
            ]
        },
        {
            "title": "Create User Profile",
            "method": "post",
            "url": "/users",
            "body": {
                "name": "Test User",
                "email": "test@example.com"
            },
            "fields": [
                ["id", "user_id"]
            ]
        },
        {
            "title": "Upload Profile Picture",
            "method": "post",
            "url": "/users/%(user_id)s/avatar",
            "content": "form",
            "files": {
                "avatar": "./test-data/avatar.jpg"
            },
            "status_code": 201
        },
        {
            "title": "Verify Profile",
            "method": "get",
            "url": "/users/%(user_id)s",
            "tests": [
                {
                    "field": "name",
                    "value": "Test User"
                },
                {
                    "field": "avatar",
                    "mode": "EXISTS"
                }
            ]
        }
    ]
}
```

## Best Practices

1. **URL Construction**
   - Use variables for dynamic parts of URLs
   - Keep base URL in system configuration
   - Use proper URL encoding for special characters

2. **Parameters**
   - Validate parameter types match API expectations
   - Use appropriate content type for the request
   - Structure nested data properly

3. **Headers**
   - Set common headers in global configuration
   - Use request-specific headers only when needed
   - Include proper content-type headers

4. **File Uploads**
   - Use relative paths from test file location
   - Verify file existence before test execution
   - Set appropriate content-type for file uploads

5. **Error Handling**
   - Set appropriate status code expectations
   - Use ignore_error for expected failures
   - Include proper error validation tests

## Troubleshooting

### Common Issues and Solutions

1. **Connection Errors**
   ```
   Problem: Cannot connect to host
   Solution: Verify base_url and network connectivity
   ```

2. **Authentication Failures**
   ```
   Problem: 401 Unauthorized
   Solution: Check token format and validity
   ```

3. **File Upload Issues**
   ```
   Problem: File not found
   Solution: Verify file paths are relative to test file
   ```

4. **Parameter Encoding**
   ```
   Problem: Malformed URL
   Solution: Let RESTest handle parameter encoding
   ```

5. **Timeout Issues**
   ```
   Problem: Request exceeds max_exec_time
   Solution: Increase timeout or optimize endpoint
   ```
