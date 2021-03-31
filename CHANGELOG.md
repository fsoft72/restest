# restest  changelog

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

  - add: new `EMPTY` value check mode
## v1.60

  - add: new `content` attribute on requests

## v1.50

  - add: postman output support

  - fix: body decoding error

## v1.20

 - add: support for `files` array to post files in requests
 - add: new internal method _resolve_fname() to support file name resolution

## v1.15

- add: support for new `no_cookies` param
- add: support for `max_time` to check if a request takes too long
- add: request time is shown in the output log
- add: request time is shown in the console output
- add: support for `PUT`, `DELETE` and `PATCH` requests
- enh: code cleanup

## v1.13

- add more documentation
- fix a bug in the "forced log"

## v1.12

- added support for Session (cookies are retrieved and used as needed)
- now sections have a better console output
- internal refactor of logfile handling
- started the changelog
