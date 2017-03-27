"""
GCMS

(c) 2017 Alpeware LLC
"""
import logging
import webapp2

from common import fix_page, enqueue_post, start_caching, parse_landing_page

from apiclient import discovery
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from oauth2client.client import GoogleCredentials

def get_credentials():
    credentials = GoogleCredentials.get_application_default()
    return credentials

def get_service():
    service = discovery.build('drive', 'v3', credentials=get_credentials())
    return service

def get_files(service=None):
    results = service.files().list(
            fields='nextPageToken, files', q='mimeType = "application/vnd.google-apps.document"').execute()
    files = results.get('files', [])
    print "Found %d files" % len(files)
    return files 

def get_comments(service=None, file_id=None):
    results = service.comments().list(fileId=file_id, fields='comments').execute()
    comments = results.get('comments', [])
    return comments

def get_file_content(service=None, file_id=None):
    content = service.files().export(fileId=file_id, mimeType='text/html').execute()
    return content 

def sort_posts(e):
    return int(e['name'].split('-')[0])

class UpdateIndexHandler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        self.service = get_service()

    def post(self):
        logging.debug('fetching files')
        files = get_files(self.service)
        posts = []
        for f in files:
            # logging.info(f)
            posts.append(f)
            file_id = f['id']
            # add slug mapping
            memcache.set(f['name'], file_id)
            memcache.set('slug_' + file_id, f['name'])
            enqueue_post(file_id)
        posts.sort(key=sort_posts)
        posts = list(reversed(posts))
        memcache.set('posts', posts)

class UpdatePostHandler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        self.service = get_service()

    def landing_page(self, file_id, content):
        posts = memcache.get('posts')
        page = parse_landing_page(content, posts)
        memcache.set(file_id, page)

    def blog_post(self, file_id, content, slug):
        (title, tags, page) = fix_page(content, slug)
        # There's ~30sec delay for new docs :(
	if len(page) > 0:
	    memcache.set(file_id, page) 
	    memcache.set('title_' + file_id, title) 
	    memcache.set('tags_' + file_id, tags) 
        else:
            enqueue_post(file_id)

    def post(self):
        file_id = self.request.get('file_id')
        slug = memcache.get('slug_' + file_id)
        logging.info('found slug: %s', slug)
        content = get_file_content(self.service, file_id)
        if '0-landing-page' in slug:
            logging.info('found landing page')
            self.landing_page(file_id, content)
        else:
            self.blog_post(file_id, content, slug)


class RefreshPostsHandler(webapp2.RequestHandler):
    def get(self):
	logging.info('refreshing cache')
	start_caching()


app = webapp2.WSGIApplication([
    ('/worker/index', UpdateIndexHandler),
    ('/worker/post', UpdatePostHandler),
    ('/worker/refresh', RefreshPostsHandler)
], debug=True)
