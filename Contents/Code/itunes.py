# -*- coding: utf-8 -*-
from common import *


class iTunesMeta:
    def score_results(self, it_dict, metadata, title, country):
        results = []
        for i, movie in enumerate(it_dict['results']):
            score = 100
            title_penalty = 0
            max_title_penalty = 0
            director_compared = False
            if 'trackName' in movie and is_chinese_cjk(movie['trackName']) is False:
                search_title = clear_text(movie['trackName'])
                title_penalty = scoring.compute_title_penalty(title, search_title)

            score = score - title_penalty
            if metadata.originally_available_at and 'releaseDate' in movie and len(movie['releaseDate']) > 0:
                release_date = Datetime.ParseDate(movie['releaseDate']).date()
                days_diff = abs((metadata.originally_available_at - release_date).days)
                if days_diff == 0:
                    release_penalty = 0
                elif days_diff <= 10:
                    release_penalty = 5
                else:
                    release_penalty = 10
                score = score - release_penalty
                year_penalty = abs(metadata.originally_available_at.year - release_date.year)
                # russian release date are wrong
                if country == 'RU' and year_penalty > 5 and title_penalty < 10:
                    score = score - 5
                else:
                    score = score - year_penalty

            if 'artistName' in movie:
                director_en_penalty=0
                director_ru_penalty=0
                max_en_title_penalty=0
                max_ru_title_penalty=0
                if 'directorsEN' in Dict[metadata.id]:
                    for name in Dict[metadata.id]['directorsEN']:
                        director_en_penalty = scoring.compute_title_penalty(movie['artistName'], name)
                        max_en_title_penalty = max(max_en_title_penalty, director_en_penalty)
                        Log.Debug('artistname = %s, name = %s, penalty = %s', movie['artistName'], name, director_en_penalty)

                if 'directorsRU' in Dict[metadata.id]:
                    for name in Dict[metadata.id]['directorsRU']:
                        director_ru_penalty = scoring.compute_title_penalty(movie['artistName'], name)
                        max_ru_title_penalty = max(max_ru_title_penalty, director_ru_penalty)
                        Log.Debug('artistname = %s, name = %s, penalty = %s', movie['artistName'], name, director_ru_penalty)

                director_penalty = min(max_ru_title_penalty, max_en_title_penalty)
                if director_penalty > 10:
                    director_compared = True

                if director_compared:
                    score = score - 10

                results.append(
                    {'id': movie['trackId'], 'title': search_title,
                     'score': score,
                     'country': country})
            Log.Debug('title_penalty = %s, year_penalty = %s, director_compared = %s, score = %s', title_penalty, year_penalty, director_compared, score)

        results = sorted(results, key=lambda item: item['score'], reverse=True)
        if len(results) > 0:
            return results[0]
        return []

    def make_search(self, result, metadata, title, country):
        if title is not None:
            try:
                it_dict = make_request(url=const.IT_SEARCH % (String.Quote(title.encode('utf-8')), country))
                if it_dict and 'resultCount' in it_dict and it_dict['resultCount'] > 0:
                    result.update(self.score_results(it_dict, metadata, title, country))
            except Exception, e:
                Log.Error('Error while loading page %s (%s)', const.IT_SEARCH % (
                    String.Quote(title.replace(":", "").encode('utf-8')),
                    country
                ), str(e))

    def search_fantv(self, tmdb_id):
        lnk = []
        try:
            page = HTML.ElementFromURL(const.FANTV_LINK % tmdb_id, headers={
                'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36',
                'Accept': 'text/html'
            }, cacheTime=0)
            lnk = page.xpath(const.FANTV_ITUNES)
        except Exception, e:
            Log.Error('Error while loading page %s, (%s)', const.FANTV_LINK % tmdb_id, str(e))

        Log.Debug('lnk = %s', lnk)
        if len(lnk) > 0:
            Log.Debug('urlparse(lnk[0]).query = %s', urlparse(lnk[0]).query)
            params = parse_qs(urlparse(lnk[0]).query)
            Log.Debug('params = %s', params)
            if 'id' in params and len(params['id']) > 0:
                return {'id': params['id'][0], 'score': 100, 'country': 'US'}

        return {'id': 0, 'country': 'US', 'score': 0}

    def search(self, metadata, lang):
        result_dict = []
        titles = []
        countries = ['US', 'RU']

        tmdb_id = get_ext_id(metadata.id, 'tmdb')
        if tmdb_id is not None:
            tmdb_titles = GetTMDBJSON(url=const.TMDB_TITLES % tmdb_id)
            Log.Debug('tmdb_titles=%s',tmdb_titles)
            titles = tmdb_titles['titles'] if 'titles' in tmdb_titles else []

        titles.append({'iso_3166_1': 'RU', 'title': metadata.title})
        titles.append({'iso_3166_1': 'US', 'title': metadata.original_title})

        filtred_titles = [title for title in titles if title['iso_3166_1'] in countries]

        # search acros countries
        @parallelize
        def do_search():
            for title in filtred_titles:
                @task
                def score_search(title=title, rd=result_dict):
                    result = {}
                    self.make_search(result, metadata, title['title'], title['iso_3166_1'])
                    if result:
                        result_dict.append(result)

        Dict[metadata.id] = None
        result_dict.append(self.search_fantv(tmdb_id))
        res = {}
        country = 'RU' if Prefs['image.itunes.prefer_local_art'] is True else ''
        for di in sorted(result_dict, key=lambda d: d['score']):
            res[str(di['id']) + di['country']] = di
        result_dict = sorted(res.values(), key=lambda d: (d['country'] == country, d['score']), reverse=True)
        Log.Debug('result_dict = %s', result_dict)
        result_dict = filter(
            lambda item: int(item['score']) >= (80 if Prefs['image.itunes.prefer_local_art'] is True else 85),
            result_dict)
        Log.Debug('result_dict = %s', result_dict)

        if len(result_dict) > 0:
            return result_dict[0]
        return None

    def update(self, metadata, media, lang, force=False):
        if not force and get_ext_id(metadata.id, 'itunes'):
            itunes = get_ext_id(metadata.id, 'itunes')
        else:
            Log('No iTunes id, searching...')
            it_dict = self.search(metadata, lang)
            # if not empty
            if it_dict is not None:
                # if storage exists
                if Data.Exists(metadata.id):
                    ids = Data.LoadObject(metadata.id)
                    ids['itunes'] = {'id': it_dict['id'], 'country': it_dict['country']}
                    Data.SaveObject(metadata.id, ids)
                # if storage empty
                else:
                    Data.SaveObject(metadata.id, {'itunes': {'id': it_dict['id'], 'country': it_dict['country']}})

    def load_images(self, metadata, valid_art, valid_poster, lang):
        itunes = get_ext_id(metadata.id, 'itunes')
        sort_int = len(valid_poster) + 1
        if itunes is not None and {'id', 'country'} <= set(itunes):
            it_dict = make_request(url=const.IT_LOOKUP % (itunes['id'], itunes['country']))
            if 'resultCount' in it_dict and it_dict['resultCount'] > 0:
                Log.Debug('### iTunes selected title %s', it_dict['results'][0]['trackName'])
                poster_url = it_dict['results'][0]['artworkUrl100'].replace('100x100bb', const.IT_POSTER_SIZE)
                thumb_url = it_dict['results'][0]['artworkUrl100'].replace('100x100bb', const.IT_PREVIEW_SIZE)
                valid_poster.append(poster_url)

                try:
                    metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(thumb_url).content, sort_int)
                except NameError, e:
                    pass