#!/usr/bin/env python3

import os, json
from urllib.parse import urlparse

class PostmanExporterItem:
	def __init__ ( self, title, mode, url, data ):
		self.mode = mode
		self.name = None
		self.url = {}
		self.data = data
		self.title = title

		self._parse ( url )

	def _parse ( self, raw_url ):
		o = urlparse ( raw_url )
		self.name = o.path
		p = [ x for x in o.path.split ( "/" ) if x ]
		self.url = {
			"raw": raw_url,
			"host": [
				o.scheme + "://" + o.netloc
			],
			"path": p
		}
		#print ( "\n\n***** URL: ", o )

	def obj ( self ):
		return {
			"name": self.name,
			"request": {
				"method": self.mode,
				"header": [],
				"url": self.url,
				"description": self.title
			},
			"response": []
		}

class PostmanExporter:
	def __init__ ( self, output_name ):
		self.schema = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
		self.output_name = output_name
		self.name = os.path.basename ( output_name )
		self.items = []

	def add ( self, title, mode, url, data, headers, r ):
		it = PostmanExporterItem ( title, mode, url, data )
		self.items.append ( it )

	def save ( self ):
		res = { "info": { "name": self.name, "schema": self.schema }, "item": [] }
		for i in self.items:
			res [ 'item' ].append ( i.obj () )

		open ( self.output_name, "w" ).write ( json.dumps ( res, indent = 4 ) )



