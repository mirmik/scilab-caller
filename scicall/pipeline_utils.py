from gi.repository import GObject, Gst, GstVideo
from scicall.util import pipeline_chain
from enum import Enum

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class GstSubchain:
    def __init__(self, *arr):
        self.arr = arr
        self.enabled = False

    def internal_link(self):
        for i in range(len(self.arr)-1):
            self.arr[i].link(self.arr[i+1])

    def internal_unlink(self):
        for i in range(len(self.arr)-1):
            self.arr[i].unlink(self.arr[i+1])

    def link(self, oth):
        if isinstance(oth, GstSubchain):
            self.arr[-1].link(oth.arr[0])
            return    
        else:
            self.arr[-1].link(oth)

    def unlink(self, oth):
        if isinstance(oth, GstSubchain):
            self.arr[-1].unlink(oth.arr[0])
            return    
        else:
            self.arr[-1].unlink(oth)

    def set_state(self, state):
        for i in range(len(self.arr)):
            self.arr[i].set_state(state)

    def reverse_link(self, f):
        f.link(self.arr[0])

    def reverse_unlink(self, f):
        f.unlink(self.arr[0])

    def remove_from_pipeline(self, pipeline):
        self.internal_unlink()
        for a in self.arr:
            pipeline.remove(a)
        self.enabled = False

    def add_to_pipeline(self, pipeline):
        for a in self.arr:
            pipeline.add(a)
        self.internal_link()
        self.enabled = True

    def is_enabled(self):
        return self.enabled

def tee_from(pipeline, src):
    q=buffer_queue()
    tee = Gst.ElementFactory.make("tee", None)
    pipeline.add(tee)
    pipeline.add(q)
    q.link(tee)
    src.link(q)
    return GstSubchain(q, tee)

def buffer_queue():
    q = Gst.ElementFactory.make("queue", None)
    q.set_property("max-size-bytes", 100000) 
    q.set_property("max-size-buffers", 0) 
    return q

def make_video_feedback_capsfilter(width, height):
    """Создаёт capsfilter, определяющий, форматирование ответвления конвеера, идущего
    к контрольному видео виджету."""
    caps = Gst.Caps.from_string(
        f"video/x-raw,width={width},height={height}")
    capsfilter = Gst.ElementFactory.make('capsfilter', None)
    capsfilter.set_property("caps", caps)
    return capsfilter


def display_video_from_tee(pipeline, tee):
    q = buffer_queue()
    videoscale = Gst.ElementFactory.make("videoscale", None)
    videoconvert = Gst.ElementFactory.make("videoconvert", None)
    sink = Gst.ElementFactory.make("autovideosink", None)
    sink.set_property("sync", False)
    sink_capsfilter = make_video_feedback_capsfilter(320, 240)
    pipeline_chain(pipeline, q, videoscale, videoconvert, sink_capsfilter, sink)
    tee.link(q)
    return sink

def display_specter_from_tee(pipeline, tee):
    q = buffer_queue()
    convert = Gst.ElementFactory.make("audioconvert", None)
    spectrascope = Gst.ElementFactory.make("spectrascope", None)
    vconvert = Gst.ElementFactory.make("videoconvert", None)
    sink = Gst.ElementFactory.make("autovideosink", None)
    sink_capsfilter = make_video_feedback_capsfilter(320, 240)
    pipeline_chain(pipeline, q, convert, spectrascope, vconvert, sink_capsfilter, sink)
    tee.link(q)
    return sink

def h264_encode_from_tee(pipeline, tee):
    q = buffer_queue()
    vconvert = Gst.ElementFactory.make("videoconvert", None)
    h264 = Gst.ElementFactory.make("x264enc", None)
    h264.set_property('tune', "zerolatency")
    pipeline_chain(pipeline, q, vconvert, h264)
    tee.link(q)
    return h264

def h264dec_from(pipeline, src):
    q = buffer_queue()
    parser = Gst.ElementFactory.make("h264parse", None)
    decoder = Gst.ElementFactory.make("avdec_h264", None)
    pipeline_chain(pipeline, q, parser, decoder)
    src.link(q)
    return GstSubchain(q, parser, decoder)

def opusdec_from(pipeline, src):
    q = buffer_queue()
    parser = Gst.ElementFactory.make("opusparse", None)
    decoder = Gst.ElementFactory.make("opusdec", None)
    pipeline_chain(pipeline, q, parser, decoder)
    src.link(q)
    return GstSubchain(q, parser, decoder)

def opus_encode_from_tee(pipeline, tee):
    q = buffer_queue()
    vconvert = Gst.ElementFactory.make("audioconvert", None)
    opus = Gst.ElementFactory.make("opusenc", None)
    pipeline_chain(pipeline, q, vconvert, opus)
    tee.link(q)
    return opus

def mpeg_combine_from(pipeline, inputs):
    mpeg = Gst.ElementFactory.make("mpegtsmux", None)
    pipeline.add(mpeg)
    for i in inputs:
        i.link(mpeg)
    return mpeg

def mpeg_demux_from(pipeline, src):
    #q = buffer_queue()    
    parse = Gst.ElementFactory.make("tsparse", None)
    demux = Gst.ElementFactory.make("tsdemux", None)
    caps = Gst.Caps.from_string(f"video/mpegts,systemstream=true")
    capsfilter = Gst.ElementFactory.make('capsfilter', None)
    capsfilter.set_property("caps", caps)
    pipeline_chain(pipeline, parse, capsfilter, demux)
    src.link(parse)
    return GstSubchain(parse, capsfilter, demux)

