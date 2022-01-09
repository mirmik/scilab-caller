from enum import Enum

class MediaType(Enum):
	VIDEO = 0,
	AUDIO = 1

class SourceMode(str, Enum):
	CAPTURE = "Захват"
	TEST = "Тестовый источник"
	STREAM = "Входной поток"

class TranslateMode(str, Enum):
	NOTRANS = "Нет" 
	STATION = "Автомат."
	STREAM = "Поток"

class TransportType(str, Enum):
	SRTREMOTE = "srt(client)" 
	SRT = "srt(server)" 
	UDP = "udp" 
	RTPUDP = "rtp/udp"

class VideoCodecType(str, Enum):
	MJPEG = "mjpeg",
	H264 = "h264",

class AudioCodecType(str, Enum):
	OPUS = "opus"

class StreamSettings:
	""" В объекте содержаться все возможные поля состаяний. 
	    Строители разберуться, что из этого имеет значение. 
	"""

	def __init__(self, 
		mode, 
		device=None, 
		transport=None, 
		codec=None,
		ip=None, 
		port=None,
		mediatype=None 
	):
		self.mode = mode
		self.device = device
		self.transport = transport
		self.codec = codec
		self.ip = ip
		self.port = port
		self.mediatype = mediatype

class MiddleSettings:
	def __init__(self, display_enabled):
		self.display_enabled = display_enabled