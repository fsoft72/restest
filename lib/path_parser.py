#!/usr/bin/env python3

import re

rx_split = re.compile ( r"([.!=[\]])" )

def _is_int ( txt ):
	print ( "--- TXT: ", txt )
	try:
		num = int ( str ( txt ), 10 )
		return True
	except:
		return False

def _parse_square ( tokens, pos ):
	res = []

	while pos < len ( tokens ):
		tok = tokens [ pos ]
		pos += 1

		if _is_int ( tok ):
			return { "mode": "pos", "value": int ( str ( tok ), 10 ) }, pos

def _parser ( tokens, pos ):
	res = []
	while pos < len ( tokens ):
		tok = tokens [ pos ]
		pos += 1
		if not tok:
			continue

		if tok not in ( '.', '!', '=', '[', ']' ):
			res.append ( { "mode": "label", "value": tok } )
		elif tok == '[':
			parsed, pos = _parse_square ( tokens, pos )

			res.append ( parsed )
	return res, pos

def path_parser ( path ):
	print ( "PATH: ", path )
	tokens = rx_split.split ( path )

	return _parser ( tokens, 0 )


if __name__ == '__main__':
	print ( path_parser ( "first.second.[0].third" ) )
	print ( path_parser ( "first.second.[user.key=5].third" ) )
	print ( path_parser ( "first.second.[user.email!=example@gmail.com].third" ) )