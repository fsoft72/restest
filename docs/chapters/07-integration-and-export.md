# Integration and Export

This chapter covers how to integrate RESTest with other tools, export test results, and use RESTest in various environments.

## Postman Export

RESTest can export your tests to Postman collections, making it easy to share and visualize your API tests.

### Basic Postman Export
```bash
restest \
  --postman export.json \
  --postman-name "My API Tests" \
  test.json
```

### Advanced Postman Configuration
```bash
restest \
  --postman export.json \
  --postman-name "Production API Tests" \
  --postman-base-url "https://api.production.com" \
  --postman-auth-name "Authorization" \
  --postman-auth-value "Bearer {{token}}" \
  test.json
```

### Example Test with Postman-Friendly Structure
```json
{
    "system": {
        "base_url": "https://api.dev.com",
        "log_file": "./restest.log"
    },
    "actions": [
        {
            "title": "Create User",
            "method": "post",
            "url": "/api/users",
            "params": {
                "name": "John Doe",
                "email": "john@example.com"
            },
            "headers": {
                "Content-Type": "application/json",
                "X-API-Version": "1.0"
            }
        }
    ]
}
```

## CSV Export

Export timing and performance metrics to CSV for analysis.

### Basic CSV Export
```bash
restest --csv metrics.csv test.json
```

### CSV Output Format
```csv
method  path    params  start_time  end_time    date    status_code duration    duration_s
GET     /users  {}      1636329600  1636329601  2024-01-01 10:00:00    200     1000    1.0
POST    /users  {"name":"John"}  1636329602  1636329603  2024-01-01 10:00:02    201     1200    1.2
```

### Test with Timing Focus
```json
{
    "actions": [
        {
            "title": "Performance Test",
            "method": "get",
            "url": "/api/heavy-operation",
            "max_exec_time": 2000,
            "tests": [
                {
                    "field": "rt:size",
                    "mode": "LT",
                    "value": 1048576
                }
            ]
        }
    ]
}
```

## Environment Variables

### Loading Environment Variables
```bash
# From system environment
restest --env test.json

# From file
restest --env-load env.json test.json
```

### Environment File Structure
```json
{
    "API_KEY": "your-api-key",
    "API_SECRET": "your-secret",
    "BASE_URL": "https://api.staging.com",
    "LOG_LEVEL": "debug"
}
```

### Saving Variables
```bash
restest --env-save output-vars.json test.json
```

### Environment-Aware Tests
```json
{
    "system": {
        "base_url": "%(BASE_URL)s",
        "headers": {
            "X-API-Key": "%(API_KEY)s"
        }
    },
    "actions": [
        {
            "title": "Environment Check",
            "method": "get",
            "url": "/api/status",
            "tests": [
                {
                    "field": "environment",
                    "value": "%(ENVIRONMENT)s"
                }
            ]
        }
    ]
}
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'

      - name: Install RESTest
        run: |
          pip install restest

      - name: Run Tests
        run: |
          restest \
            --base-url ${{ secrets.API_URL }} \
            --key api_key:${{ secrets.API_KEY }} \
            --log-clean \
            --csv results.csv \
            tests/*.json

      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: |
            results.csv
            restest.log
```

### Jenkins Pipeline Example
```groovy
pipeline {
    agent any

    environment {
        API_KEY = credentials('api-key')
        API_URL = credentials('api-url')
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install restest'
            }
        }

        stage('Test') {
            steps {
                sh """
                    restest \
                        --base-url ${API_URL} \
                        --key api_key:${API_KEY} \
                        --postman results/postman.json \
                        --csv results/metrics.csv \
                        --log-clean \
                        tests/*.json
                """
            }
        }

        stage('Archive') {
            steps {
                archiveArtifacts artifacts: 'results/*'
            }
        }
    }
}
```

### GitLab CI Example
```yaml
test:
  image: python:3.9
  variables:
    API_URL: $API_URL
    API_KEY: $API_KEY

  script:
    - pip install restest
    - |
      restest \
        --base-url $API_URL \
        --key api_key:$API_KEY \
        --csv results.csv \
        --log-clean \
        tests/*.json

  artifacts:
    paths:
      - results.csv
      - restest.log
```

## Test Report Integration

### JUnit Format Integration
```python
#!/usr/bin/env python3
import json
import sys
from junit_xml import TestSuite, TestCase

def convert_restest_to_junit(log_file):
    test_cases = []

    with open(log_file, 'r') as f:
        for line in f:
            if 'TEST FAILED' in line:
                test_case = TestCase(
                    name=line.split('"')[1],
                    classname='RESTest',
                    elapsed_sec=1,
                )
                test_case.add_failure_info(message=line)
                test_cases.append(test_case)
            elif 'TEST PASSED' in line:
                test_case = TestCase(
                    name=line.split('"')[1],
                    classname='RESTest',
                    elapsed_sec=1,
                )
                test_cases.append(test_case)

    ts = TestSuite("RESTest Suite", test_cases)
    with open('junit-results.xml', 'w') as f:
        f.write(TestSuite.to_xml_string([ts]))

convert_restest_to_junit('restest.log')
```

## Best Practices

1. **CI/CD Integration**
   - Use environment variables for sensitive data
   - Set appropriate timeouts
   - Archive test results
   - Use consistent base URLs per environment

2. **Export Management**
   - Use descriptive file names
   - Include timestamps in export files
   - Keep exports organized by date/environment
   - Clean old export files regularly

3. **Environment Handling**
   - Use separate environment files per environment
   - Never commit sensitive data
   - Document required environment variables
   - Validate environment variables before tests

4. **Results Processing**
   - Regular backup of test results
   - Automated analysis of CSV metrics
   - Trend monitoring
   - Alert on performance degradation

## Common Integration Patterns

### Load Testing Integration
```json
{
    "actions": [
        {
            "action": "section",
            "title": "Load Test",
            "actions": [
                {
                    "method": "get",
                    "url": "/api/endpoint",
                    "repeat": 100,
                    "max_exec_time": 200,
                    "tests": [
                        {
                            "field": "rt:size",
                            "mode": "LT",
                            "value": 1024
                        }
                    ]
                }
            ]
        }
    ]
}
```

### Monitoring Integration
```json
{
    "system": {
        "base_url": "%(MONITOR_URL)s",
        "log_file": "/var/log/restest/monitor.log"
    },
    "actions": [
        {
            "action": "code",
            "code": [
                "import time",
                "self.rt.globals['timestamp'] = int(time.time())"
            ]
        },
        {
            "method": "post",
            "url": "/api/metrics",
            "params": {
                "timestamp": "%(timestamp)s",
                "test_name": "api_monitor",
                "results": "%(test_results)s"
            }
        }
    ]
}
```