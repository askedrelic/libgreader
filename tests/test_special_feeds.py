#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for feeds.
"""

try:
    import unittest2 as unittest
except:
    import unittest

from libgreader import GoogleReader, OAuthMethod, ClientAuthMethod, Feed, ItemsContainer, Item, BaseFeed, SpecialFeed, ReaderUrl
import re
import time

from .config import *

class TestSpecialFeeds(unittest.TestCase):
    def test_reading_list_exists(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        reader.makeSpecialFeeds()
        feeds = reader.getFeedContent(reader.getSpecialFeed(ReaderUrl.READING_LIST))

        self.assertEqual(dict, type(feeds))

        list_match = re.search('reading list in Google Reader', feeds['title'])
        self.assertTrue(list_match)

    def test_marking_read(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems()

        feed_item = container.items[0]
        self.assertTrue(feed_item.markRead())
        self.assertTrue(feed_item.isRead())

    def test_loading_item_count(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems(loadLimit=5)

        self.assertEqual(5, len(container.items))
        self.assertEqual(5, container.countItems())

    def test_subscribe_unsubscribe(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        
        slashdot = 'feed/http://rss.slashdot.org/Slashdot/slashdot'

        #unsubscribe always return true; revert feedlist state
        self.assertTrue(reader.unsubscribe(slashdot))

        # now subscribe
        self.assertTrue(reader.subscribe(slashdot))

        # wait for server to update
        time.sleep(1)
        reader.buildSubscriptionList()

        # test subscribe successful
        self.assertIn(slashdot, [x.id for x in reader.getSubscriptionList()])

    def test_add_remove_single_feed_tag(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems()

        tag_name = 'test-single-tag'
        feed_1 = container.items[0]

        # assert tag doesn't exist yet
        self.assertFalse(any([tag_name in x for x in feed_1.data['categories']]))

        # add tag
        reader.addItemTag(feed_1, 'user/-/label/' + tag_name)

        #reload now
        container.clearItems()
        container.loadItems()
        feed_2 = container.items[0]

        # assert tag is in new
        self.assertTrue(any([tag_name in x for x in feed_2.data['categories']]))

        # remove tag
        reader.removeItemTag(feed_2, 'user/-/label/' + tag_name)

        #reload now
        container.clearItems()
        container.loadItems()
        feed_3 = container.items[0]

        # assert tag is removed
        self.assertFalse(any([tag_name in x for x in feed_3.data['categories']]))

    def test_transaction_add_feed_tags(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems()

        tags = ['test-transaction%s' % x for x in range(5)]
        feed_1 = container.items[0]

        reader.beginAddItemTagTransaction()
        for tag in tags:
            reader.addItemTag(feed_1, 'user/-/label/' + tag)
        reader.commitAddItemTagTransaction()

        #reload now
        container.clearItems()
        container.loadItems()
        feed_2 = container.items[0]

        # figure out if all tags were returned
        tags_exist = [any(map(lambda tag: tag in x, tags)) for x in feed_2.data['categories']]
        tag_exist_count = sum([1 for x in tags_exist if x])
        self.assertEqual(5, tag_exist_count)

if __name__ == '__main__':
    unittest.main()
