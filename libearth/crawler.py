""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

import re
import os
import urllib2


class Crawler(object):

    def crawl(self, url):
        request = urllib2.Request(url)
        f = urllib2.urlopen(request)
        if not f.info().type == "text/xml":
            rss_url = self.auto_discovery(f)
            request = urllib2.Request(rss_url)
            f = urllib2.urlopen(request)
        print f.read()

    def auto_discovery(self, f):
        html = f.read()
        f.close()
        rss_url_dump = re.search("link.+?type=\"application/rss\+xml\"[^>]+",
                                 html)
        rss_url = re.search("(href=\")(http://[^\"]+)",
                            rss_url_dump.group(0)).group(2)
        return rss_url
