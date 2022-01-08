from gi.repository import Gst
from scicall.stream_settings import (
	VideoCodecType, 
	AudioCodecType, 
)

class SourceCodecBuilder:
	""" Строитель декодировщика внешнего потока. 
		
		В зависимости от используемого кодека, создаёт на основании переданного 
		объекта @settings, декодирующий каскад в конвеере @pipeline  
	"""

	def make(self, pipeline, settings):
		builders = {
			VideoCodecType.MJPEG: self.mjpeg,
			AudioCodecType.OPUS: self.opus
		}
		return builders[settings.codec](pipeline, settings)	

	def mjpeg(self, pipeline, settings):
		jpegparse = Gst.ElementFactory.make("jpegparse", None)
		jpegdec = Gst.ElementFactory.make("jpegdec", None)
		pipeline.add(jpegparse)
		pipeline.add(jpegdec)
		jpegparse.link(jpegdec)
		return (jpegparse, jpegdec)

	def opus(self, pipeline, settings):
		opusparse = Gst.ElementFactory.make("opusparse", None)
		opusdec = Gst.ElementFactory.make("opusdec", None)
		pipeline.add(opusparse)
		pipeline.add(opusdec)
		opusparse.link(opusdec)
		return (opusparse, opusdec)

class TranslationCodecBuilder:
	""" Строитель кодировщика исходящего потока. 
		
		В зависимости от используемого кодека, создаёт на основании переданного 
		объекта @settings, кодирующий каскад в конвеере @pipeline  
	"""
	def make(self, pipeline, settings):
		builders = {
			VideoCodecType.MJPEG: self.mjpeg,
			AudioCodecType.OPUS: self.opus
		}
		return builders[settings.codec](pipeline, settings)

	def mjpeg(self, pipeline, settings):
		jpegenc = Gst.ElementFactory.make("jpegenc", None)
		jpegenc.set_property('quality', 50)
		pipeline.add(jpegenc)
		return (jpegenc, jpegenc)

	def opus(self, pipeline, settings):
		opusenc = Gst.ElementFactory.make("opusenc", None)
		pipeline.add(opusenc)
		return (opusenc, opusenc)