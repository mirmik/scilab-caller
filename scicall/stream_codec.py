from gi.repository import Gst
from scicall.stream_settings import (
    VideoCodecType,
    AudioCodecType,
)
from scicall.util import pipeline_chain

class CodecBuilder:
    def __init__(self):
        self.jpeg_quality = 30

class SourceCodecBuilder(CodecBuilder):
    """ Строитель декодировщика внешнего потока. 

            В зависимости от используемого кодека, создаёт на основании переданного 
            объекта @settings, декодирующий каскад в конвеере @pipeline  
    """

    def make(self, pipeline, settings):
        builders = {
            VideoCodecType.MJPEG: self.mjpeg,
            VideoCodecType.H264: self.h264,
            VideoCodecType.H264_TS: self.h264_ts,
            VideoCodecType.H265: self.h265,
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

    def h264_ts(self, pipeline, settings):
        tsparse = Gst.ElementFactory.make("tsparse", None)
        tsdemux = Gst.ElementFactory.make("tsdemux", None)
        h264parse = Gst.ElementFactory.make("h264parse", None)
        h264dec = Gst.ElementFactory.make("avdec_h264", None)
        return pipeline_chain(pipeline, tsparse, tsdemux, h264parse, h264dec)

    def h265(self, pipeline, settings):
        h265parse = Gst.ElementFactory.make("h265parse", None)
        h265dec = Gst.ElementFactory.make("avdec_h265", None)
        pipeline.add(h265parse)
        pipeline.add(h265dec)
        h265parse.link(h265dec)
        return (h265parse, h265dec)


class TranslationCodecBuilder(CodecBuilder):
    """ Строитель кодировщика исходящего потока. 

            В зависимости от используемого кодека, создаёт на основании переданного 
            объекта @settings, кодирующий каскад в конвеере @pipeline  
    """

    def make(self, pipeline, settings):
        builders = {
            VideoCodecType.MJPEG: self.mjpeg,
            VideoCodecType.H264: self.h264,
            VideoCodecType.H264_TS: self.h264_ts,
            VideoCodecType.H265: self.h265,
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
        jpegenc.set_property('quality', self.jpeg_quality)
        pipeline.add(jpegenc)
        return (jpegenc, jpegenc)

    def opus(self, pipeline, settings):
        opusenc = Gst.ElementFactory.make("opusenc", None)
        pipeline.add(opusenc)
        return (opusenc, opusenc)

    def h264(self, pipeline, settings):
        h264enc = Gst.ElementFactory.make("x264enc", None)
        #h264parse = Gst.ElementFactory.make("h264parse", None)
        convert = Gst.ElementFactory.make("videoconvert", None)
        h264enc.set_property('tune', "zerolatency")
        return pipeline_chain(pipeline, convert, h264enc)

    def h264_ts(self, pipeline, settings):
        h264enc = Gst.ElementFactory.make("x264enc", None)
        h264parse = Gst.ElementFactory.make("h264parse", None)
        convert = Gst.ElementFactory.make("videoconvert", None)
        h264enc.set_property('tune', "zerolatency")
        tsmux = Gst.ElementFactory.make("mpegtsmux", None)
        return pipeline_chain(pipeline, convert, h264enc, h264parse, tsmux)

    def h265(self, pipeline, settings):
        h265enc = Gst.ElementFactory.make("x265enc", None)
        convert = Gst.ElementFactory.make("videoconvert", None)
        h265enc.set_property('tune', "zerolatency")
        pipeline.add(h265enc)
        pipeline.add(convert)
        convert.link(h265enc)
        return (convert, h265enc)
