# -*- coding: utf-8 -*-

# libgreader
# Copyright (C) 2012  Matt Behrens <askedrelic@gmail.com>
# Python library for the Google Reader API

__author__  = "Matt Behrens <askedrelic@gmail.com>"
__version__ = "0.6.2"
__copyright__ = "Copyright (C) 2012  Matt Behrens"

from googlereader import GoogleReader
from auth import AuthenticationMethod, ClientAuthMethod, OAuthMethod, OAuth2Method
from items import *
from url import ReaderUrl
