# -*- coding: utf-8 -*-

import re
import decimal

TRANSTABLE = (
    (u"'", u"'"),
    (u'"', u'"'),
    (u"‘", u"'"),
    (u"’", u"'"),
    (u"«", u'"'),
    (u"»", u'"'),
    (u"“", u'"'),
    (u"”", u'"'),
    (u"–", u"-"),  # en dash
    (u"—", u"-"),  # em dash
    (u"‒", u"-"),  # figure dash
    (u"−", u"-"),  # minus
    (u"…", u"..."),
    (u"№", u"#"),
    ## upper
    # three-symbols replacements
    (u"Щ", u"Sch"),
    # on russian->english translation only first replacement will be done
    # i.e. Sch
    # but on english->russian translation both variants (Sch and SCH) will play
    (u"Щ", u"SCH"),
    # two-symbol replacements
    (u"Ё", u"Yo"),
    (u"Ё", u"YO"),
    (u"Ж", u"Zh"),
    (u"Ж", u"ZH"),
    (u"Ц", u"Ts"),
    (u"Ц", u"TS"),
    (u"Ч", u"Ch"),
    (u"Ч", u"CH"),
    (u"Ш", u"Sh"),
    (u"Ш", u"SH"),
    (u"Ы", u"Yi"),
    (u"Ы", u"YI"),
    (u"Ю", u"Yu"),
    (u"Ю", u"YU"),
    (u"Я", u"Ya"),
    (u"Я", u"YA"),
    # one-symbol replacements
    (u"А", u"A"),
    (u"Б", u"B"),
    (u"В", u"V"),
    (u"Г", u"G"),
    (u"Д", u"D"),
    (u"Е", u"E"),
    (u"З", u"Z"),
    (u"И", u"I"),
    (u"Й", u"J"),
    (u"К", u"K"),
    (u"Л", u"L"),
    (u"М", u"M"),
    (u"Н", u"N"),
    (u"О", u"O"),
    (u"П", u"P"),
    (u"Р", u"R"),
    (u"С", u"S"),
    (u"Т", u"T"),
    (u"У", u"U"),
    (u"Ф", u"F"),
    (u"Х", u"H"),
    (u"Э", u"E"),
    (u"Ъ", u"`"),
    (u"Ь", u"'"),
    ## lower
    # three-symbols replacements
    (u"щ", u"sch"),
    # two-symbols replacements
    (u"ё", u"yo"),
    (u"ж", u"zh"),
    (u"ц", u"ts"),
    (u"ч", u"ch"),
    (u"ш", u"sh"),
    (u"ы", u"yi"),
    (u"ю", u"yu"),
    (u"я", u"ya"),
    # one-symbol replacements
    (u"а", u"a"),
    (u"б", u"b"),
    (u"в", u"v"),
    (u"г", u"g"),
    (u"д", u"d"),
    (u"е", u"e"),
    (u"з", u"z"),
    (u"и", u"i"),
    (u"й", u"j"),
    (u"к", u"k"),
    (u"л", u"l"),
    (u"м", u"m"),
    (u"н", u"n"),
    (u"о", u"o"),
    (u"п", u"p"),
    (u"р", u"r"),
    (u"с", u"s"),
    (u"т", u"t"),
    (u"у", u"u"),
    (u"ф", u"f"),
    (u"х", u"h"),
    (u"э", u"e"),
    (u"ъ", u"`"),
    (u"ь", u"'"),
    # Make english alphabet full: append english-english pairs
    # for symbols which is not used in russian-english
    # translations. Used in slugify.
    (u"c", u"c"),
    (u"q", u"q"),
    (u"y", u"y"),
    (u"x", u"x"),
    (u"w", u"w"),
    (u"1", u"1"),
    (u"2", u"2"),
    (u"3", u"3"),
    (u"4", u"4"),
    (u"5", u"5"),
    (u"6", u"6"),
    (u"7", u"7"),
    (u"8", u"8"),
    (u"9", u"9"),
    (u"0", u"0"),
)  #: Translation table

