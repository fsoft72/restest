#!/usr/bin/env python3
#
# restest parser
#
# written by Fabio Rotondo <fabio.rotondo@gmail.com>
#

import sys, json, os
from termcolor import colored, cprint

from .engine import RESTest

class RESTestParser:
	def __init__ ( self, base_url = None, stop_on_error = None, log_file = None, quiet = False, postman = None, curl = False ):
		self.rt = RESTest ( quiet = quiet, log_file = log_file, postman = postman, curl = curl )

		self._batches = {}

		self.forced_stop_on_error = stop_on_error
		self.forced_log_file = log_file
		self.forced_base_url = base_url
		self.quiet = quiet

		self._paths = []
		self._included = {}

	def open ( self, fname ):
		self.script = self._json_load ( fname )

		self._abs_script_path = os.path.dirname ( os.path.abspath ( fname ) )

		self._paths.append ( self._abs_script_path )

		self._parse_system ()

		if self.forced_base_url != None:
			self.rt.base_url = self.forced_base_url

		if self.forced_stop_on_error != None:
			self.rt.stop_on_error = self.forced_stop_on_error

		if self.forced_log_file != None:
			self.rt.log_file = self.forced_log_file

		self._actions ( self.script [ "actions" ] )

	def _actions ( self, actions ):
		for act in actions:
			action = act.get ( 'method', act.get ( 'action', '' ) ).lower ()
			meth = getattr ( self, "_method_" + action )
			if 'title' in act and ( act.get ( 'action' ) != 'section' ): print ( act [ 'title' ] )
			meth ( act )

	def _parse_files ( self, dct ):
		files = {}

		for k, v in dct.items ():
			v = self._resolve_fname ( v )
			files [ k ] = open ( v, 'rb' )

		return files

	def _send_req ( self, act ):
		m = act [ 'method' ].upper ()

		auth = act.get ( 'auth', False )
		content = act.get ( 'content', 'json' )

		files = self._parse_files ( act.get ( 'files', {} ) )

		if not self.quiet:
			sys.stdout.write (
				"%s %s %s %s %s %s" % (
				self.rt._tabs (),
				colored ( "%-4s" % m.upper (), 'red' ),
				colored ( "%-35s" % act.get ( "url", "" ), 'yellow' ),
				colored ( act.get ( 'params', {} ), 'green' ),
				'auth:', colored ( auth, 'blue' )
				)
			)

		ignore = False
		if "ignore_error" in act:
			ignore = act [ 'ignore_error' ]
		elif "skip_error" in act:
			sys.stderr.write ( "%s 'skip_error' is deprecated use 'ignore_error' in actions\n" % ( colored ( "WARNING",  'yellow' ) ) )
			ignore = act [ 'skip_error' ]

		res = self.rt.do_EXEC ( m, act [ 'url' ],
					act.get ( 'params', {} ),
					auth,
					status_code = act.get ( 'status_code', 200 ),
					skip_error = ignore,
					no_cookies = act.get ( "no_cookies", False ),
					max_exec_time= act.get ( "max_time", 0 ),
					title = act.get ( 'title', 'No title provided' ),
					files = files,
					content=content,
				)

		if not self.quiet:
			sys.stdout.write ( " t: %s ms\n" % ( res.elapsed.microseconds / 1000 ) )

		return res

	def _method_exec ( self, act ):
		res = self._send_req ( act )

		#if 'save_cookies' in act: self.rt.save_cookies ( res, act [ 'save_cookies' ] )
		if 'fields' in act: self.rt.fields ( res, act [ 'fields' ] )
		if 'tests'  in act: self.rt.check ( res, act [ 'tests' ] )
		if 'dumps'  in act: self.rt.dumps ( res, act [ 'dumps' ] )

	def _method_get ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'get'
		self._method_exec ( act )

	def _method_post ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'post'
		self._method_exec ( act )

	def _method_delete ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'delete'
		self._method_exec ( act )

	def _method_patch ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'patch'
		self._method_exec ( act )

	def _method_put ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'put'
		self._method_exec ( act )

	def _method_section ( self, act ):
		title = act.get ( 'title', act.get ( 'name', 'SECTION TITLE MISSING' ) )
		if not self.quiet:
			print (
				"\n%s====== %s" % (
					self.rt._tabs (),
					colored ( title  , 'green' )
				)
			)

		self.rt.section_start ( title )
		self._actions ( act [ 'actions' ] )
		self.rt.section_end ()

		if not self.quiet:
			print (
				"%s=========================================== \n" % (
					self.rt._tabs (),
				)
			)

	def _method_copy ( self, act ):
		self.rt.copy_val ( act [ 'from' ], act [ 'to' ] )

	def _method_dump ( self, act ):
		self.rt.dump ( act [ 'fields' ], act.get ( 'print' ) )

	def _method_set ( self, act ):
		self.rt.set_val ( act [ 'key' ], act [ 'value' ] )

	def _resolve_fname ( self, fname ):
		if not fname.startswith ( "/" ):
			path = self._paths [ -1 ]
			fname = os.path.abspath ( os.path.join ( path, fname ) )

		if not os.path.exists ( fname ):
			sys.stderr.write ( "ERROR: could not open file: %s\n" % fname )
			sys.exit ( 1 )

		return fname

	def _method_include ( self, act ):
		fname = self._resolve_fname ( act [ 'filename' ] )

		self._paths.append ( os.path.dirname ( fname ) )

		script = self._json_load ( fname )

		skip_include = False
		if script.get ( "run-once", False ):
			if fname in self._included: skip_include = True

		if not skip_include:
			self._included [ fname ] = 1
			if "name" in act:
				name = act [ 'name' ].lower ()
				self._batches [ act [ 'name' ] ] = script [ 'actions' ]

			if "exec" in act and act [ 'exec' ] == True:
				self._actions ( script [ 'actions' ] )

		self._paths.pop ()

	def _method_batch_set ( self, act ):
		name = act [ 'name' ].lower ()
		actions = act [ 'actions' ]
		self._batches [ name ] = actions

	def _method_batch_exec ( self, act ):
		name = act [ 'name' ].lower ()
		actions = self._batches [ name ]
		self._actions ( actions )

	def _method_rem ( self, act ):
		pass


	def _parse_system ( self ):
		self.rt.sections = []

		if "system" not in self.script: return

		system = self.script [ 'system' ]

		for k, v in system.items ():
			setattr ( self.rt, k, v )

	def _json_load ( self, fname ):
		data = open ( fname ).readlines ()
		txt = '\n'.join ( [ n.strip () for n in data if not n.strip ().startswith ( "#" ) ] )
		return json.loads ( txt )