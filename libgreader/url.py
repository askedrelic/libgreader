# -*- coding: utf-8 -*-

class ReaderUrl(object):
    READER_BASE_URL        = 'https://www.google.com/reader/api'
    API_URL                = READER_BASE_URL + '/0/'

    ACTION_TOKEN_URL       = API_URL + 'token'
    USER_INFO_URL          = API_URL + 'user-info'

    SUBSCRIPTION_LIST_URL  = API_URL + 'subscription/list'
    SUBSCRIPTION_EDIT_URL  = API_URL + 'subscription/edit'
    UNREAD_COUNT_URL       = API_URL + 'unread-count'

    CONTENT_PART_URL       = 'stream/contents/'
    CONTENT_BASE_URL       = API_URL + CONTENT_PART_URL
    SPECIAL_FEEDS_PART_URL = 'user/-/state/com.google/'

    READING_LIST           = 'reading-list'
    READ_LIST              = 'read'
    KEPTUNREAD_LIST        = 'kept-unread'
    STARRED_LIST           = 'starred'
    SHARED_LIST            = 'broadcast'
    NOTES_LIST             = 'created'
    FRIENDS_LIST           = 'broadcast-friends'
    SPECIAL_FEEDS          = (READING_LIST, READ_LIST, KEPTUNREAD_LIST,
                              STARRED_LIST, SHARED_LIST, FRIENDS_LIST,
                              NOTES_LIST,)

    FEED_URL               = CONTENT_BASE_URL
    CATEGORY_URL           = CONTENT_BASE_URL + 'user/-/label/'

    EDIT_TAG_URL           = API_URL + 'edit-tag'
    TAG_READ               = 'user/-/state/com.google/read'
    TAG_STARRED            = 'user/-/state/com.google/starred'
    TAG_SHARED             = 'user/-/state/com.google/broadcast'

    MARK_ALL_READ_URL      = API_URL + 'mark-all-as-read'
