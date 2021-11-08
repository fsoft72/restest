# restest  changelog

## v1.88
  - ADD: support for raw list sending in body payload [thanks to Dario Barbazza]

## v1.87.1
  - FIX: _expand_list() sometimes returned wrong values

## v1.87
  - ADD: --env-load to load an environment file before starting the tests
  - ADD: --env-save to save an environment file with all variables before exiting
  - ADD: new --dry parameter to run the tests without doing any request (experiemental / WIP)
  - ADD: new test 'expand_complex.json' to test inner expansions
  - ENH: now the method list has different colours depending on the method and it is more tidy
  - ENH: 'mode' is now case insensitive
  - FIX: expand_list() didn't expand all variables correctly if nested.
  - FIX: uploading files used to create problems with list-like fields

## v1.86
  - ADD: the very first experimental support for custom 'code' blocks
  - ENH: better error reporting
  - ENH: updated dependencies.txt file
  - ENH: default Authorization template is now Bearer
  - FIX: a bug that prevented inner list to be expanded correctly
  - FIX: an out of bounds error in path parser

## v1.85
  - ADD: `--env` flag, that copies all environment variables so they can be accessed by the scripts
  - ADD: `NOT_EQUAL`, `!=`, `<>` mode
  - ENH: now requests are with `auth: true` by default.

## v1.84
  - ADD: total execution time in seconds/millis

## v1.83
  - ENH: better error reporting when expanding fields
  - FIX: wrong parameters expansion in path_parser

## v1.82
  - ENH: now path parser expands key values using _expand_var before starting the search

## v1.81
  - ADD: `NOT_NULL` and `IS_NOT_NULL` test modes (same as `EXIST`, `EXISTS` and `!!` )
  - ENH: now restest throws an error if a test mode is mispelled or not existent.
  - ENH: now restest shows the operation request even if it is not able to show results.

## v1.80
  - ADD: support for comments. You can add a comment using the "rem" command, or
         by putting an `#` sign at the beginning of a line (**note**: using `#` makes the
         JSON invalid)

  - ADD: now the variables inside inner structures are expanded recursively

  - ENH: now action `dump` can write to console, if you pass `"print": true` attribute

## v1.72
  - ADD: is now possible to upload multiple files with the same field name

## v1.71
  - ADD: new --curl option to see curls on console (on stderr)
  - ENH: Now GET requests can have url parameters defined in "params" instead of the URL path.
  - ENH: Better CURL formatting for easier debug
  - ENH: Updated documentation
  - FIX: error accessing not existing tokens in tests
  - FIX: better error handling for out of bounds list index

## v1.70
  - brand new path parser that enanches the search of keys inside nested structures

## v1.61
  - ADD: new `EMPTY` value check mode

## v1.60
  - ADD: new `content` attribute on requests

## v1.50
  - ADD: postman output support
  - FIX: body decoding error

## v1.20
 - ADD: support for `files` array to post files in requests
 - ADD: new internal method _resolve_fname() to support file name resolution

## v1.15
- ADD: support for new `no_cookies` param
- ADD: support for `max_time` to check if a request takes too long
- ADD: request time is shown in the output log
- ADD: request time is shown in the console output
- ADD: support for `PUT`, `DELETE` and `PATCH` requests
- ENH: code cleanup

## v1.13
- ADD: more documentation
- FIX: a bug in the "forced log"

## v1.12
- added support for Session (cookies are retrieved and used as needed)
- now sections have a better console output
- internal refactor of logfile handling
- started the changelog
