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
__version__ = "0.3"

import sys
import urllib
import urllib2
import urlparse
import time

import xml.dom.minidom
import simplejson as json
import oauth2 as oauth

#Reset due to ascii/utf-8 problems with internet data
reload(sys)
sys.setdefaultencoding("utf-8")

class Feed:
    """
    Class for representing an individual feed.
    """

    def __str__(self):
        return "<%s, %s>" % (self.title, self.url)

    def __init__(self, title, url, categories=[]):
        """
        Key args:
        title (str)
        url (str, possible urlparse obj?)
        categories (list) - list of all categories a feed belongs to, can be empty
        """
        self.title = title
        self.url = url
        self.categories = categories

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
    READING_LIST_URL = API_URL + 'stream/contents/user/-/state/com.google/reading-list'
    UNREAD_COUNT_URL = API_URL + 'unread-count'

    def __str__(self):
        return "<Google Reader object: %s>" % self.username

    def __init__(self, auth):
        self.auth = auth
        self.feedlist = []

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

    def buildSubscriptionList(self):
        """
        Hits Google Reader for a users's alphabetically ordered list of feeds.

        Returns true if succesful.
        """
        xmlSubs = self.httpGet(GoogleReader.SUBSCRIPTION_LIST_URL)

        #Work through xml list of subscriptions
        dom = xml.dom.minidom.parseString(xmlSubs)
        #Object > List > subscription objects
        subs = dom.firstChild.firstChild
        for sub in subs.childNodes:
            #Work through the dom for the important elements
            url = str(sub.firstChild.firstChild.data.lstrip('feed/'))
            title = str(sub.childNodes[1].firstChild.data)
            categories = sub.childNodes[2]
            #Build a python list of Feeds from Dom elements
            catList = []
            for cat in categories.childNodes:
                catList.append(cat.childNodes[1].firstChild.data)
            #Add Feed to the main list
            feed = Feed(title,url,catList)
            self._addFeeds(feed)

        return True

    def getReadingList(self, numResults=50):
        """
        The 'All Items' list of everything the user has not read.

        Returns dict with items
        -update -- update timestamp
        -author -- username
        -continuation
        -title -- page title "(users)'s reading list in Google Reader"
        -items -- feed items
        -self -- self url
        -id
        """
        userJson = self.httpGet(GoogleReader.READING_LIST_URL, {'n':numResults, 'exclude':'read'})
        return json.loads(userJson, strict=False)['items']

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

    def _addFeeds (self, feed):
        self.feedlist.append(feed)

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
        except Exception as e:
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
