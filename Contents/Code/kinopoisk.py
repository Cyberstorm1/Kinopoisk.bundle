# -*- coding: utf-8 -*-
from common import *


class KPMeta:
    def __init__(self):
        self.is_primary = True
        self.cache_time = 0

    # filter tv shows from search results
    # entries without name and year (people entry)
    def check_entry(self, entry):
        if {'id', 'nameRU', 'year'} <= set(entry) and entry['type'] == 'KPFilmObject':
            if '-' not in entry['year'] and not entry['nameRU'].endswith(
                            (u'(сериал)',) + (u'(мини-сериал)',) if Prefs['data.mini_series'] is False else ()):
                return True
            return False
        return False

    # parse beta search html results
    def parse_result(self, res, i):
        title = res.xpath(const.KP_BETA_TITLE)[0]
        alt_title = res.xpath(const.KP_BETA_EN_TITLE)[0]
        year = None
        if ',' in alt_title:
            alt_title = res.xpath(const.KP_BETA_EN_TITLE)[0].rsplit(', ', 1)[0]
            year = res.xpath(const.KP_BETA_EN_TITLE)[0].rsplit(', ', 1)[1]
        link = res.xpath(const.KP_BETA_LINK)[0]

        return {'nameRU': title, 'nameEN': alt_title, 'year': year, 'id': link[6:-1], 'i': i}

    # make beta search request
    def beta_search(self, result, sc):
        json = {}
        try:
            json = JSON.ObjectFromURL(const.KP_BETA_SEARCH % String.Quote(sc['title'].encode('utf-8'), usePlus=False),
                                      headers=const.HTTP_HEADERS, cacheTime=self.cache_time)
        except Ex.HTTPError, e:
            Log.Warn("Error while loading %s (%s)",
                     const.KP_BETA_SEARCH % String.Quote(sc['title'].encode('utf-8'), usePlus=False), str(e))
        if json.get('content', ''):
            page = HTML.ElementFromString(json['content'])
            if page:
                search_results = []
                for i, res in enumerate(page.xpath(const.KP_BETA_XPATH)):
                    search_results.append(self.parse_result(res, i))
                result.extend(search_results)

    # make search request
    def make_search(self, result, sc):
        # search using original name
        search_result = make_kp_request(
            const.KP_MOVIE_SEARCH % String.Quote(sc['title'].encode('utf-8'), usePlus=False), self.cache_time)
        if type(search_result) is dict and 'items' in search_result:
            result.extend([
                              dict(d, year=d['year'].split('-', 1)[0], i=n) for n, d in
                              enumerate(search_result['items']) if self.check_entry(d)
                              ])

    def make_trans_title(self, title, year, combi):
        trans_name = ""
        # contains ascii - translit
        if is_ascii(title):
            if Prefs['search.use_translit'] is True:
                trans_name = translit.detranslify(title)
                # make translit
                combi.append({'title': trans_name, 'year': year})
            # contains digits
            if Prefs['search.use_digits'] is True and contains_digits(title):
                # make digit2word english
                combi.append({'title': translit.trans_digits(title, True), 'year': year})
                if Prefs['search.use_translit'] is True:
                    # make digit2word russian
                    combi.append({'title': translit.trans_digits(trans_name), 'year': year})
        else:
            if Prefs['search.use_digits'] is True:
                # make digit2word russian
                combi.append({'title': translit.trans_digits(title), 'year': year})

    def guessit_req(self, filename):
        filename = String.Unquote(filename).replace('\\', r'\\')
        file_info = {}
        try:
            Log.Info('### guessit start (%s)', String.Unquote(filename))
            json_data = JSON.StringFromObject({"filename" : filename, "options": "--allowed-languages russian --allowed-languages english --type movie"})
            file_info = JSON.ObjectFromString(HTTP.Request(const.KP_GUESSIT, headers={'Content-Type': 'application/json; charset=UTF-8'}, data=json_data, method='POST').content)
        #file_info = dict(guessit(filename, Log, "--type=movie --name-only --expected-title='%s'" % title))
        except Exception, e:
            Log.Debug("### Couldn't get guessit results (%s)", str(e))
        finally:
            return file_info

    def search(self, results, media, lang, manual):
        Log.Info('### Kinopoisk search start ###')
        search_combinations = []
        scoring_combinations = []
        search_list = []
        # check if we are not primary
        if media.primary_agent is not None:
            Log.Info('### Kinopoisk not primary')
            self.is_primary = False
            # called from kinopoiskru.bundle - result match 100%
            if media.primary_agent == 'com.plexapp.agents.kinopoiskru':
                Log.Info('### Get request from KinopoiskRu (id %s)', media.primary_metadata.id)
                results.Append(MetadataSearchResult(
                    id=media.primary_metadata.id,
                    score=100
                ))
                return  # nothing to do here
            # other bundle - search by title + year
            else:
                search_combinations.append({'title': media.primary_metadata.title, 'year': media.primary_metadata.year})
                search_combinations.append(
                    {'title': media.primary_metadata.original_title, 'year': media.primary_metadata.year})
                scoring_combinations = list(search_combinations)
        else:
            if media.name.startswith('https://www.kinopoisk.ru/film/'):
                kp_id = media.name.split('-')[-1].strip('/')
                if kp_id.isdigit():
                    film_dict = make_kp_request(url=const.KP_MOVIE % kp_id, cache_time=self.cache_time)
                    results.Append(MetadataSearchResult(
                        id=kp_id,
                        name=film_dict['nameRU'],
                        year=int(film_dict.get('year') or 0),
                        lang=lang,
                        score=100
                    ))
                    return
            Log.Info('### Kinopoisk is primary')
            self.is_primary = True
            media_name = unicode(re.sub(r'\[.*?\]', '', media.name)).lower()
            # if no year specified
            if media.year is None:
                year_match = const.RE_YEAR.search(media_name)
                if year_match:
                    year_str = year_match.group(1)
                    year_int = int(year_str)
                    if 1900 < year_int < (Datetime.Now().year + 1) and year_str != media_name:
                        media.year = year_int
                        media_name = media_name.replace(year_str, '')

            search_combinations.append({'title': media_name.lower().strip(), 'year': media.year})
            scoring_combinations = list(search_combinations)
            self.make_trans_title(media_name, media.year, search_combinations)

        # remove duplicates
        search_combinations = [dict(t) for t in set([tuple(d.items()) for d in search_combinations])]
        # set search sources
        search_sources = [self.make_search]
        #if Prefs['search.beta'] == u'Вместо основного':
        #    search_sources = [self.beta_search]
        #elif Prefs['search.beta'] == u'Совместно с основным':
        #    search_sources.append(self.beta_search)

        # make all search requests
        @parallelize
        def do_search():
            for c in search_combinations:
                Log.Debug('### SEARCH ### Quering %s', c)
                for s in search_sources:
                    @task
                    def score_search(c=c, s=s, search_list=search_list):
                        result = []
                        s(result, c)
                        Log.Debug("result = %s", result)
                        if result:
                            search_list.extend(result)

        Log.Debug('search_list = %s', search_list)
        res = {}
        for di in sorted(search_list, key=lambda d: d['i'], reverse=True):
            res[di['id']] = di
        search_list = res.values()
        Log.Debug('search_list = %s', search_list)

        score_list = []

        @parallelize
        def do_score():
            for d in search_list:
                @task
                def calc_score(d=d):
                    score_list.append(dict(
                        d,
                        score=scoring.score_requests(d, scoring_combinations)
                    ))

        search_list = score_list
        Log.Debug('search_list = %s', search_list)

        res = {}
        for di in sorted(search_list, key=lambda d: d['score']):
            res[di['id']] = di
        search_list = res.values()

        for entry in search_list:
            if entry['score'] > 0:
                results.Append(
                    MetadataSearchResult(
                        id=entry['id'],
                        name=entry['nameRU'],
                        year=str(entry['year']),
                        lang=lang,
                        score=entry['score']
                    )
                )

        results.Sort('score', descending=True)

    def update(self, metadata, media, lang, force=False):
        Log.Info('### Kinopoisk update start ###')
        data_to_load = [self.load_main, self.load_staff, self.load_reviews]

        @parallelize
        def loop_data():
            for d in data_to_load:
                @task
                def load_data(d=d, metadata=metadata):
                    d(metadata)

    def load_main(self, metadata):
        film_dict = make_kp_request(url=const.KP_MOVIE % metadata.id, cache_time=self.cache_time)
        if not isinstance(film_dict, dict):
            return None

        # title
        repls = (u' (видео)', u' (ТВ)', u' (мини-сериал)', u' (сериал)')  # remove unnecessary text
        metadata.title = reduce(lambda a, kv: a.replace(kv, ''), repls, film_dict['nameRU'])

        # original title
        if 'nameEN' in film_dict and film_dict['nameEN'] != film_dict['nameRU']:
            metadata.original_title = film_dict['nameEN']

        # slogan
        metadata.tagline = film_dict.get('slogan', '')
        # content rating age
        metadata.content_rating_age = int(film_dict.get('ratingAgeLimits') or 0)
        # year
        metadata.year = int(film_dict.get('year') or 0)

        # countries
        metadata.countries.clear()
        if 'country' in film_dict:
            for country in film_dict['country'].split(', '):
                metadata.countries.add(country)
        # genres
        metadata.genres.clear()
        for genre in film_dict['genre'].split(', '):
            metadata.genres.add(genre.strip().title())
        # content_rating
        metadata.content_rating = film_dict.get('ratingMPAA', '')
        # originally available
        metadata.originally_available_at = Datetime.ParseDate(
            # use world premiere date, or russian premiere
            film_dict['rentData'].get('premiereWorld') or film_dict['rentData'].get('premiereRU'), '%d.%m.%Y'
        ).date() if (('rentData' in film_dict) and
                     [i for i in {'premiereWorld', 'premiereRU'} if i in film_dict['rentData']]
                     ) else None

        # summary
        summary_add = ''
        if 'ratingData' in film_dict and Prefs['data.rating_desc'] is True:
            if 'rating' in film_dict['ratingData']:
                metadata.rating = float(film_dict['ratingData'].get('rating'))
                summary_add = u'КиноПоиск: ' + film_dict['ratingData'].get('rating').__str__()
                if 'ratingVoteCount' in film_dict['ratingData']:
                    summary_add += ' (' + film_dict['ratingData'].get('ratingVoteCount').__str__() + ')'
                summary_add += '. '

            if 'ratingIMDb' in film_dict['ratingData']:
                summary_add += u'IMDb: ' + film_dict['ratingData'].get('ratingIMDb').__str__()
                if 'ratingIMDbVoteCount' in film_dict['ratingData']:
                    summary_add += ' (' + film_dict['ratingData'].get('ratingIMDbVoteCount').__str__() + ')'
                summary_add += '. '

        if summary_add != '':
            summary_add += '\n'
        metadata.summary = summary_add + film_dict.get('description', '')

    def load_staff(self, metadata):
        staff_dict = make_kp_request(url=const.KP_MOVIE_STAFF % metadata.id, cache_time=self.cache_time)
        if not isinstance(staff_dict, dict):
            return None

        metadata.directors.clear()
        metadata.writers.clear()
        metadata.producers.clear()
        metadata.roles.clear()
        for staff_type in staff_dict['creators']:
            for staff in staff_type:
                prole = staff.get('professionKey')
                pname = staff.get('nameRU') if len(staff.get('nameRU')) > 0 else staff.get('nameEN')
                if pname:
                    if prole == 'actor':
                        role = metadata.roles.new()
                        role.name = pname
                        if 'posterURL' in staff:
                            role.photo = const.KP_ACTOR_IMAGE % staff['id']
                        role.role = staff.get('description')
                    elif prole == 'director':
                        director = metadata.directors.new()
                        director.name = pname
                        Log.Debug('pname = %s', pname)
                        Dict[metadata.id]['directorsRU'].append(pname)
                    elif prole == 'writer':
                        writer = metadata.writers.new()
                        writer.name = pname
                    elif prole == 'producer':
                        producer = metadata.producers.new()
                        producer.name = pname

    def load_reviews(self, metadata):
        reviews_dict = make_kp_request(url=const.KP_MOVIE_REVIEWS % metadata.id, cache_time=self.cache_time)
        if not isinstance(reviews_dict, dict):
            return None

        metadata.reviews.clear()
        for review in reviews_dict['reviews']:
            r = metadata.reviews.new()
            r.author = review.get('reviewAutor')
            r.source = 'Kinopoisk'
            r.text = review.get('reviewDescription').replace(u'\x0b', u'')

    def load_main_poster(self, metadata, valid_poster):
        poster_url = const.KP_MAIN_POSTER % metadata.id
        preview_url = const.KP_MAIN_POSTER_THUMB % metadata.id
        req = urllib2.urlopen(poster_url, timeout=10)
        if req.geturl().endswith('no-poster.gif') is False:
            if Prefs['image.kp.main_poster'] is True:
                sort_int = 1
            else:
                sort_int = len(valid_poster) + 1
            valid_poster.append(poster_url)
            try:
                metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(preview_url).content, sort_order=sort_int)
            except NameError, e:
                pass

    def load_images(self, metadata, valid_art, valid_poster, lang):
        # loading image list
        images_dict = make_kp_request(url=const.KP_MOVIE_IMAGES % String.Quote(metadata.id, usePlus=False),
                                      cache_time=self.cache_time)
        # if gallery exists
        if images_dict and 'gallery' in images_dict:
            if 'poster' in images_dict['gallery']:
                Prefs['image.kp.main_poster'] is True and self.load_main_poster(metadata, valid_poster)
                images = []  # list of images

                @parallelize
                def LoadPosters():
                    for img in images_dict['gallery']['poster']:
                        # do load task
                        @task
                        def ScorePoster(img=img, images=images):
                            # parse jpg image file
                            jprs = None
                            try:
                                jprs = JpegImageFile(const.KP_IMAGES % img['image'])
                            except SyntaxError, e:
                                Log.Warn("Error while parsing jpg %s (%s)", const.KP_IMAGES % img['image'], str(e))
                            if jprs and jprs.quality <= 95:
                                images.append({
                                    'url': const.KP_IMAGES % img['image'],
                                    'thumb': const.KP_IMAGES % img['preview'],
                                    'size': jprs.size,
                                    'score': scoring.score_image(jprs.size, jprs.pxcount, 'poster')
                                })

                if len(images) > 0:
                    sort_int = len(valid_poster) + 1
                    images = sorted(images, key=lambda d: d['score'], reverse=True)
                    for i, poster in enumerate(sorted(images, key=lambda k: k['score'], reverse=True)):
                        if i >= int(Prefs['image.kp.max_posters']):
                            break
                        else:
                            valid_poster.append(poster['url'])
                            try:
                                metadata.posters[poster['url']] = Proxy.Preview(
                                    HTTP.Request(poster['thumb']).content,
                                    sort_order=sort_int + i)
                            except NameError, e:
                                pass
            else:
                self.load_main_poster(metadata, valid_poster)

            # loading art. if all sources or emty data
            if 'kadr' in images_dict['gallery']:
                # load img meta in parallel
                images = []  # list of images

                @parallelize
                def LoadArts():
                    for img in images_dict['gallery']['kadr']:
                        # do load task
                        @task
                        def ScoreArt(img=img, images=images):
                            # parse jpg image file
                            jprs = JpegImageFile(const.KP_IMAGES % img['image'])
                            if jprs.quality <= 95:
                                images.append({
                                    'url': const.KP_IMAGES % img['image'],
                                    'thumb': const.KP_IMAGES % img['preview'],
                                    'size': jprs.size,
                                    'score': scoring.score_image(jprs.size, jprs.pxcount, 'art')
                                })

                if len(images) > 0:
                    sort_int = len(valid_art) + 1
                    images = sorted(images, key=lambda d: d['score'], reverse=True)
                    for i, backdrop in enumerate(sorted(images, key=lambda k: k['score'], reverse=True)):
                        if i >= int(Prefs['image.kp.max_backdrops']):
                            break
                        else:
                            valid_art.append(backdrop['url'])
                            try:
                                metadata.art[backdrop['url']] = Proxy.Preview(
                                    HTTP.Request(backdrop['thumb']).content,
                                    sort_order=sort_int + i)
                            except NameError, e:
                                pass

        # there is no images, but we need poster
        else:
            self.load_main_poster(metadata, valid_poster)

    def extras(self, metadata, lang):
        page = {}
        try:
            page = HTML.ElementFromURL(const.KP_TRAILERS % metadata.id, headers={
                'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36',
                'Accept': 'text/html'
            }, cacheTime=self.cache_time)
        except Ex.HTTPError, e:
            Log.Warn("Error while loading %s (%s)", const.KP_TRAILERS % metadata.id, str(e))

        if len(page) != 0:
            trailers = []  # trailers dict
            for tr in page.xpath(const.KP_EXTRA_TR):  # loop over trailers
                tr_info = {
                    'title': tr.xpath(const.KP_EXTRA_TITLE)[0],
                    'views': tr.xpath(const.KP_EXTRA_VIEWS)[0].replace(u'\xa0', u''),
                    'data': [],
                    'img_id': tr.xpath(const.KP_EXTRA_IMG)[0].split('/')[-2]}

                @parallelize
                def load_qual():
                    for quol in tr.xpath(const.KP_EXTRA_QUAL):  # loop over quality
                        @task
                        def parse_qual(tr_info=tr_info, trailers=trailers):
                            # get trailer link. support only mp4/mov
                            tr_link = quol.xpath('.//td[3]/a/attribute::href')[0].split('link=')[-1]
                            if tr_link.split('.')[-1] in {'mp4', 'mov'}:
                                try:
                                    qtp = QtParser()
                                    if qtp.openurl(tr_link):
                                        tr_data = qtp.analyze()
                                        tr_info['data'].append({
                                            'streams': tr_data['streams'],
                                            'audio': tr_data['audio'],
                                            'video': tr_data['video'],
                                            'bt': int(tr_data['bitrate']),
                                            'dr': int(tr_data['playtime_seconds']),
                                            'lnk': tr_link,
                                            'id': const.RE_TR_ID.search(tr_link).group(1)
                                        })
                                except:
                                    pass

                trailers.append(tr_info)

            trailers = sorted(trailers, key=lambda k: (len(k['data']), int(k['views'] or 0)), reverse=True)

            extras = []
            for i, trailer in enumerate(trailers):
                if i >= int(Prefs['video.kp.max']):
                    break
                else:
                    extra_type = 'trailer'
                    spoken_lang = 'ru'
                    trailer_json = JSON.StringFromObject(trailer['data'])
                    extras.append({'type': extra_type,
                                   'lang': spoken_lang,
                                   'extra': const.TYPE_MAP[extra_type](
                                       url=const.KP_TRAILERS_URL % String.Encode(trailer_json),
                                       title=trailer['title'],
                                       year=None,
                                       originally_available_at=None,
                                       thumb='http://kp.cdn.yandex.net/%s/3_%s.jpg' % (
                                           metadata.id, trailer['img_id']))})

            for extra in extras:
                metadata.extras.add(extra['extra'])
