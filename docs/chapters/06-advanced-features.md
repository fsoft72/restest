# Advanced Features

This chapter covers RESTest's advanced features that enable more complex testing scenarios, code reuse, and test automation.

## Test Sections

Sections help organize tests into logical groups and provide better visual separation in outputs.

### Basic Section Structure
```json
{
    "actions": [
        {
            "action": "section",
            "title": "User Authentication",
            "actions": [
                {
                    "title": "Login",
                    "method": "post",
                    "url": "/auth/login"
                },
                {
                    "title": "Verify Token",
                    "method": "get",
                    "url": "/auth/verify"
                }
            ]
        }
    ]
}
```

### Nested Sections
```json
{
    "actions": [
        {
            "action": "section",
            "title": "User Management",
            "actions": [
                {
                    "action": "section",
                    "title": "Registration",
                    "actions": [
                        {
                            "title": "Register User",
                            "method": "post",
                            "url": "/users"
                        }
                    ]
                },
                {
                    "action": "section",
                    "title": "Profile Management",
                    "actions": [
                        {
                            "title": "Update Profile",
                            "method": "put",
                            "url": "/users/%(user_id)s"
                        }
                    ]
                }
            ]
        }
    ]
}
```

## Test Batches

Batches allow you to define reusable sets of actions that can be executed multiple times.

### Creating a Batch
```json
{
    "actions": [
        {
            "action": "batch_set",
            "name": "create_user",
            "actions": [
                {
                    "method": "post",
                    "url": "/users",
                    "params": {
                        "name": "%(user_name)s",
                        "email": "%(user_email)s"
                    },
                    "fields": [
                        ["id", "created_user_id"]
                    ]
                },
                {
                    "method": "post",
                    "url": "/users/%(created_user_id)s/profile",
                    "params": {
                        "bio": "%(user_bio)s"
                    }
                }
            ]
        }
    ]
}
```

### Executing a Batch
```json
{
    "actions": [
        {
            "action": "set",
            "key": "user_name",
            "value": "John Doe"
        },
        {
            "action": "set",
            "key": "user_email",
            "value": "john@example.com"
        },
        {
            "action": "batch_exec",
            "name": "create_user"
        }
    ]
}
```

## Script Inclusion

Include and reuse test scripts across multiple files.

### Including Scripts
```json
{
    "actions": [
        {
            "action": "include",
            "filename": "./auth/login.json",
            "exec": true
        },
        {
            "action": "include",
            "filename": "./common/cleanup.json",
            "name": "cleanup_actions"
        }
    ]
}
```

### Run-Once Scripts
```json
{
    "run-once": true,
    "actions": [
        {
            "title": "Initialize Test Data",
            "method": "post",
            "url": "/api/init"
        }
    ]
}
```

## Custom Code Execution

Execute Python code directly within your tests.

### Basic Code Execution
```json
{
    "action": "code",
    "code": [
        "import time",
        "timestamp = int(time.time())",
        "print(f'Current timestamp: {timestamp}')"
    ]
}
```

### Variable Manipulation with Code
```json
{
    "actions": [
        {
            "action": "code",
            "code": [
                "import random",
                "random_id = random.randint(1000, 9999)",
                "self.rt.globals['random_id'] = str(random_id)"
            ]
        },
        {
            "method": "get",
            "url": "/users/%(random_id)s"
        }
    ]
}
```

## Conditional Execution

Control test flow based on conditions.

### Basic Conditional
```json
{
    "action": "if",
    "field": "environment",
    "mode": "EQUALS",
    "value": "production",
    "actions": [
        {
            "method": "post",
            "url": "/api/logs",
            "params": {
                "level": "INFO",
                "message": "Running in production"
            }
        }
    ]
}
```

## Request Timing and Control

### Delayed Execution
```json
{
    "actions": [
        {
            "method": "post",
            "url": "/api/trigger-job"
        },
        {
            "action": "sleep",
            "ms": 5000
        },
        {
            "method": "get",
            "url": "/api/job-status"
        }
    ]
}
```

### Request Repetition
```json
{
    "method": "get",
    "url": "/api/status",
    "repeat": 3,
    "tests": [
        {
            "field": "status",
            "value": "ready"
        }
    ]
}
```

## Complete Examples

### Complex Authentication Flow
```json
{
    "actions": [
        {
            "action": "include",
            "filename": "./auth/login.json",
            "name": "auth_flow"
        },
        {
            "action": "section",
            "title": "User Operations",
            "actions": [
                {
                    "action": "code",
                    "code": [
                        "import uuid",
                        "test_user = f'test_{uuid.uuid4().hex[:8]}'",
                        "self.rt.globals['test_user'] = test_user"
                    ]
                },
                {
                    "action": "batch_exec",
                    "name": "create_user"
                },
                {
                    "action": "sleep",
                    "ms": 1000
                },
                {
                    "method": "get",
                    "url": "/users/%(created_user_id)s",
                    "tests": [
                        {
                            "field": "username",
                            "value": "%(test_user)s"
                        }
                    ]
                }
            ]
        }
    ]
}
```

### Data Migration Test
```json
{
    "actions": [
        {
            "action": "section",
            "title": "Data Migration",
            "actions": [
                {
                    "action": "code",
                    "code": [
                        "import datetime",
                        "start_time = datetime.datetime.now()",
                        "self.rt.globals['start_timestamp'] = start_time.isoformat()"
                    ]
                },
                {
                    "method": "post",
                    "url": "/api/migration/start",
                    "params": {
                        "timestamp": "%(start_timestamp)s"
                    },
                    "fields": [
                        ["job_id", "migration_id"]
                    ]
                },
                {
                    "action": "batch_set",
                    "name": "check_status",
                    "actions": [
                        {
                            "method": "get",
                            "url": "/api/migration/%(migration_id)s",
                            "tests": [
                                {
                                    "field": "status",
                                    "value": "completed"
                                }
                            ]
                        }
                    ]
                },
                {
                    "action": "sleep",
                    "ms": 5000
                },
                {
                    "action": "batch_exec",
                    "name": "check_status"
                }
            ]
        }
    ]
}
```

## Best Practices

1. **Script Organization**
   - Use sections for logical grouping
   - Keep reusable components in separate files
   - Use meaningful batch names

2. **Code Execution**
   - Keep Python code simple and focused
   - Handle exceptions in custom code
   - Document code purpose and requirements

3. **Conditional Logic**
   - Use clear condition names
   - Keep conditional blocks focused
   - Document expected outcomes

4. **Performance**
   - Use appropriate sleep durations
   - Batch related operations
   - Monitor execution times

## Troubleshooting

### Common Issues

1. **Script Inclusion**
```json
// ❌ Wrong
{
    "action": "include",
    "filename": "auth.json"  // Relative path might fail
}

// ✅ Correct
{
    "action": "include",
    "filename": "./auth/auth.json"  // Use explicit paths
}
```

2. **Code Execution**
```json
// ❌ Wrong
{
    "action": "code",
    "code": "print('Hello')"  // Must be an array
}

// ✅ Correct
{
    "action": "code",
    "code": [
        "print('Hello')"
    ]
}
```

3. **Batch References**
```json
// ❌ Wrong
{
    "action": "batch_exec",
    "name": "CreateUser"  // Case-sensitive
}

// ✅ Correct
{
    "action": "batch_exec",
    "name": "create_user"
}
```