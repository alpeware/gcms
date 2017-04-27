"""
GCMS

(c) 2017 Alpeware LLC
"""
import logging
import webapp2
from datetime import datetime

from common import fix_page, enqueue_post, start_caching, parse_landing_page
from models import Page

from apiclient import discovery
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from oauth2client.client import GoogleCredentials

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

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

def upsert_page(page):
    key = Page.query_by_file_id(page.file_id).get(keys_only=True)
    # remove empty items
    page_dict = dict((k,v) for k,v in page.to_dict().iteritems() if v is not None)
    logging.debug('key %s', key)
    logging.debug('page %s', page_dict)

    @ndb.transactional
    def update(page, key, page_dict):
        entity = page
        if key:
            entity = key.get()
        entity.populate(**page_dict)
        entity.put()

    update(page, key, page_dict)


class UpdateIndexHandler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        self.service = get_service()

    def post(self):
        logging.debug('fetching files')
        files = get_files(self.service)
        for f in files:
            # logging.info(f)
            file_id = f['id']
            slug = f['name']
            created_at = datetime.strptime(f['createdTime'], ISO_FORMAT)
            logging.debug('created at %s %s', created_at, f['createdTime'])
            upsert_page(Page(file_id=file_id, slug=slug, created_at=created_at))
            enqueue_post(file_id)

class UpdatePostHandler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        self.service = get_service()

    def landing_page(self, file_id, content, slug):
        pages = Page.query().order(-Page.created_at).fetch()
        (title, tags, html) = parse_landing_page(content, pages)
        upsert_page(Page(file_id=file_id, slug=slug, title=title, tags=tags, content=html))

    def blog_post(self, file_id, content, slug):
        (title, tags, html) = fix_page(content, slug)
        # There's ~30sec delay for new docs :(
	if len(html) > 0:
            upsert_page(Page(file_id=file_id, slug=slug, title=title, tags=tags, content=html))
        else:
            enqueue_post(file_id)

    def post(self):
        file_id = self.request.get('file_id')
        page = Page.query_by_file_id(file_id).get()
        slug = page.slug
        content = get_file_content(self.service, file_id)
        if '0-landing-page' in slug:
            logging.debug('found landing page')
            self.landing_page(file_id, content, slug)
        elif not slug.startswith('0-'):
            self.blog_post(file_id, content, slug)
        else:
            # should match 0-tags-page
            upsert_page(Page(file_id=file_id, slug=slug, content=content))


class RefreshPostsHandler(webapp2.RequestHandler):
    def get(self):
        logging.debug('refreshing cache')
        start_caching()


app = webapp2.WSGIApplication([
    ('/worker/index', UpdateIndexHandler),
    ('/worker/post', UpdatePostHandler),
    ('/worker/refresh', RefreshPostsHandler)
], debug=True)
