# restest
Scriptable REST calls test software written in Python

`restest` actions are defined inside a JSON file.

With `restest` you can control return responses and test values against an expected result / behaviour.

## JSON file structure

This is the smaller JSON file for `restest` you can write
(note: name it `simple-example.test.json`):
```
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

```
restest --base-url http://example.com simple-example.test.json
```

Every action **must** contain a `method` or `action` key.

If the `method` key is present, then the action is actually a `http`/`https` request.

If the `action` key is present, then the action is a *script* command.


## ACTION description for HTTP requests

### `title`

Every action can have a *title* field. The text included in this field will be shown on console. Useful to tell the user what's going on.

### `method`

Supported `method` modes:

- **GET** the `HTTP GET` method
- **POST** the `HTTP POST` method

Currently, other `HTTP` methods are not supported, but planned in the future.

### `url`

The partial URL to call. As you have seen before, you can specify the base URL with the `--base-url` command line argument.

### `auth`

This is a `true` / `false` flag which determines if the current call is authenticated. Default is **`false`**

### `ignore_error`

This is a `true` / `false` flag which determines if `restest` should ignore an error occurring on this request.
Default is **`false`**

### `return_code`

With `return_code` key you can specify the `HTTP Return Code` you expect the call to return.
For example, if you make an unauthorized call to a specific endpoint, it should return a `403 Unauthorized` return code.
If you do *not* specify `return_code` key and your request returns a `403`, then `restest` will return an error, but if you know *for sure* that
your request is going to fail with a `403` return code, then you can specify it with:
```
"return_code": 403
```
And the `restest` action will succeed.

Default value for `return_code` is **`200`**

### `params`

If the action is a `post` request, you can specify `POST` parameters with this keyword and passing an array.
Here there is an example:
```
{
	"method": "post",
	"url": "/api/site/login",
	"params": {
		"email": "john.doe@example.com",
		"password": "mypassword"
	}
}
```

### `fields`

The `fields` section allows you to collect values from the response and to *save* them inside `restest` to future use.
It is a list of field names that can be also "mapped" to a new name in memory while saving. You can specify both *string* (to save the key / value in memory *as is* without name modification) or a *list* with two fields `[ orig_name, new_name ]`.

**NOTE**: Field extraction supports dotted notation for nested objects.

Here there is a code snippet. Suppose the response is a JSON object like this one:

```
{
	"auth_token": "jajsj3ijssisiej",
	"user": {
		"id": "abc123",
		"username": "johndoe"
	}
}
```

You could save `auth_token` as is and remap `user.id` into `user_id` in this way:

```
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
	- `EQUALS` or `=` or `==`:  the `value` must be exactly the same as the value contained in `field`
	- `EXISTS` or `!!`: the `field` is present in the returned object
	- `CONTAINS` or `->`: the `value` must be present *inside* the `field` value
	- `SIZE` or `LEN` or `LENGTH`: the `field` object (eg. array or string) must be of the size defined in `value`
	- `GT` or `>`: the `field` value must be greater than `value`
	- `GTE` or `>=`: the `field` value must be greater than or equal to `value`
	- `LT` or `<`: the `field` value must be lesser than `value`
	- `LTE` or `<=`: the `field` value must be lesser than or equal to `value`
	- `SIZE-GT` or `()>`: the `field` value is an array or string with a size greater than `value`
	- `SIZE-GTE` or `()>=`: the `field` value is an array or string with a size greater than or equal to `value`
	- `SIZE-LT` or `()<`: the `field` value is an array or string with a size lesser than `value`
	- `SIZE-LTE` or `()<=`: the `field` value is an array or string with a size lesser than or equal to `value`
	- `OBJ` or `OBJECT`: the `field` value is an object that must match the object specified in `value`

Here there is an example of two tests, the first one is checking if the first element in array has `id` equal to 1.
The second checks if the second user in the array has the username `Antonette`.
```
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



# Contributions wanted

Contributors are more than welcome. As you can see, at the moment the project source code is quite small so it is a great time to join :-)

These are some fields you could help me:

- create a PIP package to be able to install `restest` with just `pip install restest`
- better console output: there are great examples of console output out there, but I am not very into console stilying ;-)

# Changelog

Full changelog can be seen [here](CHANGELOG.md)