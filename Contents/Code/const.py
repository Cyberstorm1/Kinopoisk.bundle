# -*- coding: utf-8 -*-
# Kinopoisk
KP_BASE_URL = 'https://ext.kinopoisk.ru/ios/5.0.0'
KP_HEADER_URL = 'http://plex.filmingdata.com/reqh'
RE_YEAR = Regex('([1-2][0-9]{3})')
RE_digits = Regex('\d')
RE_JAP = Regex(ur'[\u2E80-\u9FFF]+')
RE_TR_ID = Regex('-([0-9]+)\.')
#KP_BETA_SEARCH = 'http://plus.kinopoisk.ru/search-suggest/?q=%s&nocookiesupport=yes'
KP_BETA_SEARCH = 'https://suggest-kinopoisk.yandex.net/suggest-kinopoisk?srv=kinopoisk&part=%s&nocookiesupport=yes'
KP_BETA_XPATH = u"//div[* = 'Фильмы']/following-sibling::a[count(preceding-sibling::div)=1]"
KP_BETA_TITLE = ".//span[@class = 'input__suggest-item-title']/text()"
KP_BETA_EN_TITLE = ".//span[@class = 'input__suggest-item-production']/text()"
KP_BETA_LINK = "./@href"
KP_GUESSIT = "http://api.guessit.io/"
KP_MOVIE_SEARCH = '%s/getKPLiveSearch?keyword=%%s' % KP_BASE_URL
KP_MOVIE = '%s/getKPFilmDetailView?filmID=%%s&still_limit=50&sr=1' % KP_BASE_URL
KP_MOVIE_REVIEWS = '%s/getKPReviews?filmID=%%s&type=0&sortType=0' % KP_BASE_URL
KP_MOVIE_REVIEW = ''
KP_MOVIE_STAFF = '%s/getStaffList?type=all&filmID=%%s' % KP_BASE_URL
KP_MOVIE_IMAGES = '%s/getGallery?filmID=%%s' % KP_BASE_URL
KP_TV_SERIES = 'http://www.kinopoisk.ru/film/%s/episodes/'
KP_TRAILERS = 'http://www.kinopoisk.ru/film/%s/video/type/1/'
KP_ACTOR_IMAGE = 'http://st.kp.yandex.net/images/actor_iphone/iphone360_%s.jpg'
KP_IMAGES = 'http://st.kp.yandex.net/images/%s'
KP_MAIN_POSTER = 'http://st.kp.yandex.net/images/film_big/%s.jpg'
KP_MAIN_POSTER_THUMB = 'http://st.kp.yandex.net/images/film_iphone/iphone360_%s.jpg'

GUESSIT_API = 'http://api.guessit.io/?filename=%s&options="type=movie"'

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:27.0) Gecko/20100101 Firefox/27.0',
    'Referer': 'http://beta.kinopoisk.ru/',
    'Accept': 'text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'HOST': 'beta.kinopoisk.ru',
    'X-Requested-With': 'XMLHttpRequest'
}

# Kinopoisk trailers parse
KP_EXTRA_TR = "//table[ancestor::table[2]]//tr[*//a[@onclick] and (*//div[contains(@class,'flag2')] or not(*//div[contains(@class,'flag') and span]))]"
KP_EXTRA_TITLE = ".//div/a[not(@onclick)]/text()"
KP_EXTRA_VIEWS = ".//div//td[5]/text()"
KP_EXTRA_IMG = './/following-sibling::tr[1]//div[@class="listTrailerShare"]/attribute::data-url'
KP_EXTRA_QUAL = ".//following-sibling::tr[2]//tr[*/a[contains(@href,'kp.cdn.yandex.net')]]"

# Kinopoisk TV Series
KP_TV_SEASON = "//table[ancestor::table[3] and (*//td/h1)]"
KP_TV_EPISODE = ".//tr[position()>1 and count(td)>1]"
KP_TV_EPISODE_TITLE = ".//td[1]/h1/b/text()"

# Scoring
SCORE_PENALTY_ITEM_ORDER = 5
SCORE_PENALTY_MAIN_POSTER= 15
SCORE_PENALTY_YEAR = 20
SCORE_PENALTY_TITLE = 40
POSTER_SCORE_MIN_RESOLUTION_PX = 60 * 1000
POSTER_SCORE_MAX_RESOLUTION_PX = 600 * 1000
POSTER_SCORE_BEST_RATIO = 0.7
ART_SCORE_BEST_RATIO = 1.5
ART_SCORE_MIN_RESOLUTION_PX = 200 * 1000
ART_SCORE_MAX_RESOLUTION_PX = 1000 * 1000
IMAGE_SCORE_RESOLUTION_BONUS_MAX = 25
IMAGE_SCORE_RATIO_BONUS_MAX = 45
ARTWORK_ITEM_LIMIT = 2
POSTER_SCORE_RATIO = .3
BACKDROP_SCORE_RATIO = .3

# Plex meta
FREEBASE_URL = 'http://meta.plex.tv/m/%s?lang=%s&ratings=1&reviews=1'
PLEXMOVIE_URL = 'http://meta.plex.tv'
PLEXMOVIE_BASE = 'movie'

