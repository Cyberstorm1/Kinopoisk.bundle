import struct
import array
import urllib2
import time

QUALITY_HASH_COLOR = (
    1020, 1015,  932,  848,  780,  735,  702,  679,  660,  645,
    632,  623,  613,  607,  600,  594,  589,  585,  581,  571,
    555,  542,  529,  514,  494,  474,  457,  439,  424,  410,
    397,  386,  373,  364,  351,  341,  334,  324,  317,  309,
    299,  294,  287,  279,  274,  267,  262,  257,  251,  247,
    243,  237,  232,  227,  222,  217,  213,  207,  202,  198,
    192,  188,  183,  177,  173,  168,  163,  157,  153,  148,
    143,  139,  132,  128,  125,  119,  115,  108,  104,   99,
    94,   90,   84,   79,   74,   70,   64,   59,   55,   49,
    45,   40,   34,   30,   25,   20,   15,   11,    6,    4,
    0)

QUALITY_SUM_COLOR = (
    32640,32635,32266,31495,30665,29804,29146,28599,28104,27670,
    27225,26725,26210,25716,25240,24789,24373,23946,23572,22846,
    21801,20842,19949,19121,18386,17651,16998,16349,15800,15247,
    14783,14321,13859,13535,13081,12702,12423,12056,11779,11513,
    11135,10955,10676,10392,10208, 9928, 9747, 9564, 9369, 9193,
    9017, 8822, 8639, 8458, 8270, 8084, 7896, 7710, 7527, 7347,
    7156, 6977, 6788, 6607, 6422, 6236, 6054, 5867, 5684, 5495,
    5305, 5128, 4945, 4751, 4638, 4442, 4248, 4065, 3888, 3698,
    3509, 3326, 3139, 2957, 2775, 2586, 2405, 2216, 2037, 1846,
    1666, 1483, 1297, 1109,  927,  735,  554,  375,  201,  128,
    0)

QUALITY_HASH_GRAY = (
    510,  505,  422,  380,  355,  338,  326,  318,  311,  305,
    300,  297,  293,  291,  288,  286,  284,  283,  281,  280,
    279,  278,  277,  273,  262,  251,  243,  233,  225,  218,
    211,  205,  198,  193,  186,  181,  177,  172,  168,  164,
    158,  156,  152,  148,  145,  142,  139,  136,  133,  131,
    129,  126,  123,  120,  118,  115,  113,  110,  107,  105,
    102,  100,   97,   94,   92,   89,   87,   83,   81,   79,
    76,   74,   70,   68,   66,   63,   61,   57,   55,   52,
    50,   48,   44,   42,   39,   37,   34,   31,   29,   26,
    24,   21,   18,   16,   13,   11,    8,    6,    3,    2,
    0)

QUALITY_SUM_GRAY = (
    16320,16315,15946,15277,14655,14073,13623,13230,12859,12560,
    12240,11861,11456,11081,10714,10360,10027, 9679, 9368, 9056,
    8680, 8331, 7995, 7668, 7376, 7084, 6823, 6562, 6345, 6125,
    5939, 5756, 5571, 5421, 5240, 5086, 4976, 4829, 4719, 4616,
    4463, 4393, 4280, 4166, 4092, 3980, 3909, 3835, 3755, 3688,
    3621, 3541, 3467, 3396, 3323, 3247, 3170, 3096, 3021, 2952,
    2874, 2804, 2727, 2657, 2583, 2509, 2437, 2362, 2290, 2211,
    2136, 2068, 1996, 1915, 1858, 1773, 1692, 1620, 1552, 1477,
    1398, 1326, 1251, 1179, 1109, 1031,  961,  884,  814,  736,
    667,  592,  518,  441,  369,  292,  221,  151,   86,   64,
    0)

def i16(c, o=0):
    return struct.unpack('>H', c[o:o+2])[0]

def i8(c, o=0):
    return struct.unpack('>B', c[o:o+2])[0]

