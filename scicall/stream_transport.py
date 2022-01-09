from gi.repository import Gst
from scicall.stream_settings import (
    TransportType,
    VideoCodecType,
    AudioCodecType,
)


class SourceTransportBuilder:
    """ Строитель приёмного каскада внешнего потока. 

            В зависимости от используемого протокола, создаёт на основании переданного 
            объекта @settings, приёмный каскад в конвеере @pipeline  
    """

    def make(self, pipeline, settings):
        builders = {
            TransportType.SRT: self.srt,
            TransportType.SRTREMOTE: self.srt_remote,
            TransportType.UDP: self.udp,
            TransportType.RTPUDP: self.rtpudp
        }
        return builders[settings.transport](pipeline, settings)

    def srt(self, pipeline, settings):
        srtsrc = Gst.ElementFactory.make("srtsrc", None)
        srtsrc.set_property('uri', f"srt://:{settings.port}")
        srtsrc.set_property('wait-for-connection', False)
        pipeline.add(srtsrc)
        return (srtsrc, srtsrc)

    def srt_remote(self, pipeline, settings):
        srtsrc = Gst.ElementFactory.make("srtsrc", None)
        srtsrc.set_property('uri', f"srt://{settings.ip}:{settings.port}")
        srtsrc.set_property('wait-for-connection', False)
        pipeline.add(srtsrc)
        return (srtsrc, srtsrc)

    def udp(self, pipeline, settings):
        udpsrc = Gst.ElementFactory.make("udpsrc", None)
        udpsrc.set_property('port', settings.port)
        pipeline.add(udpsrc)
        return (udpsrc, udpsrc)

    def rtpudp(self, pipeline, settings):
        udpsrc = Gst.ElementFactory.make("udpsrc", None)
        q = Gst.ElementFactory.make("queue", None)
        caps = Gst.Caps.from_string(self.rtpcodecdepay_caps(settings.codec))
        capsfilter = Gst.ElementFactory.make('capsfilter', None)
        capsfilter.set_property("caps", caps)
        rtpjpegdepay = Gst.ElementFactory.make(
            self.rtpcodecdepay(settings.codec), None)
        udpsrc.set_property('port', settings.port)
        pipeline.add(udpsrc)
        pipeline.add(rtpjpegdepay)
        pipeline.add(q)
        pipeline.add(capsfilter)
        udpsrc.link(capsfilter)
        capsfilter.link(rtpjpegdepay)
        rtpjpegdepay.link(q)
        return (udpsrc, q)

    def rtpcodecdepay_caps(self, codec):
        return {
            VideoCodecType.H264: "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96",
            VideoCodecType.MJPEG: "application/x-rtp, encoding-name=JPEG, payload=26",
            AudioCodecType.OPUS: "application/x-rtp, encoding-name=OPUS, payload=96"
        }[codec]

    def rtpcodecdepay(self, codec):
        return {
            VideoCodecType.H264: "rtph264depay",
            VideoCodecType.MJPEG: "rtpjpegdepay",
            AudioCodecType.OPUS: "rtpopusdepay"
        }[codec]


class TranslationTransportBuilder:
    """ Строитель передающего каскада исходящего потока. 

            В зависимости от используемого протокола, создаёт на основании переданного 
            объекта @settings, передающий каскад в конвеере @pipeline  
    """

    def __init__(self):
        self.srt_latency = 30

    def make(self, pipeline, settings):
        builders = {
            TransportType.SRT: self.srt,
            TransportType.SRTREMOTE: self.srt_remote,
            TransportType.UDP: self.udp,
            TransportType.RTPUDP: self.rtpudp
        }
        return builders[settings.transport](pipeline, settings)

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
            VideoCodecType.H264: "rtph264pay",
            VideoCodecType.MJPEG: "rtpjpegpay",
            AudioCodecType.OPUS: "rtpopuspay",
        }[codec]
