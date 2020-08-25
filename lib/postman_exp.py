#!/usr/bin/env python3

import os, json
from urllib.parse import urlparse

class PostmanExporterItem:
	def __init__ ( self, title, mode, url, data, base_url ):
		self.mode = mode
		self.name = None
		self.url = {}
		self.data = data
		self.title = title
		self.body = None
		self.base_url = base_url

		self._parse ( url )

	def _parse ( self, raw_url ):
		o = urlparse ( raw_url )
		self.name = o.path
		p = [ x for x in o.path.split ( "/" ) if x ]

		if self.base_url:
			host = self.base_url
		else:
			host = o.scheme + "://" + o.netloc

		self.url = {
			"raw": raw_url,
			"host": [
				host
			],
			"path": p
		}

		self._parse_body ()

	def _parse_body ( self ):
		if not len ( self.data.keys () ): return

		body = {
			"mode": "raw",
			"raw": json.dumps ( self.data, indent = 4 ),
			"options": {
				"raw": {
					"language": "json"
				}
			}
		}

		self.body = body

	def obj ( self ):
		res = {
			"name": self.name,
			"request": {
				"method": self.mode,
				"header": [],
				"url": self.url,
				"description": self.title
			},
			"response": []
		}

		if self.body:
			res [ 'request' ] [ 'body' ] = self.body

		return res

class PostmanExporter:
	def __init__ ( self, output_name, name, base_url ):
		self.schema = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
		self.output_name = output_name
		self.name = name
		self.base_url = base_url
		if not self.name:
			self.name = os.path.basename ( output_name ).split ( "." ) [ 0 ]

		self.items = []

	def add ( self, title, mode, url, data, headers, r ):
		it = PostmanExporterItem ( title, mode, url, data, self.base_url )
		self.items.append ( it )

	def save ( self ):
		res = { "info": { "name": self.name, "schema": self.schema }, "item": [] }
		for i in self.items:
			res [ 'item' ].append ( i.obj () )

		open ( self.output_name, "w" ).write ( json.dumps ( res, indent = 4 ) )



