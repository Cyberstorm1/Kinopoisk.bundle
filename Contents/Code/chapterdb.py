# -*- coding: utf-8 -*-
from common import *


class ChaptersMeta:
    def convertTime(self, timeString):
        if (timeString == None):
            return 0

        m = re.match('(\d+):(\d+)(?::(\d+))?', timeString)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                time = int(groups[0]) * 60 + int(groups[1])
            else:
                time = int(groups[0]) * 60 * 60 + int(groups[1]) * 60 + int(groups[2])
            return time * 1000
        return None

    def cleanChapters(self, searchResult, searchTitle):
        chapterSets = []

        for match in searchResult.xpath('//cg:chapterInfo', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'}):
            confirm = match.get('confirmations')
            language = match.get('xml:lang')
            ref = match.find('cg:ref', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'})
            title = match.findtext('cg:title', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'})
            source = match.find('cg:source', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'})
            chapters = match.find('cg:chapters', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'})

            duration = None
            if source is not None:
                durationText = source.findtext('cg:duration',
                                               namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'})
                duration = self.convertTime(durationText)

            if ref is not None:
                setid = ref.findtext('cg:chapterSetId', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'})

            if duration == 0:
                duration = None

            score = 0
            if title == searchTitle:
                score += const.SCORE_TITLE_MATCH

            confirmScore = confirm * const.SCORE_PER_CONFIRM
            if confirmScore > const.SCORE_CONFIRMATION:
                score += const.SCORE_CONFIRMATION
            else:
                score += confirmScore

            # Defer duration until we start matching parts
            cleanChapters = []
            for chapter in chapters.xpath('cg:chapter', namespaces={'cg': 'http://jvance.com/2008/ChapterGrabber'}):
                timeString = chapter.get('time')
                name = chapter.get('name')

                time = self.convertTime(timeString)

                cleanChapter = {'time': time, 'name': name}
                cleanChapters.append(cleanChapter)

            chapterSet = {
                'score': score,
                'duration': duration,
                'id': setid,
                'chapters': cleanChapters
            }
            chapterSets.append(chapterSet)
        return chapterSets

    def getPartDuration(self, part):
        duration = 0
        for stream in part.streams:
            if (hasattr(stream, 'duration') and stream.duration > duration):
                duration = int(stream.duration)

        return duration

    def matchPart(self, part, chapterSets):
        duration = self.getPartDuration(part)
        return self.matchDuration(duration, chapterSets)

    def matchDuration(self, duration, chapterSets):
        bestScore = -100  # If no match is found, penalize the item that contains this part
        bestChapterSet = None

        for chapterSet in chapterSets:
            setScore = chapterSet['score']

            setDuration = chapterSet['duration']
            if setDuration != None:
                durationDelta = abs(duration - setDuration)
                if (durationDelta * 100 / setDuration) < 10:
                    setScore += const.SCORE_DURATION_SEMI_CLOSE

                if durationDelta < const.DURATION_CLOSE_VAR * 1000:
                    setScore += const.SCORE_DURATION_CLOSE

                if durationDelta < const.DURATION_MATCH_VAR * 1000:
                    setScore += const.SCORE_DURATION_MATCH

            countBeyondDuration = 0
            for chapter in chapterSet['chapters']:
                if chapter['time'] > duration:
                    countBeyondDuration += 1

            if countBeyondDuration >= const.CHAPTER_BEYOND_PART_COUNT:
                setScore += const.SCORE_CHAPTER_BEYOND_PART

            if setScore > bestScore:
                bestScore = setScore
                bestChapterSet = chapterSet

        return {
            'score': bestScore,
            'id': bestChapterSet.get('id'),
            'chapterSet': bestChapterSet,
            'duration': duration
        };

    def search(self, metadata, media, force):
        searchTitle = metadata.original_title
        bestMatch = None
        searchResult = {}
        url = '%s/%s/%s%s' % (
            const.CHAPTERDB_URL, const.CHAPTERDB_BASE, const.CHAPTERDB_SEARCH, String.Quote(searchTitle, usePlus=False))
        try:
            searchResult = XML.ElementFromURL(url, cacheTime=CACHE_1WEEK,
                                              headers={'Accept-Encoding': 'gzip', 'apikey': const.API_KEY})
        except Ex.HTTPError, e:
            Log("Error while loading %s (%s)", url, str(e))

        if len(searchResult) != 0:
            chapterSets = self.cleanChapters(searchResult, searchTitle)

            for item in media.items:
                match = {
                    'score': 0,
                    'parts': []
                }
                totalDuration = 0
                for part in item.parts:
                    partMatch = self.matchPart(part, chapterSets)
                    match['parts'].append(partMatch)
                    totalDuration += partMatch['duration']

                scoreSum = 0
                count = 0
                for partMatch in match['parts']:
                    scoreSum += partMatch['score']
                    count += 1
                match['score'] = scoreSum / count

                if len(item.parts) != 1:
                    # try match whole item as a single part
                    itemMatch = self.matchDuration(totalDuration, chapterSets)
                    if itemMatch['score'] > match['score']:
                        match['score'] = itemMatch['score']
                        match['parts'] = [itemMatch]

                if bestMatch == None or match['score'] > bestMatch['score']:
                    bestMatch = match
        return bestMatch

    def update(self, metadata, media, lang, force):
        if metadata.original_title:
            bestMatch = self.search(metadata, media, force)
            # Clear out old chapters.
            metadata.chapters.clear()
            if bestMatch != None and bestMatch['score'] > 0:

                offset = 0
                for partMatch in bestMatch['parts']:
                    lastChapter = None
                    chapterSet = partMatch['chapterSet']
                    for matchChapter in chapterSet['chapters']:
                        time = matchChapter['time'] + offset
                        self.finalizeChapter(lastChapter, time)

                        chapter = metadata.chapters.new()
                        chapter.title = matchChapter['name']
                        chapter.start_time_offset = time
                        lastChapter = chapter

                    offset += partMatch['duration']
                    self.finalizeChapter(lastChapter, offset)
            Log.Debug('Added %d chapters.' % len(metadata.chapters))

    def finalizeChapter(self, chapter, endTime):
        if chapter != None:
            chapter.end_time_offset = endTime