""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import os
import re
import urllib2


class Crawler(object):

    def crawl(self, url):
        rss_url = self.auto_descovery(url)
        request = urllib2.Request(url)
        f = urllib2.urlopen(request)
        print f.read()
        f.close()

    def auto_discovery(self, url):
        """If given url is rss feed url, it returns the url instantly.
        If given url is a url of web page, It find the site's RSS feed url
        and return it
        """
        request = urllib2.Request(url)
        f = urllib2.urlopen(request)
        if f.info().type == 'text/xml':
            f.close()
            return url
        else:
            html = f.read()
            f.close()
            rss_url_dump = re.search(
                '<link\s.+?type=\"application/rss\+xml\"[^>]+',
                html)
            rss_url = re.search('(href=\")(http://[^\"]+)',
                                rss_url_dump.group(0)).group(2)
            return rss_url