units = (
    u'ноль',

    (u'один', u'одна'),
    (u'два', u'две'),

    u'три', u'четыре', u'пять',
    u'шесть', u'семь', u'восемь', u'девять'
)

teens = (
    u'десять', u'одиннадцать',
    u'двенадцать', u'тринадцать',
    u'четырнадцать', u'пятнадцать',
    u'шестнадцать', u'семнадцать',
    u'восемнадцать', u'девятнадцать'
)

tens = (
    teens,
    u'двадцать', u'тридцать',
    u'сорок', u'пятьдесят',
    u'шестьдесят', u'семьдесят',
    u'восемьдесят', u'девяносто'
)

hundreds = (
    u'сто', u'двести',
    u'триста', u'четыреста',
    u'пятьсот', u'шестьсот',
    u'семьсот', u'восемьсот',
    u'девятьсот'
)

orders = (# plural forms and gender
    #((u'', u'', u''), 'm'), # ((u'рубль', u'рубля', u'рублей'), 'm'), # ((u'копейка', u'копейки', u'копеек'), 'f')
    ((u'тысяча', u'тысячи', u'тысяч'), 'f'),
    ((u'миллион', u'миллиона', u'миллионов'), 'm'),
    ((u'миллиард', u'миллиарда', u'миллиардов'), 'm'),
)

RU_ALPHABET = [x[0] for x in TRANSTABLE] #: Russian alphabet that we can translate
EN_ALPHABET = [x[1] for x in TRANSTABLE] #: English alphabet that we can detransliterate
ALPHABET = RU_ALPHABET + EN_ALPHABET #: Alphabet that we can (de)transliterate


def translify(in_string, strict=True):
    """
    Translify russian text

    @param in_string: input string
    @type in_string: C{unicode}

    @param strict: raise error if transliteration is incomplete.
        (True by default)
    @type strict: C{bool}

    @return: transliterated string
    @rtype: C{str}

    @raise ValueError: when string doesn't transliterate completely.
        Raised only if strict=True
    """
    translit = in_string
    for symb_in, symb_out in TRANSTABLE:
        translit = translit.replace(symb_in, symb_out)

    if strict and any(ord(symb) > 128 for symb in translit):
        raise ValueError("Unicode string doesn't transliterate completely, " + \
                         "is it russian?")

    return translit

def detranslify(in_string):
    """
    Detranslify

    @param in_string: input string
    @type in_string: C{basestring}

    @return: detransliterated string
    @rtype: C{unicode}

    @raise ValueError: if in_string is C{str}, but it isn't ascii
    """
    try:
        russian = unicode(in_string)
    except UnicodeDecodeError:
        raise ValueError("We expects if in_string is 8-bit string," + \
                         "then it consists only ASCII chars, but now it doesn't. " + \
                         "Use unicode in this case.")

    for symb_out, symb_in in TRANSTABLE:
        russian = russian.replace(symb_in, symb_out)

    # TODO: выбрать правильный регистр для ь и ъ
    # твердый и мягкий знак в dentranslify всегда будут в верхнем регистре
    # потому что ` и ' не несут информацию о регистре
    return russian

def slugify(in_string):
    """
    Prepare string for slug (i.e. URL or file/dir name)

    @param in_string: input string
    @type in_string: C{basestring}

    @return: slug-string
    @rtype: C{str}

    @raise ValueError: if in_string is C{str}, but it isn't ascii
    """
    try:
        u_in_string = unicode(in_string).lower()
    except UnicodeDecodeError:
        raise ValueError("We expects when in_string is str type," + \
                         "it is an ascii, but now it isn't. Use unicode " + \
                         "in this case.")
    # convert & to "and"
    u_in_string = re.sub('\&amp\;|\&', ' and ', u_in_string)
    # replace spaces by hyphen
    u_in_string = re.sub('[-\s]+', '-', u_in_string)
    # remove symbols that not in alphabet
    u_in_string = u''.join([symb for symb in u_in_string if symb in ALPHABET])
    # translify it
    out_string = translify(u_in_string)
    # remove non-alpha
    return re.sub('[^\w\s-]', '', out_string).strip().lower()


def dirify(in_string):
    """
    Alias for L{slugify}
    """
    slugify(in_string)


