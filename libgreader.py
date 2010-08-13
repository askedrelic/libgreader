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

import simplejson as json
try:
    import oauth2 as oauth
    has_oauth = True
except:
    has_oauth = False

#Reset due to ascii/utf-8 problems with internet data
reload(sys)
sys.setdefaultencoding("utf-8")

class ItemsContainer(object):
    """
    A base class used for all classes aimed to have items (Categories and Feeds)
    """
    def __init__(self):
        self.items  = []
        self.itemsLoaded = False
        self.unread = 0
        
    def loadItems(self):
        """
        Load items. Must be overloaded, and call itemsLoadedDone when finished
        """
        pass
        
    def itemsLoadedDone(self, data):
        """
        Called when all items are loaded
        """
        self.continuation = data.get('continuation', None)
        self.googleReader.itemsToObjects(self, data.get('items', []))
        self.itemsLoaded = True

    def _addItem(self, item):
        self.items.append(item)
        
    def clearItems(self):
        self.items = []
        self.itemsLoaded = False
        
    def getItems(self):
        return self.items

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
        
        self.fetchUrl = GoogleReader.CATEGORY_URL + urllib.quote(self.label)
        
    def _addFeed(self, feed):
        if not feed in self.feeds:
            self.feeds.append(feed)
            try:
                self.unread += feed.unread
            except:
                pass
            
    def getFeeds(self):
        return self.feeds
        
    def loadItems(self, excludeRead=False):
        self.itemsLoadedDone(self.googleReader.getCategoryContent(self, excludeRead))

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
            self._addCategory(category)
        
        self.continuation = None
        
    def _addCategory(self, category):
        if not category in self.categories:
            self.categories.append(category)
            category._addFeed(self)
            
    def getCategories(self):
        return self.categories
        
    def loadItems(self, excludeRead=False):
        self.itemsLoadedDone(self.googleReader.getFeedContent(self, excludeRead))

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
        
        self.fetchUrl = GoogleReader.CONTENT_BASE_URL + urllib.quote(self.id)

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
        self.url      = self.feedUrl # for compatibility with libgreader 0.3
        self.siteUrl = siteUrl
    
        self.fetchUrl = GoogleReader.FEED_URL + urllib.quote(self.id)
        
class Item(object):
    """
    Class for representing an individual item (an entry of a feed)
    """

    def __str__(self):
        return '<"%s" by %s, %s>' % (self.title, self.author, self.id)
    
    def __init__(self, googleReader, item, parent):
        """
        item : An item loaded from json
        parent : the object (Feed of Category) containing thi Item
        """
        self.googleReader = googleReader
        self.parent = parent
        
        self.data   = item # save original data for accessing other fields
        self.id     = item['id']
        self.title  = item['title']
        self.author = item.get('author', None)
        self.content = item.get('content', item.get('summary', {})).get('content', '')
                
        # check original url
        self.url    = None
        for alternate in item.get('alternate', []):
            if alternate.get('type', '') == 'text/html':
                self.url = alternate['href']
                break
                
        # check status
        self.unread  = True
        self.starred = False
        self.shared  = False
        for category in item.get('categories', []):
            if category.endswith('/state/com.google/read'):
                self.unread = False
            elif category.endswith('/state/com.google/starred'):
                self.starred = True
            elif category.endswith('/state/com.google/broadcast'):
                self.shared = True

        self.canUnread = item.get('isReadStateLocked', 'false') != 'true'

        # keep feed, can be used when item si fetched from a special feed then it's the original one
        try:
            f = item['origin']
            self.feed = self.googleReader.getFeed(f['streamId'], None)
        except:
            try:
                self.feed = Feed(self, f['title'], f['streamId'], f.get('htmlUrl', None), 0, [])
            except:
                self.feed = None

        self.parent._addItem(self)

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
                     SHARED_LIST, FRIENDS_LIST, )
    
    FEED_URL     = CONTENT_BASE_URL
    CATEGORY_URL = CONTENT_BASE_URL + 'user/-/label/'

    def __str__(self):
        return "<Google Reader object: %s>" % self.username

    def __init__(self, auth):
        self.auth = auth
        self.feeds = []
        self.categories = []
        self.feedsById = {}
        self.categoriesById = {}
        self.specialFeeds = {}

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
            feed = Feed(self, sub['title'], sub['id'], sub.get('htmlUrl', None), unreadById.get(sub['id'], 0), categories)
            self._addFeed(feed)

        return True
        
    def _getFeedContent(self, url, excludeRead=False):
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
        contentJson = self.httpGet(url, parameters)
        return json.loads(contentJson, strict=False)
        
    def itemsToObjects(self, parent, items):
        objects = []
        for item in items:
            objects.append(Item(self, item, parent))
        return objects
        
    def getFeedContent(self, feed, excludeRead=False):
        """
        Return items for a particular feed
        """
        return self._getFeedContent(feed.fetchUrl, excludeRead)
        
    def getCategoryContent(self, category, excludeRead=False):
        """
        Return items for a particular category
        """
        return self._getFeedContent(category.fetchUrl, excludeRead)

    def getUserInfo(self):
        """
        Returns a dictionary of user info that google stores.
        """
        userJson = self.httpGet(GoogleReader.USER_INFO_URL)
        return json.loads(userJson, strict=False)

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

    def _httpPost(self, request):
        pass

    def _addFeed(self, feed):
        self.feedsById[feed.id] = feed
        self.feeds.append(feed)

    def _addCategory (self, category):
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

class AuthenticationMethod(object):
    """
    Defines an interface for authentication methods, must have a get method
    make this abstract?
    1. auth on setup
    2. need to have GET method
    """

    def get(self, url, parameters):
        #basic http getting method for both auth methods
        raise NotImplementedError

class ClientAuth(AuthenticationMethod):
    """
    Auth type which requires a valid Google Reader username and password
    """
    CLIENT_URL = 'https://www.google.com/accounts/ClientLogin'

    def __init__(self, username, password):
        self.client = "libgreader" #@todo: is this needed?
        self.username = username
        self.password = password
        self.auth_token = self._getAuth()
        self.token = self._getToken()

    def get(self, url, extraargs):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        #ck is a timecode to help google with caching
        parameters = {'ck':time.time(), 'client':self.client}
        if extraargs:
            parameters.update(extraargs)
        parameters = urllib.urlencode(parameters)
        req = urllib2.Request(url + "?" + parameters)
        req.add_header('Authorization','GoogleLogin auth=%s' % self.auth_token)
        r = urllib2.urlopen(req)
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
        except Exception:
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
        except Exception, e:
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
        #include parameters in call
        if self.authorized_client:
            resp,content = self.authorized_client.request(url)
            return content
        else:
            raise IOError("No authorized client available.")
