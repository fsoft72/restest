# Command Line Options

This chapter details all available command-line options in RESTest, their usage, and practical examples.

## Basic Syntax

```bash
restest [options] test_file [test_file...]
```

## Core Options

### Version Information
```bash
# Show version
restest --version
```
Output: `v2.2.1`

### Base URL Configuration
```bash
# Override base URL from test files
restest --base-url https://api.example.com test.json
```

### Authentication Mode
```bash
# Set default authentication mode
restest --auth-mode auth test.json    # Default: require authentication
restest --auth-mode no test.json      # Default: no authentication
```

### API Prefix
```bash
# Add prefix to all API calls
restest --prefix /api/v2 test.json
```

## Logging Options

### Log File Control
```bash
# Specify log file
restest --log custom.log test.json

# Clean log file before starting
restest --log-clean test.json

# Suppress console output
restest --quiet test.json

# Disable colored output
restest --no-colors test.json
```

### Debug Options
```bash
# Show curl commands on console
restest --curl test.json

# Dry run (no actual requests)
restest --dry test.json
```

## Data Management

### Environment Variables
```bash
# Load system environment variables
restest --env test.json

# Load variables from file
restest --env-load vars.json test.json

# Save variables to file
restest --env-save output.json test.json
```

### Custom Variables
```bash
# Set individual variables
restest --key user_id:123 --key token:abc test.json
```

## Export Options

### Postman Export
```bash
# Basic Postman export
restest --postman export.json test.json

# Full Postman configuration
restest \
    --postman export.json \
    --postman-name "API Tests" \
    --postman-base-url "https://api.prod.com" \
    --postman-auth-name "Authorization" \
    --postman-auth-value "Bearer {{token}}" \
    test.json
```

### CSV Export
```bash
# Export timing data
restest --csv metrics.csv test.json
```

## Execution Control

### Error Handling
```bash
# Continue on test failures
restest --dont-stop-on-error test.json
```

### Request Timing
```bash
# Add delay between requests (milliseconds)
restest --delay 1000 test.json
```

## Complete Command Reference

| Option | Default | Description | Example |
|--------|---------|-------------|---------|
| `--auth-mode` | `auth` | Set default authentication mode (`auth`/`no`) | `--auth-mode no` |
| `--base-url` | None | Override base URL from test files | `--base-url https://api.example.com` |
| `--csv` | None | Export timing data to CSV file | `--csv metrics.csv` |
| `--curl` | False | Show curl commands on console | `--curl` |
| `--delay` | 0 | Add delay between requests (ms) | `--delay 1000` |
| `--dont-stop-on-error` | False | Continue on test failures | `--dont-stop-on-error` |
| `--dry` | False | Perform dry run without requests | `--dry` |
| `--env` | False | Load system environment variables | `--env` |
| `--env-load` | None | Load variables from file | `--env-load vars.json` |
| `--env-save` | None | Save variables to file | `--env-save output.json` |
| `--key` | None | Set custom variables | `--key user_id:123` |
| `--log` | None | Specify custom log file | `--log custom.log` |
| `--log-clean` | False | Clean log file before starting | `--log-clean` |
| `--no-colors` | False | Disable colored output | `--no-colors` |
| `--postman` | None | Export to Postman collection | `--postman export.json` |
| `--postman-auth-name` | None | Postman auth header name | `--postman-auth-name "Authorization"` |
| `--postman-auth-value` | None | Postman auth header value | `--postman-auth-value "Bearer {{token}}"` |
| `--postman-base-url` | None | Postman base URL | `--postman-base-url "https://api.prod.com"` |
| `--postman-name` | None | Postman collection name | `--postman-name "API Tests"` |
| `--prefix` | None | Add prefix to all API calls | `--prefix /api/v2` |
| `--quiet` | False | Suppress console output | `--quiet` |
| `--version` | N/A | Show version number | `--version` |

## Usage Examples

### Basic Testing
```bash
# Simple test execution
restest test.json

# Multiple test files
restest auth.json users.json orders.json
```

### Production Testing
```bash
# Production configuration
restest \
    --base-url https://api.prod.com \
    --log prod.log \
    --log-clean \
    --env-load prod-vars.json \
    --csv prod-metrics.csv \
    --dont-stop-on-error \
    tests/*.json
```

### Development Testing
```bash
# Development configuration
restest \
    --base-url http://localhost:8080 \
    --curl \
    --delay 500 \
    --env \
    test.json
```

### CI/CD Pipeline
```bash
# CI/CD configuration
restest \
    --base-url ${CI_API_URL} \
    --key api_key:${CI_API_KEY} \
    --log-clean \
    --quiet \
    --csv results.csv \
    --postman postman.json \
    --dont-stop-on-error \
    tests/*.json
```

## Environment-Specific Examples

### Local Development
```bash
# Local testing with debugging
restest \
    --base-url http://localhost:3000 \
    --curl \
    --prefix /api \
    --env-load .env.local \
    --delay 100 \
    test.json
```

### Staging Environment
```bash
# Staging environment testing
restest \
    --base-url https://api.staging.com \
    --log staging.log \
    --env-load staging.env \
    --postman staging-collection.json \
    --csv staging-metrics.csv \
    test.json
```

### Production Monitoring
```bash
# Production monitoring
restest \
    --base-url https://api.production.com \
    --quiet \
    --log /var/log/restest/monitor.log \
    --csv /var/log/restest/metrics.csv \
    --dont-stop-on-error \
    monitoring/*.json
```

## Best Practices

1. **Environment Management**
   ```bash
   # Development
   restest --env-load dev.env --curl test.json

   # Production
   restest --env-load prod.env --quiet test.json
   ```

2. **Debug Configuration**
   ```bash
   # Full debug mode
   restest \
       --curl \
       --delay 500 \
       --log debug.log \
       test.json
   ```

3. **CI/CD Integration**
   ```bash
   # CI pipeline configuration
   restest \
       --quiet \
       --log-clean \
       --dont-stop-on-error \
       --csv results.csv \
       tests/*.json
   ```

4. **Performance Testing**
   ```bash
   # Load test configuration
   restest \
       --delay 100 \
       --csv perf.csv \
       --log perf.log \
       load-test.json
   ```
