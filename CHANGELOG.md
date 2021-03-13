# restest  changelog

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
