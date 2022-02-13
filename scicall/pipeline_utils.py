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

class GPUType(str, Enum):
    AUTOMATIC = "Автоматически",
    CPU = "Нет",
    NVIDIA = "Видеокарта nvidia",

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

ISNVIDIA = None 
class GPUChecker(QComboBox):
    def __init__(self):
        super().__init__()
        
        for a in GPUType:
            self.addItem(a)

    def automatic(self):
        global ISNVIDIA
        if ISNVIDIA is False:
            return GPUType.CPU
        if ISNVIDIA is True:
            return GPUType.NVIDIA
        try:
            p = Gst.parse_launch("nvh264enc")
            p.set_state(Gst.State.PLAYING)
            p.set_state(Gst.State.NULL)
            ISNVIDIA=True
        except Exception as ex:
            ISNVIDIA=False
            return GPUType.CPU

        return GPUType.NVIDIA

    def get(self):
        text = self.currentText()
        if text == GPUType.AUTOMATIC:
            return self.automatic()
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

def global_audiocaps():
    #return "audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1"
    return "audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1"

def queue_size():
    return 100000

def udpbuffer_size():
    return 100000

def default_audiocodec():
    return "opus"

def default_audiodecoder():
    if default_audiocodec() == "opus":
        return "opusdec"
    elif default_audiocodec() == "aac":
        return "faad"

def default_audioparser():
    if default_audiocodec() == "opus":
        return "opusparse"
    elif default_audiocodec() == "aac":
        return "aacparse"

def default_audioencoder():
    if default_audiocodec() == "opus":
        return "opusenc frame-size=20 perfect-timestamp=true"
    elif default_audiocodec() == "aac":
        return "faac"

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