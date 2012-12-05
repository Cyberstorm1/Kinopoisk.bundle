import unicodedata, datetime

KINOPOISK_OPEN_API_URL = 'http://www.kinopoisk.ru/export/export.php?encoding=utf8&search=%s'
KINOPOISK_META_URL = 'http://www.kinopoisk.ru/export/export.php?encoding=utf8&id_film=%s'
RE_YEAR = Regex('([1-2][0-9]{3})')

def Start():
#	HTTP.CacheTime = CACHE_1HOUR * 4
	HTTP.CacheTime = 0

class KinoPoiskAgent(Agent.Movies):
	name = "Kinopoisk"
	primary_provider = True
	languages = [Locale.Language.Russian]

	accepts_from = ['com.plexapp.agents.localmedia']

	def GetFixedXML(self, url, isHtml=False):		# function for getting XML in the corresponding URL
		#xml = HTTP.Request(url)
		#return XML.ElementFromString(xml, isHtml)
		return XML.ElementFromURL(url)

	def search(self, results, media, lang):   
		name = unicodedata.normalize('NFC', media.name.decode('utf-8')).encode('utf-8')
		media_name = name.lower()

		if media.year is None :
			yearMatch = RE_YEAR.search(media_name)
			if yearMatch :
				yearStr = yearMatch.group(1)
				yearInt = int(yearStr)
				if yearInt > 1900 and yearInt < (datetime.date.today().year + 1):
					media.year = yearInt
					media_name = media_name.replace(yearStr, '')	

		url = KINOPOISK_OPEN_API_URL % (String.Quote(media_name, usePlus=False))	# URL for movie name search
		xml = self.GetFixedXML(url)                                                           # to get XML for search result
		items = xml.xpath('//film')
		score = 99

		for item in items:
			years = item.xpath('year')								# at first, year is compared
			if years != [] : year = int(years[0].text)
			else :	    year = 0      
			if media.year is not None and year != 0:
				if( (int(media.year) - year) > 1 or (int(media.year) - year) < -1) :	# if year is different, other attributes are not compared
					continue

			id = item.xpath('@id')[0]

			rus_title_cand = item.xpath('@rus_title')[0]					# Russian title
			eng_title_cands = item.xpath('@eng_title')[0]						# English title
			if eng_title_cands != [] :
				eng_title_cand = eng_title_cands.lower()
			else :			
				org_title_cands = rus_title_cand					# getting original title when english title is not given
				if org_title_cands != [] :
					eng_title_cand = org_title_cands.lower()
				else :
					eng_title_cand = '?'

			results.Append(MetadataSearchResult(id=id, name=rus_title_cand, year=year, lang=lang, score=score))
			score = score - 4

		results.Sort('score', descending=True)

	def update(self, metadata, media, lang):
		if metadata.id:
			proxy = Proxy.Preview
			Log('---->In update ID = %s' % metadata.id)
			url = KINOPOISK_META_URL % metadata.id
			xml = self.GetFixedXML(url)
			#metadata.title = media.title
			metadata.content_rating = u'R'

			try :
				metadata.content_rating = xml.xpath('//mpaa')[0].text
			except :
				pass


			try :
				metadata.originally_available_at = Datetime.ParseDate(xml.xpath('//premier_world')[0].text).date()
				Log('metadata.originally_available_at = %s', metadata.originally_available_at)
			except :
				pass

			

			try :													#tagline
				Log('metadata.tagline = %s', xml.xpath('//tagline')[0].text)
				metadata.tagline = xml.xpath('//tagline')[0].text
			except :
				pass


			items = xml.xpath('//companies/company')
			try :													# companies
				for item in items:
					Log('company = %s', item.xpath('//name')[0].text)
					metadata.studio = item.xpath('//name')[0].text
					break				# Get first studio only
			except :
				pass


			try :													#title
				metadata.title = xml.xpath('//film/attribute::rus_title')[0]
				Log('metadata.name = %s', xml.xpath('//film/attribute::rus_title')[0])
			except :
				pass

			try :													#year
				metadata.year = int(xml.xpath('//year')[0].text)
				Log('metadata.year = %d', metadata.year)
			except :
				pass

			try :													#genre
				items = xml.xpath('//genres/genre')
				for item in items:
					Log('genre = %s', item.xpath('rus_genre')[0].text)
					metadata.genres.add(item.xpath('rus_genre')[0].text)
			except :
				pass
				
			try :													#description
				metadata.summary = "( Kinopoisk ) " + xml.xpath('//synopsis')[0].text
			except :
				pass

			try :													#duration
				metadata.duration = int(xml.xpath('//runtime')[0].text) * 60 * 1000
				Log('metadata.duration = %d', metadata.duration)
			except :
				pass

			try :													#rating
				metadata.rating = float(xml.xpath('//rating')[0].text)
				Log('>1>metadata.rating = %f', metadata.rating)
			except :
				pass
				

			items = xml.xpath('//stills/still')
			try :													# posters
				for item in items:
					imageUrl = item.text
					Log('imageUrl = %s', imageUrl)
					name = imageUrl.split('/')[-1]
					if name not in metadata.posters:
						metadata.posters[name] = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
			except :
				pass

			try :													#image
				imageUrl = xml.xpath('//image')[0].text
				name = imageUrl.split('/')[-1]
				if name not in metadata.posters:
					metadata.posters[name] = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
			except :
				pass


			try :													# actors    &     directors   &   writers
				metadata.roles.clear()
				metadata.directors.clear()
				metadata.writers.clear()
				items = xml.xpath('//persons/person')
				for item in items:
					pRole = item.xpath('@class')[0]
					if pRole == u'actor':
						role = metadata.roles.new()
						role.actor = item.xpath('@rus_name')[0]
						role.photo = item.xpath('image')[0].text

					elif pRole == u'director' :
						metadata.directors.add (item.xpath('@rus_name')[0])
						
					elif pRole == u'writer' :
						metadata.writers.add (item.xpath('@rus_name')[0])

			except :
				pass
