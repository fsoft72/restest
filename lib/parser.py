#!/usr/bin/env python3

import sys, json, os
from termcolor import colored, cprint

from .engine import RESTest

class RESTestParser:
	def __init__ ( self, base_url = None, stop_on_error = None, log_file = None, quiet = False ):
		self.rt = RESTest ( quiet = quiet )

		self._batches = {}

		self.forced_stop_on_error = stop_on_error
		self.forced_log_file = log_file
		self.forced_base_url = base_url
		self.quiet = quiet

		self._paths = []
		self._included = {}

	def open ( self, fname ):
		self.script = json.loads ( open ( fname ).read () )

		self._abs_script_path = os.path.dirname ( os.path.abspath ( fname ) )

		self._paths.append ( self._abs_script_path )

		self._parse_system ()

		if self.forced_base_url != None:
			self.rt.base_url = self.forced_base_url

		if self.forced_stop_on_error != None:
			self.rt.stop_on_error = self.forced_stop_on_error

		if self.forced_log_file != None:
			self.rt.output_file_name = self.forced_log_file

		self._actions ( self.script [ "actions" ] )

	def _actions ( self, actions ):
		for act in actions:
			action = act.get ( 'method', act.get ( 'action', '' ) ).lower ()
			#action = act [ 'action' ].lower ()
			meth = getattr ( self, "_method_" + action )
			if 'title' in act: print ( act [ 'title' ] )
			meth ( act )

	def _send_req ( self, act ):
		m = act [ 'method' ].lower ()
		if m == "get":
			f = getattr ( self.rt, "do_GET" )
		else:
			f = getattr ( self.rt, "do_POST" )

		# Support both 'authentication' and 'auth' flags
		if 'authentication' in act:
			sys.stderr.write ( "%s 'authentication' is deprecated use 'auth' in actions\n" % ( colored ( "WARNING",  'yellow' ) ) )
			auth = act.get ( 'authentication', False )
		else:
			auth = act.get ( 'auth', False )

		if not self.quiet:
			sys.stdout.write (
				"%s %s %s %s %s %s\n" % (
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

		return f ( act [ 'url' ], act.get ( 'params', {} ), auth, status_code = act.get ( 'status_code', 200 ), skip_error = ignore  )

	def _method_exec ( self, act ):
		res = self._send_req ( act )

		if 'fields' in act: self.rt.save  ( res, act [ 'fields' ] )
		if 'tests'  in act: self.rt.check ( res, act [ 'tests' ] )
		if 'dumps'  in act: self.rt.dumps ( res, act [ 'dumps' ] )

	def _method_get ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'get'
		self._method_exec ( act )

	def _method_post ( self, act ):
		if 'method' not in act: act [ 'method' ] = 'post'
		self._method_exec ( act )

	def _method_section ( self, act ):
		title = act.get ( 'title', act.get ( 'name', 'SECTION TITLE MISSING' ) )
		if not self.quiet:
			print (
				"\n%s ====== %s" % (
					self.rt._tabs (),
					colored ( title  , 'green' )
				)
			)

		self.rt.section_start ( title )
		self._actions ( act [ 'actions' ] )
		self.rt.section_end ()

		if not self.quiet:
			print (
				"%s =========================================== \n" % (
					self.rt._tabs (),
				)
			)

	def _method_copy ( self, act ):
		self.rt.copy_val ( act [ 'from' ], act [ 'to' ] )

	def _method_dump ( self, act ):
		self.rt.dump ( act [ 'fields' ] )

	def _method_set ( self, act ):
		self.rt.set_val ( act [ 'key' ], act [ 'value' ] )

	def _method_include ( self, act ):
		fname = act [ 'filename' ]

		if not fname.startswith ( "/" ):
			path = self._paths [ -1 ]
			fname = os.path.abspath ( os.path.join ( path, fname ) )

		if not os.path.exists ( fname ):
			sys.stderr.write ( "ERROR: could not open file: %s\n" % fname )
			sys.exit ( 1 )

		self._paths.append ( os.path.dirname ( fname ) )

		script = json.loads ( open ( fname ).read () )

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


	def _parse_system ( self ):
		self.rt.sections = []

		if "system" not in self.script: return

		system = self.script [ 'system' ]

		for k, v in system.items ():
			setattr ( self.rt, k, v )