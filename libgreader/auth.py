# -*- coding: utf-8 -*-

import urllib
import urllib2
import urlparse
import time

try:
    import oauth2 as oauth
    has_oauth = True
except:
    has_oauth = False

from googlereader import GoogleReader
from url import ReaderUrl

def toUnicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

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

class ClientAuthMethod(AuthenticationMethod):
    """
    Auth type which requires a valid Google Reader username and password
    """
    CLIENT_URL = 'https://www.google.com/accounts/ClientLogin'

    def __init__(self, username, password):
        super(ClientAuthMethod, self).__init__()
        self.username   = username
        self.password   = password
        self.auth_token = self._getAuth()
        self.token      = self._getToken()

    def postParameters(self, post=None):
        post.update({'T': self.token})
        return super(ClientAuthMethod, self).postParameters(post)

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
        return toUnicode(data)

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
        return toUnicode(data)

    def _getAuth(self):
        """
        Main step in authorizing with Reader.
        Sends request to Google ClientAuthMethod URL which returns an Auth token.

        Returns Auth token or raises IOError on error.
        """
        parameters = urllib.urlencode({
            'service'     : 'reader',
            'Email'       : self.username,
            'Passwd'      : self.password,
            'accountType' : 'GOOGLE'})
        try:
            conn = urllib2.urlopen(ClientAuthMethod.CLIENT_URL,parameters)
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
        req = urllib2.Request(ReaderUrl.API_URL + 'token')
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
    GOOGLE_URL        = 'https://www.google.com/accounts/'
    REQUEST_TOKEN_URL = (GOOGLE_URL + 'OAuthGetRequestToken?scope=%s' %
                         ReaderUrl.READER_BASE_URL)
    AUTHORIZE_URL     = GOOGLE_URL + 'OAuthAuthorizeToken'
    ACCESS_TOKEN_URL  = GOOGLE_URL + 'OAuthGetAccessToken'

    def __init__(self, consumer_key, consumer_secret):
        if not has_oauth:
            raise ImportError("No module named oauth2")
        super(OAuthMethod, self).__init__()
        self.oauth_key         = consumer_key
        self.oauth_secret      = consumer_secret
        self.consumer          = oauth.Consumer(self.oauth_key, self.oauth_secret)
        self.authorized_client = None
        self.token_key         = None
        self.token_secret      = None
        self.callback          = None
        self.username          = "OAuth"

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
        self.token_key         = oauth_token
        self.token_key_secret  = oauth_token_secret
        token                  = oauth.Token(oauth_token,oauth_token_secret)
        self.authorized_client = oauth.Client(self.consumer, token)

    def getAccessToken(self):
        return (self.token_key, self.token_secret)

    def get(self, url, parameters=None):
        if self.authorized_client:
            getString = self.getParameters(parameters)
            #can't pass in urllib2 Request object here?
            resp, content = self.authorized_client.request(url + "?" + getString)
            return toUnicode(content)
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
            return toUnicode(content)
        else:
            raise IOError("No authorized client available.")
