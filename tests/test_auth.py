#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for oauth and ClientAuthMethod in libgreader. Requires mechanize for automated oauth authenication.

"""

try:
    import unittest2 as unittest
except:
    import unittest

from libgreader import GoogleReader, OAuthMethod, OAuth2Method, ClientAuthMethod, Feed
import urllib
import urllib2
import urlparse
import mechanize

from config import *

class TestClientAuthMethod(unittest.TestCase):
    def test_ClientAuthMethod_login(self):
        ca = ClientAuthMethod(username,password)
        self.assertNotEqual(ca, None)

    def test_reader(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        self.assertNotEqual(reader, None)

    def test_bad_user_details(self):
        self.assertRaises(IOError, ClientAuthMethod, 'asdsa', '')

    def test_reader_user_info(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual(firstname, info['userName'])


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
    br.select_form(nr=0)
    response2 = br.submit()
    return response2

@unittest.skip('being deprecated')
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
        self.assertEqual(firstname, info['userName'])

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
        self.assertEqual(firstname, info['userName'])


#automate getting the approval token
def automated_oauth2_approval(url):
    """
    general process is:
    1. assume user isn't logged in, so get redirected to google accounts
    login page. login using account credentials
    But, if the user has already granted access, the user is auto redirected without
    having to confirm again.
    2. redirected back to oauth approval page. br.submit() should choose the
    first submit on that page, which is the "Accept" button
    3. mechanize follows the redirect, and should throw 40X exception and
    we return the token
    """
    br = mechanize.Browser()
    br.open(url)
    br.select_form(nr=0)
    br["Email"] = username
    br["Passwd"] = password
    try:
        response1 = br.submit()
        br.select_form(nr=0)
        response2 = br.submit()
    except Exception as e:
        #watch for 40X exception on trying to load redirect page
        pass
    callback_url = br.geturl()
    # split off the token in hackish fashion
    return callback_url.split('code=')[1]

@unittest.skipIf(globals().has_key('client_id') == False, 'OAuth2 config not setup')
class TestOAuth2(unittest.TestCase):
    def test_full_auth_and_access_userdata(self):
        auth = OAuth2Method(client_id, client_secret)
        auth.setRedirectUri(redirect_url)
        url = auth.buildAuthUrl()
        token = automated_oauth2_approval(url)
        auth.code = token
        auth.setAccessToken()

        reader = GoogleReader(auth)
        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual(firstname, info['userName'])


if __name__ == '__main__':
    unittest.main()
