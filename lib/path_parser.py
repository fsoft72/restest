#!/usr/bin/env python3

import re

rx_split = re.compile ( r"([.!=[\]])" )

def _is_int ( txt ):
	try:
		num = int ( str ( txt ), 10 )
		return True
	except:
		return False

def _parse_square ( tokens, pos ):
	res = []
	tok = tokens [ pos ]

	if _is_int ( tok ):
		return { "mode": "pos", "value": int ( str ( tok ), 10 ) }, pos +2

	return _parser ( tokens, pos )

def _extract_value ( tokens, pos, equal = False ):
	mode = "equal"
	if not equal:
		mode = "not_equal"
		pos = pos + 1

	tok = tokens [ pos ]

	pos = pos + 1

	return { "mode": mode, "value": tok }, pos


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
		elif tok == ']':
			return res, pos
		elif tok == '=':
			parsed, pos = _extract_value ( tokens, pos, equal = True )
			res.append ( parsed )
		elif tok == '!':
			parsed, pos = _extract_value ( tokens, pos, equal = False )
			res.append ( parsed )

	return res, pos

def path_parser ( path ):
	print ( "PATH: ", path )
	tokens = rx_split.split ( path )

	return _parser ( tokens, 0 ) [ 0 ]


if __name__ == '__main__':
	import json
	#print ( path_parser ( "first.second.[0].third" ) )
	#print ( json.dumps ( path_parser ( "first.second.[user.key=5].third" ), indent = 4 ) )
	#print ( path_parser ( "first.second.[user.email!=example@gmail.com].third" ) )
	#print ( json.dumps ( path_parser ( "first.[3].[user.key=23].second.[1].name" ), indent = 4 ) )
	print ( json.dumps ( path_parser ( "first.[sub[user.key=3]].second" ), indent=4 ) )