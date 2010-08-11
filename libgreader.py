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

class Category:
    """
    Class for representing a category
    """
    
    def __str__(self):
        return "<%s (%d), %s>" % (self.label, self.unread, self.id)
        
    def __init__(self, label, id):
        """
        Key args:
        label (str)
        id (str)
        """
        self.label = label
        self.id    = id
        
        self.unread = 0
        self.feeds  = []
        
    def _addFeed(self, feed):
        if not feed in self.feeds:
            self.feeds.append(feed)
            self.unread += feed.unread
            
    def getFeeds(self):
        return self.feeds

    def toArray(self):
        pass

    def toJSON(self):
        pass

class Feed:
    """
    Class for representing an individual feed.
    """

    def __str__(self):
        return "<%s (%d), %s>" % (self.title, self.unread, self.url)

    def __init__(self, title, id, site_url=None, unread=0, categories=[]):
        """
        Key args:
        title (str, name of the feed)
        id (str, id for google reader)
        site_url (str, can be empty)
        unread (int, number of unread items, 0 by default)
        categories (list) - list of all categories a feed belongs to, can be empty
        """
        self.title    = title
        self.id       = id
        self.feed_url = self.id.lstrip('feed/')
        self.url      = self.feed_url # for compatibility with libgreader 0.3
        self.site_url = site_url
        self.unread   = unread
        
        self.categories = []
        for category in categories:
            self._addCategory(category)
        
    def _addCategory(self, category):
        if not category in self.categories:
            self.categories.append(category)
            category._addFeed(self)
            
    def getCategories(self):
        return self.categories

    def toArray(self):
        pass

    def toJSON(self):
        pass

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
    
    SPECIAL_ITEMS_URL   = API_URL + 'stream/contents/user/-/state/com.google/'
    READING_LIST_URL    = SPECIAL_ITEMS_URL + 'reading-list'
    READ_LIST_URL       = SPECIAL_ITEMS_URL + 'read'
    KEPTUNREAD_LIST_URL = SPECIAL_ITEMS_URL + 'kept-unread'
    STARRED_LIST_URL    = SPECIAL_ITEMS_URL + 'starred'
    SHARED_LIST_URL     = SPECIAL_ITEMS_URL + 'broadcast'
    NOTES_LIST_URL      = SPECIAL_ITEMS_URL + 'created'
    FRIENDS_LIST_URL    = SPECIAL_ITEMS_URL + 'broadcast-friends'
    
    FEED_URL     = API_URL + 'stream/contents/'
    CATEGORY_URL = API_URL + 'stream/contents/user/-/label/'

    def __str__(self):
        return "<Google Reader object: %s>" % self.username

    def __init__(self, auth):
        self.auth = auth
        self.feedlist = []
        self.categories = []

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
        return self.feedlist

    def getCategories(self):
        """
        Returns a list of all the categories or None if buildSubscriptionList
        has not been called, to get the Feeds
        """
        return self.categories

    def buildSubscriptionList(self):
        """
        Hits Google Reader for a users's alphabetically ordered list of feeds.

        Returns true if succesful.
        """

        self._clearLists()
        categoriesById = {}
        unreadById     = {}

        unreadJson = self.httpGet(GoogleReader.UNREAD_COUNT_URL, { 'output': 'json', })
        unreadcounts = json.loads(unreadJson, strict=False)['unreadcounts']
        for unread in unreadcounts:
            unreadById[unread['id']] = unread['count']
        
        feedsJson = self.httpGet(GoogleReader.SUBSCRIPTION_LIST_URL, { 'output': 'json', })
        subscriptions = json.loads(feedsJson, strict=False)['subscriptions']

        for sub in subscriptions:
            categories = []
            if 'categories' in sub:
                for hCategory in sub['categories']:
                    cId = hCategory['id']
                    if not cId in categoriesById:
                        categoriesById[cId] = Category(hCategory['label'], cId)
                        self._addCategory(categoriesById[cId])
                    categories.append(categoriesById[cId])
            feed = Feed(sub['title'], sub['id'], sub.get('htmlUrl', None), unreadById.get(sub['id'], 0), categories)
            self._addFeed(feed)

        return True

    def getReadingList(self, exclude='read'):
        """
        The 'All Items' list of everything the user has not read.
        """
        return self.getSpecialItemsList(self.READING_LIST_URL, {'exclude':exclude} )
        
    def getItemsList(self, url, parameters={}):
        """
        A list of items (from a feed or see URLs made with SPECIAL_ITEMS_URL)

        Returns dict with items
        -update -- update timestamp
        -author -- username
        -continuation
        -title -- page title "(users)'s reading list in Google Reader"
        -items -- feed items
        -self -- self url
        -id
        """
        userJson = self.httpGet(url, parameters)
        return json.loads(userJson, strict=False)['items']
        
    def getFeedItemsList(self, feed, parameters={}):
        """
        Return items for a particular feed
        """
        return self.getItemsList(self.FEED_URL + urllib.quote(feed.id), parameters)        
        
    def getCategoryItemsList(self, category, parameters={}):
        """
        Return items for a particular category
        """
        return self.getItemsList(self.CATEGORY_URL + urllib.quote(category.label), parameters)        

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
        self.feedlist.append(feed)

    def _addCategory (self, category):
        self.categories.append(category)
        
    def searchFeed(self, id):
        try:
            return [feed for feed in self.feedlist if feed.id == id][0]
        except:
            return None
        
    def searchCategory(self, id):
        try:
            return [category for category in self.categories if category.id == id][0]
        except:
            return None

    def _clearLists(self):
        """
        Clear all list before sync : feeds and categories
        """
        self.feedlist = []
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
