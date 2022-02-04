from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from gi.repository import GObject, Gst, GstVideo
import traceback
import time

from scicall.display_widget import GstreamerDisplay
import scicall.pipeline_utils as pipeline_utils
import scicall.util as util
import json
import threading

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
        self.mtx = threading.RLock()
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

        self.ndi_updater = QTimer()
        self.ndi_updater.timeout.connect(self.ndi_name_list_update)
        self.ndi_updater.start(1000)
        self.known_ndi_sources = set()

    def make_control_panel(self):
        self.source_types = ["Тестовый1", "Тестовый2", "NDI"]
        self.source_types_cb = QComboBox()
        self.source_types_cb.addItems(self.source_types)
        self.ndi_name_list = QComboBox()
        self.control_layout = QGridLayout()
        self.control_layout.addWidget(QLabel(f"Внешний источник: {self.chno}"), 0, 0, 1, 2)
        self.control_layout.addWidget(QLabel("Тип источника:"), 1, 0)
        self.control_layout.addWidget(self.source_types_cb, 1, 1)
        self.control_layout.addWidget(QLabel("Имя (для ndi):"), 2, 0)
        self.control_layout.addWidget(self.ndi_name_list, 2, 1)
        self.hlayout.addLayout(self.control_layout)
        self.source_types_cb.currentIndexChanged.connect(self.source_types_cb_handle)

    def ndi_name_list_update(self):
        check_result = set(util.ndi_device_list_names())
        new_ndi_names = check_result.difference(self.known_ndi_sources)

        for n in new_ndi_names:
            self.known_ndi_sources.add(n)
            self.ndi_name_list.addItem(n)

    def ndi_name_text_handle(self):
        self.update_control()

    def source_types_cb_handle(self, str):
        self.update_control()

    def update_control(self):
        self.zone.start_restart_feedback_streams()

    def source_type(self):
        with self.mtx:
            return self.source_types_cb.currentText()

    def stop_pipeline(self):
        print("Q")
        with self.mtx:
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None

    def input_ndi_name(self):
        return self.ndi_name_list.currentText()

    def start_global_video_feedback_pipeline(self, ports):
        with self.mtx:            
            srctype = self.source_type()
            videocaps = pipeline_utils.global_videocaps()
            h264caps = "video/x-h264,profile=baseline,stream-format=byte-stream,alignment=au,framerate=30/1"
            video_source = "videotestsrc"
            video_encoder = "x264enc tune=zerolatency"

            if srctype == "Нет":
                return None
            elif srctype == "Тестовый1":
                video_source = "videotestsrc"
            elif srctype == "Тестовый2":
                video_source = "videotestsrc pattern=snow"
            elif srctype == "NDI":
                video_source = f"""ndivideosrc ndi-name=\"{self.input_ndi_name()}\" ! queue name=q5"""                        

            srtsouts = ""
            for p in ports:
                srtsouts += f" h264tee. ! queue ! srtsink latency=60 uri=srt://:{p} wait-for-connection=false sync=false \n"

            template = f""" 
                {video_source} ! videoconvert ! {videocaps} ! queue name=q0 ! tee name=sourcetee
                sourcetee. ! queue name=q1 ! videoconvert ! autovideosink name=videoend
                sourcetee. ! queue name=q2 ! {video_encoder} ! {h264caps} ! tee name=h264tee
                {srtsouts}
            """ 
            print("template:", template)   

            self.pipeline=Gst.parse_launch(template)
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.enable_sync_message_emission()
            self.bus.connect('sync-message::element', self.on_sync_message)
            
            if self.source_type() != "Нет":
                self.pipeline.set_state(Gst.State.PLAYING)
    
            qs = [ "q0", "q1", "q2", "q3", "q4", "q5" ] 
            qs = [ self.pipeline.get_by_name(qname) for qname in qs ]
            for q in qs:
                pipeline_utils.setup_queuee(q)  

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            name = msg.src.get_parent().get_parent().name
            if name=="videoend":
                self.viddisp.connect_to_sink(msg.src)
            if name=="audioend":
                self.auddisp.connect_to_sink(msg.src)

    def showEvent(self, ev):
        if self.inited == False:
            self.inited = True
            self.source_types_cb.setCurrentIndex(0)
            self.start_global_video_feedback_pipeline([])

class ExternalSignalsZone(QWidget):
    def __init__(self, zone):
        self.mtx = threading.RLock()
        super().__init__()
        self.panels = []
        self.lay = QHBoxLayout()
        for i in range(1):
            self.add_panel(i, zone)
        self.setLayout(self.lay)

        self.start_global_audio_feedback_pipeline()

    def add_panel(self, i, zone):
        panel = ExternalSignalPanel(i, zone)
        self.panels.append(panel)
        self.lay.addWidget(panel)

    def stop_streams(self):
        print("W")
        with self.mtx:
            for z in self.panels:
                z.stop_pipeline()

    def start_streams(self):
        with self.mtx:
            for z in self.panels:
                z.start_pipeline()


    def start_global_streams(self, ports):
        with self.mtx:
            for z in self.panels:
                z.start_global_video_feedback_pipeline(ports)

    def start_global_audio_feedback_pipeline(self):
        audioparser = pipeline_utils.default_audioparser()
        audiodecoder = pipeline_utils.default_audiodecoder()
        audioencoder = pipeline_utils.default_audioencoder()
        
        template = f"""
            udpsrc port=20105 ! {audioparser} ! {audiodecoder} ! audioconvert ! tee name=in1
            udpsrc port=20125 ! {audioparser} ! {audiodecoder} ! audioconvert ! tee name=in2
            udpsrc port=20145 ! {audioparser} ! {audiodecoder} ! audioconvert ! tee name=in3
        
            liveadder latency=0 name=mix1 ! {audioencoder} ! srtsink uri=srt://:20109 wait-for-connection=false
            liveadder latency=0 name=mix2 ! {audioencoder} ! srtsink uri=srt://:20129 wait-for-connection=false
            liveadder latency=0 name=mix3 ! {audioencoder} ! srtsink uri=srt://:20149 wait-for-connection=false
        
            in2. ! queue name=q21 ! mix1. 
            in3. ! queue name=q31 ! mix1.

            in1. ! queue name=q12 ! mix2. 
            in3. ! queue name=q32 ! mix2.

            in1. ! queue name=q13 ! mix3. 
            in2. ! queue name=q23 ! mix3.
        """

        self.audio_pipeline = Gst.parse_launch(template)
        self.audio_pipeline.set_state(Gst.State.PLAYING)

        qs = [ self.audio_pipeline.get_by_name(qname) for qname in [
            "q21", "q31", "qt12", "qt32", "q13", "q23"
        ]]
        #for q in qs:
        #    pipeline_utils.setup_queuee(q)
