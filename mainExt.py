#!/usr/bin/env python
###
### This web service is used in conjunction with App
### Inventor for Android. It stores and retrieves data as instructed by an App Inventor app and its TinyWebDB component.
### It also provides a web interface to the database for administration

### Author: Dave Wolber via template of Hal Abelson and incorporating changes of Dean Sanvitale

### Note-- updated for use with Python2.7 in App Engine, June 2013

import webapp2
import base64
import logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.db import Key
from google.appengine.api import files
from google.appengine.api import images
from google.appengine.ext import blobstore
from django.utils import simplejson as json

# DWW
import os
from google.appengine.ext.webapp import template
import urllib

# DEAN
import logging
import re

max_entries = 1000

class StoredData(db.Model):
  tag = db.StringProperty()
  value = db.TextProperty()
  date = db.DateTimeProperty(required=True, auto_now=True)
class StoredPicture(db.Model):
	tag = db.StringProperty()
	picture = db.BlobProperty()
	extension = db.StringProperty()
	value = db.TextProperty()
	date = db.DateTimeProperty(required=True, auto_now=True)

	def url_for(self):
		return "/image/%d" % self.key().id()

class StoreAValue(webapp2.RequestHandler):

  def store_a_value(self, tag, value):
	store(tag, value)
	# call trimdb if you want to limit the size of db
	# trimdb()
	
	## Send back a confirmation message.  The TinyWebDB component ignores
	## the message (other than to note that it was received), but other
	## components might use this.
	result = ["STORED", tag, value]
	
	## When I first implemented this, I used  json.JSONEncoder().encode(value)
	## rather than json.dump.  That didn't work: the component ended up
	## seeing extra quotation marks.  Maybe someone can explain this to me.
	
	if self.request.get('fmt') == "html":
		WriteToWeb(self,tag,value)
	else:
		WriteToPhoneAfterStore(self,tag,value)
	

  def post(self):
	tag = self.request.get('tag')
	value = self.request.get('value')
	self.store_a_value(tag, value)

class StoreAPicture(webapp2.RequestHandler):

  def store_a_picture(self, tag, picture, val, extension):
	storePic(tag, picture, val, extension)
	# call trimdb if you want to limit the size of db
	# trimdb()
	
	## Send back a confirmation message.  The TinyWebDB component ignores
	## the message (other than to note that it was received), but other
	## components might use this.
	result = ["STORED", tag, val]
	
	## When I first implemented this, I used  json.JSONEncoder().encode(picture)
	## rather than json.dump.  That didn't work: the component ended up
	## seeing extra quotation marks.  Maybe someone can explain this to me.
	entry = db.GqlQuery("SELECT * FROM StoredPicture where tag = :1", tag).get()
	if self.request.get('fmt') == "html":
		WritePicToWeb(self,entry)
	else:
		WritePicToPhoneAfterStore(self,entry)
	

  def post(self):
	tag = self.request.get('tag')
	picture = self.request.get('pic')
	logging.info(self.request)
	extension = self.request.get('ext')
	logging.info(extension)
	if self.request.get('fmt') == "html":
		encoded = picture.encode("base64")
	else:
		encoded = picture
	encoded=encoded.replace('\\n','')
	encoded=encoded.replace('\\','')
	encoded=encoded.replace(' ','')	
	encoded=encoded.replace('\"','')
	encoded += "=" * ((4 - len(encoded) % 4) % 4)
	logging.info('image after padding %s', encoded)
	try:
		decoded = base64.b64decode(encoded[:-2])
	except Exception:
		decoded=encoded

	logging.info('image after decoding %s', decoded)		
	self.store_a_picture(tag,decoded, encoded, extension)     
class DeleteEntry(webapp2.RequestHandler):

  def post(self):
	logging.info('/deleteentry?%s\n|%s|' %
				  (self.request.query_string, self.request.body))
	entry_key_string = self.request.get('entry_key_string')
	key = db.Key(entry_key_string)
	tag = self.request.get('tag')
	if tag.startswith("http"):
	  DeleteUrl(tag)
	db.run_in_transaction(dbSafeDelete,key)
	self.redirect('/')


