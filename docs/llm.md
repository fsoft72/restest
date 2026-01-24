# RESTest LLM Reference

RESTest is a JSON-based REST API testing tool. Tests are JSON files with `system` (config) and `actions` (test steps) sections.

## Basic Structure

```json
{
    "system": {
        "base_url": "https://api.example.com",
        "log_file": "./test.log",
        "stop_on_error": true,
        "global_headers": {"X-API-Version": "1.0"},
        "headers": {"Authorization": "Bearer %(token)s"},
        "cookies": {"session": "test"},
        "authorization_header": "Authorization",
        "authorization_template": "Bearer %(token)s"
    },
    "actions": []
}
```

## Variables

- **Reference syntax**: `%(variable_name)s` (string) or `%(variable_name)d` (integer)
- **Expression syntax**: `${a + b}` (arithmetic with `+`, `-`, `*`, `/`, `%`)
  - **NEW v2.6.0**: Expressions work in **ALL fields** (URLs, headers, cookies, data, etc.)
  - Pure expressions: `"${a + b}"` returns numeric value (e.g., `15`)
  - String interpolation: `"user_${counter}"` returns string (e.g., `"user_1"`)
  - Multiple expressions: `"/users/${id}/posts/${page}"` → `"/users/123/posts/2"`
  - Combines with `%(var)s`: `"%(prefix)s_v${version}"` → `"api_v2"`
- **Length extraction**: `#path.to.array` extracts length

### Expression Examples

```json
{
  "url": "/api/v${version}/users/${user_id}",
  "headers": {"X-Request-ID": "req_${counter}"},
  "data": {
    "username": "user_${counter}",
    "offset": "${(page - 1) * per_page}"
  }
}
```

## HTTP Request Actions

```json
{
    "title": "Create user",
    "method": "post",
    "url": "/users",
    "auth": true,
    "content": "json",
    "body": {"name": "John"},
    "headers": {"X-Custom": "value"},
    "cookies": {"session": "%(session_id)s"},
    "status_code": 201,
    "ignore_error": false,
    "repeat": 3,
    "skip": false,
    "max_time": 1000,
    "tests": [],
    "fields": []
}
```

**Methods**: `get`, `post`, `put`, `patch`, `delete`
**Content types**: `json` (default), `form`
**Body aliases**: `body`, `params`, `data` are interchangeable

### File Upload
```json
{
    "method": "post",
    "url": "/upload",
    "content": "form",
    "files": {"document": "./file.pdf"}
}
```

### Direct Body (raw array/value)
```json
{
    "body": {"__direct__": [1, 2, 3]}
}
```

## Field Extraction

Extract values from responses into variables:

```json
{
    "fields": [
        "id",
        ["user.profile.id", "profile_id"],
        ["items[0].name", "first_name"],
        ["#data.items", "item_count"],
        {"path": "items", "mode": "length", "save": "count"}
    ]
}
```

**Field modes**: `value` (default), `length`, `type`, `keys`

## Tests

```json
{
    "tests": [
        {"field": "status", "value": "active"},
        {"field": "id", "mode": "EXISTS"},
        {"field": "items", "mode": "SIZE-GT", "value": 0},
        {"field": "name", "mode": "CONTAINS", "value": "John"},
        {"mode": "EXPR", "key": "total", "op": "==", "expr": "${subtotal + tax}"}
    ]
}
```

### Test Modes

| Mode | Aliases | Description |
|------|---------|-------------|
| `EQUALS` | `=`, `==` | Exact match |
| `EXISTS` | `!!`, `NOT_NULL` | Field exists and not null |
| `EMPTY` | `IS_NULL`, `NULL` | Field is null or missing |
| `NOT_EXISTS` | | Field does not exist |
| `NOT_EQUAL` | `!=`, `<>` | Not equal |
| `CONTAINS` | `->` | Array/string contains value |
| `SIZE` | `LEN`, `LENGTH` | Array/string length equals |
| `GT`, `GTE`, `LT`, `LTE` | `>`, `>=`, `<`, `<=` | Numeric comparisons |
| `SIZE-GT`, `SIZE-GTE`, `SIZE-LT`, `SIZE-LTE` | `()>`, `()>=`, `()<`, `()<=` | Size comparisons |
| `OBJ` | `OBJECT` | Object structure validation |
| `EXPR` | | Expression-based comparison |

