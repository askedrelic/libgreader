#History

##WIP
*

##v0.6 - 2012/08/10
* OAuth2 support
* Deprecating OAuth support
* Added auth support for Google App Engine with GAPDecoratorAuthMethod
* Internal code re-organization

##v0.5 - 2010/12/29
* Added project to PyPi, moved to real Python project structure
* Style cleanup, more tests

##v0.4 - 2010/08/10
Lot of improvements : 

* Manage special feeds (reading-list, shared, starred, friends...)
* Manage categories (get all items, mark as read)
* Manage feeds (get items, unread couts, mark as read, "fetch more")
* Manage items (get and mark read, star, share)

and:

* oauth2 not required if you don't use it
* replacing all xml calls by json ones

##v0.3 - 2010/03/07
* All requests to Google use HTTPS
* CLeaned up formatting, should mostly meet PEP8
* Fixed random unicode issues
* Added licensing

##v0.2 - 2009/10/27
* Moved all get requests to private convenience method
* Added a few more basic data calls

##v0.1 - 2009/10/27
* Connects to GR and receives auth token correctly.
* Pulls down subscription list.
