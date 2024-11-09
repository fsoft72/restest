# Test Structure

This chapter explains how to structure your RESTest test files, including system configuration, action types, and test organization.

## JSON File Structure

A RESTest file consists of two main sections:
- `system`: Global configuration settings (optional)
- `actions`: Array of test actions to execute

Basic structure:
```json
{
    "system": {
        // Global configuration (optional)
    },
    "actions": [
        // Test actions
    ]
}
```

## System Configuration

The `system` section defines global settings for your tests.

### Available Options

```json
{
    "system": {
        "base_url": "https://api.example.com",
        "log_file": "./restest.log",
        "stop_on_error": true,
        "global_headers": {
            "X-API-Version": "1.0",
            "Accept-Language": "en-US"
        },
        "headers": {
            "Authorization": "Bearer %(token)s"
        }
    }
}
```

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `base_url` | Base URL for all requests | None | `"https://api.example.com"` |
| `log_file` | Path to log file | None | `"./restest.log"` |
| `stop_on_error` | Stop execution on test failure | `true` | `false` |
| `global_headers` | Headers added to all requests | `{}` | `{"X-API-Version": "1.0"}` |
| `headers` | Headers with variable support | `{}` | `{"Authorization": "Bearer %(token)s"}` |

### Headers Priority

Headers are applied in this order (later ones override earlier ones):
1. Global headers from `system.global_headers`
2. Variable-based headers from `system.headers`
3. Request-specific headers in individual actions

## Actions Structure

The `actions` array contains test steps. Each action can be:
- An HTTP request
- A control command
- A test operation

### HTTP Request Structure

```json
{
    "title": "Create new user",
    "method": "post",
    "url": "/api/users",
    "auth": true,
    "content": "json",
    "body": {
        "name": "John Doe",
        "email": "john@example.com"
    },
    "headers": {
        "X-Custom": "value"
    },
    "cookies": {
        "session": "%(session_id)s"
    },
    "files": {
        "avatar": "./avatar.jpg"
    },
    "status_code": 201,
    "ignore_error": false,
    "tests": [],
    "fields": []
}
```

| Field | Description | Required | Default |
|-------|-------------|----------|---------|
| `title` | Test description | No | None |
| `method` | HTTP method (`get`, `post`, `put`, `patch`, `delete`) | Yes | None |
| `url` | Request endpoint | Yes | None |
| `auth` | Enable authentication | No | `true` |
| `content` | Content type (`json`, `form`) | No | `json` |
| `body` | Request parameters | No | `{}` |
| `headers` | Request headers | No | `{}` |
| `cookies` | Request cookies | No | `{}` |
| `files` | Files to upload | No | `{}` |
| `status_code` | Expected status code | No | `200` |
| `ignore_error` | Continue on error | No | `false` |
| `tests` | Response validations | No | `[]` |
| `fields` | Data extraction | No | `[]` |

### Control Commands

#### Section Grouping

You can group related actions using `section`. Section is just a container for nested actions and has no direct effect on the test execution.
Output of a section is nested inside the parent section.
Syntax is as follows:

```json
{
    "action": "section",
    "title": "User Management",
    "actions": [
        // Nested actions
    ]
}
```

#### Variable Setting

You can create or update variables using `set` action (or reading from request responses).
Variables are key/value pairs that can be referenced in subsequent requests. Since they are based on Python's dictionaries, keys must be unique and the same key will be overwritten if set again.
Also, keys are case-sensitive.

Syntax is as follows:
```json
{
    "action": "set",
    "key": "user_id",
    "value": "12345"
}
```

#### Script Including

It is very common, especially in large test suites, to split tests into multiple files for better organization and reusability. You can include external files using the `include` action.
The `filename` field specifies the path to the file to include. If `exec` is set to `true`, the included file will be executed at import time.

```json
{
    "action": "include",
    "filename": "./auth.json",
    "exec": true
}
```

#### Sleep/Delay

