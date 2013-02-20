# -*- coding: utf-8 -*-

from requests.compat import quote

from .url import ReaderUrl

class ItemsContainer(object):
    """
    A base class used for all classes aimed to have items (Categories and Feeds)
    """
    def __init__(self):
        self.items          = []
        self.itemsById      = {}
        self.lastLoadOk     = False
        self.lastLoadLength = 0
        self.lastUpdated    = None
        self.unread         = 0
        self.continuation   = None

    def _getContent(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        Get content from google reader with specified parameters.
        Must be overladed in inherited clases
        """
        return None

    def loadItems(self, excludeRead=False, loadLimit=20, since=None, until=None):
        """
        Load items and call itemsLoadedDone to transform data in objects
        """
        self.clearItems()
        self.loadtLoadOk    = False
        self.lastLoadLength = 0
        self._itemsLoadedDone(self._getContent(excludeRead, None, loadLimit, since, until))

    def loadMoreItems(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        Load more items using the continuation parameters of previously loaded items.
        """
        self.lastLoadOk     = False
        self.lastLoadLength = 0
        if not continuation and not self.continuation:
            return
        self._itemsLoadedDone(self._getContent(excludeRead, continuation or self.continuation, loadLimit, since, until))

    def _itemsLoadedDone(self, data):
        """
        Called when all items are loaded
        """
        if data is None:
            return
        self.continuation   = data.get('continuation', None)
        self.lastUpdated    = data.get('updated', None)
        self.lastLoadLength = len(data.get('items', []))
        self.googleReader.itemsToObjects(self, data.get('items', []))
        self.lastLoadOk = True

    def _addItem(self, item):
        self.items.append(item)
        self.itemsById[item.id] = item

    def getItem(self, id):
        return self.itemsById[id]

    def clearItems(self):
        self.items        = []
        self.itemsById    = {}
        self.continuation = None

    def getItems(self):
        return self.items

    def countItems(self, excludeRead=False):
        if excludeRead:
            sum([1 for item in self.items if item.isUnread()])
        else:
            return len(self.items)

    def markItemRead(self, item, read):
        if read and item.isUnread():
            self.unread -= 1
        elif not read and item.isRead():
            self.unread += 1

    def markAllRead(self):
        self.unread = 0
        for item in self.items:
            item.read = True
            item.canUnread = False
        result = self.googleReader.markFeedAsRead(self)
        return result.upper() == 'OK'

    def countUnread(self):
        self.unread = self.countItems(excludeRead=True)

class Category(ItemsContainer):
    """
    Class for representing a category
    """
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "<%s (%d), %s>" % (self.label, self.unread, self.id)

    def __init__(self, googleReader, label, id):
        """
         :param label: (str)
         :param id: (str)
        """
        super(Category, self).__init__()
        self.googleReader = googleReader

        self.label = label
        self.id    = id

        self.feeds  = []

        self.fetchUrl = ReaderUrl.CATEGORY_URL + Category.urlQuote(self.label)

    def _addFeed(self, feed):
        if not feed in self.feeds:
            self.feeds.append(feed)
            try:
                self.unread += feed.unread
            except:
                pass

    def getFeeds(self):
        return self.feeds

    def _getContent(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        return self.googleReader.getCategoryContent(self, excludeRead, continuation, loadLimit, since, until)

    def countUnread(self):
        self.unread = sum([feed.unread for feed in self.feeds])

    def toArray(self):
        pass

    def toJSON(self):
        pass

    @staticmethod
    def urlQuote(string):
        """ Quote a string for being used in a HTTP URL """
        return quote(string.encode("utf-8"))

class BaseFeed(ItemsContainer):
    """
    Class for representing a special feed.
    """
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "<%s, %s>" % (self.title, self.id)

    def __init__(self, googleReader, title, id, unread, categories=[]):
        """
         :param title: (str, name of the feed)
         :param id: (str, id for google reader)
         :param unread: (int, number of unread items, 0 by default)
         :param categories: (list) - list of all categories a feed belongs to, can be empty
        """
        super(BaseFeed, self).__init__()

        self.googleReader = googleReader

        self.id    = id
        self.title = title
        self.unread = unread

        self.categories = []
        for category in categories:
            self.addCategory(category)

        self.continuation = None

    def addCategory(self, category):
        if not category in self.categories:
            self.categories.append(category)
            category._addFeed(self)

    def getCategories(self):
        return self.categories

    def _getContent(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        return self.googleReader.getFeedContent(self, excludeRead, continuation, loadLimit, since, until)

    def markItemRead(self, item, read):
        super(BaseFeed, self).markItemRead(item, read)
        for category in self.categories:
            category.countUnread()

    def markAllRead(self):
        self.unread = 0
        for category in self.categories:
            category.countUnread()
        return super(BaseFeed, self).markAllRead()

    def toArray(self):
        pass

    def toJSON(self):
        pass

class SpecialFeed(BaseFeed):
    """
    Class for representing specials feeds (starred, shared, friends...)
    """
    def __init__(self, googleReader, type):
        """
        type is one of ReaderUrl.SPECIAL_FEEDS
        """
        super(SpecialFeed, self).__init__(
            googleReader,
            title      = type,
            id         = ReaderUrl.SPECIAL_FEEDS_PART_URL+type,
            unread     = 0,
            categories = [],
        )
        self.type = type

        self.fetchUrl = ReaderUrl.CONTENT_BASE_URL + Category.urlQuote(self.id)

class Feed(BaseFeed):
    """
    Class for representing a normal feed.
    """

    def __init__(self, googleReader, title, id, siteUrl=None, unread=0, categories=[]):
        """
        :param title: str name of the feed
        :param id: str, id for google reader
        :param siteUrl: str, can be empty
        :param unread: int, number of unread items, 0 by default
        :param categories: (list) - list of all categories a feed belongs to, can be empty
        """
        super(Feed, self).__init__(googleReader, title, id, unread, categories)

        self.feedUrl = self.id.lstrip('feed/')
        self.siteUrl = siteUrl

        self.fetchUrl = ReaderUrl.FEED_URL + Category.urlQuote(self.id)

class Item(object):
    """
    Class for representing an individual item (an entry of a feed)
    """
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return '<"%s" by %s, %s>' % (self.title, self.author, self.id)

    def __init__(self, googleReader, item, parent):
        """
        :param item: An item loaded from json
        :param parent: the object (Feed of Category) containing the Item
        """
        self.googleReader = googleReader
        self.parent = parent

        self.data   = item # save original data for accessing other fields
        self.id     = item['id']
        self.title  = item.get('title', '(no title)')
        self.author = item.get('author', None)
        self.content = item.get('content', item.get('summary', {})).get('content', '')
        self.origin  = { 'title': '', 'url': ''}
        if 'crawlTimeMsec' in item:
            self.time = int(item['crawlTimeMsec']) // 1000
        else:
            self.time = None

        # check original url
        self.url    = None
        for alternate in item.get('alternate', []):
            if alternate.get('type', '') == 'text/html':
                self.url = alternate['href']
                break

        # check status
        self.read    = False
        self.starred = False
        self.shared  = False
        for category in item.get('categories', []):
            if category.endswith('/state/com.google/read'):
                self.read = True
            elif category.endswith('/state/com.google/starred'):
                self.starred = True
            elif category in ('user/-/state/com.google/broadcast',
                              'user/%s/state/com.google/broadcast' % self.googleReader.userId):
                self.shared = True

        self.canUnread = item.get('isReadStateLocked', 'false') != 'true'

        # keep feed, can be used when item is fetched from a special feed, then it's the original one
        try:
            f = item['origin']
            self.origin = {
                'title': f.get('title', ''),
                'url': f.get('htmlUrl', ''),
            }
            self.feed = self.googleReader.getFeed(f['streamId'])
            if not self.feed:
                raise
            if not self.feed.title and 'title' in f:
                self.feed.title = f['title']
        except:
            try:
                self.feed = Feed(self, f.get('title', ''), f['streamId'], f.get('htmlUrl', None), 0, [])
                try:
                    self.googleReader._addFeed(self.feed)
                except:
                    pass
            except:
                self.feed = None

        self.parent._addItem(self)

    def isUnread(self):
        return not self.read

    def isRead(self):
        return self.read

    def markRead(self, read=True):
        self.parent.markItemRead(self, read)
        self.read = read
        if read:
            result = self.googleReader.addItemTag(self, ReaderUrl.TAG_READ)
        else:
            result = self.googleReader.removeItemTag(self, ReaderUrl.TAG_READ)
        return result.upper() == 'OK'

    def markUnread(self, unread=True):
        return self.markRead(not unread)

    def isShared(self):
        return self.shared

    def markShared(self, shared=True):
        self.shared = shared
        if shared:
            result = self.googleReader.addItemTag(self, ReaderUrl.TAG_SHARED)
        else:
            result = self.googleReader.removeItemTag(self, ReaderUrl.TAG_SHARED)
        return result.upper() == 'OK'

    def share(self):
        return self.markShared()

    def unShare(self):
        return self.markShared(False)

    def isStarred(self):
        return self.starred

    def markStarred(self, starred=True):
        self.starred = starred
        if starred:
            result = self.googleReader.addItemTag(self, ReaderUrl.TAG_STARRED)
        else:
            result = self.googleReader.removeItemTag(self, ReaderUrl.TAG_STARRED)
        return result.upper() == 'OK'

    def star(self):
        return self.markStarred()

    def unStar(self):
        return self.markStarred(False)
