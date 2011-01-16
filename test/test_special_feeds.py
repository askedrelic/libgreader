#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for feeds. Requires mechanize for automated oauth authenication.

"""

import unittest

from libgreader import GoogleReader, OAuthMethod, ClientAuth, Feed
import urllib
import urllib2
import urlparse
import mechanize
import re

#ClientAuth
#User account I created for testing
username = 'relic@asktherelic.com'
password = 'testtest'

class TestSpecialFeeds(unittest.TestCase):
    def test_reading_list_exists(self):
        ca = ClientAuth(username,password)
        reader = GoogleReader(ca)
        reader.makeSpecialFeeds()
        feeds = reader.getFeedContent(reader.getSpecialFeed(reader.READING_LIST))

        self.assertEqual(dict, type(feeds))

        list_match = re.search('reading list in Google Reader', feeds['title'])
        self.assertTrue(list_match)

if __name__ == '__main__':
    unittest.main()