def thousand(rest, sex):
    """Converts numbers from 19 to 999"""
    prev = 0
    plural = 2
    name = []
    use_teens = rest % 100 >= 10 and rest % 100 <= 19
    if not use_teens:
        data = ((units, 10), (tens, 100), (hundreds, 1000))
    else:
        data = ((teens, 10), (hundreds, 1000))
    for names, x in data:
        cur = ((rest - prev) % x) * 10 / x
        prev = rest % x
        if x == 10 and use_teens:
            plural = 2
            name.append(teens[cur])
        elif cur == 0:
            continue
        elif x == 10:
            name_ = names[cur]
            if isinstance(name_, tuple):
                name_ = name_[0 if sex == 'm' else 1]
            name.append(name_)
            if cur >= 2 and cur <= 4:
                plural = 1
            elif cur == 1:
                plural = 0
            else:
                plural = 2
        else:
            name.append(names[cur - 1])
    return plural, name


def num2text(num, main_units=((u'', u'', u''), 'm')):
    """
    http://ru.wikipedia.org/wiki/Gettext#.D0.9C.D0.BD.D0.BE.D0.B6.D0.B5.D1.81.\
    D1.82.D0.B2.D0.B5.D0.BD.D0.BD.D1.8B.D0.B5_.D1.87.D0.B8.D1.81.D0.BB.D0.B0_2
    """
    l_orders = (main_units,) + orders
    if num == 0:
        return ' '.join((units[0], l_orders[0][0][2])).strip() # ноль

    rest = num
    ord = 0
    name = []
    while rest > 0:
        plural, nme = thousand(rest % 1000, l_orders[ord][1])
        if nme or ord == 0:
            name.append(l_orders[ord][0][plural])
        name += nme
        rest = rest / 1000
        ord += 1
    name.reverse()
    return ' '.join(name).strip()


def decimal2text(value, places=2,
                 int_units=(('', '', ''), 'm'),
                 exp_units=(('', '', ''), 'm')):
    q = decimal.Decimal(10) ** -places
    integral, exp = str(value.quantize(q)).split('.')
    return u'{} {}'.format(
        num2text(int(integral), int_units),
        num2text(int(exp), exp_units))

def trans_digits(value, ascii=False):
    if ascii:
        return reduce(lambda a, kv: a.replace(kv, num2Words(int(kv))), [s for s in value.split() if s.isdigit()], value)
    else:
        return reduce(lambda a, kv: a.replace(kv, num2text(int(kv))), [s for s in value.split() if s.isdigit()], value)


def num2Words(num,join=True):
    '''words = {} convert an integer number into words'''
    units = ['','one','two','three','four','five','six','seven','eight','nine']
    teens = ['','eleven','twelve','thirteen','fourteen','fifteen','sixteen', \
             'seventeen','eighteen','nineteen']
    tens = ['','ten','twenty','thirty','forty','fifty','sixty','seventy', \
            'eighty','ninety']
    thousands = ['','thousand','million','billion','trillion','quadrillion', \
                 'quintillion','sextillion','septillion','octillion', \
                 'nonillion','decillion','undecillion','duodecillion', \
                 'tredecillion','quattuordecillion','sexdecillion', \
                 'septendecillion','octodecillion','novemdecillion', \
                 'vigintillion']
    words = []
    if num==0: words.append('zero')
    else:
        numStr = '%d'%num
        numStrLen = len(numStr)
        groups = (numStrLen+2)/3
        numStr = numStr.zfill(groups*3)
        for i in range(0,groups*3,3):
            h,t,u = int(numStr[i]),int(numStr[i+1]),int(numStr[i+2])
            g = groups-(i/3+1)
            if h>=1:
                words.append(units[h])
                words.append('hundred')
            if t>1:
                words.append(tens[t])
                if u>=1: words.append(units[u])
            elif t==1:
                if u>=1: words.append(teens[u])
                else: words.append(tens[t])
            else:
                if u>=1: words.append(units[u])
            if (g>=1) and ((h+t+u)>0): words.append(thousands[g]+',')
    if join: return ' '.join(words)
    return words
