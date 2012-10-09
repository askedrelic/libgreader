# -*- coding: utf-8 -*-

import time

try:
    import json
except:
    import simplejson as json

from url import ReaderUrl
from items import SpecialFeed, Item, Category, Feed

class GoogleReader(object):
    """
    Class for using the unofficial Google Reader API and working with
    the data it returns.

    Requires valid google username and password.
    """
    def __repr__(self):
        return "<Google Reader object: %s>" % self.auth.username

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "<Google Reader object: %s>" % self.auth.username

    def __init__(self, auth):
        self.auth           = auth
        self.feeds          = []
        self.categories     = []
        self.feedsById      = {}
        self.categoriesById = {}
        self.specialFeeds   = {}
        self.orphanFeeds    = []
        self.userId         = None

    def toJSON(self):
        """
        TODO: build a json object to return via ajax
        """
        pass

    def getFeeds(self):
        """
        @Deprecated, see getSubscriptionList
        """
        return self.feeds

    def getSubscriptionList(self):
        """
        Returns a list of Feed objects containing all of a users subscriptions
        or None if buildSubscriptionList has not been called, to get the Feeds
        """
        return self.feeds

    def getCategories(self):
        """
        Returns a list of all the categories or None if buildSubscriptionList
        has not been called, to get the Feeds
        """
        return self.categories

    def makeSpecialFeeds(self):
        for type in ReaderUrl.SPECIAL_FEEDS:
            self.specialFeeds[type] = SpecialFeed(self, type)

    def getSpecialFeed(self, type):
        return self.specialFeeds[type]

    def buildSubscriptionList(self):
        """
        Hits Google Reader for a users's alphabetically ordered list of feeds.

        Returns true if succesful.
        """
        self._clearLists()
        unreadById = {}

        if not self.userId:
            self.getUserInfo()

        unreadJson = self.httpGet(ReaderUrl.UNREAD_COUNT_URL, { 'output': 'json', })
        unreadCounts = json.loads(unreadJson, strict=False)['unreadcounts']
        for unread in unreadCounts:
            unreadById[unread['id']] = unread['count']

        feedsJson = self.httpGet(ReaderUrl.SUBSCRIPTION_LIST_URL, { 'output': 'json', })
        subscriptions = json.loads(feedsJson, strict=False)['subscriptions']

        for sub in subscriptions:
            categories = []
            if 'categories' in sub:
                for hCategory in sub['categories']:
                    cId = hCategory['id']
                    if not cId in self.categoriesById:
                        category = Category(self, hCategory['label'], cId)
                        self._addCategory(category)
                    categories.append(self.categoriesById[cId])

            try:
                feed = self.getFeed(sub['id'])
                if not feed:
                    raise
                if not feed.title:
                    feed.title = sub['title']
                for category in categories:
                    feed.addCategory(category)
                feed.unread = unreadById.get(sub['id'], 0)
            except:
                feed = Feed(self,
                            sub['title'],
                            sub['id'],
                            sub.get('htmlUrl', None),
                            unreadById.get(sub['id'], 0),
                            categories)
            if not categories:
                self.orphanFeeds.append(feed)
            self._addFeed(feed)

        specialUnreads = [id for id in unreadById
                            if id.find('user/%s/state/com.google/' % self.userId) != -1]
        for type in self.specialFeeds:
            feed = self.specialFeeds[type]
            feed.unread = 0
            for id in specialUnreads:
                if id.endswith('/%s' % type):
                    feed.unread = unreadById.get(id, 0)
                    break

        return True

    def _getFeedContent(self, url, excludeRead=False, continuation=None):
        """
        A list of items (from a feed, a category or from URLs made with SPECIAL_ITEMS_URL)

        Returns a dict with
         :param id: (str, feed's id)
         :param continuation: (str, to be used to fetch more items)
         :param items:  array of dits with :
            - update (update timestamp)
            - author (str, username)
            - title (str, page title)
            - id (str)
            - content (dict with content and direction)
            - categories (list of categories including states or ones provided by the feed owner)
        """
        parameters = {}
        if excludeRead:
            parameters['xt'] = 'user/-/state/com.google/read'
        if continuation:
            parameters['c'] = continuation
        contentJson = self.httpGet(url, parameters)
        return json.loads(contentJson, strict=False)

    def itemsToObjects(self, parent, items):
        objects = []
        for item in items:
            objects.append(Item(self, item, parent))
        return objects

    def getFeedContent(self, feed, excludeRead=False, continuation=None):
        """
        Return items for a particular feed
        """
        return self._getFeedContent(feed.fetchUrl, excludeRead, continuation)

    def getCategoryContent(self, category, excludeRead=False, continuation=None):
        """
        Return items for a particular category
        """
        return self._getFeedContent(category.fetchUrl, excludeRead, continuation)

    def removeItemTag(self, item, tag):
        return self.httpPost(ReaderUrl.EDIT_TAG_URL,
                             {'i': item.id, 'r': tag, 'ac': 'edit-tags', })

    def addItemTag(self, item, tag):
        return self.httpPost(
            ReaderUrl.EDIT_TAG_URL,
            {'i': item.id, 'a': tag, 'ac': 'edit-tags', })

    def markFeedAsRead(self, feed):
        return self.httpPost(
            ReaderUrl.MARK_ALL_READ_URL,
            {'s': feed.id, })

    def subscribe(self, feedUrl):
        """
        Adds a feed to the top-level subscription list

        Ubscribing seems idempotent, you can subscribe multiple times
        without error

        returns True or throws urllib2 HTTPError
        """
        response = self.httpPost(
            ReaderUrl.SUBSCRIPTION_EDIT_URL,
            {'ac':'subscribe', 's': feedUrl})
        # FIXME - need better return API
        if response and 'OK' in response:
            return True
        else:
            return False

    def unsubscribe(self, feedUrl):
        """
        Removes a feed url from the top-level subscription list

        Unsubscribing seems idempotent, you can unsubscribe multiple times
        without error

        returns True or throws urllib2 HTTPError
        """
        response = self.httpPost(
            ReaderUrl.SUBSCRIPTION_EDIT_URL,
            {'ac':'unsubscribe', 's': feedUrl})
        # FIXME - need better return API
        if response and 'OK' in response:
            return True
        else:
            return False

    def getUserInfo(self):
        """
        Returns a dictionary of user info that google stores.
        """
        userJson = self.httpGet(ReaderUrl.USER_INFO_URL)
        result = json.loads(userJson, strict=False)
        self.userId = result['userId']
        return result

    def getUserSignupDate(self):
        """
        Returns the human readable date of when the user signed up for google reader.
        """
        userinfo = self.getUserInfo()
        timestamp = int(float(userinfo["signupTimeSec"]))
        return time.strftime("%m/%d/%Y %H:%M", time.gmtime(timestamp))

    def httpGet(self, url, parameters=None):
        """
        Wrapper around AuthenticationMethod get()
        """
        return self.auth.get(url, parameters)

    def httpPost(self, url, post_parameters=None):
        """
        Wrapper around AuthenticationMethod post()
        """
        return self.auth.post(url, post_parameters)

    def _addFeed(self, feed):
        if feed.id not in self.feedsById:
            self.feedsById[feed.id] = feed
            self.feeds.append(feed)

    def _addCategory (self, category):
        if category.id not in self.categoriesById:
            self.categoriesById[category.id] = category
            self.categories.append(category)

    def getFeed(self, id):
        return self.feedsById.get(id, None)

    def getCategory(self, id):
        return self.categoriesById.get(id, None)

    def _clearLists(self):
        """
        Clear all list before sync : feeds and categories
        """
        self.feedsById      = {}
        self.feeds          = []
        self.categoriesById = {}
        self.categories     = []
        self.orphanFeeds    = []
