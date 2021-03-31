#!/usr/bin/env python3
#
# restest engine
#
# written by Fabio Rotondo (fabio.rotondo@gmail.com)
#

import requests, json, sys, copy
import urllib

from .path_parser import expand_value

class RESTest:
	def __init__ ( self, base_url = '', log_file = '', stop_on_error = True, quiet = False, postman = None, curl = False ):
		self.quiet = quiet
		self.base_url = base_url
		self.log_file = log_file
		self.postman = postman
		self.dump_curl_on_console = curl

		self.globals = {}		# Global var / values for requests

		self.authorization_header = "Authorization"
		self.authorization_template = "Token %(token)s"

		# This is a number used to generate counts
		self._inner_count = 0

		self.stop_on_error = stop_on_error
		self.sections = []

		self._tests  = 0
		self._errors = 0

		self.session = requests.Session ()

	def _tabs ( self, indent = 0 ):
		return "\t" * ( len ( self.sections ) + indent )

	def _parse_headers ( self, r ):
		heads = {}
		for k, v in r.headers.items ():
			hk = k.lower ()
			heads [ hk ] = r.headers [ k ]

		r._headers = heads

	def _log_write ( self, txt ):
		if not self.log_file: return

		fout = open ( self.log_file, "a" )
		fout.write ( txt )

	def _log_start ( self, method, endpoint, data ):
		self._tests += 1
		if not self.log_file: return

		self._log_write ( "=" * 70 )
		self._log_write ( """
Endpoint:     %s %s
Data:         %s
""" % ( method, endpoint, json.dumps ( data, default = str ) ) )

	def _log_resp ( self, headers, resp ):
		if not self.log_file: return

		self._log_write ( """Headers:      %s
Status Code:  %s
Request Time: %s
Raw Response: %s
""" % ( headers, resp.status_code, resp.elapsed.microseconds / 1000, resp.text ) )

	def _log_curl ( self, req ):
		command = "curl -X {method} \\\n -H {headers} \\\n -d '{data}' \\\n '{uri}'"

		method = req.method
		uri = req.url
		#data = str ( req.body ) [ 2 : -1 ]   # quick and dirty way to remove b'...' from string
		try:
			data = req.body.decode ( 'utf-8' )
		except:
			data = ""

		headers = [ '"{0}: {1}"'.format ( k, v ) for k, v in req.headers.items() ]
		headers = " \\\n -H ".join ( headers )

		curl = command.format ( method = method, headers = headers, data = data, uri = uri )
		self._log_write ( "\nCURL:         %s\n\n" % curl )

		if self.dump_curl_on_console:
			sys.stderr.write ( "\n\n%s\n\n" % curl )
			sys.stderr.flush ()

	def _mk_headers ( self, authenticated ):
		headers = {}
		if authenticated:
			hv = ""
			try:
				hv = self._expand_var ( self.authorization_template )
			except:
				sys.stderr.write ( "ERROR: could not create Authorization template: %s" % self.authorization_template )
				raise

			if hv:
				headers [ self.authorization_header ] = hv

		return headers

	def _resolve_url ( self, endpoint ):
		if endpoint.lower ().find ( "http:" ) != -1:  return endpoint
		if endpoint.lower ().find ( "https:" ) != -1: return endpoint
		if endpoint.startswith ( "/" ):
			return self.base_url + endpoint

		return self.base_url + "/" + endpoint

	def _expand_dict ( self, dct ):
		for k, v in dct.items ():
			if isinstance ( v, str ) and v.find ( "%(") != -1:
				v = self._get_v ( v )
			elif isinstance ( v, dict ):
				v = self._expand_dict ( v )

			dct [ k ] = v

		return dct

	def _get_v ( self, x ):
		if isinstance ( x, dict ):
			return self._expand_dict ( x )

		if isinstance ( x, bool ):
			if x == True: x = 1
			if x == False: x = 0

		x = str ( x )
		if x.find ( "%(" ) == -1: return x

		return  x % self.globals


	def _expand_var ( self, v ):
		globs = copy.copy ( self.globals )
		globs [ "inner_count" ] = self._inner_count

		try:
			if isinstance ( v, list ):
				res = []
				for x in v:
					res.append ( self._get_v ( x ) )
			else:
				v = self._get_v ( v )
		except:
			sys.stderr.write ( "ERROR: could not expand: %s (%s)" % ( v, self.globals ) )


		return v

	def _expand_data ( self, data ):
		res = {}

		self._inner_count += 1

		for k, v in data.items ():
			k = self._expand_var ( k )
			v = self._expand_var ( v )
			res [ k ] = v

		return res

	def _object_compare ( self, v1, v2 ):
		o1 = eval ( v1 )
		o2 = eval ( v2 )

		k1 = list ( o1.keys () )
		k2 = list ( o2.keys () )
		k1.sort ()
		k2.sort ()
		if k1 != k2: return False

		for k in k1:
			if o1 [ k ] != o2 [ k ]: return False


		return True
		pass

	def _data_to_url ( self, dct ):
		elems = []
		for k, v in dct.items ():
			elems.append ( f"{k}={urllib.parse.quote(v)}" )

		if not elems: return ""

		return "&".join ( elems )

	def _reorder_files ( self, files ):
		has_multi = False
		for k, v in files.items ():
			if isinstance ( v, list ):
				has_multi = True
				break

		if not has_multi: return files

		res = []
		for k, v in files.items ():
			if isinstance ( v, list ):
				for el in v:
					res.append ( ( k, el ) )
			else:
				res.append ( ( k, v ) )

		return res


	def _req ( self, mode, endpoint, data = {}, authenticated = True, status_code = 200, skip_error = False, no_cookies = False, max_exec_time = 0, files = None, title = "", content = "json" ):
		endpoint = self._expand_data ( { "endpoint" : endpoint } ) [ 'endpoint' ]

		url = self._resolve_url ( endpoint )
		headers = self._mk_headers ( authenticated = authenticated )

		data = self._expand_data ( data )

		if no_cookies:
			obj = requests
		else:
			obj = self.session

		if mode == "GET":
			m = obj.get
		elif mode == "POST":
			m = obj.post
		elif mode == "DELETE":
			m = obj.delete
		elif mode == "PUT":
			m = obj.put
		elif mode == "PATCH":
			m = obj.patch
		else:
			m = obj.post


		if mode == "GET" and data:
			url_params = self._data_to_url ( data )
			if url.find ( "?" ) == -1:
				url += "?" + url_params
			else:
				url += "&" + url_params

		files = self._reorder_files ( files )

		if content == 'json':
			r = m ( url, json = data, headers = headers, files = files )
		elif content == 'form':
			r = m ( url, data = data, headers = headers, files = files )


		self._parse_headers ( r )

		if self.postman:
			self.postman.add ( title, mode, url, data, headers, r )

		self._log_start ( mode, url, data )
		self._log_resp ( headers, r )
		self._log_curl ( r.request )

		# If skip_error is set, we don't have to check for the status code
		if skip_error: return r

		if r.status_code != status_code and self.stop_on_error:
			sys.stderr.write ( """%s\nREQUEST ERROR\n%s\n""" % ( "*" * 70, "*" * 70 ) )
			sys.exit ( 1 )

		ms = r.elapsed.microseconds / 1000
		if max_exec_time and ms > max_exec_time:
			sys.stderr.write ( """%s\nTOO MUCH TIME ERROR (res: %s - exprected: %s)\n%s\n""" % ( "*" * 70, ms, max_exec_time,  "*" * 70 ) )
			sys.exit ( 1 )

		return r

	def do_EXEC ( self, meth, endpoint, data = {}, authenticated = True, status_code = 200, skip_error = False, no_cookies = False, max_exec_time = 0, files = None, title = "", content = "json" ):
		return self._req ( meth, endpoint, data, authenticated, status_code, skip_error = skip_error, no_cookies=no_cookies, max_exec_time = max_exec_time, files = files, title = title, content=content )

	def fields ( self, resp, fields ):
		j = resp.json ()

		for k in fields:
			if isinstance ( k, list ) or isinstance ( k, tuple ):
				json_key = k [ 0 ]
				glob_key = k [ 1 ]
			else:
				glob_key = k
				json_key = k

			# ADD: support for '*' field name (all JSON)
			if json_key == '*':
				self.globals [ glob_key ] = j
				continue

			self.globals [ glob_key ] = self._expand_value ( j, json_key )

	def dumps ( self, resp, fields ):
		j = resp.json ()

		for k in fields:
			if isinstance ( k, list ) or isinstance ( k, tuple ):
				glob_key = k [ 1 ]
				json_key = k [ 0 ]
			elif isinstance ( k, dict ):
				json_key = k [ 'field' ]
				glob_key = json_key
			else:
				glob_key = k
				json_key = k

			v = self._expand_value ( j, json_key )

			print ( "==== %s: %s\n" % ( glob_key, json.dumps ( v, indent = 4, default=str ) ) )

	def _error ( self, txt ):
		sys.stderr.write ( "*** ERROR: %s\n" % txt )
		self._log_write ( "\n\n*** ERROR: %s\n" % txt )
		if self.stop_on_error: sys.exit ( 1 )
		self._errors += 1
		return None

	def _expand_value ( self, dct, key ):
		key = self._expand_var ( key )
		res, err = expand_value ( key, dct )

		if err:
			print ( "PATH: %s - Error: %s" % ( key, err ) )
			return "__NOT_FOUND__"

		return res

	def copy_val ( self, _from, _to ):
		_from = self._expand_var ( _from )
		_to   = self._expand_var ( _to )

		self.globals [ _to ] = self.globals [ _from ]

	def set_val ( self, _key, _val ):
		_key = self._expand_var ( _key )
		_val = self._expand_var ( _val )

		self.globals [ _key ] = _val

	def check ( self, resp, checks ):
		j = resp.json ()

		for chk in checks:
			if 'title' in chk: print ( "%s%s" % ( self._tabs ( 1 ), chk [ 'title' ] ) )

			self._tests += 1

			field = self._expand_var ( chk [ 'field' ] )

			v = self._expand_value ( j, field ) #chk [ 'field' ] )
			current_val = self._expand_var ( v )
			expected_val = self._expand_var ( chk.get ( 'value' ) )
			if v == "__NOT_FOUND__":
				self._error ( "FIELD: %s missing %s" % ( field, json.dumps ( j, default = str ) ) )
				return

			mode = chk.get ( 'mode', 'EQUALS' )

			if mode in ( 'EXISTS', 'EXIST', "!!", "NOT_NULL", "IS_NOT_NULL" ):
				if ( str ( v ) == "None" ) or ( len ( str ( v ) ) == 0 ):
					self._error ( "FIELD: %s is EMPTY" % ( field ) )
					return
			elif mode in ( "EMPTY", "IS_EMPTY", "IS_NULL", "NULL", "@" ):
				if ( str ( v ) != "None" ):
					self._error ( "FIELD: %s VALUE mismatch. Expected: Null - got: %s" % ( field, current_val ) )
			elif mode in ( 'EQUALS', "==", "=", "EQUAL" ):
				if current_val != expected_val:
					self._error ( "FIELD: %s VALUE mismatch. Expected: %s - got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'CONTAINS', '->' ):
				if expected_val  not in current_val:
					self._error ( "FIELD: %s DOES NOT contains %s. List: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'SIZE', 'LEN', 'LENGTH' ):
				if len ( current_val ) != int ( expected_val ):
					self._error ( "FIELD: %s SIZE mismatch. Expected: %s - got: %s (%s)" % ( field, expected_val, len ( current_val ), current_val ) )
			elif mode in ( 'GT', '>' ):
				if current_val  <= expected_val:
					self._error ( "FIELD: %s is SMALLER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'GTE', '>=' ):
				if current_val  < expected_val:
					self._error ( "FIELD: %s is SMALLER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'LT', '<' ):
				if current_val  >= expected_val:
					self._error ( "FIELD: %s is BIGGER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'LTE', '<=' ):
				if current_val  <= expected_val:
					self._error ( "FIELD: %s is BIGGER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'SIZE-GT', '()>' ):
				if len ( current_val ) <= int ( expected_val ):
					self._error ( "FIELD: %s is SMALLER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'SIZE-GTE', '()>=' ):
				if len ( current_val ) < int ( expected_val ):
					self._error ( "FIELD: %s is SMALLER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'SIZE-LT', '()<' ):
				if len ( current_val ) >= int ( expected_val ):
					self._error ( "FIELD: %s is BIGGER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( 'SIZE-LTE', '()<=' ):
				if len ( current_val ) <= int ( expected_val ):
					self._error ( "FIELD: %s is BIGGER. Expected: %s got: %s" % ( field, expected_val, current_val ) )
			elif mode in ( "OBJ", "OBJECT" ):
				if not self._object_compare ( current_val, expected_val ):
					self._error ( "FIELD: %s object values mismatch" % ( field ) )
			else:
				self._error ( "ERROR: unsupported test mode: %s " % mode )


			if 'save' in chk:
				self.globals [ chk [ 'save' ] ] = v

	def dump ( self, fields, do_print = False ):
		for f in fields:
			f = self._expand_var ( f )
			v = self.globals [ f ]

			s = "==== %s: %s\n" % ( f, json.dumps ( v, indent = 4, default=str ) )
			self._log_write ( s )

			if do_print: print ( s )

	def section_start ( self, name ):
		self.sections.append ( name )

		self._log_write ( """
%s
START  ---->  %s
%s
""" % ( "*" * 70, name, "*" * 70 ) )

	def section_end ( self ):
		name = self.sections.pop ()
		self._log_write ( ( "=" * 70 ) + "\n\n" )
		self._log_write ( """%s
END  ----  %s
%s

""" % ( "*" * 70, name, "*" * 70 ) )

"""
if __name__ == '__main__':
	rt = RESTest ( 'http://localhost:8000', log_file = "/ramdisk/req.log" )

	rt.save (
		rt.do_POST ( "/api/auth/login", { "email": "info@example.com", "password": "ciao" }, authenticated = False ),
		[ "otl", "token", "id_user" ]
	)

	rt.section_start ( "USER CREATION" )

	rt.save (
		rt.do_POST ( "/api/auth/register", { "email": "test%(inner_count)s@example.com", "password": "hello123" }, authenticated=False ),
		[ ( "user", "test_user" ) ]
	)

	rt.check (
		rt.do_GET ( "/api/user/%(test_user)s/debug" ),
		[
			{
				"field" : "user.auth_code",
				"mode": "EXISTS",
				"save": "auth_code"
			}
		]
	)

	rt.check (
		rt.do_POST ( "/api/user/activate", { "auth_code" : "%(auth_code)s", "password": "hello%(inner_count)s" } ),
		[
			{
				"field": "ok",
				"mode": "EQUALS",
				"value": 1
			}
		]
	)

	rt.section_end ()

	rt.do_POST ( "/api/user/del", { "id_user" : "%(test_user)s" } )
"""
