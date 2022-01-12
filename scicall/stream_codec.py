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
            VideoCodecType.H264: self.h264,
            VideoCodecType.NOCODEC: self.nocodec,
            AudioCodecType.NOCODEC: self.nocodec,
            AudioCodecType.OPUS: self.opus,
        }
        return builders[settings.codec](pipeline, settings)

    def nocodec(self, pipeline, settings):
        elem = Gst.ElementFactory.make("ident", None)
        pipeline.add(elem)
        return (elem, elem)

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

    def h264(self, pipeline, settings):
        h264parse = Gst.ElementFactory.make("h264parse", None)
        h264dec = Gst.ElementFactory.make("avdec_h264", None)
        pipeline.add(h264parse)
        pipeline.add(h264dec)
        h264parse.link(h264dec)
        return (h264parse, h264dec)


class TranslationCodecBuilder:
    """ Строитель кодировщика исходящего потока. 

            В зависимости от используемого кодека, создаёт на основании переданного 
            объекта @settings, кодирующий каскад в конвеере @pipeline  
    """

    def make(self, pipeline, settings):
        builders = {
            VideoCodecType.MJPEG: self.mjpeg,
            VideoCodecType.H264: self.h264,
            AudioCodecType.OPUS: self.opus,
            VideoCodecType.NOCODEC: self.nocodec,
            AudioCodecType.NOCODEC: self.nocodec
        }
        return builders[settings.codec](pipeline, settings)

    def nocodec(self, pipeline, settings):
        elem = Gst.ElementFactory.make("identity", None)
        pipeline.add(elem)
        return (elem, elem)
        
    def mjpeg(self, pipeline, settings):
        jpegenc = Gst.ElementFactory.make("jpegenc", None)
        jpegenc.set_property('quality', 85)
        pipeline.add(jpegenc)
        return (jpegenc, jpegenc)

    def opus(self, pipeline, settings):
        opusenc = Gst.ElementFactory.make("opusenc", None)
        pipeline.add(opusenc)
        return (opusenc, opusenc)

    def h264(self, pipeline, settings):
        h264enc = Gst.ElementFactory.make("x264enc", None)
        h264enc.set_property('tune', "zerolatency")
        pipeline.add(h264enc)
        return (h264enc, h264enc)
