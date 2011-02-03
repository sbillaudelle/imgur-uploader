#!/usr/bin/python

IMGUR_UPLOAD_URL = 'http://imgur.com/api/upload.json'

import urllib2
from urllib import urlencode
import base64
import json

class Imgur(object):
    
    def __init__(self, api_key):
        
        self.api_key = api_key


    def upload(self, path):

        image = open(path, 'rb').read()

        data = {
            'key': self.api_key,
            'image': base64.b64encode(image),
            'path': path
            }

        request = urllib2.Request(IMGUR_UPLOAD_URL, urlencode(data))
        u = urllib2.urlopen(request)
        data = json.loads(u.read())
        
        return data
