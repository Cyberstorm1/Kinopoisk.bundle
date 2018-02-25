from Framework.api.logkit import LogKit
from Framework import exceptions as Ex
from Framework.api import utilkit, datakit, parsekit, networkkit, modelkit, localekit
from Framework.objects import MetadataSearchResult

Log = LogKit
Hash = utilkit.HashKit
Datetime = utilkit.DatetimeKit
Data = datakit.DataKit
Dict = datakit.DictKit
String = utilkit.StringKit
Regex = utilkit.RegexKit
JSON = parsekit.JSONKit
HTML = parsekit.HTMLKit
XML = parsekit.XMLKit
Util = utilkit.UtilKit
HTTP = networkkit.HTTPKit
Proxy = modelkit.ProxyKit
Locale = localekit.LocaleKit
Prefs = {}
CACHE_1MINUTE = 60
CACHE_1HOUR = CACHE_1MINUTE * 60
CACHE_1DAY = CACHE_1HOUR * 24
CACHE_1WEEK = CACHE_1DAY * 7
CACHE_1MONTH = CACHE_1DAY * 30