### EXPR Mode
```json
{"mode": "EXPR", "key": "path.or.${expression}", "op": "==", "expr": "${var1 + var2}"}
```

### Save Test Value
```json
{"field": "user.id", "mode": "EXISTS", "save": "user_id"}
```

## Path Parser

| Syntax | Example | Description |
|--------|---------|-------------|
| `field` | `name` | Direct access |
| `parent.child` | `user.email` | Nested access |
| `[n]` | `items[0]` | Array index |
| `.[field=value]` | `users.[role=admin]` | Conditional |
| `.[field!=value]` | `items.[status!=deleted]` | Inequality |
| `.[field>value]` | `orders.[total>100]` | Numeric condition |

## Control Actions

### Set Variable
```json
{"action": "set", "key": "user_id", "value": "123"}
{"action": "set", "key": "total", "value": "${price * qty}"}
```

### Copy Variable
```json
{"action": "copy", "from": "token", "to": "backup_token"}
```

### Section (grouping)
```json
{
    "action": "section",
    "title": "User Tests",
    "actions": []
}
```

### Include External File
```json
{"action": "include", "filename": "./auth.json", "exec": true, "show_filename": true}
```

### Sleep
```json
{"action": "sleep", "ms": 1000}
```

### Conditional Execution
```json
{
    "action": "if",
    "field": "environment",
    "mode": "EQUALS",
    "value": "production",
    "actions": []
}
```

### Batch (reusable action set)
```json
{"action": "batch_set", "name": "create_user", "actions": []}
{"action": "batch_exec", "name": "create_user"}
```

### Dump Variables
```json
{"action": "dump", "fields": ["user_id", "token"], "print": true}
```

### Comment
```json
{"rem": "This is a comment"}
```

### Python Code
```json
{
    "action": "code",
    "code": [
        "import uuid",
        "self.rt.globals['test_id'] = str(uuid.uuid4())"
    ]
}
```

## Special Features

### Counter in Repeat
```json
{
    "method": "post",
    "url": "/items",
    "body": {"name": "Item %(counter)s"},
    "repeat": 5
}
```

### Response Size Test
```json
{"field": "rt:size", "mode": "LT", "value": 1024}
```

### Debug Break
```json
{"method": "get", "url": "/test", "break": true}
```

## Command Line

```bash
restest test.json
restest --base-url https://api.example.com test.json
restest --key user_id:123 --key token:abc test.json
restest --env-load vars.json test.json
restest --dont-stop-on-error test.json
restest --csv metrics.csv test.json
restest --postman export.json test.json
restest --curl test.json
restest --dry test.json
restest --step test.json
restest --quiet test.json
```

## Complete Example

```json
{
    "system": {
        "base_url": "https://api.example.com",
        "log_file": "./test.log"
    },
    "actions": [
        {
            "title": "Login",
            "method": "post",
            "url": "/auth/login",
            "auth": false,
            "body": {"username": "admin", "password": "secret"},
            "tests": [{"field": "token", "mode": "EXISTS"}],
            "fields": [["token", "auth_token"], ["user.id", "user_id"]]
        },
        {
            "title": "Get Profile",
            "method": "get",
            "url": "/users/%(user_id)s",
            "headers": {"Authorization": "Bearer %(auth_token)s"},
            "tests": [
                {"field": "email", "mode": "EXISTS"},
                {"field": "roles", "mode": "SIZE-GT", "value": 0},
                {"field": "roles", "mode": "CONTAINS", "value": "admin"}
            ]
        },
        {
            "title": "Create Items",
            "method": "post",
            "url": "/items",
            "body": {"name": "Item %(counter)s"},
            "repeat": 3,
            "status_code": 201
        },
        {
            "title": "Verify Items",
            "method": "get",
            "url": "/items",
            "fields": [["#data", "item_count"]],
            "tests": [
                {"field": "data", "mode": "SIZE", "value": "${item_count}"}
            ]
        }
    ]
}
```
