"""
GCMS

(c) 2017 Alpeware LLC
"""
import logging
import re
import string
from google.appengine.api import taskqueue
from google.appengine.api import memcache

TAGS_RE = re.compile('(<p[^>]+>)<span([^>]+)>[Tt]ags:([^<]+)</span></p>')
TITLE_RE = re.compile('<p class="title"([^>]+)><span([^>]+)>([^<]+)')
COMMENTS_RE = re.compile('(<div\sstyle="border:1px[^"]+">)')
IMAGES_RE = re.compile('(<span[^>]+><img[^>]+></span>)')
HEAD_RE = '</head>'
BODY_RE = '<body\s(style="background-color:[^;]+;)[^>]+>'

VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'
CUSTOM_CSS = '<style>img { width: 100% }</style>';

DISQUS_SCRIPT = """
<div id="disqus_thread"></div>
<script>
var disqus_config = function () {
  this.page.url = 'https://www.alpeware.com/%s';
  this.page.identifier = '/%s';
};
(function() { // DON'T EDIT BELOW THIS LINE
var d = document, s = d.createElement('script');
s.src = 'https://www-alpeware-com.disqus.com/embed.js';
s.setAttribute('data-timestamp', +new Date());
(d.head || d.body).appendChild(s);
})();
</script>
<noscript>Please enable JavaScript to view the <a href="https://disqus.com/?ref_noscript">comments powered by Disqus.</a></noscript>
"""

ANALYTICS_SCRIPT = """
<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-91886762-1', 'auto');
  ga('send', 'pageview');

</script>
"""

ADSENSE_SCRIPT = """
<script async src="//pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>
<!-- Alpeware -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-6123540793627831"
     data-ad-slot="8549779304"
     data-ad-format="auto"></ins>
<script>
(adsbygoogle = window.adsbygoogle || []).push({});
</script>
"""

POST_TMPL_RE = re.compile('<p[^>]*><span[^>]*>//--\+ Post</span></p>(.*)<p[^>]*><span[^>]*>Post \+--//</span></p>')

def make_resp(match):
    s = match.group(0)
    s = string.replace(s, 'display: inline-block;', '')
    s = string.replace(s, 'width:', 'max-width:')
    s = string.replace(s, 'height:', 'max-height:')
    return s

def parse_landing_page(html, posts):
    title_tag = '<title>' + 'Alpeware' + '</title>'
    fixed_head = re.sub(HEAD_RE, title_tag + VIEWPORT + CUSTOM_CSS + HEAD_RE, html)
    html = re.sub(BODY_RE, r'<body style="background-color:#f3f3f3;"><div \1max-width:80%;margin-left:auto;margin-right:auto;margin-top:10px;padding:20px;">', fixed_head)
    html = re.sub(IMAGES_RE, make_resp, html)
    html = re.sub('</body>', ANALYTICS_SCRIPT + '</body>', html)
    logging.info('processing landing page')
    post_tmpl = ''
    post_section = ''
    tmpl_match = re.search(POST_TMPL_RE, html)
    if tmpl_match:
        post_tmpl = tmpl_match.group(1)
        post_tmpl = string.replace(post_tmpl, '{post.name}', "<a href='{post.name}'>{post.title}</a>")
        for post in posts:
            logging.info(post['name'])
            if '0-landing-page' not in post['name']:
                p = post_tmpl
                file_id = post['id']
                title = memcache.get('title_' + file_id)
                # logging.info(title)
                post['title'] = title
                # logging.info(post)
                for k in post.keys():
                    if isinstance(post[k], basestring):
                        p = string.replace(p, ("{post.%s}" % k), post[k])
                post_section += p
        with_section = re.sub(POST_TMPL_RE, post_section, html)
        return with_section
    return html


def fix_page(html, slug):
    title = 'Blog'
    tags = []
    tags_links = ''

    tags_match = re.search(TAGS_RE, html)
    if tags_match:
        tags = [i.strip() for i in tags_match.group(3).split(',')]
        tags_links = tags_match.group(1) + 'Tags: ' + ', '.join(["<a href='/tags/%s'>%s</a>" % (i, i) for i in tags]) + '</p>'
    no_tags = re.sub(TAGS_RE, tags_links, html)

    title_match = re.search(TITLE_RE, no_tags)
    if title_match:
        title = title_match.group(3)
    title_tag = '<title>' + title + '</title>'

    resp_imgs = re.sub(IMAGES_RE, make_resp, no_tags)

    def style_comms(match):
        s = match.group(0)
        s = string.replace(s, 'border:1px', '')
        return s
    styled_comms = re.sub(COMMENTS_RE, style_comms, resp_imgs)

    add_comments = re.sub('</body>', ADSENSE_SCRIPT + ANALYTICS_SCRIPT + (DISQUS_SCRIPT % (slug, slug)) + '</body>', styled_comms)

    fixed_head = re.sub(HEAD_RE, title_tag + VIEWPORT + CUSTOM_CSS + HEAD_RE, add_comments)

    fixed_body = re.sub(BODY_RE, r'<body style="background-color:#f3f3f3;"><div \1max-width:80%;margin-left:auto;margin-right:auto;margin-top:10px;padding:20px;">', fixed_head)

    return (title, tags, fixed_body)

def enqueue_post(file_id):
    queue = taskqueue.Queue(name='post-queue')
    task = taskqueue.Task(
        url='/worker/post',
        target='worker',
        params={'file_id': file_id})
    rpc = queue.add_async(task)
    task = rpc.get_result()

def start_caching():
    queue = taskqueue.Queue(name='index-queue')
    task = taskqueue.Task(
        url='/worker/index',
        target='worker')
    rpc = queue.add_async(task)
    task = rpc.get_result()
