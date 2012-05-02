#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for oauth and ClientAuthMethod in libgreader. Requires mechanize for automated oauth authenication.

"""

#ClientAuthMethod
#User account I created for testing
username  = 'libgreadertest@gmail.com'
password  = 'libgreadertest'
firstname = 'Foo'

#OAuth
#Actual keys for my domain :/
#Probably not the best to have these public, but fuck it
oauth_key = 'www.asktherelic.com'
oauth_secret = 'WtAfQlY4+MJqsge45b9VuwNn'

#OAuth2
# requires API access tokens from google 
# available at https://code.google.com/apis/console/
# -goto "API Access" and generate a new client id for web applications
try:
    from local_config import *
except Exception:
    pass
