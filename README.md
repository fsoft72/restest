# RESTest Documentation

RESTest is a powerful and flexible REST API testing tool written in Python that allows you to create, run and validate API tests through simple JSON files. With RESTest, you can quickly set up test suites for your APIs, validate responses, extract and reuse data between requests, and much more.

**WATCH my PyCon IT 2023 presentation (in Italian)**

[![Watch the video](https://i.ytimg.com/vi/W2xV3mGT2RA/hq720.jpg)](https://youtu.be/W2xV3mGT2RA)

## Key Features

- **Simple JSON-based Test Definition**: Write tests using straightforward JSON syntax
- **Session Management**: Automatic handling of cookies and authentication tokens
- **Variable Storage and Reuse**: Extract data from responses and use them in subsequent requests
- **Powerful Path Parser**: Extract and validate nested JSON values with ease
- **Request Authentication**: Built-in support for Bearer token authentication
- **Comprehensive Testing**: Validate response status codes, headers, and body content
- **Test Organization**: Group tests into logical sections
- **Test Chaining**: Use data from previous responses in subsequent requests
- **Export Capabilities**: Generate Postman collections from your tests
- **Detailed Logging**: Keep track of all requests and responses
- **Performance Metrics**: Monitor request timing and response sizes

## Quick Start

### Installation

Install RESTest using pip:

```bash
pip install restest
```

### Basic Usage

Create a simple test file (e.g., `test.json`):

```json
{
  "system": {
    "base_url": "https://api.example.com",
    "log_file": "./restest.log"
  },
  "actions": [
    {
      "method": "get",
      "url": "/users/1",
      "tests": [
        {
          "field": "id",
          "value": 1
        }
      ]
    }
  ]
}
```

Run the test:

```bash
restest test.json
```

## Documentation Chapters

1. [**Getting Started**](docs/chapters/01-getting-started.md)
2. [**Test Structure**](docs/chapters/02-test-structure.md)
3. [**Making Requests**](docs/chapters/03-making-requests.md)
4. [**Testing Responses**](docs/chapters/04-testing-responses.md)

5. [**Variables and Data**](docs/chapters/05-variables-and-data.md)
6. [**Advanced Features**](docs/chapters/06-advanced-features.md)
7. [**Integration and Export**](docs/chapters/07-integration-and-export.md)
8. [**Command Line Options**](docs/chapters/08-command-line-options.md)

[**APPENDIX A - Test Modes Reference**](docs/chapters/A-testing-modes.md)

[**APPENDIX B - Path Parser**](docs/chapters/B-path-parser.md)

## Contributing

RESTest is an open-source project and welcomes contributions. Visit the [GitHub repository](https://github.com/fsoft72/restest) to:

- Report issues
- Submit pull requests
- Suggest new features
- Help improve documentation

## License

RESTest is released under the GPLv3 License. See the LICENSE file in the project repository for more details.
