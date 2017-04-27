"""
GCMS

(c) 2017 Alpeware LLC
"""
import logging

from google.appengine.ext import ndb

class Page(ndb.Model):
    """Models an individual page."""
    file_id = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()
    slug = ndb.StringProperty()
    title = ndb.StringProperty()
    content = ndb.TextProperty()
    tags = ndb.StringProperty(repeated=True)

    @classmethod
    def query_by_tag(self, tag):
        return self.query(self.tags == tag)

    @classmethod
    def query_by_file_id(self, file_id):
        return self.query(self.file_id == file_id)

    @classmethod
    def query_by_slug(self, slug):
        return self.query(self.slug == slug)

