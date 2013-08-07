""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import os
import re
import urllib2

from .compat import string_type


class Crawler(object):
    
    document_rss_url = None
    document_type = None
    document_xml = None

    def __init__(self, url):
        if not isinstance(url, string_type):
            raise TypeError(
                '__tag__ has to be a string, not ' + repr(url)
            )
        self.document_rss_url = self.auto_discovery(url)
        self.document_type = self.get_document_type()
        self.document_xml = self.crawl()

    def reset(self, url):
        if not isinstance(url, string_type):
            raise TypeError(
                '__tag__ has to be a string, not ' + repr(url)
            )
        self.document_rss_url = self.auto_discovery(url)
        self.document_type = self.get_document_type() 
        self.document_xml = self.crawl()

    def crawl(self):
        request = urllib2.Request(self.document_rss_url)
        f = urllib2.urlopen(request)
        xml = f.read()
        return xml

    def auto_discovery(self, url):
        """If given url is rss feed url, it returns the url instantly.
        If given url is a url of web page, It find the site's RSS feed url
        and return it
        """
        request = urllib2.Request(url)
        f = urllib2.urlopen(request)
        if f.info().type in ('text/xml', 
                             'application/xml',
                             'application/atom+xml'):
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

    def get_document_type(self):
        request = urllib2.Request(self.document_rss_url)
        f = urllib2.urlopen(request)
        if f.info().type in ('text/xml', 'application/xml'):
            return 'RSS'
        elif f.info().type == 'application/atom+xml':
            return 'Atom'
