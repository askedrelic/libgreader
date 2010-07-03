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

The Authentication class authenticates itself and then provides a GET/POST method for making authenticated calls to Reader. Currently, ClientLogin and OAuth are supported.

The GoogleReader class keeps of user data and all provides wrapper methods around Reader urls.

To get started using the ClientLogin auth type, create a new ClientAuth class:

	from libgreader import GoogleReader, ClientAuth, Feed

	auth = ClientAuth('USERNAME','PASSWORD')
	
Then setup GoogleReader:
	
	reader = GoogleReader(auth)
	
Then make whatever requests you want:

	print reader.getUserInfo()
	print reader.getReadingList()

##Etc

Todo:

* Add most APIs?. Get a generic "getThisUrl" method
* Add to PyPi
* CLI script using the library?
* Move to setup/distribute package 
* More tests

History:

* v0.3 -- 2010/03/07
    * All requests to Google use HTTPS
    * CLeaned up formatting, should mostly meet PEP8
    * Fixed random unicode issues
    * Added licensing

* v0.2 -- 2009/10/27
	* Moved all get requests to private convenience method
	* Added a few more basic data calls

* v0.1 -- 2009/10/27
	* Connects to GR and receives auth token correctly.
	* Pulls down subscription list.