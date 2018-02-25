# -*- coding: utf-8 -*-
import common
from kinopoisk import KPMeta
from tmdb import MDMeta
from itunes import iTunesMeta
from chapterdb import ChaptersMeta

@route('/ValidatePrefs')
def ValidatePrefs():
    Log('Validating Prefs 1234')
    return ObjectContainer(header='Error', message='Ooops! Error')

def Start():
    HTTP.CacheTime = CACHE_1WEEK

# check that extras is supported by server
def check_extras():
    find_extras = False
    try:
        t = InterviewObject()
        if Util.VersionAtLeast(Platform.ServerVersion, 0, 9, 9, 13):
            find_extras = True
        else:
            find_extras = False
            Log('Not adding extras: Server v0.9.9.13+ required')
    except NameError, e:
        Log('Not adding extras: Framework v2.5.0+ required')
        find_extras = False
    return find_extras


class KinopoiskAgent(Agent.Movies):
    name = u'Кинопоиск'
    primary_provider = True
    languages = [Locale.Language.Russian]
    accepts_from = ['com.plexapp.agents.localmedia']
    contributes_to = [
        'com.plexapp.agents.kinopoiskru',
        'com.plexapp.agents.themoviedb',
        'com.plexapp.agents.imdb'
    ]  # support for other plugin

    kp = KPMeta()
    tmdb = MDMeta()
    itunes = iTunesMeta()
    cp = ChaptersMeta()

    # load images according plugins settings
    def load_images(self, metadata, lang, is_primary):
        valid_art = list()
        valid_poster = list()
        list_prefs = ['image.order.kp', 'image.order.tmdb', 'image.order.itunes']

        if is_primary is True:
            orders = {k.replace('image.order.', ''): Prefs[k] for k in list_prefs}
            call_order = sorted(orders, key=orders.get)
            for source in call_order:
                getattr(self, source).load_images(metadata, valid_art, valid_poster, lang)
        else:
            self.kp.load_images(metadata, valid_art, valid_poster, lang)

        metadata.posters.validate_keys(valid_poster)
        metadata.art.validate_keys(valid_art)

    # load extras according plugins settings
    def load_extras(self, metadata, lang, is_primary):
        list_prefs = ['video.order.kp', 'video.order.tmdb']
        if is_primary is True:
            orders = {k.replace('video.order.', ''): Prefs[k] for k in list_prefs}
            call_order = sorted(orders, key=orders.get)
            for source in call_order:
                getattr(self, source).extras(metadata, lang)
        else:
            self.kp.extras(metadata, lang)

    def search(self, results, media, lang, manual=False):
        self.kp.search(results, media, lang, manual)

    def update(self, metadata, media, lang, force=False):
        Dict[metadata.id] = {}
        Dict[metadata.id]['directorsEN'] = []
        Dict[metadata.id]['directorsRU'] = []
        self.kp.update(metadata, media, lang, force)
        # if we are primary - load from tmdb
        if self.kp.is_primary is True:
            self.tmdb.update(metadata, media, lang, force)
            self.itunes.update(metadata, media, lang, force)
            self.cp.update(metadata, media, lang, force)

        self.load_images(metadata, lang, self.kp.is_primary)
        if check_extras:
            self.load_extras(metadata, lang, self.kp.is_primary)