If you need to pause the test execution for a certain amount of time, you can use the `sleep` action. The `ms` field specifies the duration in milliseconds.

```json
{
    "action": "sleep",
    "ms": 1000
}
```

## Complex Example

Here's a complete example showing different structural elements:

```json
{
    "system": {
        "base_url": "https://api.example.com",
        "log_file": "./restest.log",
        "stop_on_error": true,
        "global_headers": {
            "X-App-Version": "2.0"
        }
    },
    "actions": [
        {
            "action": "section",
            "title": "Authentication",
            "actions": [
                {
                    "title": "Login",
                    "method": "post",
                    "url": "/auth/login",
                    "auth": false,
                    "body": {
                        "username": "admin",
                        "password": "secret123"
                    },
                    "tests": [
                        {
                            "field": "success",
                            "value": true
                        }
                    ],
                    "fields": [
                        ["token", "auth_token"]
                    ]
                }
            ]
        },
        {
            "action": "section",
            "title": "User Operations",
            "actions": [
                {
                    "title": "Create User",
                    "method": "post",
                    "url": "/users",
                    "body": {
                        "name": "John Doe",
                        "email": "john@example.com"
                    },
                    "status_code": 201,
                    "tests": [
                        {
                            "field": "id",
                            "mode": "EXISTS"
                        }
                    ],
                    "fields": [
                        ["id", "new_user_id"]
                    ]
                },
                {
                    "title": "Upload Avatar",
                    "method": "post",
                    "url": "/users/%(new_user_id)s/avatar",
                    "content": "form",
                    "files": {
                        "avatar": "./test-data/avatar.jpg"
                    },
                    "status_code": 200
                }
            ]
        },
        {
            "action": "sleep",
            "ms": 1000
        },
        {
            "title": "Verify User",
            "method": "get",
            "url": "/users/%(new_user_id)s",
            "tests": [
                {
                    "field": "name",
                    "value": "John Doe"
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

1. **Organization**
   - Use sections to group related tests
   - Give descriptive titles to actions
   - Keep authentication tests in a separate section

2. **File Structure**
   - Split large test suites into multiple files
   - Use includes for reusable components
   - Keep environment-specific settings separate

3. **Variables**
   - Use meaningful variable names
   - Document expected variable values
   - Clean up temporary variables when done

4. **Error Handling**
   - Set appropriate `status_code` expectations
   - Use `ignore_error` judiciously
   - Include validation tests for error cases

## Common Patterns

### Authentication Flow
```json
{
    "action": "section",
    "title": "Auth",
    "actions": [
        {
            "method": "post",
            "url": "/auth/login",
            "auth": false,
            "body": {"username": "user", "password": "pass"},
            "fields": [["token", "auth_token"]]
        }
    ]
}
```

### Data Creation and Verification
```json
[
    {
        "method": "post",
        "url": "/resource",
        "body": {"name": "test"},
        "fields": [["id", "resource_id"]]
    },
    {
        "method": "get",
        "url": "/resource/%(resource_id)s",
        "tests": [
            {"field": "name", "value": "test"}
        ]
    }
]
```

### File Upload with Verification
```json
[
    {
        "method": "post",
        "url": "/upload",
        "content": "form",
        "files": {"file": "./test.pdf"},
        "fields": [["id", "file_id"]]
    },
    {
        "method": "get",
        "url": "/files/%(file_id)s",
        "tests": [
            {"field": "status", "value": "processed"}
        ]
    }
]
```

## Error Examples

Here are some common structural errors to avoid:

### ❌ Incorrect Variable Reference
```json
{
    "url": "/users/${user_id}"  // Wrong syntax
}
```

### ✅ Correct Variable Reference
```json
{
    "url": "/users/%(user_id)s"  // Correct syntax
}
```

### ❌ Missing Required Fields
```json
{
    "method": "post",
    "body": {"name": "test"}  // Missing URL
}
```

### ✅ Complete Request
```json
{
    "method": "post",
    "url": "/users",
    "body": {"name": "test"}
}
```