def output_sender_srtstream(pipeline, src, host, port, latency=80):
    srtsink = Gst.ElementFactory.make("srtsink", None)
    srtsink.set_property('uri', f"srt://{host}:{port}")
    srtsink.set_property('wait-for-connection', True)
    srtsink.set_property('latency', latency)
    srtsink.set_property('async', True)
    srtsink.set_property('sync', False)
    pipeline.add(srtsink)
    src.link(srtsink)
    return GstSubchain(srtsink)

def on_srt_caller_removed(self, a, b):
    print("On srt caller removed", a, b)

def on_srt_caller_added(self, a, b):
    print("On srt caller added", a, b)

def input_listener_srtstream(pipeline, port, latency=80):
    srtsrc = Gst.ElementFactory.make("srtsrc", None)
    srtsrc.set_property('uri', f"srt://0.0.0.0:{port}?mode=listener")
    srtsrc.set_property('wait-for-connection', True)
    srtsrc.set_property('latency', latency)

    srtsrc.connect("caller-removed", on_srt_caller_removed)    
    srtsrc.connect("caller-added", on_srt_caller_added)

    pipeline_chain(pipeline, srtsrc)
    return GstSubchain(srtsrc)


def output_udpstream(pipeline, src, host, port):
    srtsink = Gst.ElementFactory.make("udpsink", None)
    srtsink.set_property('host', host)
    srtsink.set_property('port', port)
    pipeline.add(srtsink)
    src.link(srtsink)
    return GstSubchain(srtsink)

def fakestub_from(pipeline, src):
    sink = Gst.ElementFactory.make("fakesink", None)
    pipeline.add(sink)
    src.link(sink)
    sink.set_property("sync", False)
    return sink

def autovideosink():
    vconvert = Gst.ElementFactory.make("videoconvert", None)
    sink = Gst.ElementFactory.make("autovideosink", None)
    return GstSubchain(vconvert, sink)

def imagesource(file):
    q = buffer_queue()
    filesrc = Gst.ElementFactory.make("filesrc", None)
    parse = Gst.ElementFactory.make("pngparse", None)
    decode = Gst.ElementFactory.make("pngdec", None)
    convert = Gst.ElementFactory.make("videoconvert", None)
    freeze = Gst.ElementFactory.make("imagefreeze", None)
    freeze.set_property("is-live", True)
    filesrc.set_property("location", file)
    subchain = GstSubchain(filesrc, parse, decode, q, convert, freeze)
    return subchain

def videotestsrc():
    q = buffer_queue()
    src = Gst.ElementFactory.make("videotestsrc", None)
    src.set_property("is-live", True)
    subchain = GstSubchain(src, q)
    return subchain

def capture_video(device):
    source = device.make_gst_element()
    return GstSubchain(source)

def capture_audio(device):
    source = device.make_gst_element()
    aconvert = Gst.ElementFactory.make("audioconvert", None)
    return GstSubchain(source, aconvert)

def quiteaudio():
    src = Gst.ElementFactory.make("audiotestsrc", None)
    src.set_property("is-live", True)
    src.set_property("volume", 0)
    return GstSubchain(src)

class GPUType(str, Enum):
    CPU = "Нет",
    NVIDIA = "Видеокарта nvidia",
    AUTOMATIC = "Автоматически (тестируется)",

def video_decoder_type(codertype):
    if codertype == GPUType.CPU:
        videodecoder = "avdec_h264" 
    elif codertype == GPUType.NVIDIA:
        videodecoder = "nvh264dec"
    return videodecoder 

def video_coder_type(codertype):
    if codertype == GPUType.CPU:
        videocoder = "x264enc tune=zerolatency" 
    elif codertype == GPUType.NVIDIA:
        videocoder = "nvh264enc"
    return videocoder

def get_gpu_type():
    return GPUType.NVIDIA

class GPUChecker(QComboBox):
    def __init__(self):
        super().__init__()
        
        for a in GPUType:
            self.addItem(a)

    def get(self):
        text = self.currentText()
        if text == GPUType.AUTOMATIC:
            return GPUType.NVIDIA
        else:
            return text

    def set(self, type):
        lst = list(GPUType)
        for i, o in enumerate(lst):
            if type == o:
                self.setCurrentIndex(i)


def global_videocaps():
    #return "video/x-raw"
    return "video/x-raw,width=640,height=480,framerate=30/1"

def audiocaps():
    #return "audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1"
    return "audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1"

def queue_size():
    return 100000

def udpbuffer_size():
    return 100000


def max_size_bytes(): return 100000
def max_size_buffers(): return 3
def max_size_time(): return 0
def max_threshold_bytes(): return 0
def max_threshold_buffers(): return 0
def max_threshold_time(): return 0

def setup_queuee(q):
    if q is None:
        return
    q.set_property("max-size-bytes", max_size_bytes()) 
    q.set_property("max-size-buffers", max_size_buffers())
    q.set_property("max-size-time", max_size_time())
    q.set_property("min-threshold-bytes", max_threshold_bytes()) 
    q.set_property("min-threshold-buffers", max_threshold_buffers())
    q.set_property("min-threshold-time", max_threshold_time())
    q.set_property("silent", True)