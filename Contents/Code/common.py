# -*- coding: utf-8 -*-
import hashlib
import re
import types
import unicodedata
import ntpath
from urlparse import parse_qs, urlparse
import urllib2
import inspect, os
from jpgparser import JpegImageFile
from qtparse import QtParser
import const
import scoring
import translit
import time
import hashlib
from functools import wraps


# used for retry decorator
class RetryableError(Exception):
    pass

class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    Log.Warn("%s, Retrying in %d seconds..." % (str(e), mdelay))
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry

def GetTMDBJSON(url, cache_time=CACHE_1MONTH):
    return make_request(const.TMDB_BASE_URL % String.Quote(url, True))

    
def make_request(url, headerlist={'Accept': 'application/json'}, cache_time=CACHE_1WEEK):
    json_data = None
    try:
        json_data = JSON.ObjectFromURL(url, timeout=5.0, headers=headerlist, cacheTime=cache_time)
    except Ex.HTTPError, e:
        template = "Unable to load data from url (0). Error code {1}"
        raise RetryableError(template.format(url, e.code))
    except ssl.SSLError, e:
        template = "Unable to load data from url (0). Error args\n{1!r}"
        raise RetryableError(template.format(url, e.args))
    except Exception as e:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        Log.Warn(template.format(type(e).__name__, e.args))
    finally:
        Log.Debug("json = %s", json_data)
        return json_data.get('data', json_data) if json_data is not None else json_data

def req_headers(url):
    r = urllib2.Request(const.KP_HEADER_URL)
    r.get_method = lambda : 'HEAD'
    r.add_header('X-Kinopoisk-Url', url)
    r.add_header('X-Server-ID', Platform.MachineIdentifier) 
    try:
        response = urllib2.urlopen(r)
        response_headers = response.info()
        return {
            'X-SIGNATURE': response_headers.dict.get('x-signature',''),
            'X-TIMESTAMP': response_headers.dict.get('x-timestamp','')
        }

    except urllib2.HTTPError, e:
        return {}

def make_kp_request(url, cache_time=CACHE_1WEEK):
    headerlist = dict({
        'Image-Scale': 1,
        'countryID': 2,
        'cityID': 1,
        'Content-Lang': 'ru',
        'Accept': 'application/json',
		'User-Agent': 'Android client (4.4 / api19), ru.kinopoisk/4.0.2 (52)',
        'device': 'android',
        'Android-Api-Version': 19,
        'clientDate': Datetime.Now().strftime("%H:%M %d.%m.%Y"),
    }, **req_headers(url))
    Log.Debug('headers = %s', headerlist)
    return make_request(url, headerlist, cache_time)


def get_ext_id(meta_id, type):
    if Data.Exists(meta_id):
        ids = Data.LoadObject(meta_id)
        if isinstance(ids, dict) and type in ids:
            return ids[type]
    return None


# clear text from iTunes
def clear_text(s):
    return re.sub(u'[\W_]+', ' ', re.sub(r'\(.*?\)', '', s), 0, re.U).strip()


# check for ascii
def is_ascii(s):
    return s.encode("ascii", "ignore").decode("ascii") == s


# check for digits
def contains_digits(d):
    return bool(const.RE_digits.search(d))


# check for chinese/jap
def is_chinese_cjk(s):
    return bool(const.RE_JAP.search(s))