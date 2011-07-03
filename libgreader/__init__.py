# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.
Google may break this at anytime, I am not responsible for damages from that
breakage, but I will try my best to fix it.

Uses HTTPS for all requests to and from Google.

Licensing included in LICENSE.txt
"""

__author__  = "Matt Behrens <askedrelic@gmail.com>"
__version__ = "0.6.0beta1"
__credits__ = "Matt Behrens <askedrelic@gmail.com>, Stephane Angel aka Twidi <s.angel@twidi.com>"

from googlereader import GoogleReader
from auth import AuthenticationMethod, ClientAuthMethod, OAuthMethod
from items import *
from url import ReaderUrl
