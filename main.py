"""
GCMS

(c) 2017 Alpeware LLC
"""
import re
import string
import logging
import webapp2

from common import enqueue_post, start_caching 
from google.appengine.api import memcache
from oauth2client.client import GoogleCredentials

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        file_id = memcache.get('0-landing-page')
        if file_id is None:
            self.response.write('Landing page not found.')
            return
        page = memcache.get(file_id)
        if page is None:
            enqueue_post(file_id)
            self.response.write('Cache miss. Please try again.')
            return
        self.response.write(page)


class PostHandler(webapp2.RequestHandler):
    def get(self, slug):
        self.response.headers['Content-Type'] = 'text/html'
        file_id = memcache.get(slug)
        if file_id is None:
            self.response.write('Post not found.')
            return

        page = memcache.get(file_id)
        title = memcache.get('title_' + file_id)
        tags = memcache.get('tags_' + file_id)
        if page is None:
            enqueue_post(file_id)
            self.response.write('Cache miss. Please try again.')
            return

        self.response.write(page)


app = webapp2.WSGIApplication([
    (r'/', MainHandler),
    (r'/(.*)', PostHandler)
], debug=True)
