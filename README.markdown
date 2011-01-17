#libgreader
Python library for working with the unofficial Google Reader API.  
Google may break this at anytime, not my fault.  
Licensed under the MIT license: [http://www.opensource.org/licenses/mit-license.php]()  

Created with help from:  
[http://blog.martindoms.com/2009/08/15/using-the-google-reader-api-part-1/]()  
[http://code.google.com/p/pyrfeed/wiki/GoogleReaderAPI]()  
[http://groups.google.com/group/fougrapi]()

##Usage
The library is currently broken into 2 parts: The Authentication class and the GoogleReader class. 

The Authentication class authenticates itself with Google and then provides a GET/POST method for making authenticated calls.  
Currently, ClientLogin and OAuth are supported.

The GoogleReader class keeps track of user data and provides wrapper methods around known Reader urls.

###ClientLogin
To get started using the ClientLogin auth type, create a new ClientAuth class:

	from libgreader import GoogleReader, ClientAuth, Feed
	auth = ClientAuth('USERNAME','PASSWORD')
	
Then setup GoogleReader:
	
	reader = GoogleReader(auth)
	
Then make whatever requests you want:

	print reader.getUserInfo()
	reader.makeSpecialFeeds()
	feed = reader.getSpecialFeed(reader.READING_LIST)
	print feed.getItems()
	
###OAuth
The OAuth method is a bit more complicated, depending on whether you want to use a callback or not, and because oauth is just complicated.

####No Callback
Send user to authorize with Google in a new window or JS lightbox, tell them to close the window when done authenicating

The oauth key and secret are setup with Google for your domain [https://www.google.com/accounts/ManageDomains]()

	from libgreader import GoogleReader, OAuthMethod, Feed
	auth = OAuthMethod(oauth_key, oauth_secret)

We want to internally set the request token

	auth.setRequestToken()

Get the authorization URL for that request token, which you can link the user to or popup in a new window

	auth_url = auth.buildAuthUrl()

After they have authorized you, set the internal access token, and then you should have access to the user's data

	auth.setAccessToken()
	reader = GoogleReader(auth)
	print reader.getUserInfo()

####Callback
User goes to Google, authenticates, then is automatically redirected to your callback url without using a new window, a much more seamless user experience

Same opening bit, you still need an oauth key and secret from Google

	from libgreader import GoogleReader, OAuthMethod, Feed
	auth = OAuthMethod(oauth_key, oauth_secret)

Set the callback...

	auth.setCallback("http://www.asktherelic.com/theNextStep")

Now the interesting thing with using a callback is that you must split up the process of authenticating the user and store their token data while they leave your site. Whether you use internal sessions or cookies is up to you, but you need access to the token_secret when the user returns from Google.

	token, token_secret = auth.setAndGetRequestToken()
	auth_url = auth.buildAuthUrl()

So assume the user goes, authenticates you, and now they are returning to http://www.asktherelic.com/theNextStep with two query string variables, the token and the verifier. You can now finish authenticating them and access their data.

	#get the token verifier here
	token_verifier = ""
	auth.setAccessTokenFromCallback(token, token_secret, token_verifier)
	reader = GoogleReader(auth)
	print reader.getUserInfo()	

##Etc

Todo:
* Add most url endpoints?. Get a generic "getThisUrl" method
* CLI script using the library?
* More functional tests
* Better usage guide, more docs
