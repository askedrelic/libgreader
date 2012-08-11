#Usage
The library is currently broken into 2 parts: The Authentication class and the GoogleReader class. 

The Authentication class authenticates itself with Google and then provides a GET/POST method for making authenticated calls.  
Currently, ClientLogin, OAuth are supported.

The GoogleReader class keeps track of user data and provides wrapper methods around known Reader urls.

##ClientLogin
To get started using the ClientLogin auth type, create a new ClientAuthMethod class:

```python
from libgreader import GoogleReader, ClientAuthMethod, Feed
auth = ClientAuthMethod('USERNAME','PASSWORD')
```
	
Then setup GoogleReader:
	
```python
reader = GoogleReader(auth)
```

Then make whatever requests you want:

```python
print reader.getUserInfo()
```

##OAuth
The OAuth method is a bit more complicated, depending on whether you want to use a callback or not, and because oauth is just complicated.

###No Callback
Send user to authorize with Google in a new window or JS lightbox, tell them to close the window when done authenicating

The oauth key and secret are setup with Google for your domain [https://www.google.com/accounts/ManageDomains]()

```python
from libgreader import GoogleReader, OAuthMethod, Feed
auth = OAuthMethod(oauth_key, oauth_secret)
```

We want to internally set the request token

```python
auth.setRequestToken()
```

Get the authorization URL for that request token, which you can link the user to or popup in a new window

```python
auth_url = auth.buildAuthUrl()
```

After they have authorized you, set the internal access token, and then you should have access to the user's data

```python
auth.setAccessToken()
reader = GoogleReader(auth)
print reader.getUserInfo()
```

###Callback
User goes to Google, authenticates, then is automatically redirected to your callback url without using a new window, a much more seamless user experience

Same opening bit, you still need an oauth key and secret from Google

```python
from libgreader import GoogleReader, OAuthMethod, Feed
auth = OAuthMethod(oauth_key, oauth_secret)
```

Set the callback...

```python
auth.setCallback("http://www.asktherelic.com/theNextStep")
```

Now the interesting thing with using a callback is that you must split up the process of authenticating the user and store their token data while they leave your site. Whether you use internal sessions or cookies is up to you, but you need access to the token_secret when the user returns from Google.

```python
token, token_secret = auth.setAndGetRequestToken()
auth_url = auth.buildAuthUrl()
```

So assume the user goes, authenticates you, and now they are returning to http://www.asktherelic.com/theNextStep with two query string variables, the token and the verifier. You can now finish authenticating them and access their data.

```python
#get the token verifier here
token_verifier = ""
auth.setAccessTokenFromCallback(token, token_secret, token_verifier)
reader = GoogleReader(auth)
print reader.getUserInfo()
```

##Using libgreader on Google AppEngine
If you want to use libgreader on Google AppEngine it is easier to use the Google's API for Python library which
contains implementation of OAuth2 especially designed for AppEngine.

Here is a minimal way to implement it:

```python
from google.appengine.ext.webapp.util import login_required

from oauth2client.appengine import CredentialsProperty
from oauth2client.appengine import StorageByKeyName
from oauth2client.appengine import OAuth2WebServerFlow

from libgreader import GoogleReader
from libgreader.auth import GAPDecoratorAuthMethod

GOOGLE_URL = 'https://accounts.google.com'
AUTHORIZATION_URL = GOOGLE_URL + '/o/oauth2/auth'
ACCESS_TOKEN_URL = GOOGLE_URL + '/o/oauth2/token'
REDIRECT_URI = '<YOU REDIRECT URI>'

FLOW = OAuth2WebServerFlow(
    client_id='<YOUR GOOGLE API CLIENT ID>',
    client_secret='<YOUR GOOGLE API CLIENT SECRET>',
    scope=[
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.google.com/reader/api/',
    ],
    redirect_uri=REDIRECT_URI,
    user_agent='<YOU USER AGENT>',
    auth_uri=AUTHORIZATION_URL,
    token_uri=ACCESS_TOKEN_URL)

class Credentials(db.Model):
    credentials = CredentialsProperty()


#... Checking and obtaining credentials if needed
class MainHandler(webapp2.RequestHandler):
@login_required
def get(self):
    user = users.get_current_user()

    # get stored credentials for current user from the Datastore
    credentials = StorageByKeyName(Credentials, user.user_id(), 'credentials').get()
    
    if credentials is None or credentials.invalid == True:
        # we are not authorized (=no credentials) create an authorization URL
        authorize_url = FLOW.step1_get_authorize_url(REDIRECT_URI)
        template_values = {
            'authurl': authorize_url
        }
        # a courtsey message to user to ask for authorization. we can just redirect here if we want
        path = os.path.join(os.path.dirname(__file__), 'templates/template_authorize.html')
        self.response.out.write(template.render(path, template_values))

#... Using credentials:
class SubscriptionListHandler(webapp2.RequestHandler):
@login_required
def get(self):
    user = users.get_current_user()
    
    if user:
        storage = StorageByKeyName(Credentials, user.user_id(), 'credentials')
        credentials = storage.get()
        
        # Use the new AuthMethod to decorate all the requests with correct credentials
        auth = GAPDecoratorAuthMethod(credentials)
        reader = GoogleReader(auth)
        reader.buildSubscriptionList()
```
