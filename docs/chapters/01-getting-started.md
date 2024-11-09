# Getting Started with RESTest

This chapter will guide you through installing RESTest, understanding its basic concepts, and creating your first test.

## Installation

RESTest requires Python 3.6 or later. Install it using pip:

```bash
pip install restest
```

To verify the installation, run:

```bash
restest --version
```

This should display the current version number (e.g., `v2.2.1`).

## Basic Concepts

Before diving into creating tests, let's understand the key concepts of RESTest:

### Test Files
- RESTest uses JSON files to define tests
- Each test file may contain a `system` section for configuration and must contain `actions` array for tests
- Tests are executed in sequence, from top to bottom

### Actions
Actions are the building blocks of RESTest tests. Each action can be:
- An HTTP request (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`)
- A control command (like `section`, `set`, `include`)

### Variables
- RESTest can store and reuse values between requests
- Variables can be set manually or extracted from responses
- Use the `%(variable_name)s` syntax to reference string variables and `%(variable_name)d` for integers

### Tests
- Each request can include tests to validate the response
- Tests can check status codes, response body, headers, and more
- Multiple test conditions can be applied to a single response

## Your First Test

Let's create a simple test that verifies a public API endpoint. We'll use the JSONPlaceholder API as an example.

Create a file named `first-test.json`:

```json
{
    "system": {
        "base_url": "https://jsonplaceholder.typicode.com",
        "log_file": "./restest-first.log"
    },
    "actions": [
        {
            "title": "Get a user",
            "method": "get",
            "url": "/users/1",
            "auth": false,
            "tests": [
                {
                    "field": "name",
                    "value": "Leanne Graham"
                },
                {
                    "field": "email",
                    "value": "Sincere@april.biz"
                }
            ],
            "fields": [
                ["id", "user_id"],
                ["username", "user_name"]
            ]
        },
        {
            "title": "Get user's posts",
            "method": "get",
            "url": "/users/%(user_id)s/posts",
            "auth": false,
            "tests": [
                {
                    "field": "[0].userId",
                    "value": %(user_id)d
                },
                {
                    "field": "[]",
                    "mode": "SIZE-GT",
                    "value": 1
                }
            ]
        }
    ]
}
```

Let's break down this test file:

### System Configuration
```json
"system": {
    "base_url": "https://jsonplaceholder.typicode.com",
    "log_file": "./restest-first.log"
}
```
- `base_url`: The API's base URL
- `log_file`: Where RESTest will save detailed logs

### First Action: Get User
```json
{
    "title": "Get a user",
    "method": "get",
    "url": "/users/1",
    "auth": false,
    "tests": [
        {
            "field": "name",
            "value": "Leanne Graham"
        }
    ],
    "fields": [
        ["id", "user_id"],
        ["username", "user_name"]
    ]
}
```
- `title`: Description of the test (optional but recommended)
- `method`: HTTP method to use
- `auth`: Whether authentication is required
- `tests`: Validates the response
- `fields`: Extracts values for later use

### Second Action: Get Posts
```json
{
    "title": "Get user's posts",
    "method": "get",
    "url": "/users/%(user_id)s/posts",
    "auth": false,
    "tests": [
        {
            "field": "[0].userId",
            "value": %(user_id)d
        },
        {
            "field": "[]",
            "mode": "SIZE-GT",
            "value": 0
        }
    ]
}
```
- Uses `%(user_id)d` from the previous request
- Tests array elements using `[0]` notation
- The whole array returned as response is checked using `[]`
- Validates array size using `SIZE-GT` mode

### Running the Test

Run the test using:

```bash
restest first-test.json
```

You should see output similar to:
```
Get a user
      GET  /users/1                                {} auth: False size:   292 - status: 200 - t: 523 ms / 0.523 s

Get user's posts
      GET  /users/1/posts                          {} auth: False size:  2.7KB - status: 200 - t: 245 ms / 0.245 s

===== FINISHED. Total Errors: 0 / 4 [Total time: 0.768000]
```

### Understanding the Output
- Each request shows the method, URL, and parameters
- Response size and status code are displayed
- Request timing is shown in milliseconds and seconds
- Final summary shows total tests and errors

## Next Steps

Now that you've created your first test, you can:
1. Explore more complex test scenarios
2. Learn about different test modes
3. Use variables and data extraction
4. Organize tests into sections

These topics will be covered in detail in the following chapters.

## Common Issues

### Base URL Problems
If you get connection errors, verify:
- The `base_url` is correct
- You have internet access
- The API is accessible from your location

### JSON Syntax
If RESTest fails to parse your file:
- Validate your JSON syntax (use a JSON validator)
- Check for missing commas or brackets
- Ensure all strings are properly quoted

### Test Failures
If tests fail:
- Check the log file for detailed response data
- Verify your test conditions match the actual response
- Ensure variables are properly referenced

## Command Line Tips

Some useful command-line options for beginners:

```bash
# Override base URL
restest --base-url https://api.example.com test.json

# Don't stop on test failures
restest --dont-stop-on-error test.json

# Show detailed curl commands
restest --curl test.json

# Clean log file before starting
restest --log-clean test.json
```