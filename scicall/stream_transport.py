from gi.repository import Gst
from scicall.stream_settings import (
    TransportType,
    VideoCodecType,
    AudioCodecType,
    MediaType
)
from scicall.util import pipeline_chain

class TransportBuilder:
    def __init__(self):
        self.srt_latency = 60

class SourceTransportBuilder(TransportBuilder):
    """ Строитель приёмного каскада внешнего потока. 

            В зависимости от используемого протокола, создаёт на основании переданного 
            объекта @settings, приёмный каскад в конвеере @pipeline  
    """

    def make(self, pipeline, settings):
        builders = {
            TransportType.SRT: self.srt,
            TransportType.SRTREMOTE: self.srt_remote,
            TransportType.RTPSRT: self.rtpsrt,
            TransportType.RTPSRTREMOTE: self.rtpsrt_remote,
            TransportType.UDP: self.udp,
            TransportType.RTPUDP: self.rtpudp,
            TransportType.NDI: self.ndi
        }
        return builders[settings.transport](pipeline, settings)


    def srt(self, pipeline, settings):
        srtsrc = Gst.ElementFactory.make("srtsrc", None)
        srtsrc.set_property('uri', f"srt://:{settings.port}")
        srtsrc.set_property('wait-for-connection', False)
        srtsrc.set_property('latency', self.srt_latency)
    
        if settings.on_srt_caller_removed:    
            srtsrc.connect("caller-removed", settings.on_srt_caller_removed)
        
        if settings.on_srt_caller_added:    
            srtsrc.connect("caller-added", settings.on_srt_caller_added)
        
        return pipeline_chain(pipeline, srtsrc)

    def ndi(self, pipeline, settings):
        raise Exception("Not Supported")

    def srt_remote(self, pipeline, settings):
        srtsrc = Gst.ElementFactory.make("srtsrc", None)
        srtsrc.set_property('uri', f"srt://{settings.ip}:{settings.port}")
        srtsrc.set_property('wait-for-connection', False)
        srtsrc.set_property('latency', self.srt_latency)
        return pipeline_chain(pipeline, srtsrc)

    def udp(self, pipeline, settings):
        udpsrc = Gst.ElementFactory.make("udpsrc", None)
        udpsrc.set_property('port', settings.port)
        return pipeline_chain(pipeline, udpsrc)

    def rtpudp(self, pipeline, settings):
        udpsrc = Gst.ElementFactory.make("udpsrc", None)
        jitterbuffer = Gst.ElementFactory.make("rtpjitterbuffer", None)
        q = Gst.ElementFactory.make("queue", None)
        caps = Gst.Caps.from_string(self.rtpcodecdepay_caps(settings.codec))
        capsfilter = Gst.ElementFactory.make('capsfilter', None)
        capsfilter.set_property("caps", caps)
        rtpjpegdepay = Gst.ElementFactory.make(
            self.rtpcodecdepay(settings.codec), None)
        udpsrc.set_property('port', settings.port)
        udpsrc.link(capsfilter)
        capsfilter.link(jitterbuffer)
        jitterbuffer.link(rtpjpegdepay)
        rtpjpegdepay.link(q)
        return pipeline_chain(pipeline, udpsrc, capsfilter, jitterbuffer, rtpjpegdepay, q)

    def on_srt_caller_removed(self):
        print("On srt caller removed")
    def on_srt_caller_added(self):
        print("On srt caller added")

    def rtpsrt(self, pipeline, settings):
        srtsrc = Gst.ElementFactory.make("srtsrc", None)
        srtsrc.set_property('uri', f"srt://:{settings.port}")
        srtsrc.set_property('wait-for-connection', False)
        srtsrc.set_property('latency', self.srt_latency)
        srtsrc.connect("caller-removed", self.on_srt_caller_removed)
        srtsrc.connect("caller-added", self.on_srt_caller_added)
        capsfilter = self.make_capsfilter(settings.codec)
        depay = self.make_depay(settings.codec)
        q = Gst.ElementFactory.make("queue", None)
        return pipeline_chain(pipeline, srtsrc, capsfilter, depay, q)

    def rtpsrt_remote(self, pipeline, settings):
        srtsrc = Gst.ElementFactory.make("srtsrc", None)
        srtsrc.set_property('uri', f"srt://{settings.ip}:{settings.port}")
        srtsrc.set_property('wait-for-connection', False)
        srtsrc.set_property('latency', self.srt_latency)
        capsfilter = self.make_capsfilter(settings.codec)
        depay = self.make_depay(settings.codec)
        q = Gst.ElementFactory.make("queue", None)
        return pipeline_chain(pipeline, srtsrc, capsfilter, depay, q)

    def make_capsfilter(self, codec):
        caps = Gst.Caps.from_string(self.rtpcodecdepay_caps(codec))
        capsfilter = Gst.ElementFactory.make('capsfilter', None)
        capsfilter.set_property("caps", caps)
        return capsfilter

    def make_depay(self, codec):
        depay = Gst.ElementFactory.make(self.rtpcodecdepay(codec), None)
        return depay


    def rtpcodecdepay_caps(self, codec):
        return {
            VideoCodecType.H264_TS: "application/x-rtp,media=video,clock-rate=90000,encoding-name=MP2T-ES",
            VideoCodecType.H265: "application/x-rtp, media=video, clock-rate=90000, encoding-name=H265, payload=96",
            VideoCodecType.H264: "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96",
            VideoCodecType.MJPEG: "application/x-rtp, encoding-name=JPEG, payload=26",
            AudioCodecType.OPUS: "application/x-rtp, encoding-name=OPUS, payload=96"
        }[codec]

    def rtpcodecdepay(self, codec):
        return {
            VideoCodecType.H264_TS: "rtpmp2tdepay",
            VideoCodecType.H264: "rtph264depay",
            VideoCodecType.H265: "rtph265depay",
            VideoCodecType.MJPEG: "rtpjpegdepay",
            AudioCodecType.OPUS: "rtpopusdepay"
        }[codec]


