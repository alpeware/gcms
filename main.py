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
        posts = memcache.get('posts')
        if posts is None:
            start_caching()
            self.response.write('No posts found. Please try again.')
            return
        self.response.write('<html><body><h1>Posts</h1>')
        for post in posts:
            slug = post['name']
            file_id = post['id']
            created = post['createdTime']
            modified = post['modifiedTime']
            title = memcache.get('title_' + file_id)
            tags = memcache.get('tags_' + file_id)
            self.response.write("""
            <p><a href='/%s'>%s</a></p>
            <p><small>Created: %s</small></p>
            <p><small>Modified: %s</small></p>
            <p><small>Tags: %s</small></p>
            <hr>
            """ % (slug, title, created, modified, ', '.join(tags)))
        self.response.write('</body></html>')

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

class CacheHandler(webapp2.RequestHandler):
    def get(self):
        start_caching()

app = webapp2.WSGIApplication([
    (r'/', MainHandler),
    (r'/(.*)', PostHandler),
    ('/cache', CacheHandler)
], debug=True)
