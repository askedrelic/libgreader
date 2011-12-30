#libgreader
Python library for working with the unofficial Google Reader API.  
Google may break this at anytime, not my fault.  
Licensed under the MIT license: [http://www.opensource.org/licenses/mit-license.php]()  

Created with help from:  
[http://blog.martindoms.com/2009/08/15/using-the-google-reader-api-part-1/]()  
[http://code.google.com/p/pyrfeed/wiki/GoogleReaderAPI]()  
[http://groups.google.com/group/fougrapi]()

See Usage.md for further detailed instructions.

###Contributions

Want to contribute?

First, fork the repository on Github to make changes on your branch.
Then, create a dev environment using a virtualenv:

	$ pip install virtualenvwrapper
	$ mkvirtualenv libgreader --no-site-packages

Clone your fork and install the development requirements, required for running the tests:

	$ pip install -r dev_requirements.txt

Then run the tests:

	$ python setup.py test

Now hack away! Write tests which show that a bug was fixed or that the feature works as expected. Then send a pull request and bug me until it gets merged in and published.

###TODO

* Add most url endpoints?
* CLI script using the library?
* More functional tests
* Better usage guide, more docs
