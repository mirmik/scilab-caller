from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from gi.repository import GObject, Gst, GstVideo
import traceback
import time

from scicall.display_widget import GstreamerDisplay
import scicall.pipeline_utils as pipeline_utils
import json

from scicall.util import (
    channel_control_port, 
    channel_video_port,
    channel_audio_port, 
    channel_feedback_video_port,
    channel_feedback_audio_port,
    internal_channel_udpspam_port,
    channel_mpeg_stream_port,
    channel_feedback_mpeg_stream_port)


class ExternalSignalPanel(QWidget):
    def __init__(self, chno, zone):
        super().__init__()
        self.zone = zone
        self.pipeline = None
        self.chno = chno
        self.viddisp = GstreamerDisplay()
        self.auddisp = GstreamerDisplay()
        self.viddisp.setFixedSize(QSize(160, 160))
        self.auddisp.setFixedSize(QSize(160, 160))
        #self.displayout = QHBoxLayout()
        self.hlayout = QHBoxLayout()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.viddisp)
        self.layout.addWidget(self.auddisp)
        self.hlayout.addLayout(self.layout)
        self.setLayout(self.hlayout)
        self.inited=False
        self.make_control_panel()

    def make_control_panel(self):
        self.source_types = ["Нет", "Тестовый1", "Тестовый2", "NDI", "SRT", "UDP"]
        self.source_types_cb = QComboBox()
        self.source_types_cb.addItems(self.source_types)
        self.ndi_name_edit = QLineEdit()
        self.control_layout = QGridLayout()
        self.control_layout.addWidget(QLabel(f"Внешний источник: {self.chno}"), 0, 0, 1, 2)
        self.control_layout.addWidget(QLabel("Тип источника:"), 1, 0)
        self.control_layout.addWidget(self.source_types_cb, 1, 1)
        self.control_layout.addWidget(QLabel("Имя (для ndi):"), 2, 0)
        self.control_layout.addWidget(self.ndi_name_edit, 2, 1)
        self.hlayout.addLayout(self.control_layout)
        self.source_types_cb.currentIndexChanged.connect(self.source_types_cb_handle)
        self.ndi_name_edit.editingFinished.connect(self.ndi_name_text_handle)

        #label = QLabel()
        #label.setMinimumSize( QSize(0,0) )
        #label.setMaximumSize( QSize(16777215, 16777215) )
        #label.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred );
        #self.control_layout.addWidget(label, 9,0)

    def ndi_name_text_handle(self):
        self.update_control()

    def source_types_cb_handle(self, str):
        self.update_control()

    def update_control(self):
        self.stop_pipeline()
        self.zone.stop_external_stream()
        self.start_pipeline()
        self.zone.start_external_stream()

    def source_type(self):
        return self.source_types_cb.currentText()

    def stop_pipeline(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        time.sleep(0.1)
        self.pipeline = None

    def input_ndi_name(self):
        return self.ndi_name_edit.text()

    def generate_pipeline_template(self):
            videocaps = pipeline_utils.global_videocaps()
            srctype = self.source_type()
            if srctype == "Нет":
                return None
            elif srctype == "Тестовый1" or srctype == "Тестовый2":
                pattern = "" if srctype == "Тестовый1" else "pattern=snow"
                return f"""videotestsrc {pattern} ! videoconvert ! tee name=vidtee 
                    vidtee. ! queue name=q0 ! appsink name=videoapp
                    vidtee. ! queue name=q1 ! autovideosink name=videoend
                """

                """
                    audiotestsrc ! audioconvert ! tee name=audtee 
                    audtee. ! queue name=q2 ! appsink name=audioapp
                    audtee. ! queue name=q3 ! spectrascope ! 
                        videoconvert ! {videocaps} ! autovideosink name=audioend"""

            
            elif srctype == "NDI":
                common_source = f"""
                     ndivideosrc ndi-name="ASUS-PC19 (vMix - Output 4)" ! queue ! videoconvert 
                        ! autovideosink name=videoend"""

                return common_source                   
            elif srctype == "SRT":
                common_source = f"""srtsrc uri=srt://127.0.0.1:10000 do-timestamp=true latency=60 ! 
                    queue name=q3 ! tsparse set-timestamps=true ! tsdemux name=demux"""
                video_source = f"demux. ! queue name=q1 ! h264parse update-timecode=true ! nvh264dec"
                audio_source = f"demux. ! queue name=q4"                     

            elif srctype == "UDP":
                common_source = f"udpsrc port=10001 do-timestamp=true ! queue ! tsparse set-timestamps=true ! tsdemux name=demux"
                video_source = f"demux. ! queue name=q1 ! h264parse ! nvh264dec"
                audio_source = f"fakesrc"  

            return f"""
                {common_source}
                {video_source} ! queue name=q0 ! videoconvert ! autovideosink name=videoend
                {audio_source} ! fakesink
            """
  #              {video_source} ! queue ! videoconvert ! tee name=vidtee 
 #               vidtee. ! queue ! videoconvert ! autovideosink name=videoend
#                vidtee. ! queue ! appsink name=vidapp
            #    {audio_source} ! queue ! audioconvert ! spectrascope ! videoconvert ! autovideosink name=audioend 
            

    def start_pipeline(self):
        template = self.generate_pipeline_template()
        if not template:
            return

        self.pipeline=Gst.parse_launch(template)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        
        if self.source_type() != "Нет":
            self.pipeline.set_state(Gst.State.PLAYING)

        qs = [ "q0", "q1", "q2", "q3", "q4" ] 
        qs = [ self.pipeline.get_by_name(qname) for qname in qs ]
        for q in qs:
            pipeline_utils.setup_queuee(q)  

        self.audioapp = self.pipeline.get_by_name("audioapp")
        if self.audioapp:
            self.audioapp.set_property("sync", False)
            self.audioapp.set_property("emit-signals", True)
            self.audioapp.set_property("max-buffers", 1)
            self.audioapp.set_property("drop", True)
            self.audioapp.set_property("emit-signals", True)
            self.audioapp.connect("new-sample", self.audio_new_sample, None)

        self.videoapp = self.pipeline.get_by_name("videoapp")
        self.videoapp.set_property("sync", False)
        self.videoapp.set_property("emit-signals", True)
        self.videoapp.set_property("max-buffers", 1)
        self.videoapp.set_property("drop", True)
        self.videoapp.set_property("emit-signals", True)
        self.videoapp.connect("new-sample", self.video_new_sample, None)

    def audio_new_sample(self, a, b):
        sample = self.audioapp.emit("pull-sample")
        self.zone.external_audio_sample(self.chno, sample)
        #buf = sample.get_buffer()
        #buf.pts = Gst.CLOCK_TIME_NONE 
        #buf.dts = Gst.CLOCK_TIME_NONE 
        #buf.duration = Gst.CLOCK_TIME_NONE
        return Gst.FlowReturn.OK

    def video_new_sample(self, a, b):
        sample = self.videoapp.emit("pull-sample")
        self.zone.external_video_sample(self.chno, sample)
        #buf = sample.get_buffer()
        #buf.pts = Gst.CLOCK_TIME_NONE 
        #buf.dts = Gst.CLOCK_TIME_NONE 
        #buf.duration = Gst.CLOCK_TIME_NONE
        return Gst.FlowReturn.OK

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            name = msg.src.get_parent().get_parent().name
            if name=="videoend":
                self.viddisp.connect_to_sink(msg.src)
            if name=="audioend":
                self.auddisp.connect_to_sink(msg.src)

    def showEvent(self, ev):
        if self.inited == False:
            self.start_pipeline()
            self.inited = True

class ExternalSignalsZone(QWidget):
    def __init__(self, zone):
        super().__init__()
        self.panels = []
        self.lay = QHBoxLayout()
        for i in range(1):
            self.add_panel(i, zone)
        self.setLayout(self.lay)

    def add_panel(self, i, zone):
        panel = ExternalSignalPanel(i, zone)
        self.panels.append(panel)
        self.lay.addWidget(panel)