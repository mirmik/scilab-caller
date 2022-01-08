from enum import Enum

class SourceMode(str, Enum):
	CAMERA = "Камера"
	TEST = "Тестовый источник"
	STREAM = "Входной поток"

class TranslateMode(str, Enum):
	NOTRANS = "Нет" 
	STATION = "Автомат."
	STREAM = "Поток"

class TransportType(str, Enum):
	SRT = "srt(listen)" 
	SRTREMOTE = "srt(remote)" 
	UDP = "udp" 
	RTPUDP = "rtp/udp"

class CodecType(str, Enum):
	MJPEG = "mjpeg"

class SourceStreamSettings:
	def __init__(self, 
		mode, 
		device=None, 
		transport=None, 
		codec=None,
		ip=None, 
		port=None 
	):
		self.mode = mode
		self.device = device
		self.transport = transport
		self.codec = codec
		self.ip = ip
		self.port = port

class TranslationStreamSettings:
	def __init__(self, 
		mode, 
		transport=None, 
		codec=None,
		ip=None, 
		port=None 
	):
		self.mode = mode
		self.transport = transport
		self.codec = codec
		self.ip = ip
		self.port = port