class GetValueHandler(webapp2.RequestHandler):

  def get_value(self, tag):
	entry = db.GqlQuery("SELECT * FROM StoredData where tag = :1", tag).get()
	if entry:
	   value = entry.value
	else: value = ""

	if self.request.get('fmt') == "html":
		WriteToWeb(self,tag,value)
	else:
		WriteToPhone(self,tag,value)

  def post(self):
	tag = self.request.get('tag')
	self.get_value(tag)

  # there is a web ui for this as well, here is the get
  def get(self):
	# this did pump out the form
	template_values={}
	path = os.path.join(os.path.dirname(__file__),'index.html')
	self.response.out.write(template.render(path,template_values))

class GetPictureHandler(webapp2.RequestHandler):

  def get_picture(self, tag):
	entry = db.GqlQuery("SELECT * FROM StoredPicture where tag = :1", tag).get()
	if entry:
	   picture = entry.picture
	else: picture = ""
	if self.request.get('fmt') == "html":
		WritePicToWeb(self, entry)
	else:
		WritePicToPhone(self, entry)

  def post(self):
	tag = self.request.get('tag')
	self.get_picture(tag)

  # there is a web ui for this as well, here is the get
  def get(self):
	# this did pump out the form
	template_values={}
	path = os.path.join(os.path.dirname(__file__),'index.html')
	self.response.out.write(template.render(path,template_values))

class MainPage(webapp2.RequestHandler):

  def get(self):
	entries = db.GqlQuery("SELECT * FROM StoredData ORDER BY date desc")
	picEntries = db.GqlQuery("SELECT * FROM StoredPicture ORDER BY date desc")
	template_values = {"entryList":entries, "picEntryList":picEntries}
	# render the page using the template engine
	path = os.path.join(os.path.dirname(__file__),'index.html')
	self.response.out.write(template.render(path,template_values))

#### Utilty procedures for generating the output

def WriteToPhone(handler,tag,value):
 
	handler.response.headers['Content-Type'] = 'application/jsonrequest'
	json.dump(["VALUE", tag, value], handler.response.out)

def WriteToWeb(handler, tag,value):
	entries = db.GqlQuery("SELECT * FROM StoredData ORDER BY date desc")
	picEntries = db.GqlQuery("SELECT * FROM StoredPicture ORDER BY date desc")

	template_values={"result":  value,"entryList":entries, "picEntryList":picEntries}  
	path = os.path.join(os.path.dirname(__file__),'index.html')
	handler.response.out.write(template.render(path,template_values))

def WriteToPhoneAfterStore(handler,tag, value):
	handler.response.headers['Content-Type'] = 'application/jsonrequest'
	json.dump(["STORED", tag, value], handler.response.out)

def WritePicToWeb(handler, entry):
	entries = db.GqlQuery("SELECT * FROM StoredData ORDER BY date desc")
	picEntries = db.GqlQuery("SELECT * FROM StoredPicture ORDER BY date desc")
	template_values={"resultPic":  entry,"entryList":entries, "picEntryList":picEntries}  
	path = os.path.join(os.path.dirname(__file__),'index.html')
	handler.response.out.write(template.render(path,template_values))

def WritePicToPhone(handler, entry):
	handler.response.headers['Content-Type'] = 'application/jsonrequest'
	
	logging.info(entry.tag);
	logging.info(entry.value);
	logging.info(entry.extension);
	json.dump(["PICTURE", entry.tag, entry.value, entry.extension], handler.response.out)


def WritePicToPhoneAfterStore(handler, entry):
	handler.response.headers['Content-Type'] = 'application/jsonrequest'
	json.dump(["STORED", entry.tag, entry.value, entry.extension], handler.response.out)


# db utilities from Dean

