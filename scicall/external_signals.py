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

from scicall.ports import (
    channel_control_port, 
    channel_video_port,
    channel_audio_port, 
    channel_feedback_video_port,
    channel_feedback_audio_port,
    internal_channel_audio_udpspam_port,
    channel_mpeg_stream_port,
    channel_feedback_mpeg_stream_port
)


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

    def global_audio_external_template(self):
        srctype = self.source_type()
        audiocaps = pipeline_utils.global_audiocaps()
        audio_source = "audiotestsrc"
        audioparser = pipeline_utils.default_audioparser()
        audiodecoder = pipeline_utils.default_audiodecoder()
        audioencoder = pipeline_utils.default_audioencoder()
        #audio_encoder = "x264enc tune=zerolatency"

        if srctype == "Нет":
            return None
        elif srctype == "Тестовый1":
            audio_source = "audiotestsrc is-live=true"
        elif srctype == "Тестовый2":
            audio_source = "audiotestsrc is-live=true"
        elif srctype == "NDI":
            audio_source = f"""ndiaudiosrc do-timestamp=true timeout=0 ndi-name=\"{self.input_ndi_name()}\" ! audioresample ! audioconvert ! queue name=qa5"""                        

        template = f""" 
            {audio_source} ! audioconvert ! queue name=qa0 ! tee name=audiotee 
            audiotee. ! queue name=qa1 ! audioconvert ! spectrascope ! 
                videoconvert ! autovideosink name=audioend
            audiotee. ! queue name=qa2 ! {audioencoder} ! udpsink host=127.0.0.1 port=20190
        """ 

        """
        """
        return template

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
                video_source = "videotestsrc is-live=true"
            elif srctype == "Тестовый2":
                video_source = "videotestsrc pattern=snow is-live=true"
            elif srctype == "NDI":
                video_source = f"""ndivideosrc do-timestamp=true timeout=0 ndi-name=\"{self.input_ndi_name()}\" ! queue name=q5"""                        

            srtsouts = ""
            for p in ports:
                srtsouts += f" h264tee. ! queue ! srtsink latency=60 uri=srt://:{p} wait-for-connection=false sync=false \n"
            external_source_substring = self.global_audio_external_template()
            #external_source_substring = ""
            template = f""" 
                {video_source} ! videoconvert ! {videocaps} ! queue name=q0 ! tee name=sourcetee
                sourcetee. ! queue name=q1 ! videoconvert ! autovideosink name=videoend
                sourcetee. ! queue name=q2 ! {video_encoder} ! {h264caps} ! tee name=h264tee
                {srtsouts}
                {external_source_substring}
            """ 
            print("template:", template)   

            self.pipeline=Gst.parse_launch(template)
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.enable_sync_message_emission()
            self.bus.connect('sync-message::element', self.on_sync_message)
            
            if self.source_type() != "Нет":
                self.pipeline.set_state(Gst.State.PLAYING)
    
            qs = [ "q0", "q1", "q2", "q3", "q4", "q5", "qa0", "qa1", "qa2", "qa5" ] 
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
        self.start_global_audio_feedback_pipeline(zone.get_audioends())
        self.zone = zone

    def add_panel(self, i, zone):
        panel = ExternalSignalPanel(i, zone)
        self.panels.append(panel)
        self.lay.addWidget(panel)

    def stop_streams(self):
        with self.mtx:
            for z in self.panels:
                z.stop_pipeline()
            #self.stop_global_audio_feedback_pipeline()

    #def start_streams(self):
    #    with self.mtx:
    #        for z in self.panels:
    #            z.start_pipeline()

    def stop_global_audio_feedback_pipeline(self):
        self.audio_pipeline.set_state(Gst.State.PAUSED)
        self.audio_pipeline.set_state(Gst.State.READY)
        self.audio_pipeline.set_state(Gst.State.NULL)
        self.bus = None
        self.audio_pipeline = None

    def start_global_streams(self, ports):
        with self.mtx:
            for z in self.panels:
                z.start_global_video_feedback_pipeline(ports)
            #self.start_global_audio_feedback_pipeline(self.zone.get_audioends())

    def channels_count(self):
        return 3

    def set_volume(self, f, t, val):
        name = f"v_{f}{t}"
        print(name, val)
        self.audio_pipeline.get_by_name(name).set_property("volume", val)

    def start_global_audio_feedback_pipeline(self, audioends):
        self.audioends = audioends
        audioparser = pipeline_utils.default_audioparser()
        audiodecoder = pipeline_utils.default_audiodecoder()
        audioencoder = pipeline_utils.default_audioencoder()
        
        N=self.channels_count()
        udpspam_ports = [ internal_channel_audio_udpspam_port(i) for i in range(N) ]
        srtports = [ channel_feedback_audio_port(i) for i in range(N) ]
        
        template_a = ""
        for i in range(N):
            template_a += f"""
              udpsrc port={udpspam_ports[i]} ! {audioparser} ! {audiodecoder} ! audioconvert ! tee name=in{i}
              liveadder latency=0 name=mix{i} ! queue name=before_t{i} ! tee name=t{i} ! queue name=after0_t{i} ! {audioencoder} ! srtsink uri=srt://:{srtports[i]} wait-for-connection=false
              t{i}. ! queue name=after1_t{i} ! audioconvert ! spectrascope ! videoconvert ! autovideosink name=audiofeed{i}
            """

        external_source_substring = f"""
            udpsrc port=20190 ! {audioparser} ! {audiodecoder} ! audioconvert ! tee name=externaltee
        """

        outpart = f"""
            in0.         ! volume volume=0 name=v_00 ! queue name=q00 ! mix0. 
            in1.         ! volume volume=0 name=v_10 ! queue name=q10 ! mix0. 
            in2.         ! volume volume=0 name=v_20 ! queue name=q20 ! mix0. 
            externaltee. ! volume volume=0 name=v_e0 ! queue name=qe0 ! mix0.

            in0.         ! volume volume=0 name=v_01 ! queue name=q01 ! mix1. 
            in1.         ! volume volume=0 name=v_11 ! queue name=q11 ! mix1. 
            in2.         ! volume volume=0 name=v_21 ! queue name=q21 ! mix1.
            externaltee. ! volume volume=0 name=v_e1 ! queue name=qe1 ! mix1.

            in0.         ! volume volume=0 name=v_02 ! queue name=q02 ! mix2. 
            in1.         ! volume volume=0 name=v_12 ! queue name=q12 ! mix2. 
            in2.         ! volume volume=0 name=v_22 ! queue name=q22 ! mix2.
            externaltee. ! volume volume=0 name=v_e2 ! queue name=qe2 ! mix2.
        """

        #outpart = ""

        # TODO переписать для случая N каналов.
        template = f"""
            {template_a}
            {external_source_substring}

            {outpart}
        """

        print(template)

        self.audio_pipeline = Gst.parse_launch(template)
        self.bus = self.audio_pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.audio_pipeline.set_state(Gst.State.PLAYING)

        qs = [ qname for qname in [
            "q0", "q1",
        ] + 
        [f"before_t{i}" for i in range(N)] +
        [f"after0_t{i}" for i in range(N)] +
        [f"after1_t{i}" for i in range(N)]
        ]

        for i in range(N):
            for j in range(N):
                qs += [f"q{i}{j}"]

        for j in range(N):
            qs += [f"qe{j}"]

        #print(qs)
        #for q in qs:
        #    pipeline_utils.setup_queuee(self.audio_pipeline.get_by_name(q))  

    def on_sync_message(self, bus, msg):
        print("ON_sync_message")
        if msg.get_structure().get_name() == 'prepare-window-handle':
            name = msg.src.get_parent().get_parent().name
            for i in range(self.channels_count()):
                if name == f"audiofeed{i}":
                    self.audioends[i].connect_to_sink(msg.src)