def SOF(self, marker):
    #
    # Start of frame marker.  Defines the size and mode of the
    # image.  JPEG is colour blind, so we use some simple
    # heuristics to map the number of layers to an appropriate
    # mode.  Note that this could be made a bit brighter, by
    # looking for JFIF and Adobe APP markers.

    n = i16(self.fp.read(2))-2
    s = self.fp.read(n)
    self.size = i16(s[3:]), i16(s[1:])
    self.pxcount = i16(s[3:]) * i16(s[1:])

    self.bits = i8(s[0])
    if self.bits != 8:
        raise SyntaxError("cannot handle %d-bit layers" % self.bits)

    self.layers = i8(s[5])
    if self.layers == 1:
        self.mode = "L"
    elif self.layers == 3:
        self.mode = "RGB"
    elif self.layers == 4:
        self.mode = "CMYK"
    else:
        raise SyntaxError("cannot handle %d-layer images" % self.layers)

    if marker in [0xFFC2, 0xFFC6, 0xFFCA, 0xFFCE]:
        self.info["progressive"] = self.info["progression"] = 1

    if self.icclist:
        # fixup icc profile
        self.icclist.sort()  # sort by sequence number
        if i8(self.icclist[0][13]) == len(self.icclist):
            profile = []
            for p in self.icclist:
                profile.append(p[14:])
            icc_profile = b"".join(profile)
        else:
            icc_profile = None  # wrong number of fragments
        self.info["icc_profile"] = icc_profile
        self.icclist = None

    for i in range(6, len(s), 3):
        t = s[i:i+3]
        # 4-tuples: id, vsamp, hsamp, qtable
        self.layer.append((t[0], i8(t[1])//16, i8(t[1]) & 15, i8(t[2])))

def APP(self, marker):
    #
    # Application marker.  Store these in the APP dictionary.
    # Also look for well-known application markers.

    n = i16(self.fp.read(2))-2
    s = self.fp.read(n)

    app = "APP%d" % (marker & 15)

    self.app[app] = s  # compatibility
    self.applist.append((app, s))

    if marker == 0xFFE0 and s[:4] == b"JFIF":
        # extract JFIF information
        self.info["jfif"] = version = i16(s, 5)  # version
        self.info["jfif_version"] = divmod(version, 256)
        # extract JFIF properties
        try:
            jfif_unit = i8(s[7])
            jfif_density = i16(s, 8), i16(s, 10)
        except:
            pass
        else:
            if jfif_unit == 1:
                self.info["dpi"] = jfif_density
            self.info["jfif_unit"] = jfif_unit
            self.info["jfif_density"] = jfif_density
    elif marker == 0xFFE1 and s[:5] == b"Exif\0":
        # extract Exif information (incomplete)
        self.info["exif"] = s  # FIXME: value will change
    elif marker == 0xFFE2 and s[:5] == b"FPXR\0":
        # extract FlashPix information (incomplete)
        self.info["flashpix"] = s  # FIXME: value will change
    elif marker == 0xFFE2 and s[:12] == b"ICC_PROFILE\0":
        # Since an ICC profile can be larger than the maximum size of
        # a JPEG marker (64K), we need provisions to split it into
        # multiple markers. The format defined by the ICC specifies
        # one or more APP2 markers containing the following data:
        #   Identifying string      ASCII "ICC_PROFILE\0"  (12 bytes)
        #   Marker sequence number  1, 2, etc (1 byte)
        #   Number of markers       Total of APP2's used (1 byte)
        #   Profile data            (remainder of APP2 data)
        # Decoders should use the marker sequence numbers to
        # reassemble the profile, rather than assuming that the APP2
        # markers appear in the correct sequence.
        self.icclist.append(s)
    elif marker == 0xFFEE and s[:5] == b"Adobe":
        self.info["adobe"] = i16(s, 5)
        # extract Adobe custom properties
        try:
            adobe_transform = i8(s[1])
        except:
            pass
        else:
            self.info["adobe_transform"] = adobe_transform
    elif marker == 0xFFE2 and s[:4] == b"MPF\0":
        # extract MPO information
        self.info["mp"] = s[4:]
        # offset is current location minus buffer size
        # plus constant header size
        #self.info["mpoffset"] = self.fp.tell() - n + 4

def COM(self, marker):
    n = i16(self.fp.read(2))-2
    s = self.fp.read(n)

    self.app["COM"] = s  # compatibility
    self.applist.append(("COM", s))

def Skip(self, marker):
    n = i16(self.fp.read(2))-2
    self.fp.read(n)

def DQT(self, marker):
    n = i16(self.fp.read(2))-2
    s = self.fp.read(n)
    while len(s):
        if len(s) < 65:
            raise SyntaxError("bad quantization table marker")
        v = i8(s[0])
        if v//16 == 0:
            self.quantization[v & 15] = array.array("b", s[1:65])
            s = s[65:]
        else:
            return  # FIXME: add code to read 16-bit tables!
            # raise SyntaxError, "bad quantization table element size"

def compileQuol(self):
    if len(self.quantization)>0:
        sumcoeff = 0
        for qt in self.quantization:
            coeff = self.quantization[qt]
            for index in xrange(64):
                sumcoeff += coeff[index]
        hashval= self.quantization[0][5] +  self.quantization[0][56]
        if 2 <= len(self.quantization):
            hashval += self.quantization[1][0] + self.quantization[1][63]
            hashtable = QUALITY_HASH_COLOR
            sumtable = QUALITY_SUM_COLOR
        else:
            hashtable = QUALITY_HASH_GRAY
            sumtable = QUALITY_SUM_GRAY

        for index in xrange(100):
            if (hashval >= hashtable[index]) or (sumcoeff >= sumtable[index]):
                self.quality = index + 1
                return


MARKER = {
    0xFFC0: ("SOF0", "Baseline DCT", SOF),
    0xFFC1: ("SOF1", "Extended Sequential DCT", SOF),
    0xFFC2: ("SOF2", "Progressive DCT", SOF),
    0xFFC3: ("SOF3", "Spatial lossless", SOF),
    0xFFC4: ("DHT", "Define Huffman table", Skip),
    0xFFC5: ("SOF5", "Differential sequential DCT", SOF),
    0xFFC6: ("SOF6", "Differential progressive DCT", SOF),
    0xFFC7: ("SOF7", "Differential spatial", SOF),
    0xFFC8: ("JPG", "Extension", None),
    0xFFC9: ("SOF9", "Extended sequential DCT (AC)", SOF),
    0xFFCA: ("SOF10", "Progressive DCT (AC)", SOF),
    0xFFCB: ("SOF11", "Spatial lossless DCT (AC)", SOF),
    0xFFCC: ("DAC", "Define arithmetic coding conditioning", Skip),
    0xFFCD: ("SOF13", "Differential sequential DCT (AC)", SOF),
    0xFFCE: ("SOF14", "Differential progressive DCT (AC)", SOF),
    0xFFCF: ("SOF15", "Differential spatial (AC)", SOF),
    0xFFD0: ("RST0", "Restart 0", None),
    0xFFD1: ("RST1", "Restart 1", None),
    0xFFD2: ("RST2", "Restart 2", None),
    0xFFD3: ("RST3", "Restart 3", None),
    0xFFD4: ("RST4", "Restart 4", None),
    0xFFD5: ("RST5", "Restart 5", None),
    0xFFD6: ("RST6", "Restart 6", None),
    0xFFD7: ("RST7", "Restart 7", None),
    0xFFD8: ("SOI", "Start of image", None),
    0xFFD9: ("EOI", "End of image", None),
    0xFFDA: ("SOS", "Start of scan", Skip),
    0xFFDB: ("DQT", "Define quantization table", DQT),
    0xFFDC: ("DNL", "Define number of lines", Skip),
    0xFFDD: ("DRI", "Define restart interval", Skip),
    0xFFDE: ("DHP", "Define hierarchical progression", SOF),
    0xFFDF: ("EXP", "Expand reference component", Skip),
    0xFFE0: ("APP0", "Application segment 0", APP),
    0xFFE1: ("APP1", "Application segment 1", APP),
    0xFFE2: ("APP2", "Application segment 2", APP),
    0xFFE3: ("APP3", "Application segment 3", APP),
    0xFFE4: ("APP4", "Application segment 4", APP),
    0xFFE5: ("APP5", "Application segment 5", APP),
    0xFFE6: ("APP6", "Application segment 6", APP),
    0xFFE7: ("APP7", "Application segment 7", APP),
    0xFFE8: ("APP8", "Application segment 8", APP),
    0xFFE9: ("APP9", "Application segment 9", APP),
    0xFFEA: ("APP10", "Application segment 10", APP),
    0xFFEB: ("APP11", "Application segment 11", APP),
    0xFFEC: ("APP12", "Application segment 12", APP),
    0xFFED: ("APP13", "Application segment 13", APP),
    0xFFEE: ("APP14", "Application segment 14", APP),
    0xFFEF: ("APP15", "Application segment 15", APP),
    0xFFF0: ("JPG0", "Extension 0", None),
    0xFFF1: ("JPG1", "Extension 1", None),
    0xFFF2: ("JPG2", "Extension 2", None),
    0xFFF3: ("JPG3", "Extension 3", None),
    0xFFF4: ("JPG4", "Extension 4", None),
    0xFFF5: ("JPG5", "Extension 5", None),
    0xFFF6: ("JPG6", "Extension 6", None),
    0xFFF7: ("JPG7", "Extension 7", None),
    0xFFF8: ("JPG8", "Extension 8", None),
    0xFFF9: ("JPG9", "Extension 9", None),
    0xFFFA: ("JPG10", "Extension 10", None),
    0xFFFB: ("JPG11", "Extension 11", None),
    0xFFFC: ("JPG12", "Extension 12", None),
    0xFFFD: ("JPG13", "Extension 13", None),
    0xFFFE: ("COM", "Comment", COM)
}


class JpegImageFile:
    def __init__(self, url):
        self.bits = self.pxcount = self.layers = self.quality = 0
        self.layer = []
        self.huffman_dc = {}
        self.huffman_ac = {}
        self.quantization = {}
        self.app = {}  # compatibility
        self.applist = []
        self.icclist = []
        self.fp = None
        self.tile = []
        self.info = {}
        self.size = {}
        self.open(url)

    def openurl(self, url):
        while True:
            try:
                self.fp = urllib2.urlopen(url, timeout=10)
            except urllib2.URLError as exc:
                Log("Error loading image. Sleeping for 3 sec")
                time.sleep(3)
                continue
            except:
                Log("Something wrong!!!")
                self.fp.close()
            else:
                break

    def open(self, url):
        self.openurl(url)
        if self.fp:
            s = ''
            s = self.fp.read(1)
            if i8(s[0]) != 255:
                raise SyntaxError("not a JPEG file")
                self.fp.close()

            while True:
                i = i8(s)
                if i == 0xFF:
                    s = s + self.fp.read(1)
                    i = i16(s)
                else:
                    # Skip non-0xFF junk
                    s = b"\xff"
                    continue

                if i in MARKER:
                    name, description, handler = MARKER[i]
                    # print hex(i), name, description
                    if handler is not None:
                        handler(self, i)
                    if i == 0xFFDA:  # start of scan
                        rawmode = self.mode
                        if self.mode == "CMYK":
                            rawmode = "CMYK;I"  # assume adobe conventions
                        self.tile = [("jpeg", (0, 0) + self.size, 0,
                                      (rawmode, ""))]
                        # self.__offset = self.fp.tell()
                        break
                    s = self.fp.read(1)
                elif i == 0 or i == 0xFFFF:
                    # padded marker or junk; move on
                    s = b"\xff"
                else:
                    raise SyntaxError("no marker found")
            compileQuol(self)
            self.fp.close()
        else:
            raise SyntaxError("nothing to read")