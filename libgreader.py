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
    require a google username and password

    send
    """
    CLIENT_URL = 'https://www.google.com/accounts/ClientLogin'

    def __init__(self, username, password):
        self.client = "libgreader" #TEST: is this needed?
        self.username = username
        self.password = password
        self.sid = self._getSID()
        self.token = self._getToken(self.sid)

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
        req.add_header('Cookie', 'SID=%s;T=%s' % (self.sid, self.token))
        r = urllib2.urlopen(req)
        data = r.read()
        r.close()
        return data

    def _getSID(self):
        """
        First step in authorizing with google reader.
        Request to google returns 4 values, SID is the only value we need.

        Returns SID or raises URLError on error.
        """
        parameters = urllib.urlencode({'service':'reader',
                                        'Email':self.username,
                                        'Passwd':self.password})
        try:
            conn = urllib2.urlopen(ClientAuth.CLIENT_URL,parameters)
            data = conn.read()
            conn.close()
        except Exception:
            raise urllib2.URLError("Error getting the SID, have you entered a"
                    "correct username and password?")
        #Strip newline and non SID text.
        sid_dict = dict(x.split('=') for x in data.split('\n') if x)
        return sid_dict["SID"]

    def _getToken(self, sid):
        """
        Second step in authorizing with google reader.
        Sends request to Google with SID and returns a token value.

        Returns SID or raises URLError on error.
        """
        req = urllib2.Request(GoogleReader.API_URL + 'token')
        req.add_header('Cookie','name=SID;SID=%s;domain=.google.com;'
                                'path=/;expires=1600000' % sid)
        try:
            conn = urllib2.urlopen(req)
            token = conn.read()
            conn.close()
        except Exception:
            raise urllib2.URLError("Error getting the token.")
        return token

class OAuthMethod(AuthenticationMethod):
    """
    require an oauth key and secret

    how to setup callback? noncallback?
    """

    def __init__(self, username, password, client):
        """
        """
        self.username = username
        self.password = password
        self.sid = self._getSID()
        self.token = self._getToken(self.sid)

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
        userJson = self._httpGet(GoogleReader.READING_LIST_URL, {'n':numResults})
        return json.loads(userJson, strict=False)

    def getUserInfo(self):
        """
        Returns a dictionary of user info that google stores.
        """
        userJson = self._httpGet(GoogleReader.USER_INFO_URL)
        return json.loads(userJson, strict=False)

    def getUserSignupDate(self):
        """
        Returns the human readable date of when the user signed up for google reader.
        """
        userinfo = self.getUserInfo()
        timestamp = int(float(userinfo["signupTimeSec"]))
        return time.strftime("%m/%d/%Y %H:%M", time.gmtime(timestamp))

    def buildSubscriptionList(self):
        """
        Hits Google Reader for a users's alphabetically ordered list of feeds.

        Returns true if succesful.
        """
        print GoogleReader.SUBSCRIPTION_LIST_URL
        xmlSubs = self._httpGet(GoogleReader.SUBSCRIPTION_LIST_URL)

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

    def _httpGet(self, url, parameters=None):
        """
        Wrapper around AuthenticationMethod get()
        """
        return self.auth.get(url, parameters)

    def _httpPost(self, request):
        pass

    def _addFeeds (self, feed):
        self.feedlist.append(feed)
