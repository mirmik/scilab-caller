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
        self.chno = chno
        self.viddisp = GstreamerDisplay()
        self.auddisp = GstreamerDisplay()
        self.viddisp.setFixedSize(QSize(200, 160))
        self.auddisp.setFixedSize(QSize(200, 160))
        self.hlayout = QHBoxLayout()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.viddisp)
        self.layout.addWidget(self.auddisp)
        self.hlayout.addLayout(self.layout)
        self.setLayout(self.hlayout)
        self.inited=False
        self.make_control_panel()

    def make_control_panel(self):
        self.source_types = ["Тестовый1", "Тестовый2", "NDI", "SRT", "UDP"]
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

        label = QLabel()
        label.setMinimumSize( QSize(0,0) )
        label.setMaximumSize( QSize(16777215, 16777215) )
        label.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred );
        self.control_layout.addWidget(label, 9,0)

    def ndi_name_text_handle(self):
        self.update_control()

    def source_types_cb_handle(self, str):
        self.update_control()

    def update_control(self):
        self.stop_pipeline()
        self.start_pipeline()

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
            srctype = self.source_type()
            if srctype == "Тестовый1":
                common_source = ""
                video_source = f"videotestsrc"
                audio_source = f"audiotestsrc"
            elif srctype == "Тестовый2":
                common_source = ""
                video_source = f"videotestsrc pattern=snow"
                audio_source = f"audiotestsrc"
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
                {audio_source} ! fakesink sync=false
            """
  #              {video_source} ! queue ! videoconvert ! tee name=vidtee 
 #               vidtee. ! queue ! videoconvert ! autovideosink name=videoend
#                vidtee. ! queue ! appsink name=vidapp
            #    {audio_source} ! queue ! audioconvert ! spectrascope ! videoconvert ! autovideosink name=audioend 
            

    def video_new_sample(self, a, b):
        sample = self.vidapp.emit("pull-sample")
        self.zone.new_sample_external_channel(self.chno, sample)
        return Gst.FlowReturn.OK

    def start_pipeline(self):
        template = self.generate_pipeline_template()
        print(template)
        self.pipeline=Gst.parse_launch(template)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.pipeline.set_state(Gst.State.PLAYING)

        qs = [ "q0", "q1", "q2", "q3", "q4" ] 
        print(qs)
        qs = [ self.pipeline.get_by_name(qname) for qname in qs ]
        for q in qs:
            pipeline_utils.setup_queuee(q)  

        if self.source_type() == "NDI":
            self.appndisrc = self.pipeline.get_by_name("appndisrc")
            #self.appndisrc.set_property("sync", False)
            #self.appndisrc.set_property("emit-signals", True)
            #self.appndisrc.set_property("max-buffers", 1)
            #self.appndisrc.set_property("drop", True)
            #self.appndisrc.set_property("emit-signals", True)
            #self.appndisrc.connect("new-sample", self.appndi_new_sample, None)

    def appndi_new_sample(self, a, b):
        sample = self.appndisrc.emit("pull-sample")
        el = self.pipeline.get_by_name("appndiretrans")
        buf = sample.get_buffer()
        buf.pts = Gst.CLOCK_TIME_NONE 
        buf.dts = Gst.CLOCK_TIME_NONE 
        buf.duration = Gst.CLOCK_TIME_NONE
        el.emit("push-sample", sample)
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