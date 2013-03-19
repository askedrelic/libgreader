#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for oauth and ClientAuthMethod in libgreader.

"""

try:
    import unittest2 as unittest
except:
    import unittest

from libgreader import GoogleReader, OAuthMethod, OAuth2Method, ClientAuthMethod, Feed
import requests
import re

from .config import *

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
    req2 = br.click(type="submit", nr=0)
    response2 = br.open(req2)
    return response2

@unittest.skip('deprecated')
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
def mechanize_oauth2_approval(url):
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

def automated_oauth2_approval(url):
    """
    general process is:
    1. assume user isn't logged in, so get redirected to google accounts
    login page. login using account credentials
    2. get redirected to oauth approval screen
    3. authorize oauth app
    """
    auth_url = url
    headers = {'Referer': auth_url}

    s = requests.Session()
    r1 = s.get(auth_url)
    post_data = dict((x[0],x[1]) for x in re.findall('name="(.*?)".*?value="(.*?)"', str(r1.content), re.MULTILINE))
    post_data['Email'] = username
    post_data['Passwd'] = password
    post_data['timeStmp'] = ''
    post_data['secTok'] = ''
    post_data['signIn'] = 'Sign in'
    post_data['GALX'] = s.cookies['GALX']

    r2 = s.post('https://accounts.google.com/ServiceLoginAuth', data=post_data, headers=headers, allow_redirects=False)

    #requests is fucking up the url encoding and double encoding ampersands
    scope_url = r2.headers['location'].replace('amp%3B','')

    # now get auth screen
    r3 = s.get(scope_url)

    # unless we have already authed!
    if 'asktherelic' in r3.url:
        code = r3.url.split('=')[1]
        return code

    post_data = dict((x[0],x[1]) for x in re.findall('name="(.*?)".*?value="(.*?)"', str(r3.content)))
    post_data['submit_access'] = 'true'
    post_data['_utf8'] = '&#9731'

    # again, fucked encoding for amp;
    action_url = re.findall('action="(.*?)"', str(r3.content))[0].replace('amp;','')

    r4 = s.post(action_url, data=post_data, headers=headers, allow_redirects=False)
    code = r4.headers['Location'].split('=')[1]

    s.close()

    return code

@unittest.skipIf("client_id" not in globals(), 'OAuth2 config not setup')
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

    def test_oauth_subscribe(self):
        auth = OAuth2Method(client_id, client_secret)
        auth.setRedirectUri(redirect_url)
        url = auth.buildAuthUrl()
        token = automated_oauth2_approval(url)
        auth.code = token
        auth.setAccessToken()
        auth.setActionToken()

        reader = GoogleReader(auth)

        slashdot = 'feed/http://rss.slashdot.org/Slashdot/slashdot'
        #unsubscribe always return true; revert feedlist state
        self.assertTrue(reader.unsubscribe(slashdot))
        # now subscribe
        self.assertTrue(reader.subscribe(slashdot))
        # wait for server to update
        import time
        time.sleep(1)
        reader.buildSubscriptionList()
        # test subscribe successful
        self.assertIn(slashdot, [x.id for x in reader.getSubscriptionList()])

if __name__ == '__main__':
    unittest.main()