class TranslationTransportBuilder(TransportBuilder):
    """ Строитель передающего каскада исходящего потока. 

            В зависимости от используемого протокола, создаёт на основании переданного 
            объекта @settings, передающий каскад в конвеере @pipeline  
    """

    def make(self, pipeline, settings):
        builders = {
            TransportType.SRT: self.srt,
            TransportType.SRTREMOTE: self.srt_remote,
            TransportType.RTPSRT: self.rtpsrt,
            TransportType.RTPSRTREMOTE: self.rtpsrt_remote,
            TransportType.UDP: self.udp,
            TransportType.RTPUDP: self.rtpudp,
            TransportType.NDI: self.ndi
        }
        return builders[settings.transport](pipeline, settings)

    def converter(self,mediatype):
        if mediatype == MediaType.VIDEO:
            return "videoconvert"
        else:
            return "audioconvert"

    def ndi(self, pipeline, settings):

        if settings.mediatype == MediaType.VIDEO:
            converter = Gst.ElementFactory.make(self.converter(settings.mediatype), None)
            videoscale = Gst.ElementFactory.make("videoscale", None)
            ndisink = Gst.ElementFactory.make("ndisink", None)
            caps = Gst.Caps.from_string("video/x-raw,format=UYVY,width=800,height=600")
            capsfilter = Gst.ElementFactory.make('capsfilter', None)
            capsfilter.set_property("caps", caps)        
            ndisink.set_property('ndi-name', settings.ndi_name)
            return pipeline_chain(pipeline, converter, videoscale, capsfilter, ndisink) 

        else:
            converter = Gst.ElementFactory.make(self.converter(settings.mediatype), None)
            ndisink = Gst.ElementFactory.make("ndisink", None)
            ndisink.set_property('ndi-name', settings.ndi_name)
            return pipeline_chain(pipeline, converter, ndisink)

    def srt(self, pipeline, settings):
        srtsink = Gst.ElementFactory.make("srtsink", None)
        srtsink.set_property('uri', f"srt://:{settings.port}")
        srtsink.set_property('wait-for-connection', False)
        #srtsink.set_property('sync', False)
        srtsink.set_property('latency', self.srt_latency)
        pipeline.add(srtsink)
        return srtsink, srtsink

    def srt_remote(self, pipeline, settings):
        srtsink = Gst.ElementFactory.make("srtsink", None)
        srtsink.set_property('uri', f"srt://{settings.ip}:{settings.port}")
        srtsink.set_property('wait-for-connection', False)
        srtsink.set_property('latency', self.srt_latency)
        #srtsink.set_property('sync', False)
        pipeline.add(srtsink)
        return srtsink, srtsink

    def rtpsrt(self, pipeline, settings):
        srtsink = Gst.ElementFactory.make("srtsink", None)
        srtsink.set_property('uri', f"srt://:{settings.port}")
        srtsink.set_property('wait-for-connection', False)
        srtsink.set_property('latency', self.srt_latency)
        rtpcodecpay = Gst.ElementFactory.make(self.rtpcodecpay(settings.codec), None)
        return pipeline_chain(pipeline, rtpcodecpay, srtsink)

    def rtpsrt_remote(self, pipeline, settings):
        srtsink = Gst.ElementFactory.make("srtsink", None)
        srtsink.set_property('uri', f"srt://{settings.ip}:{settings.port}")
        srtsink.set_property('wait-for-connection', False)
        srtsink.set_property('latency', self.srt_latency)
        rtpcodecpay = Gst.ElementFactory.make(self.rtpcodecpay(settings.codec), None)
        return pipeline_chain(pipeline, rtpcodecpay, srtsink)

    def udp(self, pipeline, settings):
        udpsink = Gst.ElementFactory.make("udpsink", None)
        udpsink.set_property('port', settings.port)
        udpsink.set_property('host', settings.ip)
        #udpsink.set_property('sync', False)
        pipeline.add(udpsink)
        return udpsink, udpsink

    def rtpudp(self, pipeline, settings):
        udpsink = Gst.ElementFactory.make("udpsink", None)
        udpsink.set_property('port', settings.port)
        udpsink.set_property('host', settings.ip)
        #udpsink.set_property('sync', False)
        rtpcodecpay = Gst.ElementFactory.make(
            self.rtpcodecpay(settings.codec), None)
        pipeline.add(udpsink)
        pipeline.add(rtpcodecpay)
        rtpcodecpay.link(udpsink)
        return rtpcodecpay, udpsink

    def rtpcodecpay(self, codec):
        return {
            VideoCodecType.H264_TS: "rtpmp2tpay",
            VideoCodecType.H265: "rtph265pay",
            VideoCodecType.H264: "rtph264pay",
            VideoCodecType.MJPEG: "rtpjpegpay",
            AudioCodecType.OPUS: "rtpopuspay",
        }[codec]
