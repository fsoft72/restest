# restest

Scriptable REST calls test software written in Python

**WATCH my PyCon IT 2023 presentation (in Italian)**

[![Watch the video](https://i.ytimg.com/vi/W2xV3mGT2RA/hq720.jpg)](https://youtu.be/W2xV3mGT2RA)

`restest` actions are defined inside a JSON file.

With `restest` you can control return responses and test values against an expected result / behaviour.

**NOTE**: for full documentation, please refer to [restest documentation](https://liwe.org/tools/restest/)

**NOTE**: The complete roadmap of the project, please visit here: [restest project](https://github.com/users/fsoft72/projects/1/views/1)

I am currently working on a `v2` version with brand new features and some code cleanup. You can test it from the `2.0` branch.

## Main Features

Main features of `restest` are:

- Support session based request
- Powerful path parser to extract keys in nested JSON structures
- Output containing a working CURL string of every test
- Dump of all headers and fields
- Supports Token authentication
- Support values storing and reusing during the script
- Uses Python string formatting rules to create custom strings and values
- A script can include other scripts
- Tests can be grouped in "sections" to logically and visually gather them in a single place.
- Batch operations
- Clean debug output

## Installation

`restest` is a Python 3 software distributed as a PIP package (see [PyPi page](https://pypi.org/project/restest/)).
You can install it with `pip`:

```bash
pip install restest
```

## How to run it

Typically you run `restest` from a command line with some parameters and one or more JSON files with the tests to be performed.

```bash
~/src/restest$ restest --help
usage: restest [-h] [--base-url BASE_URL] [--dont-stop-on-error] [--log LOG] [--key KEY [KEY ...]] [--quiet] [--version] file [file ...]

RESTest the easy REST test manager - by Fabio Rotondo (fabio.rotondo@gmail.com)

positional arguments:
  file                  Files containing the tests

optional arguments:
  -h, --help                                show this help message and exit
  --base-url BASE_URL                       Base URL. This string overrides the 'system' parameter in JSON file
  --curl                                    Dumps CURL also on console (defaults on log only
  --dont-stop-on-error                      Flag to stop RESTest on error. This flag overrides the 'system' parameter in JSON file
  --env                                     Makes environment variables available before starting
  --env-load ENV_LOAD                       If set, global vars will be loaded from the specified file
  --env-save ENV_SAVE                       If set, global vars will be saved to specified file
  --no-colors                               Disables colors in output
  --postman POSTMAN                         Export activity to a Postman JSON file
  --postman-name POSTMAN_NAME               The Postman Collection name
  --postman-base-url POSTMAN_BASE_URL       The base url to use in Postman instead of the real host
  --postman-auth-name POSTMAN_AUTH_NAME     Name of the authorization header name
  --postman-auth-value POSTMAN_AUTH_VALUE   Value to use for authorization header
  --log LOG                                 Custom log file overriding the one in 'system'
  --log-clean                               If set, log file will be cleaned before starting
  --key KEY [KEY ...]                       One or more keys to be added to the globals dict use key:value format
  --quiet                                   If set, no output on console
  --version                                 show program's version number and exit
```

If the first JSON file you load has a `system` section with at least `base_url` configuration you can just run `restest` with:

```bash
restest ./tests.json
```

## JSON file structure

This is the smaller JSON file for `restest` you can write
(note: name it `simple-example.test.json`):

```json
{
  "actions": [
    {
      "method": "get",
      "url": "/api/your/url/hello-world"
    }
  ]
}
```

In this example, the JSON file is created with just one single action that will do a GET request to the `/api/your/url/hello-world` URI.
As you can see, the URI is incomplete, as it misses the `http`/`https` part. Don't worry: you can specify it in the command line.
Specifying using the command line allows you to run the same tests on different URLs (for example, development and production environments).

Here is the shortest command line to execute the script above:

```bash
restest --base-url http://example.com simple-example.test.json
```

Every action **must** contain a `method` or `action` key.

If the `method` key is present, then the action is actually a `http`/`https` request.

If the `action` key is present, then the action is a _script_ command.

## ACTION description for HTTP requests

### `title`

Every action can have a _title_ field. The text included in this field will be shown on console. Useful to tell the user what's going on.

### `method`

Supported `method` modes:

- **GET** the `HTTP GET` method
- **POST** the `HTTP POST` method
- **PUT** the `HTTP PUT` method
- **PATCH** the `HTTP PATCH` method
- **DELETE** the `HTTP DELETE` method

Currently, other `HTTP` methods are not supported, but planned in the future.

### `url`

The partial URL to call. As you have seen before, you can specify the base URL with the `--base-url` command line argument.

### `auth`

This is a `true` / `false` flag which determines if the current call is authenticated. Default is **`false`**

### `content`

Defines the request content-type and mode. Possible values are:

- **json** the request is a `application/json` (_default_)
- **form** the request is a `application/x-www-form-urlencoded`

### `ignore_error`

This is a `true` / `false` flag which determines if `restest` should ignore an error occurring on this request.
Default is **`true`**

### `status_code`

With `status_code` key you can specify the `HTTP Status Code` you expect the call to return.
For example, if you make an unauthorized call to a specific endpoint, it should return a `403 Unauthorized` return code.
If you do _not_ specify `status_code` key and your request returns a `403`, then `restest` will return an error, but if you know _for sure_ that
your request is going to fail with a `403` return code, then you can specify it with:

```json
"status_code": 403
```

And the `restest` action will succeed.

Default value for `return_code` is **`200`**

### `params`

If the request has parameters, you can specify them with the `params` keyword and passing an array.
Here there is an example:

```json
{
  "method": "post",
  "url": "/api/site/login",
  "params": {
    "email": "john.doe@example.com",
    "password": "mypassword"
  }
}
```

if the request is a `POST` request, parameters will be sent in post data, if it is a `GET` request, parameters will be added to the `url` with the classic `name=value&` format, correctly escaped.

### `headers`

If the request needs custom headers, you can add them with the `headers` keyword.
Provided headers are not manipulated in any way (so, be carefull with uppercase and lowercase letters).
You can add the usual _variable escape_ feature in the `value` field of your headers.

**NOTE 1**: headers can only contain `string` values.

**NOTE 2**: authentication headers are still handled with the `auth` keyword.

**NOTE 3**: if you have the same header key in both `global_headers` and `headers`, the value from `headers` will be used for this call.

```json
{
	"method": "post",
	"url": "/api/site/login",
	"params": {
		...
	},
	"headers": {
		"X-Header1": "header 1",
		"X-Custom": "%(custom_value)s"
	}
}
```

### `files`

If the action is a `post` request, you can specify `files` keyword, passing an array of files to be posted.
Here there is an example:

```json
{
  "method": "post",
  "url": "/api/site/files",
  "files": {
    "file1": "relative/path/to/file.txt",
    "file2": "/absolute/path/to/file.jpg"
  }
}
```

### `no_cookies`

This is a `true` or `false` flag. If set to `true` the cookies will not be sent or read during this single request.

### `max_time`

You can have a test failing when the request exceedes a certain amount of time defined by `max_time`.
`max_time` is set in milliseconds, so if you want to fail after one second, set it to `1000`.

### `fields`

The `fields` section allows you to collect values from the response and to _save_ them inside `restest` to future use.
It is a list of field names that can be also "mapped" to a new name in memory while saving. You can specify both _string_ (to save the key / value in memory _as is_ without name modification) or a _list_ with two fields `[ orig_name, new_name ]`.

**NOTE**: Field extraction supports dotted notation for nested objects.

Here there is a code snippet. Suppose the response is a JSON object like this one:

```json
{
  "auth_token": "jajsj3ijssisiej",
  "user": {
    "id": "abc123",
    "username": "johndoe"
  }
}
```

You could save `auth_token` as is and remap `user.id` into `user_id` in this way:

```json
"fields": [
	"auth_token",
	[ "user.id", "user_id" ]
]
```

### `tests`

The `tests` section allows you to run tests against the request response.
It contains an array of tests structured in this way:

- `title` (optional) a title of the running test
- `field` is the name of the field to run the test against. Field can be one of the following:

  - an attribute name of the returned object (eg. `email`)
  - if the field is a list of values (eg, `tags: [ 'hello', 'world' ]`) you can instruct to check against a specific value using the `[]` square notation. For example: `tags[0]` will be `hello` and `tags[1]` will be `world`.
    Square notations also work when the returned object is just an array. In this case, omit the field name (since there isn't any) and just go for `[0]` or `[1]` and so on.
  - the field name can use dotted notation to access an inner field. There is no limit to the nested field notation. Examples: `user.email` or `user.address.location.lat`

- `value` is the expected value
- `mode` is how to test the `field` value against the provided `value`. You can use one of those conditions (if omitted, default is `EQUALS`):
  - `EQUALS` or `=` or `==`: the `value` must be exactly the same as the value contained in `field`
  - `EMPTY` or `IS_EMPTY` or `IS_NULL` or `NULL`: the `value` must not exists
  - `EXISTS` or `!!`: the `field` is present in the returned object
  - `CONTAINS` or `->`: the `value` must be present _inside_ the `field` value
  - `SIZE` or `LEN` or `LENGTH`: the `field` object (eg. array or string) must be of the size defined in `value`
  - `GT` or `>`: the `field` value must be greater than `value`
  - `GTE` or `>=`: the `field` value must be greater than or equal to `value`
  - `LT` or `<`: the `field` value must be lesser than `value`
  - `LTE` or `<=`: the `field` value must be lesser than or equal to `value`
  - `NOT_NULL` or `IS_NOT_NULL`: the `field` value must exist
  - `NOT_EQUAL` or `!=` or `<>`: the `field` value must be different to `value`
  - `SIZE-GT` or `()>`: the `field` value is an array or string with a size greater than `value`
  - `SIZE-GTE` or `()>=`: the `field` value is an array or string with a size greater than or equal to `value`
  - `SIZE-LT` or `()<`: the `field` value is an array or string with a size lesser than `value`
  - `SIZE-LTE` or `()<=`: the `field` value is an array or string with a size lesser than or equal to `value`
  - `OBJ` or `OBJECT`: the `field` value is an object that must match the object specified in `value`

Here there is an example of two tests, the first one is checking if the first element in array has `id` equal to 1.
The second checks if the second user in the array has the username `Antonette`.

```json
"tests": [
	{
		"title": "Checking for id=1 on first user",
		"field": "[0].id",
		"value": 1
	},
	{
		"title": "Checking for right name on second user",
		"field": "[1].username",
		"value": "Antonette"
	}
]
```

# Path declarations

During tests or variable extraction, sometimes it is important to be able to access a nested value in the returning JSON object.

`restest` offers a very powerful path parser, that will help you reaching the node you want inside your structure. Let's see some examples.
First of all, suppose that the JSON returning is similar to this one:

```json
{
  "user": {
    "email": "user@example.com",
    "id": 123,
    "perms": ["admin", "superuser"]
  },
  "preferences": [
    {
      "name": "color",
      "value": "blue"
    },
    {
      "name": "avatar",
      "value": 1204
    },
    {
      "name": "children",
      "value": [
        {
          "name": "child01",
          "value": 1
        },
        {
          "name": "child02",
          "value": 2
        }
      ]
    }
  ]
}
```

Here there are some path examples:

- `"user.email"` - returns the value of the field `email` (`user@example.com` in this example)
- `"user.perms.[0]"` - returns the first element of the perms array (`admin` in this example)
- `"preferences.[name=avatar]"` - returns the object that has `avatar` in `name` field inside `preferences`
- `"preferences.[name=children].value[value!=2]"` - returns the first child of object with `name` == `children` that hasn't a `value` of `2`.

# Actions

`restest` features a set of actions that can be used to perform some operations during the test.

### `sleep`

The `sleep` action is used to wait for a number of milliseconds. It is useful to wait for a certain amount of time before performing the next action.

```json
{
  "action": "sleep",
  "ms": 1000
}
```

# See examples

You can see a fully working example in `examples` directory.
I'll add more examples during time.

[To see the Typicode example, click here](examples/typicode.example.json)

# Contributors wanted

Contributors are more than welcome. As you can see, at the moment the project source code is quite small so it is a great time to join :-)

These are some fields you could help me:

- create a PIP package to be able to install `restest` with just `pip install restest`
- better console output: there are great examples of console output out there, but I am not very into console stilying ;-)

# Changelog

Full changelog can be seen [here](CHANGELOG.md)
