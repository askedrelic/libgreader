#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for oauth and ClientAuth in libgreader. Requires mechanize for automated oauth authenication.

"""

import unittest

from libgreader import GoogleReader, OAuthMethod, ClientAuth, Feed
import urllib
import urllib2
import urlparse
import mechanize

#ClientAuth
#User account I created for testing
username = 'relic@asktherelic.com'
password = 'testtest'

#OAuth
#Actual keys for my domain :/
#Probably not the best to have these public, but fuck it
oauth_key = 'www.asktherelic.com'
oauth_secret = 'WtAfQlY4+MJqsge45b9VuwNn'

#automated approval of oauth url
#returns mechanize Response of the last "You have accepted" page
def automated_oauth_approval(url):
    #general process is:
    # 1. assume user isn't logged in, so get redirected to google accounts
    # login page. login using test account credentials
    # 2. redirected back to oauth approval page. br.submit() should choose the
    # first submit on that page, which is the "Accept" button
    br = mechanize.Browser()
    br.open(url)
    br.select_form(nr=0)
    br["Email"] = username
    br["Passwd"] = password
    response1 = br.submit()
    response1.geturl()
    br.select_form(nr=0)
    response2 = br.submit()
    return response2

class TestClientAuth(unittest.TestCase):
    def test_clientauth_login(self):
        ca = ClientAuth(username,password)
        self.assertNotEqual(ca, None)

    def test_reader(self):
        ca = ClientAuth(username,password)
        reader = GoogleReader(ca)
        self.assertNotEqual(reader, None)

    def test_bad_user_details(self):
        self.assertRaises(IOError, ClientAuth, 'asdsa', '')

    def test_reader_user_info(self):
        ca = ClientAuth(username,password)
        reader = GoogleReader(ca)
        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual('relic', info['userName'])

class TestOAuth(unittest.TestCase):
    def test_oauth_login(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        self.assertNotEqual(auth, None)

    def test_getting_request_token(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        token, token_secret = auth.setAndGetRequestToken()
        url = auth.buildAuthUrl()
        response = automated_oauth_approval(url)
        self.assertNotEqual(-1,response.get_data().find('You have successfully granted'))

    def test_full_auth_process_without_callback(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        auth.setRequestToken()
        auth_url = auth.buildAuthUrl()
        response = automated_oauth_approval(auth_url)
        auth.setAccessToken()
        reader = GoogleReader(auth)

        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual('relic', info['userName'])

    def test_full_auth_process_with_callback(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        #must be a working callback url for testing
        auth.setCallback("http://www.asktherelic.com")
        token, token_secret = auth.setAndGetRequestToken()
        auth_url = auth.buildAuthUrl()

        #callback section
        #get response, which is a redirect to the callback url
        response = automated_oauth_approval(auth_url)
        query_string = urlparse.urlparse(response.geturl()).query
        #grab the verifier token from the callback url query string
        token_verifier = urlparse.parse_qs(query_string)['oauth_verifier'][0]

        auth.setAccessTokenFromCallback(token, token_secret, token_verifier)
        reader = GoogleReader(auth)

        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual('relic', info['userName'])

if __name__ == '__main__':
    unittest.main()
