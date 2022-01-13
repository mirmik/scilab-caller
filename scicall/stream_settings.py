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
    RTPSRTREMOTE = "rtp/srt(client)"
    RTPSRT = "rtp/srt(server)"
    UDP = "udp"
    RTPUDP = "rtp/udp"
    NDI = "ndi"


class VideoCodecType(str, Enum):
    MJPEG = "mjpeg",
    H264 = "h264",
    H264_TS = "h264_ts",
    H265 = "h265",
    NOCODEC = "nocodec",


class AudioCodecType(str, Enum):
    OPUS = "opus",
    NOCODEC = "nocodec",


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
                 mediatype=None,
                 ndi_name=None,
                 on_srt_caller_removed=None,
                 on_srt_caller_added=None
):
        self.mode = mode
        self.device = device
        self.transport = transport
        self.codec = codec
        self.ip = ip
        self.port = port
        self.mediatype = mediatype
        self.ndi_name = ndi_name
        self.on_srt_caller_added = on_srt_caller_added
        self.on_srt_caller_removed = on_srt_caller_removed


class MiddleSettings:
    def __init__(self, display_enabled):
        self.display_enabled = display_enabled