# PlexMovie tunables.
INITIAL_SCORE = 100 # Starting value for score before deductions are taken.
PERCENTAGE_PENALTY_MAX = 20.0 # Maximum amount to penalize matches with low percentages.
COUNT_PENALTY_THRESHOLD = 500.0 # Items with less than this value are penalized on a scale of 0 to COUNT_PENALTY_MAX.
COUNT_PENALTY_MAX = 10.0 # Maximum amount to penalize matches with low counts.
FUTURE_RELEASE_DATE_PENALTY = 10.0 # How much to penalize movies whose release dates are in the future.
YEAR_PENALTY_MAX = 10.0 # Maximum amount to penalize for mismatched years.
GOOD_SCORE = 98 # Score required to short-circuit matching and stop searching.
SEARCH_RESULT_PERCENTAGE_THRESHOLD = 80 # Minimum 'percentage' value considered credible for PlexMovie results.

# TheMovieDB
TMDB_BASE_URL = 'http://127.0.0.1:32400/services/tmdb?uri=%s'
TMDB_CONFIG = '/configuration'
TMDB_MOVIE_SEARCH = '/search/movie?query=%s&year=%s&language=%s&include_adult=%s'
TMDB_MOVIE = '/movie/%s?append_to_response=credits,created_by,production_companies,images&language=%s&include_image_language=en,ru,null'
TMDB_TITLES = '/movie/%s/alternative_titles'
TMDB_MOVIE_IMAGES = '/movie/%s/images'

# iTunes search
IT_BASE = 'http://ax.itunes.apple.com/WebObjects/MZStoreServices.woa/wa'
IT_SEARCH = '%s/wsSearch?term=%%s&country=%%s&media=movie' % (IT_BASE)
IT_LOOKUP = '%s/wsLookup?id=%%s&country=%%s' % (IT_BASE)
IT_POSTER_SIZE = '2100x2100bb-92'
IT_PREVIEW_SIZE = '320x480bb-92'

# Fan.TV
FANTV_LINK = 'https://www.fan.tv/movies/%s'
FANTV_ITUNES = "//main//div[@id='play']//a[contains(@data-tooltip,'iTunes')]/attribute::href"

# ChaptersDB
CHAPTERDB_URL       = 'http://chapterdb.plex.tv'
CHAPTERDB_BASE      = 'chapters'
CHAPTERDB_SEARCH    = 'search?title='
API_KEY             = 'O98XUZA7ORFGADJR3L1X'

# PlexChapterDB tunables.
SCORE_TITLE_MATCH         = 50  #Score for exact title match
SCORE_DURATION_MATCH      = 10  #Score for matching duration
SCORE_PER_CONFIRM         = 1   #Score per confirmation
SCORE_CONFIRMATION        = 10  #Maximum confirmation score
SCORE_DURATION_SEMI_CLOSE = 10  #Score for duration being within 10%
SCORE_DURATION_CLOSE      = 10  #Score for duration being close
SCORE_CHAPTER_BEYOND_PART = -30 #Score for having chapters beyond the end of the current part
DURATION_MATCH_VAR        = 3   #seconds by which the duration can be off and still considered a match
DURATION_CLOSE_VAR        = 20  #seconds by which the duration can be off and still considered close
CHAPTER_BEYOND_PART_COUNT = 2   #Number of chapters beyond end of part to affect score

# Trailers
KP_TRAILERS_URL = 'kpru://%s'
TYPE_MAP = {'primary_trailer': TrailerObject,
            'trailer': TrailerObject,
            'interview': InterviewObject,
            'behind_the_scenes': BehindTheScenesObject,
            'scene_or_sample': SceneOrSampleObject}

PLEXMOVIE_EXTRAS_URL = 'http://127.0.0.1:32400/services/iva/metadata/%s?lang=%s&extras=1'
IVA_ASSET_URL = 'iva://api.internetvideoarchive.com/2.0/DataService/VideoAssets(%s)?lang=%s&bitrates=%s&duration=%s&adaptive=%d&dts=%d'
TYPE_ORDER = ['primary_trailer', 'trailer', 'behind_the_scenes', 'interview', 'scene_or_sample']
IVA_LANGUAGES = {-1   : Locale.Language.Unknown,
                 0   : Locale.Language.English,
                 12  : Locale.Language.Swedish,
                 3   : Locale.Language.French,
                 2   : Locale.Language.Spanish,
                 32  : Locale.Language.Dutch,
                 10  : Locale.Language.German,
                 11  : Locale.Language.Italian,
                 9   : Locale.Language.Danish,
                 26  : Locale.Language.Arabic,
                 44  : Locale.Language.Catalan,
                 8   : Locale.Language.Chinese,
                 18  : Locale.Language.Czech,
                 80  : Locale.Language.Estonian,
                 33  : Locale.Language.Finnish,
                 5   : Locale.Language.Greek,
                 15  : Locale.Language.Hebrew,
                 36  : Locale.Language.Hindi,
                 29  : Locale.Language.Hungarian,
                 276 : Locale.Language.Indonesian,
                 7   : Locale.Language.Japanese,
                 13  : Locale.Language.Korean,
                 324 : Locale.Language.Latvian,
                 21  : Locale.Language.Norwegian,
                 24  : Locale.Language.Persian,
                 40  : Locale.Language.Polish,
                 17  : Locale.Language.Portuguese,
                 28  : Locale.Language.Romanian,
                 4   : Locale.Language.Russian,
                 105 : Locale.Language.Slovak,
                 25  : Locale.Language.Thai,
                 64  : Locale.Language.Turkish,
                 493 : Locale.Language.Ukrainian,
                 50  : Locale.Language.Vietnamese}