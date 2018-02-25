# -*- coding: utf-8 -*-
from common import *


class MDMeta:
    def safe_unicode(self, s, encoding='utf-8'):
        if s is None:
            return None
        if isinstance(s, basestring):
            if isinstance(s, types.UnicodeType):
                return s
            else:
                return s.decode(encoding)
        else:
            return str(s).decode(encoding)

    def identifierize(self, string):
        string = re.sub(r"\s+", " ", string.strip())
        string = unicodedata.normalize('NFKD', self.safe_unicode(string))
        string = re.sub(r"['\"!?@#$&%^*\(\)_+\.,;:/]", "", string)
        string = re.sub(r"[_ ]+", "_", string)
        string = string.strip('_')
        return string.strip().lower()

    def guidize(self, string):
        hash = hashlib.sha1()
        hash.update(string.encode('utf-8'))
        return hash.hexdigest()

    def titleyear_guid(self, title, year):
        if title is None:
            title = ''

        if year == '' or year is None or not year:
            string = "%s" % self.identifierize(title)
        else:
            string = "%s_%s" % (self.identifierize(title).lower(), year)
        return self.guidize("%s" % string)

    def meta_search(self, matches, title, year):
        titleyear_guid = self.titleyear_guid(title, year)
        url = '%s/%s/guid/%s/%s.xml' % (const.PLEXMOVIE_URL, const.PLEXMOVIE_BASE, titleyear_guid[0:2], titleyear_guid)
        try:
            res = XML.ElementFromURL(url, cacheTime=CACHE_1WEEK, headers={'Accept-Encoding': 'gzip'})

            for match in res.xpath('//match'):
                id = "tt%s" % match.get('guid')
                name = self.safe_unicode(match.get('title'))
                year = self.safe_unicode(match.get('year'))
                count = int(match.get('count'))
                pct = int(match.get('percentage', 0))
                dist = Util.LevenshteinDistance(title, name.encode('utf-8'))

                # Intialize.
                if not matches.has_key(id):
                    matches[id] = [1000, '', None, 0, 0, 0]

                # Tally.
                vector = matches[id]
                vector[3] = vector[3] + pct
                vector[4] = vector[4] + count

                # See if a better name.
                if dist < vector[0]:
                    vector[0] = dist
                    vector[1] = name
                    vector[2] = year

        except Exception, e:
            Log("freebase/proxy lookup failed: %s" % str(e))

    def score_matches(self, metadata, matches):
        Log('Scoring ' + str(matches))

        for key in matches.keys():
            match = matches[key]

            dist = match[0]
            name = match[1]
            year = match[2]
            total_pct = match[3]
            total_cnt = match[4]

            # Compute score penalty for percentage/count.
            score_penalty = (100 - total_pct) * (const.PERCENTAGE_PENALTY_MAX / 100)
            if total_cnt < const.COUNT_PENALTY_THRESHOLD:
                score_penalty += (
                                     const.COUNT_PENALTY_THRESHOLD - total_cnt) / const.COUNT_PENALTY_THRESHOLD * const.COUNT_PENALTY_MAX

            # Year penalty/bonus.
            try:
                if year and int(year) > Datetime.Now().year:
                    score_penalty += const.FUTURE_RELEASE_DATE_PENALTY

                if metadata.year and year:
                    per_year_penalty = int(const.YEAR_PENALTY_MAX / 3)
                    year_delta = abs(int(metadata.year) - (int(year)))
                    if year_delta > 3:
                        score_penalty += const.YEAR_PENALTY_MAX
                    else:
                        score_penalty += year_delta * per_year_penalty
            except Exception, e:
                Log('Exception applying year penalty/bonus (%s)', str(e))

            # Store the final score in the result vector.
            matches[key][5] = int(const.INITIAL_SCORE - dist - score_penalty)

    def get_best_name_and_year(self, guid, lang, fallback, fallback_year, best_name_map, no_force=False):
        url = const.FREEBASE_URL % (guid, lang)
        ret = (fallback, fallback_year)

        if no_force:
            url += '&force=-1'

        try:
            movie = XML.ElementFromURL(url, cacheTime=CACHE_1WEEK, headers={'Accept-Encoding': 'gzip'})
            movieEl = movie.xpath('//movie')[0]

            # Sometimes we have a good hash or title/year lookup result, but no detailed Freebase XML.
            # Detect this and bail gracefully: trying to improve the title makes things worse.
            #
            if len(movieEl.xpath('//title')) == 0:
                Log('No details found in Freebase XML, using fallback title and year.')
                return None, None

            if movieEl.get('originally_available_at'):
                fallback_year = int(movieEl.get('originally_available_at').split('-')[0])

            lang_match = False
            for movie in movie.xpath('//title'):
                if lang == movie.get('lang'):
                    ret = (movie.get('title'), fallback_year)
                    lang_match = True

            # Default to the English title.
            if not lang_match:
                ret = (movieEl.get('title'), fallback_year)

            # Note that we returned a pristine name.
            best_name_map['tt' + guid] = True
            return ret

        except Exception, e:
            Log("Error getting best name. %s", str(e))

        return ret

    def score_results(self, tmdb_dict, metadata):
        results = []
        for i, movie in enumerate(sorted(tmdb_dict['results'], key=lambda k: k['popularity'], reverse=True)):
            score = 100

            original_title_penalty = 0
            if metadata.original_title and 'original_title' in movie and is_chinese_cjk(
                    movie['original_title']) is False:
                original_title_penalty = scoring.compute_title_penalty(metadata.original_title,
                                                                       movie['original_title'])
            # if original title = translated title and != russian title - movie is not translated
            if movie['original_title'] == movie['title'] and movie['title'] != metadata.title:
                title_penalty = 0
            else:
                title_penalty = scoring.compute_title_penalty(metadata.title, movie['title'])
            score = score - title_penalty - original_title_penalty

            if metadata.originally_available_at and 'release_date' in movie and len(movie['release_date']) > 0:
                release_date = Datetime.ParseDate(movie['release_date']).date()
                days_diff = abs((metadata.originally_available_at - release_date).days)
                if days_diff == 0:
                    release_penalty = 0
                elif days_diff <= 10:
                    release_penalty = 5
                else:
                    release_penalty = 10
                score = score - release_penalty
                score = score - abs(metadata.originally_available_at.year - release_date.year)

            results.append({'id': movie['id'], 'title': movie['title'], 'score': score})

        results = sorted(results, key=lambda item: item['score'], reverse=True)
        if len(results) > 0:
            return results[0]
        return {}

    def make_search(self, result, metadata, title, year, lang):
        if title is not None:
            try:
                tmdb_dict = GetTMDBJSON(
                    url=const.TMDB_MOVIE_SEARCH % (
                        String.Quote(title.replace(":", "").encode('utf-8')),
                        year,
                        lang,
                        False
                    )
                )
                if tmdb_dict and 'total_results' in tmdb_dict and tmdb_dict['total_results'] > 0:
                    result.update(self.score_results(tmdb_dict, metadata))
            except Exception, e:
                Log.Error('Error while loading page %s (%s)', const.TMDB_MOVIE_SEARCH % (
                    String.Quote(title.replace(":", "").encode('utf-8')),
                    year,
                    lang,
                    False
                ), str(e))

    def make_tmdb_search(self, metadata, lang):
        result_dict = []
        search_combinations = [
            {'title': metadata.title, 'year': metadata.year},
            {'title': metadata.title, 'year': ''},
            {'title': metadata.title.replace(u'ё', u'е'), 'year': metadata.year},
            {'title': metadata.title.replace(u'ё', u'е'), 'year': ''},
            {'title': metadata.original_title.replace("'s", "") if metadata.original_title else None,
             'year': metadata.year},
            {'title': metadata.original_title.replace("'s", "") if metadata.original_title else None, 'year': ''}
        ]

        @parallelize
        def do_search():
            for s in search_combinations:
                @task
                def score_search(s=s, rd=result_dict):
                    result = {}
                    self.make_search(result, metadata, s['title'], s['year'], lang)
                    if result:
                        result_dict.append(result)

        res = {}
        for di in sorted(result_dict, key=lambda d: d['score'], reverse=True):
            res[di['id']] = di
        result_dict = res.values()

        if len(result_dict) > 0:
            # will give a chance
            if result_dict[0].get('score', 0) < 85:
                result_dict[0]['score'] = result_dict[0]['score'] + 5
            if result_dict[0].get('score', 0) >= 85:
                return result_dict[0]['id']
            return None
        return None

    def search(self, metadata, lang):
        search_matches = {}
        lockedNameMap = {}
        bestHitScore = 0
        tmdb_id = 0
        continueSearch = True
        results = []

        if metadata.original_title is not None:
            self.meta_search(search_matches, metadata.original_title, metadata.year)
            Log.Debug('search_matches =%s', search_matches)
            self.score_matches(metadata, search_matches)

            # Add scored title year results to search results.
            for key in search_matches.keys():
                match = search_matches[key]
                if int(match[3]) >= const.SEARCH_RESULT_PERCENTAGE_THRESHOLD:
                    best_name, year = self.get_best_name_and_year(key[2:], lang, match[1], match[2], lockedNameMap,
                                                                  True)
                    if best_name is not None and year is not None:
                        Log("Adding title_year match: %s (%s) score=%d, key=%s" % (best_name, year, match[5], key))
                        results.append(
                            MetadataSearchResult(id=key, name=best_name, year=year, lang=lang, score=match[5]))
                        if bestHitScore < match[5]:
                            bestHitScore = match[5]
                else:
                    Log("Skipping title/year match (doesn\'t meet percentage threshold): %s (%s) percentage=%d" % (
                        match[1], match[2], match[3]))

            if bestHitScore >= const.GOOD_SCORE:
                Log('Found perfect match with title/year query.')
                tmdb_id = results[0].id
                continueSearch = False

        if continueSearch:
            tmdb_id = self.make_tmdb_search(metadata, lang)

        return tmdb_id

    def update(self, metadata, media, lang, force=False):
        if not force and get_ext_id(metadata.id, 'tmdb') is not None:
            tmdb_id = get_ext_id(metadata.id, 'tmdb')
            Log('TMDB id exists, using (%s)', tmdb_id)
        else:
            tmdb_id = self.search(metadata, lang)
            Log('No TMDB id, searching...')

        if tmdb_id is not None:
            tmdb_dict = GetTMDBJSON(url=const.TMDB_MOVIE % (tmdb_id, lang))
            imdb_id = tmdb_dict['imdb_id']
            tmdb_id = tmdb_dict['id']

            Log.Debug('### TheMovieDB selected title %s', tmdb_dict['title'])

            if Data.Exists(metadata.id) is False:
                Data.SaveObject(metadata.id, {'tmdb': tmdb_id, 'imdb': imdb_id})
            else:
                ids = Data.LoadObject(metadata.id)
                ids['tmdb'] = tmdb_id
                ids['imdb'] = imdb_id
                Data.SaveObject(metadata.id, ids)

            if 'production_companies' in tmdb_dict and len(tmdb_dict['production_companies']) > 0:
                metadata.studio = tmdb_dict['production_companies'][0]['name']

            if 'production_countries' in tmdb_dict and len(tmdb_dict['production_countries']) > 0:
                Dict[metadata.id]['countries'] = tmdb_dict['production_countries']

            if Prefs['data.collections'] is True and 'belongs_to_collection' in tmdb_dict and tmdb_dict['belongs_to_collection']:
                metadata.collections.clear()
                metadata.collections.add(tmdb_dict['belongs_to_collection']['name'])

            if Prefs['data.actors_eng'] is True:
                config_dict = GetTMDBJSON(url=const.TMDB_CONFIG, cache_time=CACHE_1WEEK * 2)
                # Crew.
                metadata.directors.clear()
                metadata.writers.clear()
                metadata.producers.clear()

                for member in tmdb_dict['credits']['crew']:
                    if member['job'] == 'Director':
                        director = metadata.directors.new()
                        director.name = member['name']
                        Dict[metadata.id]['directorsEN'].append(member['name'])
                    elif member['job'] in ('Writer', 'Screenplay'):
                        writer = metadata.writers.new()
                        writer.name = member['name']
                    elif member['job'] == 'Producer':
                        producer = metadata.producers.new()
                        producer.name = member['name']

                # Cast.
                metadata.roles.clear()

                for member in sorted(tmdb_dict['credits']['cast'], key=lambda k: k['order']):
                    role = metadata.roles.new()
                    role.role = member['character']
                    role.name = member['name']
                    if member['profile_path'] is not None:
                        role.photo = config_dict['images']['base_url'] + 'original' + member['profile_path']
            else:
                for member in tmdb_dict['credits']['crew']:
                    if member['job'] == 'Director':
                        Dict[metadata.id]['directorsEN'].append(member['name'])

    def load_images(self, metadata, valid_art, valid_poster, lang):
        tmdb_images_dict = {}
        tmdb_id = get_ext_id(metadata.id, 'tmdb')
        if tmdb_id is not None:
            tmdb_images_dict = GetTMDBJSON(url=const.TMDB_MOVIE_IMAGES % tmdb_id)
        if tmdb_images_dict:
            config_dict = GetTMDBJSON(url=const.TMDB_CONFIG, cache_time=CACHE_1WEEK * 2)
            if tmdb_images_dict['posters']:
                max_average = max([(lambda p: float(p['vote_average']) or 5)(p) for p in tmdb_images_dict['posters']])
                max_count = max([(lambda p: float(p['vote_count']))(p) for p in tmdb_images_dict['posters']]) or 1

                for i, poster in enumerate(tmdb_images_dict['posters']):
                    score = (float(poster['vote_average']) / max_average) * const.POSTER_SCORE_RATIO
                    score += (float(poster['vote_count']) / max_count) * (1 - const.POSTER_SCORE_RATIO)
                    tmdb_images_dict['posters'][i]['score'] = score

                    # Boost the score for localized posters (according to the preference).
                    if Prefs['image.tmdb.prefer_local_art']:
                        if poster['iso_639_1'] == lang:
                            tmdb_images_dict['posters'][i]['score'] = poster['score'] + 2

                        # Discount score for foreign posters.
                        if poster['iso_639_1'] != lang and poster['iso_639_1'] is not None and poster[
                            'iso_639_1'] != 'en':
                            tmdb_images_dict['posters'][i]['score'] = poster['score'] - 2

                sort_int = len(valid_poster) + 1
                for i, poster in enumerate(sorted(tmdb_images_dict['posters'], key=lambda k: k['score'], reverse=True)):
                    if i >= int(Prefs['image.tmdb.max_posters']):
                        break
                    else:
                        poster_url = config_dict['images']['base_url'] + 'original' + poster['file_path']
                        thumb_url = config_dict['images']['base_url'] + 'w154' + poster['file_path']
                        valid_poster.append(poster_url)

                        try:
                            metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(thumb_url).content,
                                                                         sort_order=sort_int + i)
                        except NameError, e:
                            pass

            # loading art. if all sources or emty data
            if tmdb_images_dict['backdrops']:
                max_average = max([(lambda p: float(p['vote_average']) or 5)(p) for p in tmdb_images_dict['backdrops']])
                max_count = max([(lambda p: float(p['vote_count']))(p) for p in tmdb_images_dict['backdrops']]) or 1

                for i, backdrop in enumerate(tmdb_images_dict['backdrops']):
                    score = (float(backdrop['vote_average']) / max_average) * const.BACKDROP_SCORE_RATIO
                    score += (float(backdrop['vote_count']) / max_count) * (1 - const.BACKDROP_SCORE_RATIO)
                    tmdb_images_dict['backdrops'][i]['score'] = score

                    # For backdrops, we prefer "No Language" since they're intended to sit behind text.
                    if backdrop['iso_639_1'] == 'xx' or backdrop['iso_639_1'] == 'none':
                        tmdb_images_dict['backdrops'][i]['score'] = float(backdrop['score']) + 2

                    # Boost the score for localized art (according to the preference).
                    if Prefs['image.tmdb.prefer_local_art']:
                        if backdrop['iso_639_1'] == lang:
                            tmdb_images_dict['backdrops'][i]['score'] = float(backdrop['score']) + 2

                        # Discount score for foreign art.
                        if backdrop['iso_639_1'] != lang and backdrop['iso_639_1'] is not None and backdrop[
                            'iso_639_1'] != 'en':
                            tmdb_images_dict['backdrops'][i]['score'] = float(backdrop['score']) - 2

                sort_int = len(valid_art) + 1
                for i, backdrop in enumerate(
                        sorted(tmdb_images_dict['backdrops'], key=lambda k: k['score'], reverse=True)):
                    if i >= int(Prefs['image.tmdb.max_backdrops']):
                        break
                    else:
                        backdrop_url = config_dict['images']['base_url'] + 'original' + backdrop['file_path']
                        thumb_url = config_dict['images']['base_url'] + 'w300' + backdrop['file_path']
                        valid_art.append(backdrop_url)

                        try:
                            metadata.art[backdrop_url] = Proxy.Preview(HTTP.Request(thumb_url).content,
                                                                       sort_order=sort_int + i)
                        except NameError, e:
                            pass

    def extras(self, metadata, lang):
        imdb_id = get_ext_id(metadata.id, 'imdb')
        if imdb_id is None:
            return None
        try:
            req = const.PLEXMOVIE_EXTRAS_URL % (imdb_id[2:], lang)
            xml = XML.ElementFromURL(req)

            extras = []
            media_title = None
            for extra in xml.xpath('//extra'):
                avail = Datetime.ParseDate(extra.get('originally_available_at'))
                lang_code = int(extra.get('lang_code')) if extra.get('lang_code') else -1
                subtitle_lang_code = int(extra.get('subtitle_lang_code')) if extra.get('subtitle_lang_code') else -1

                spoken_lang = const.IVA_LANGUAGES.get(lang_code) or Locale.Language.Unknown
                subtitle_lang = const.IVA_LANGUAGES.get(subtitle_lang_code) or Locale.Language.Unknown
                include = False

                # Include extras in section language...
                if spoken_lang == lang:

                    # ...if there are no subs or english.
                    if subtitle_lang_code in {-1, Locale.Language.English}:
                        include = True

                # Include foreign language extras if they have subs in the section language.
                if spoken_lang != lang and subtitle_lang == lang:
                    include = True

                # Always include English language extras anyway (often section lang options are not available), but only if they have no subs.
                if spoken_lang == Locale.Language.English and subtitle_lang_code == -1:
                    include = True

                # Exclude non-primary trailers and scenes.
                extra_type = 'primary_trailer' if extra.get('primary') == 'true' else extra.get('type')
                if extra_type == 'trailer' or extra_type == 'scene_or_sample':
                    include = False

                if include:

                    bitrates = extra.get('bitrates') or ''
                    duration = int(extra.get('duration') or 0)
                    adaptive = 1 if extra.get('adaptive') == 'true' else 0
                    dts = 1 if extra.get('dts') == 'true' else 0

                    # Remember the title if this is the primary trailer.
                    if extra_type == 'primary_trailer':
                        media_title = extra.get('title')

                    # Add the extra.
                    if extra_type in const.TYPE_MAP:
                        extras.append({'type': extra_type,
                                       'lang': spoken_lang,
                                       'extra': const.TYPE_MAP[extra_type](url=const.IVA_ASSET_URL % (
                                           extra.get('iva_id'), spoken_lang, bitrates, duration, adaptive, dts),
                                                                           title=extra.get('title'),
                                                                           year=avail.year,
                                                                           originally_available_at=avail,
                                                                           thumb=extra.get('thumb') or '')})
                    else:
                        Log('Skipping extra %s because type %s was not recognized.' % (extra.get('iva_id'), extra_type))

            # Sort the extras, making sure the primary trailer is first.
            extras.sort(key=lambda e: const.TYPE_ORDER.index(e['type']))

            # If red band trailers were requested in prefs, see if we have one and swap it in.
            if Prefs['video.tmdb.redband']:
                redbands = [t for t in xml.xpath('//extra') if
                            t.get('type') == 'trailer' and re.match(r'.+red.?band.+', t.get('title'),
                                                                    re.IGNORECASE) and const.IVA_LANGUAGES.get(
                                int(t.get('lang_code') or -1)) == lang]
                if len(redbands) > 0:
                    extra = redbands[0]
                    adaptive = 1 if extra.get('adaptive') == 'true' else 0
                    dts = 1 if extra.get('dts') == 'true' else 0
                    extras[0]['extra'].url = const.IVA_ASSET_URL % (
                        extra.get('iva_id'), lang, extra.get('bitrates') or '', int(extra.get('duration') or 0), adaptive,
                        dts)
                    extras[0]['extra'].thumb = extra.get('thumb') or ''
                    Log('Adding red band trailer: ' + extra.get('iva_id'))

            # If our primary trailer is in English but the library language is something else, see if we can do better.
            if lang != Locale.Language.English and extras[0]['lang'] == Locale.Language.English:
                lang_matches = [t for t in xml.xpath('//extra') if
                                t.get('type') == 'trailer' and const.IVA_LANGUAGES.get(
                                    int(t.get('subtitle_lang_code') or -1)) == lang]
                lang_matches += [t for t in xml.xpath('//extra') if
                                 t.get('type') == 'trailer' and const.IVA_LANGUAGES.get(
                                     int(t.get('lang_code') or -1)) == lang]
                if len(lang_matches) > 0:
                    extra = lang_matches[0]
                    spoken_lang = const.IVA_LANGUAGES.get(int(extra.get('lang_code') or -1)) or Locale.Language.Unknown
                    adaptive = 1 if extra.get('adaptive') == 'true' else 0
                    dts = 1 if extra.get('dts') == 'true' else 0
                    extras[0]['lang'] = spoken_lang
                    extras[0]['extra'].url = const.IVA_ASSET_URL % (
                        extra.get('iva_id'), spoken_lang, extra.get('bitrates') or '', int(extra.get('duration') or 0),
                        adaptive, dts)
                    extras[0]['extra'].thumb = extra.get('thumb') or ''
                    Log(
                        'Adding trailer with spoken language %s and subtitled langauge %s to match library language.' % (
                            spoken_lang,
                            const.IVA_LANGUAGES.get(int(extra.get('subtitle_lang_code') or -1)) or Locale.Language.Unknown))

            # Clean up the found extras.
            extras = [self.scrub_extra(extra, media_title) for extra in extras]
            # Add them in the right order to the metadata.extras list.
            for i, extra in enumerate(extras):
                if i >= int(Prefs['video.tmdb.max']):
                    break
                else:
                    metadata.extras.add(extra['extra'])

            Log('Added %d of %d extras.' % (len(metadata.extras), len(xml.xpath('//extra'))))
        except Ex.HTTPError, e:
            if e.code == 403:
                Log('Skipping online extra lookup (an active Plex Pass is required).')
        except Exception, e:
            Log('Error while loading extras (%s)', str(e))

    def scrub_extra(self, extra, media_title):
        e = extra['extra']
        # Remove the "Movie Title: " from non-trailer extra titles.
        if media_title is not None:
            r = re.compile(media_title + ': ', re.IGNORECASE)
            e.title = r.sub('', e.title)
        # Remove the "Movie Title Scene: " from SceneOrSample extra titles.
        if media_title is not None:
            r = re.compile(media_title + ' Scene: ', re.IGNORECASE)
            e.title = r.sub('', e.title)
        # Capitalise UK correctly.
        e.title = e.title.replace('Uk', 'UK')

        return extra