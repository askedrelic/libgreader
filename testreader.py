
#if reader.buildSubscriptionList():
#    for feed in reader.getFeeds():
#        print feed.title, feed.url, feed.categories
#
#print reader.getUserInfo()

import unittest

from libgreader import GoogleReader, OAuthMethod, ClientAuth, Feed
import urllib2

#ClientAuth
#User account I created for testing
username = 'relic@asktherelic.com'
password = 'testtest'
#ca = ClientAuth(username,password)

#OAuth
#callback = "http://www.asktherelic.com:8000"
#ca.setCallback(callback)
#c1, c2 =  ca.setAndGetRequestToken()
#print ca.buildAuthUrl()
#accepted = 'n'
#while accepted.lower() == 'n':
#    accepted = raw_input('Have you authorized me? (y/n) ')
#ca.setAccessTokenFromCallback(c1, c2, raw_input('verifier'))
#ca = OAuthMethod(oauth_key, oauth_secret)

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

#class TestReaderFunctions(unittest.TestCase):
#    def test_reader_user_info(self):
#        reader = GoogleReader(ca)
#        info = reader.getUserInfo()
#        self.assertEqual(dict, type(info))
#        self.assertEqual('relic', info['userName'])


#suite = unittest.TestLoader().loadTestsFromTestCase(TestReaderFunctions)
suite = unittest.TestLoader().loadTestsFromTestCase(TestClientAuth)
unittest.TextTestRunner(verbosity=2).run(suite)
