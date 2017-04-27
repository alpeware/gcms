"""
GCMS

(c) 2017 Alpeware LLC
"""
import re
import string
import logging
import webapp2

from common import enqueue_post, start_caching, parse_landing_page
from models import Page
from google.appengine.api import memcache
from oauth2client.client import GoogleCredentials

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        page = Page.query_by_slug('0-landing-page').get()
        if page is None:
            self.response.write('Landing page not found. Please try again.')
            start_caching()
            return
        return self.response.write(page.content)


class PostHandler(webapp2.RequestHandler):
    def get(self, slug):
        self.response.headers['Content-Type'] = 'text/html'
        page = Page.query_by_slug(slug).get()
        if page is None:
            self.response.write('Post not found.')
            return
        self.response.write(page.content)


class TagHandler(webapp2.RequestHandler):
    def get(self, tag):
        self.response.headers['Content-Type'] = 'text/html'
        pages = Page.query_by_tag(tag).fetch()
        tag_page = Page.query_by_slug('0-tags-page').get()
        if not pages or not tag_page:
            self.response.write('Tag not found.')
            return
        (title, tags, html) = parse_landing_page(tag_page.content, pages)
        self.response.write(html)


app = webapp2.WSGIApplication([
    (r'/', MainHandler),
    (r'/tags/(.*)', TagHandler),
    (r'/(.*)', PostHandler)
], debug=True)
