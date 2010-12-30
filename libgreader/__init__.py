#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.
Google may break this at anytime, I am not responsible for damages from that
breakage, but I will try my best to fix it.

Uses HTTPS for all requests to and from Google.

Licensing included in LICENSE.txt
"""

__author__  = "Matt Behrens <askedrelic@gmail.com>"
__version__ = "0.4"
__credits__ = "Matt Behrens <askedrelic@gmail.com>, Stephane Angel aka Twidi <s.angel@twidi.com>"

import sys
import urllib
import urllib2
import urlparse
import time

try:
    import json
except:
    import simplejson as json
try:
    import oauth2 as oauth
    has_oauth = True
except:
    has_oauth = False

#Reset due to ascii/utf-8 problems with internet data
reload(sys)
sys.setdefaultencoding("utf-8")

def urlquote(string):
    """Encode a string to utf-8 and encode it for urllib"""
    return urllib.quote(string.encode("utf-8"))

class ItemsContainer(object):
    """
    A base class used for all classes aimed to have items (Categories and Feeds)
    """
    def __init__(self):
        self.items          = []
        self.itemsById      = {}
        self.lastLoadOk     = False
        self.lastLoadLength = 0
        self.lastUpdated    = None
        self.unread         = 0
        self.continuation   = None

    def _getContent(self, excludeRead=False, continuation=None):
        """
        Get content from google reader with specified parameters.
        Must be overladed in inherited clases
        """
        return None

    def loadItems(self, excludeRead=False):
        """
        Load items and call itemsLoadedDone to transform data in objects
        """
        self.clearItems()
        self.loadtLoadOk    = False
        self.lastLoadLength = 0
        self._itemsLoadedDone(self._getContent(excludeRead, None))

    def loadMoreItems(self, excludeRead=False, continuation=None):
        """
        Load more items using the continuation parameters of previously loaded items.
        """
        self.lastLoadOk     = False
        self.lastLoadLength = 0
        if not continuation and not self.continuation:
            return
        self._itemsLoadedDone(self._getContent(excludeRead, continuation or self.continuation))

    def _itemsLoadedDone(self, data):
        """
        Called when all items are loaded
        """
        if data is None:
            return
        self.continuation = data.get('continuation', None)
        self.lastUpdated  = data.get('updated', None)
        self.lastLoadLength = len(data.get('items', []))
        self.googleReader.itemsToObjects(self, data.get('items', []))
        self.lastLoadOk = True

    def _addItem(self, item):
        self.items.append(item)
        self.itemsById[item.id] = item

    def getItem(self, id):
        return self.itemsById[id]

    def clearItems(self):
        self.items        = []
        self.itemsById    = {}
        self.continuation = None

    def getItems(self):
        return self.items

    def countItems(self, excludeRead=False):
        if excludeRead:
            sum([1 for item in self.items if item.isUnread()])
        else:
            return len(self.items)

    def markItemRead(self, item, read):
        if read and item.isUnread():
            self.unread -= 1
        elif not read and item.isRead():
            self.unread += 1

    def markAllRead(self):
        self.unread = 0
        for item in self.items:
            item.read = True
            item.canUnread = False
        result = self.googleReader.markFeedAsRead(self)
        return result.upper() == 'OK'

    def countUnread(self):
        self.unread = self.countItems(excludeRead=True)

class Category(ItemsContainer):
    """
    Class for representing a category
    """

    def __str__(self):
        return "<%s (%d), %s>" % (self.label, self.unread, self.id)

    def __init__(self, googleReader, label, id):
        """
        Key args:
          - label (str)
          - id (str)
        """
        super(Category, self).__init__()
        self.googleReader = googleReader

        self.label = label
        self.id    = id

        self.feeds  = []

        self.fetchUrl = GoogleReader.CATEGORY_URL + urlquote(self.label)

    def _addFeed(self, feed):
        if not feed in self.feeds:
            self.feeds.append(feed)
            try:
                self.unread += feed.unread
            except:
                pass

    def getFeeds(self):
        return self.feeds

    def _getContent(self, excludeRead=False, continuation=None):
        return self.googleReader.getCategoryContent(self, excludeRead, continuation)

    def countUnread(self):
        self.unread = sum([feed.unread for feed in self.feeds])

    def toArray(self):
        pass

    def toJSON(self):
        pass

class BaseFeed(ItemsContainer):
    """
    Class for representing a special feed.
    """
    def __str__(self):
        return "<%s, %s>" % (self.title, self.id)

    def __init__(self, googleReader, title, id, unread, categories=[]):
        """
        Key args:
          - title (str, name of the feed)
          - id (str, id for google reader)
          - unread (int, number of unread items, 0 by default)
          - categories (list) - list of all categories a feed belongs to, can be empty
        """
        super(BaseFeed, self).__init__()

        self.googleReader = googleReader

        self.id    = id
        self.title = title
        self.unread = unread

        self.categories = []
        for category in categories:
            self.addCategory(category)

        self.continuation = None

    def addCategory(self, category):
        if not category in self.categories:
            self.categories.append(category)
            category._addFeed(self)

    def getCategories(self):
        return self.categories

    def _getContent(self, excludeRead=False, continuation=None):
        return self.googleReader.getFeedContent(self, excludeRead, continuation)

    def markItemRead(self, item, read):
        super(BaseFeed, self).markItemRead(item, read)
        for category in self.categories:
            category.countUnread()

    def markAllRead(self):
        self.unread = 0
        for category in self.categories:
            category.countUnread()
        return super(BaseFeed, self).markAllRead()

    def toArray(self):
        pass

    def toJSON(self):
        pass

class SpecialFeed(BaseFeed):
    """
    Class for representing specials feeds (starred, shared, friends...)
    """
    def __init__(self, googleReader, type):
        """
        type is one of GoogleReader.SPECIAL_FEEDS
        """
        super(SpecialFeed, self).__init__(
            googleReader,
            title      = type,
            id         = GoogleReader.SPECIAL_FEEDS_PART_URL+type,
            unread     = 0,
            categories = [],
        )
        self.type = type

        self.fetchUrl = GoogleReader.CONTENT_BASE_URL + urlquote(self.id)

class Feed(BaseFeed):
    """
    Class for representing a normal feed.
    """

    def __init__(self, googleReader, title, id, siteUrl=None, unread=0, categories=[]):
        """
        Key args:
          - title (str, name of the feed)
          - id (str, id for google reader)
          - siteUrl (str, can be empty)
          - unread (int, number of unread items, 0 by default)
          - categories (list) - list of all categories a feed belongs to, can be empty
        """
        super(Feed, self).__init__(googleReader, title, id, unread, categories)

        self.feedUrl = self.id.lstrip('feed/')
        self.siteUrl = siteUrl

        self.fetchUrl = GoogleReader.FEED_URL + urlquote(self.id)

class Item(object):
    """
    Class for representing an individual item (an entry of a feed)
    """

    def __str__(self):
        return '<"%s" by %s, %s>' % (self.title, self.author, self.id)

    def __init__(self, googleReader, item, parent):
        """
        item : An item loaded from json
        parent : the object (Feed of Category) containing the Item
        """
        self.googleReader = googleReader
        self.parent = parent

        self.data   = item # save original data for accessing other fields
        self.id     = item['id']
        self.title  = item.get('title', '(no title)')
        self.author = item.get('author', None)
        self.content = item.get('content', item.get('summary', {})).get('content', '')
        self.origin  = { 'title': '', 'url': ''}

        # check original url
        self.url    = None
        for alternate in item.get('alternate', []):
            if alternate.get('type', '') == 'text/html':
                self.url = alternate['href']
                break

        # check status
        self.read    = False
        self.starred = False
        self.shared  = False
        for category in item.get('categories', []):
            if category.endswith('/state/com.google/read'):
                self.read = True
            elif category.endswith('/state/com.google/starred'):
                self.starred = True
            elif category in ('user/-/state/com.google/broadcast',
                              'user/%s/state/com.google/broadcast' % self.googleReader.userId):
                self.shared = True

        self.canUnread = item.get('isReadStateLocked', 'false') != 'true'

        # keep feed, can be used when item is fetched from a special feed, then it's the original one
        try:
            f = item['origin']
            self.origin = {
                'title': f.get('title', ''),
                'url': f.get('htmlUrl', ''),
            }
            self.feed = self.googleReader.getFeed(f['streamId'])
            if not self.feed:
                raise
            if not self.feed.title and 'title' in f:
                self.feed.title = f['title']
        except:
            try:
                self.feed = Feed(self, f.get('title', ''), f['streamId'], f.get('htmlUrl', None), 0, [])
                try:
                    self.googleReader._addFeed(self.feed)
                except:
                    pass
            except:
                self.feed = None

        self.parent._addItem(self)

    def isUnread(self):
        return not self.read

    def isRead(self):
        return self.read

    def markRead(self, read=True):
        self.parent.markItemRead(self, read)
        self.read = read
        if read:
            result = self.googleReader.addItemTag(self, GoogleReader.TAG_READ)
        else:
            result = self.googleReader.removeItemTag(self, GoogleReader.TAG_READ)
        return result.upper() == 'OK'

    def markUnread(self, unread=True):
        return self.markRead(not unread)

    def isShared(self):
        return self.shared

    def markShared(self, shared=True):
        self.shared = shared
        if shared:
            result = self.googleReader.addItemTag(self, GoogleReader.TAG_SHARED)
        else:
            result = self.googleReader.removeItemTag(self, GoogleReader.TAG_SHARED)
        return result.upper() == 'OK'

    def share(self):
        return self.markShared()

    def unShare(self):
        return self.markShared(False)

    def isStarred(self):
        return self.starred

    def markStarred(self, starred=True):
        self.starred = starred
        if starred:
            result = self.googleReader.addItemTag(self, GoogleReader.TAG_STARRED)
        else:
            result = self.googleReader.removeItemTag(self, GoogleReader.TAG_STARRED)
        return result.upper() == 'OK'

    def star(self):
        return self.markStarred()

    def unStar(self):
        return self.markStarred(False)

class GoogleReader(object):
    """
    Class for using the unofficial Google Reader API and working with
    the data it returns.

    Requires valid google username and password.
    """
    READER_BASE_URL = 'https://www.google.com/reader/api'
    API_URL = READER_BASE_URL + '/0/'

    USER_INFO_URL = API_URL + 'user-info'

    SUBSCRIPTION_LIST_URL = API_URL + 'subscription/list'
    UNREAD_COUNT_URL = API_URL + 'unread-count'

    CONTENT_PART_URL       = 'stream/contents/'
    CONTENT_BASE_URL       = API_URL + CONTENT_PART_URL
    SPECIAL_FEEDS_PART_URL = 'user/-/state/com.google/'

    READING_LIST    = 'reading-list'
    READ_LIST       = 'read'
    KEPTUNREAD_LIST = 'kept-unread'
    STARRED_LIST    = 'starred'
    SHARED_LIST     = 'broadcast'
    NOTES_LIST      = 'created'
    FRIENDS_LIST    = 'broadcast-friends'
    SPECIAL_FEEDS = (READING_LIST, READ_LIST, KEPTUNREAD_LIST, STARRED_LIST, \
                     SHARED_LIST, FRIENDS_LIST, NOTES_LIST, )

    FEED_URL     = CONTENT_BASE_URL
    CATEGORY_URL = CONTENT_BASE_URL + 'user/-/label/'

    EDIT_TAG_URL = API_URL + 'edit-tag'
    TAG_READ     = 'user/-/state/com.google/read'
    TAG_STARRED  = 'user/-/state/com.google/starred'
    TAG_SHARED   = 'user/-/state/com.google/broadcast'

    MARK_ALL_READ_URL = API_URL + 'mark-all-as-read'

    def __str__(self):
        return "<Google Reader object: %s>" % self.username

    def __init__(self, auth):
        self.auth = auth
        self.feeds = []
        self.categories = []
        self.feedsById = {}
        self.categoriesById = {}
        self.specialFeeds = {}
        self.orphanFeeds = []

        self.userId = None

    def toJSON(self):
        """
        TODO: build a json object to return via ajax
        """
        pass

    def getFeeds(self):
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
        for type in self.SPECIAL_FEEDS:
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

        unreadJson = self.httpGet(GoogleReader.UNREAD_COUNT_URL, { 'output': 'json', })
        unreadCounts = json.loads(unreadJson, strict=False)['unreadcounts']
        for unread in unreadCounts:
            unreadById[unread['id']] = unread['count']

        feedsJson = self.httpGet(GoogleReader.SUBSCRIPTION_LIST_URL, { 'output': 'json', })
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
          - id (str, feed's id)
          - continuation (str, to be used to fetch more items)
          - items, array of dits with :
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
        return self.httpPost(GoogleReader.EDIT_TAG_URL,
                             {'i': item.id, 'r': tag, 'ac': 'edit-tags', })

    def addItemTag(self, item, tag):
        return self.httpPost(GoogleReader.EDIT_TAG_URL,
                             {'i': item.id, 'a': tag, 'ac': 'edit-tags', })

    def markFeedAsRead(self, feed):
        return self.httpPost(GoogleReader.MARK_ALL_READ_URL, {'s': feed.id, })

    def getUserInfo(self):
        """
        Returns a dictionary of user info that google stores.
        """
        userJson = self.httpGet(GoogleReader.USER_INFO_URL)
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
        self.feedsById = {}
        self.feeds = []
        self.categoriesById = {}
        self.categories = []
        self.orphanFeeds = []

class AuthenticationMethod(object):
    """
    Defines an interface for authentication methods, must have a get method
    make this abstract?
    1. auth on setup
    2. need to have GET method
    """
    def __init__(self):
        self.client = "libgreader" #@todo: is this needed?

    def getParameters(self, extraargs=None):
        #ck is a timecode to help google with caching
        parameters = {'ck':time.time(), 'client':self.client}
        if extraargs:
            parameters.update(extraargs)
        return urllib.urlencode(parameters)

    def postParameters(self, post=None):
        if post is not None:
            post_string = urllib.urlencode(post)
        else:
            post_string = None
        return post_string

class ClientAuth(AuthenticationMethod):
    """
    Auth type which requires a valid Google Reader username and password
    """
    CLIENT_URL = 'https://www.google.com/accounts/ClientLogin'

    def __init__(self, username, password):
        super(ClientAuth, self).__init__()
        self.username = username
        self.password = password
        self.auth_token = self._getAuth()
        self.token = self._getToken()

    def postParameters(self, post=None):
        post.update({'T': self.token})
        return super(ClientAuth, self).postParameters(post)

    def get(self, url, parameters=None):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        getString = self.getParameters(parameters)
        req = urllib2.Request(url + "?" + getString)
        req.add_header('Authorization','GoogleLogin auth=%s' % self.auth_token)
        r = urllib2.urlopen(req)
        data = r.read()
        r.close()
        return data

    def post(self, url, postParameters=None, urlParameters=None):
        if urlParameters:
            getString = self.getParameters(urlParameters)
            req = urllib2.Request(url + "?" + getString)
        else:
            req = urllib2.Request(url)
        req.add_header('Authorization','GoogleLogin auth=%s' % self.auth_token)
        postString = self.postParameters(postParameters)
        r = urllib2.urlopen(req, data=postString)
        data = r.read()
        r.close()
        return data

    def _getAuth(self):
        """
        Main step in authorizing with Reader.
        Sends request to Google ClientAuth URL which returns an Auth token.

        Returns Auth token or raises IOError on error.
        """
        parameters = urllib.urlencode({
            'service':'reader',
            'Email':self.username,
            'Passwd':self.password,
            'accountType':'GOOGLE'})
        try:
            conn = urllib2.urlopen(ClientAuth.CLIENT_URL,parameters)
            data = conn.read()
            conn.close()
        except urllib2.HTTPError:
            raise IOError("Error getting the Auth token, have you entered a"
                    "correct username and password?")
        #Strip newline and non token text.
        token_dict = dict(x.split('=') for x in data.split('\n') if x)
        return token_dict["Auth"]

    def _getToken(self):
        """
        Second step in authorizing with Reader.
        Sends authorized request to Reader token URL and returns a token value.

        Returns token or raises IOError on error.
        """
        req = urllib2.Request(GoogleReader.API_URL + 'token')
        req.add_header('Authorization','GoogleLogin auth=%s' % self.auth_token)
        try:
            conn = urllib2.urlopen(req)
            token = conn.read()
            conn.close()
        except urllib2.HTTPError:
            raise IOError("Error getting the Reader token.")
        return token

class OAuthMethod(AuthenticationMethod):
    """
    Loose wrapper around OAuth2 lib. Kinda awkward.
    """
    GOOGLE_URL = 'https://www.google.com/accounts/'
    REQUEST_TOKEN_URL = (GOOGLE_URL + 'OAuthGetRequestToken?scope=%s'
            % GoogleReader.READER_BASE_URL)
    AUTHORIZE_URL = GOOGLE_URL + 'OAuthAuthorizeToken'
    ACCESS_TOKEN_URL = GOOGLE_URL + 'OAuthGetAccessToken'

    def __init__(self, consumer_key, consumer_secret):
        if not has_oauth:
            raise ImportError("No module named oauth2")
        super(OAuthMethod, self).__init__()
        self.oauth_key = consumer_key
        self.oauth_secret = consumer_secret
        self.consumer = oauth.Consumer(self.oauth_key, self.oauth_secret)
        self.authorized_client = None
        self.token_key = None
        self.token_secret = None
        self.callback = None

    def setCallback(self, callback_url):
        self.callback = '&oauth_callback=%s' % callback_url

    def setRequestToken(self):
        # Step 1: Get a request token. This is a temporary token that is used for
        # having the user authorize an access token and to sign the request to obtain
        # said access token.
        client = oauth.Client(self.consumer)
        if not self.callback:
            resp, content = client.request(OAuthMethod.REQUEST_TOKEN_URL)
        else:
            resp, content = client.request(OAuthMethod.REQUEST_TOKEN_URL + self.callback)
        if int(resp['status']) != 200:
            raise IOError("Error setting Request Token")
        token_dict = dict(urlparse.parse_qsl(content))
        self.token_key = token_dict['oauth_token']
        self.token_secret = token_dict['oauth_token_secret']

    def setAndGetRequestToken(self):
        self.setRequestToken()
        return (self.token_key, self.token_secret)

    def buildAuthUrl(self, token_key=None):
        if not token_key:
            token_key = self.token_key
        #return auth url for user to click or redirect to
        return "%s?oauth_token=%s" % (OAuthMethod.AUTHORIZE_URL, token_key)

    def setAccessToken(self):
        self.setAccessTokenFromCallback(self.token_key, self.token_secret, None)

    def setAccessTokenFromCallback(self, token_key, token_secret, verifier):
        token = oauth.Token(token_key, token_secret)
        #step 2 depends on callback
        if verifier:
            token.set_verifier(verifier)
        client = oauth.Client(self.consumer, token)

        resp, content = client.request(OAuthMethod.ACCESS_TOKEN_URL, "POST")
        if int(resp['status']) != 200:
            raise IOError("Error setting Access Token")
        access_token = dict(urlparse.parse_qsl(content))

        #created Authorized client using access tokens
        self.authFromAccessToken(access_token['oauth_token'],
                                 access_token['oauth_token_secret'])

    def authFromAccessToken(self, oauth_token, oauth_token_secret):
        self.token_key = oauth_token
        self.token_key_secret = oauth_token_secret
        token = oauth.Token(oauth_token,oauth_token_secret)
        self.authorized_client = oauth.Client(self.consumer, token)

    def getAccessToken(self):
        return (self.token_key, self.token_secret)

    def get(self, url, parameters=None):
        if self.authorized_client:
            getString = self.getParameters(parameters)
            #can't pass in urllib2 Request object here?
            resp, content = self.authorized_client.request(url + "?" + getString)
            return content
        else:
            raise IOError("No authorized client available.")

    def post(self, url, postParameters=None, urlParameters=None):
        if self.authorized_client:
            if urlParameters:
                getString = self.getParameters(urlParameters)
                req = urllib2.Request(url + "?" + getString)
            else:
                req = urllib2.Request(url)
            postString = self.postParameters(postParameters)
            resp,content = self.authorized_client.request(req, method="POST", body=postString)
            return content
        else:
            raise IOError("No authorized client available.")
