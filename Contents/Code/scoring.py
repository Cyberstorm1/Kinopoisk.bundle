# -*- coding: utf-8 -*-
import difflib
import re
import math
import urllib2

import translit
import const
from fuzzywuzzy import fuzz


def check_main_poster(film_id):
    poster_url = const.KP_MAIN_POSTER % film_id
    try:
        req = urllib2.urlopen(poster_url, timeout=10)
        return req.geturl().endswith('no-poster.gif')
    except:
        return False

# clear titles from kinopoisk
def clear_title(s):
    repls = (u' (видео)', u' (ТВ)', u' (мини-сериал)', u' (сериал)')  # remove unnecessary text
    return reduce(lambda a, kv: a.replace(kv, ''), repls, s)

def score_requests(entry, combinations):
    scores = []
    for combo in combinations:
        scores.append(score_title(entry, combo['year'], combo['title'], entry['i'] + 1))
    return max(scores)

def score_title(entry, fileyear, medianame, idx):
    score = 90
    Log.Debug('### Start scoring %s (%s) <-> %s (%s)  idx = %s', medianame, fileyear, entry['nameRU'], entry['year'], idx)
    # result position penalty
    if Prefs['search.trust_kp'] is True and idx == 1:
        score = score + 10
    else:
        score = score - idx * const.SCORE_PENALTY_ITEM_ORDER

    yearpenalty = const.SCORE_PENALTY_YEAR / 3  # if we have no year
    mediayear = int(fileyear or 0)
    year = int(re.sub('[^0-9]', '', entry.get('year') or '0') or '0')
    if mediayear != 0 and year != 0:
        yeardiff = abs(mediayear - year)
        if yeardiff < 1:
            score = score + 10
            yearpenalty = 0
        else:
            if yeardiff == 1:
                yearpenalty = int(const.SCORE_PENALTY_YEAR / 4)
            elif yeardiff == 2:
                yearpenalty = int(const.SCORE_PENALTY_YEAR / 3)
            else:
                yearpenalty = yeardiff * int(const.SCORE_PENALTY_YEAR / 2)

    score = score - yearpenalty
    titlepenalty = compute_title_penalty(medianame, clear_title(entry['nameRU']))
    alttitlepenalty = 100
    if 'nameEN' in entry:
        alttitlepenalty = compute_title_penalty(medianame, entry['nameEN'])

    Log.Debug('yearpenalty = %s, titlepenalty = %s, alttitlepenalty = %s', yearpenalty, titlepenalty, alttitlepenalty)

    try:
        detranslifiedmedianame = translit.detranslify(medianame)
        detranslifiedtitlepenalty = compute_title_penalty(detranslifiedmedianame, clear_title(entry['nameRU']))
        titlepenalty = min(detranslifiedtitlepenalty, titlepenalty)

        if 'nameEN' in entry:
            detranslifiedalttitlepenalty = compute_title_penalty(detranslifiedmedianame, entry['nameEN'])
            alttitledetranslified = translit.detranslify(entry['nameEN'])
            reverseddetranslifiedalttitlepenalty = compute_title_penalty(detranslifiedmedianame, alttitledetranslified)
            alttitlepenalty = min(detranslifiedalttitlepenalty, reverseddetranslifiedalttitlepenalty, alttitlepenalty)
    except:
        Log('Error computing title penalty for %s', medianame)

    titlepenalty = min(titlepenalty, alttitlepenalty)
    score = score - titlepenalty

    if check_main_poster(entry['id']) is True:
        score = score - const.SCORE_PENALTY_MAIN_POSTER

    if idx == 0 and score <= 80:
        score = score + 5

    Log.Debug('### End scoring %s', medianame)
    return score if score <= 100 else 100


def compute_title_penalty(medianame, title):
    medianame = medianame.lower()
    title = title.lower()
    if medianame != title:
        diffratio = fuzz.UWRatio(medianame, title)/float(100) #difflib.SequenceMatcher(None, medianame, title).ratio()
        penalty = int(round(const.SCORE_PENALTY_TITLE * (1 - diffratio), 0))
        if penalty >= 15:
            medianameparts = medianame.split()
            titleparts = title.split()
            if len(medianameparts) <= len(titleparts):
                i = 0
                penaltyalt = max(5, int(round((1.0 - (float(len(medianameparts)) / len(titleparts))) * 15 - 5)))
                penaltyperpart = const.SCORE_PENALTY_TITLE / len(medianameparts)
                for mediaNamePart in medianameparts:
                    partdiffratio = fuzz.ratio(mediaNamePart, titleparts[i])/float(100) #difflib.SequenceMatcher(None, mediaNamePart, titleparts[i]).ratio()
                    penaltyalt = penaltyalt + int(penaltyperpart * (1 - partdiffratio))
                    i = i + 1
                penalty = min(penalty, penaltyalt)
        return penalty
    return 0


def score_image(img_size, image_pxcount, img_type='poster'):
    score = 0
    if img_type == 'poster':
        min_px = const.POSTER_SCORE_MIN_RESOLUTION_PX
        max_px = const.POSTER_SCORE_MAX_RESOLUTION_PX
        best_ratio = const.POSTER_SCORE_BEST_RATIO
    else:
        min_px = const.ART_SCORE_MIN_RESOLUTION_PX
        max_px = const.ART_SCORE_MAX_RESOLUTION_PX
        best_ratio = const.ART_SCORE_BEST_RATIO

    if image_pxcount > min_px:
        if image_pxcount > max_px:
            image_pxcount = max_px
        bonus = float(const.IMAGE_SCORE_RESOLUTION_BONUS_MAX) * \
                float(( image_pxcount- min_px)) / float((max_px - min_px))
        score = score + bonus

    ratio = img_size[0] / float(img_size[1])
    ratio_diff = math.fabs(best_ratio - ratio)
    if ratio_diff < 0.5:
        bonus = const.IMAGE_SCORE_RATIO_BONUS_MAX * (0.5 - ratio_diff) * 2.0
        score = score + bonus
    return score