### A utility that guards against attempts to delete a non-existent object
def dbSafeDelete(key):
  if db.get(key) :	db.delete(key)
  
def store(tag, value, bCheckIfTagExists=True):
	if bCheckIfTagExists:
		# There's a potential readers/writers error here :(
		entry = db.GqlQuery("SELECT * FROM StoredData where tag = :1", tag).get()
		if entry:
		  entry.value = value
		else: entry = StoredData(tag = tag, value = value)
	else:
		entry = StoredData(tag = tag, value = value)
	entry.put()		
	

def storePic(tag, picture, value, extension,  bCheckIfTagExists=True):
	if bCheckIfTagExists:
		# There's a potential readers/writers error here :(
		entry = db.GqlQuery("SELECT * FROM StoredPicture where tag = :1", tag).get()
		if entry:
		  entry.value = value
		  entry.extension = extension
		else: entry = StoredPicture(tag = tag , value = value, extension = extension)
	else:
		entry = StoredPicture(tag = tag,  value = value, extension = extension)
	entry.put()	
def trimdb():
	## If there are more than the max number of entries, flush the
	## earliest entries.
	entries = db.GqlQuery("SELECT * FROM StoredData ORDER BY date")
	if (entries.count() > max_entries):
		for i in range(entries.count() - max_entries): 
			db.delete(entries.get())

from htmlentitydefs import name2codepoint 
def replace_entities(match):
	try:
		ent = match.group(1)
		if ent[0] == "#":
			if ent[1] == 'x' or ent[1] == 'X':
				return unichr(int(ent[2:], 16))
			else:
				return unichr(int(ent[1:], 10))
		return unichr(name2codepoint[ent])
	except:
		return match.group()

entity_re = re.compile(r'&(#?[A-Za-z0-9]+?);')

def html_unescape(data):
	return entity_re.sub(replace_entities, data)
	
def ProcessNode(node, sPath):
	entries = []
	if node.nodeType == minidom.Node.ELEMENT_NODE:
		value = ""
		for childNode in node.childNodes:
			if (childNode.nodeType == minidom.Node.TEXT_NODE) or (childNode.nodeType == minidom.Node.CDATA_SECTION_NODE):
				value += childNode.nodeValue

		value = value.strip()
		value = html_unescape(value)
		if len(value) > 0:
			entries.append(StoredData(tag = sPath, value = value))
		for attr in node.attributes.values():
			if len(attr.value.strip()) > 0:
				entries.append(StoredData(tag = sPath + ">" + attr.name, value = attr.value))
		
		childCounts = {}
		for childNode in node.childNodes:
			if childNode.nodeType == minidom.Node.ELEMENT_NODE:
				sTag = childNode.tagName
				try:
					childCounts[sTag] = childCounts[sTag] + 1
				except:
					childCounts[sTag] = 1
				if (childCounts[sTag] <= 5):
					entries.extend(ProcessNode(childNode, sPath + ">" + sTag + str(childCounts[sTag])))
		return entries
		
def DeleteUrl(sUrl):
	entries = StoredData.all().filter('tag >=', sUrl).filter('tag <', sUrl + u'\ufffd')
	db.delete(entries[:500])
  
class ImageHandler(webapp2.RequestHandler):
	def get(self, image_id):
		temp_key = db.Key.from_path('StoredPicture', image_id)
		requestedImage = StoredPicture.get_by_id(int(image_id))
		if requestedImage is not None:
			self.response.headers['Content-Type'] = 'image/jpeg'
			self.response.out.write(requestedImage.picture)
### Assign the classes to the URL's

app = webapp2.WSGIApplication ([('/', MainPage),
						   ('/getvalue', GetValueHandler),('/image/(\d+)', ImageHandler), 
			   ('/storeavalue', StoreAValue), ('/getpicture', GetPictureHandler),
				   ('/deleteentry', DeleteEntry),  ('/storeapicture',StoreAPicture)

						   ])



