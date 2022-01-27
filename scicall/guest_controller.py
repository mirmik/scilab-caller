from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from gi.repository import GObject, Gst, GstVideo
import traceback
import time

from scicall.stream_pipeline import StreamPipeline
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
    channel_mpeg_stream_port)

from scicall.stream_settings import (
    StreamSettings,
    MiddleSettings,
    SourceMode,
    MediaType,
    TranslateMode,
    TransportType,
    VideoCodecType,
    AudioCodecType
)

class ConnectionController(QWidget):
    def __init__(self, number):
        super().__init__()
        self.flow_runned = False
        self.audio_feedback_checkboxes = []
        self.video_connected = False
        self.audio_connected = False
        self.runned = False
        self.channelno = number
        self.display = GstreamerDisplay()
        self.spectroscope = GstreamerDisplay()
        self.feedback_display = GstreamerDisplay()
        self.feedback_spectroscope = GstreamerDisplay() 
        self.layout = QHBoxLayout()
        self.clients = []
        self.server = QTcpServer()
        self.server.newConnection.connect(self.on_server_new_connect)
        self.listener = None

        self.infowdg = QTextEdit()
        self.enable_disable_button = QPushButton("Включить")
        
        self.info_layout = QVBoxLayout()
        self.info_layout.addWidget(self.infowdg)
        self.info_layout.addStretch()

        self.control_layout = QVBoxLayout()
        self.make_checkboxes_for_sound_feedback()
        self.control_layout.addWidget(self.enable_disable_button)

        self.layout.addWidget(self.spectroscope)
        self.layout.addWidget(self.display)
        self.layout.addWidget(self.feedback_spectroscope)
        self.layout.addWidget(self.feedback_display)
        self.layout.addLayout(self.info_layout)
        self.layout.addLayout(self.control_layout)

        #self.audio_pipeline = StreamPipeline(self.spectroscope)
        #self.video_pipeline = StreamPipeline(self.display)
        #self.feedback_audio_pipeline = StreamPipeline(self.feedback_spectroscope)
        #self.feedback_video_pipeline = StreamPipeline(self.feedback_display)

        self.display.setFixedSize(160,160)
        self.spectroscope.setFixedSize(160,160)
        self.feedback_display.setFixedSize(160,160)
        self.feedback_spectroscope.setFixedSize(160,160)

        self.enable_disable_button.clicked.connect(self.enable_disable_clicked)
        self.setLayout(self.layout)
        self.update_info()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_if_need)
        self.update_timer.start(100);

    def make_checkboxes_for_sound_feedback(self):
        for i in range(3):
            wdg = QCheckBox("Ретранс. звука: " + str(i))
            if self.channelno != i: wdg.setChecked(True)
            self.control_layout.addWidget(wdg)
            self.audio_feedback_checkboxes.append(wdg)

    def audio_feedbacks(self):
        idx=0
        indexes=[]
        for chb in self.audio_feedback_checkboxes:
            if chb.isChecked():
                indexes.append(idx)
            idx+=1
        return indexes

    def update_if_need(self):
        if self.need_update:
            self.update_info()

    def update_info(self):
        self.need_update = False
        self.infowdg.setText(f"""Контрольный порт: {self.control_port()}

Видео:
  порт: {self.video_port()}
  NDI-поток: {self.ndi_video_name()}
  состояние: (резерв){self.video_connected}

Аудио:
  порт: {self.audio_port()}
  NDI-поток: {self.ndi_audio_name()}
  состояние: (резерв){self.audio_connected}
  обратная петля: {self.pipeline_udpspam(MediaType.AUDIO)}
""")

    def control_port(self):
        return channel_control_port(self.channelno)

    def video_port(self):
        return channel_video_port(self.channelno)

    def audio_port(self):
        return channel_audio_port(self.channelno)

    def feedback_video_port(self):
        return channel_feedback_video_port(self.channelno)

    def feedback_audio_port(self):
        return channel_feedback_audio_port(self.channelno)

    def send_greetings(self):
        self.listener.send(json.dumps(
            {"cmd" : "hello"}
        ))

    def on_server_new_connect(self):
        print("Station: on_server_connect")
        client = self.server.nextPendingConnection()

        if len(self.clients) == 0:
            client.readyRead.connect(self.client_ready_read)
            client.disconnected.connect(self.client_disconnected)
            self.clients.append(client)
            self.send_to_opposite({"cmd": "hello_from_server"})
        else:
            client.close()

    def start_control_server(self):
        port = channel_control_port(self.channelno)
        self.server.listen(QHostAddress("0.0.0.0"), port)
        print("StartControlServer", port)

    def client_disconnected(self):
        print("STATION : guest_disconnected")
        self.clients.clear()
        self.stop_common_stream()

    def client_ready_read(self):
        print("client_ready_read")
        client = self.clients[0]
        rawdata = client.readLineData(1024).decode("utf-8")
        data = json.loads(rawdata)
        self.new_opposite_command(data)

    def new_opposite_command(self, data):
        print("GUEST >>", data)
        cmd = data["cmd"]
        
        if cmd == "hello_from_guest":
            self.send_to_opposite({"cmd": "start_common_stream"})
            self.start_common_stream()
        else:
            print("unresolved command")        

    def send_to_opposite(self, dct):
        client = self.clients[0]
        client.writeData(json.dumps(dct).encode("utf-8"))

    def stop_control_server(self):
        print("StopControlServer")
        for c in self.clients:
            c.close()
        self.server.close()

    def enable_disable_clicked(self):
        try:
            if self.runned:
                self.stop_control_server()
            #    self.stop_common_stream()
            #    self.stop_recv_pipeline()       
            #    self.stop_feedback_pipeline() 
                self.enable_disable_button.setText("Включить")
                self.runned = False
            else:
                self.start_control_server()
            #    self.setup_common_stream()
            #    self.start_common_stream()
            #    self.start_recv_pipeline()
            #    self.start_feedback_pipeline()
                self.enable_disable_button.setText("Отключить")
                self.runned = True
            self.update_info()
        except Exception as ex:
            traceback.print_exc()
            msgBox = QMessageBox()
            msgBox.setText("Возникла непредвиденная ситуация:\r\n" +
                           traceback.format_exc())
            msgBox.exec()
        
    def start_recv_pipeline(self):
        self.raw_video_pipeline = self.video_pipeline.make_pipeline(
            self.input_settings(self.video_pipeline),
            self.output_settings(self.video_pipeline),
            self.middle_settings(self.video_pipeline))
        self.raw_audio_pipeline = self.audio_pipeline.make_pipeline(
            self.input_settings(self.audio_pipeline),
            self.output_settings(self.audio_pipeline),
            self.middle_settings(self.audio_pipeline))
        for pipeline in [
            self.video_pipeline, 
            self.audio_pipeline
        ]:
            pipeline.setup()
            pipeline.start()
        

    def start_feedback_pipeline(self):
        print("start_feedback_pipeline")
        #self.feedback_raw_video_pipeline = self.feedback_video_pipeline.make_pipeline(
        #   self.feedback_input_settings(self.feedback_video_pipeline),
        #   self.feedback_output_settings(self.feedback_video_pipeline),
        #   self.feedback_middle_settings(self.feedback_video_pipeline))
        a=self.feedback_input_settings(MediaType.AUDIO)
        b=self.feedback_output_settings(MediaType.AUDIO)
        c=self.feedback_middle_settings(MediaType.AUDIO)        
        self.feedback_raw_audio_pipeline = self.feedback_audio_pipeline.make_pipeline(a,b,c)
        for pipeline in [
        #   self.feedback_video_pipeline, 
            self.feedback_audio_pipeline
        ]:
            pipeline.setup()
            pipeline.start()

    def stop_recv_pipeline(self):
        print("stop_recv_pipeline")
        for pipeline in [self.video_pipeline, self.audio_pipeline]:
            pipeline.stop()

    def stop_feedback_pipeline(self):
        print("stop_feedback_pipeline")
        for pipeline in [
            #self.feedback_video_pipeline, 
            self.feedback_audio_pipeline
        ]:
            pipeline.stop()

    def on_srt_video_caller_removed(self, srtsrc, a, pipeline):
        print("ON_SRT_VIDEO_REMOVE")
        self.video_connected = False
        self.need_update = True
        #self.raw_video_pipeline.set_state(Gst.State.PAUSED)
        #self.raw_video_pipeline.set_state(Gst.State.READY)
        #self.raw_video_pipeline.set_state(Gst.State.PAUSED)
        #self.raw_video_pipeline.set_state(Gst.State.PLAYING)
        
    def on_srt_audio_caller_removed(self, srtsrc, a, pipeline):
        print("ON_SRT_AUDIO_REMOVE")
        self.audio_connected = False
        self.need_update = True
        #self.raw_audio_pipeline.set_state(Gst.State.PAUSED)
        #self.raw_audio_pipeline.set_state(Gst.State.READY)
        #self.raw_audio_pipeline.set_state(Gst.State.PAUSED)
        #self.raw_audio_pipeline.set_state(Gst.State.PLAYING)
    
    def on_srt_video_caller_added(self, srtsrc, a, pipeline):
        print("ON_SRT_VIDEO_ADDED")
        self.video_connected = True
        self.need_update = True
    
    def on_srt_audio_caller_added(self, srtsrc, a, pipeline):
        print("ON_SRT_AUDIO_ADDED")
        self.audio_connected = True
        self.need_update = True
        
    def input_settings(self, pipeline):
        return StreamSettings(
            mediatype = self.pipeline_mediatype(pipeline),
            mode = SourceMode.STREAM,
            transport = TransportType.SRT,
            codec = self.pipeline_codec(pipeline),
            port = self.pipeline_port(pipeline),
            #on_srt_caller_removed = self.on_srt_video_caller_removed if pipeline is self.video_pipeline else self.on_srt_audio_caller_removed,
            #on_srt_caller_added = self.on_srt_video_caller_added if pipeline is self.video_pipeline else self.on_srt_audio_caller_added,
        )

    def output_settings(self, pipeline):
        return StreamSettings(
            mediatype = self.pipeline_mediatype(pipeline),
            mode = TranslateMode.STREAM,
            transport = TransportType.NDI,
            codec = VideoCodecType.NOCODEC,
            ndi_name = self.ndi_name(pipeline),
            udpspam = self.pipeline_udpspam(self.pipeline_mediatype(pipeline))
        )       

    def middle_settings(self, pipeline):
        return MiddleSettings(
            display_enabled = True,
            width=160,
            height=160,
        )

    def feedback_input_settings(self, mediatype):
        input_array=[]
        #sett = StreamSettings(
        #   mediatype = mediatype,
        #   mode = SourceMode.STREAM,
        #   transport = TransportType.NDI,
        #   codec = VideoCodecType.NOCODEC,
        #   ndi_name = self.ndi_name_feedback(mediatype)
        #)
        #input_array.append(sett)
        for i in self.audio_feedbacks():
            print(internal_channel_udpspam_port(i))
            sett = StreamSettings(
                mediatype = mediatype,
                mode = SourceMode.STREAM,
                transport = TransportType.UDP,
                codec = self.pipeline_codec(mediatype),
                port = internal_channel_udpspam_port(i),
            )
            input_array.append(sett)  
        return input_array

    def feedback_output_settings(self, mediatype):
        sett = StreamSettings(
            mediatype = mediatype,
            mode = TranslateMode.STREAM,
            transport = TransportType.SRT,
            codec = self.pipeline_codec(mediatype),
            port = self.feedback_pipeline_port(mediatype)
        )      
        return sett 

    def feedback_middle_settings(self, mediatype):
        return MiddleSettings(
            display_enabled = True,
            width=160,
            height=160,
        )

    def pipeline_codec(self, pipeline_mediatype):
        if pipeline_mediatype is MediaType.VIDEO:
            return VideoCodecType.H264
        if pipeline_mediatype is MediaType.AUDIO:
            return AudioCodecType.OPUS
        if pipeline_mediatype is self.video_pipeline:
            return VideoCodecType.H264
        else:
            return AudioCodecType.OPUS

    def pipeline_port(self, pipeline):
        if pipeline is self.video_pipeline:
            return self.video_port()
        else:
            return self.audio_port()

    def feedback_pipeline_port(self, mediatype):
        if mediatype is MediaType.VIDEO:
            return self.feedback_video_port()
        else:
            return self.feedback_audio_port()

    def pipeline_mediatype(self, pipeline):
        if pipeline is self.video_pipeline:
            return MediaType.VIDEO
        else:
            return MediaType.AUDIO

    def ndi_name(self, pipeline):
        if pipeline is self.video_pipeline:
            return self.ndi_video_name()
        else:
            return self.ndi_audio_name()

    def ndi_name_feedback(self, mediatype):
        if pipeline is self.video_pipeline:
            return self.ndi_video_name_feedback()
        else:
            return self.ndi_audio_name_feedback()

    def ndi_video_name(self):
        return f"Guest{self.channelno+1}-Video0"

    def ndi_audio_name(self):
        return f"Guest{self.channelno+1}-Audio0"

    def ndi_video_name_feedback(self):
        return f"Guest{self.channelno+1}-Video0-Feedback"

    def ndi_audio_name_feedback(self):
        return f"Guest{self.channelno+1}-Audio0-Feedback"

    def pipeline_udpspam(self, mediatype):
        if mediatype == MediaType.VIDEO:
            return False
        else:
            return internal_channel_udpspam_port(self.channelno)

    def start_common_stream(self):
        srtport = channel_mpeg_stream_port(self.channelno)
        srtlatency = 80
        self.common_pipeline = Gst.parse_launch(
            f"""srtsrc uri=srt://:{srtport} wait-for-connection=true latency={srtlatency} 
                ! queue name=q0 ! tsparse ! tsdemux name=t 
                ! queue name=q1 ! h264parse ! avdec_h264 ! tee name=t1 ! queue name=qt0 ! videoconvert ! autovideosink sync=false name=videoend
             t. ! queue name=q2 ! opusparse ! opusdec ! tee name=t2 ! queue name=qt1 !audioconvert ! spectrascope ! videoconvert ! autovideosink sync=false name=audioend
             t1. ! queue name=qt2 ! appsink name=appsink
        """)
        qs = [ self.common_pipeline.get_by_name(qname) for qname in [
            "q0", "q1", "q2", "qt0", "qt1", "qt2"
        ]]
        for q in qs:
            q.set_property("max-size-bytes", 100000) 
            q.set_property("max-size-buffers", 0) 

        appsink = self.common_pipeline.get_by_name("appsink")
        appsink.set_property("sync", False)
        appsink.set_property("emit-signals", True)
        appsink.set_property("max-buffers", 1)
        appsink.set_property("drop", True)
        appsink.set_property("emit-signals", True)
        appsink.connect("new-sample", self.new_sample, None)

        self.last_sample = time.time()
        self.flow_runned = False
        self.sample_controller = QTimer()
        self.sample_controller.timeout.connect(self.sample_flow_control)
        self.sample_controller.setInterval(100)
        self.sample_controller.start()

        self.bus = self.common_pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.bus.connect('message::error', self.on_error_message)
        self.bus.connect("message::eos", self.eos_handle)
        self.common_pipeline.set_state(Gst.State.PLAYING)

    def new_sample(self, a, b):
        self.last_sample = time.time()
        return Gst.FlowReturn.OK

    def sample_flow_control(self):
        if self.flow_runned is False and time.time() - self.last_sample < 0.3:
            print("Connect?")
            self.flow_runned = True
            self.last_sample = time.time()
            return

        if self.flow_runned is True and time.time() - self.last_sample > 0.3:
            self.flow_runned = False
            print("Disconnect?")
            self.common_pipeline.set_state(Gst.State.PAUSED)
            self.common_pipeline.set_state(Gst.State.READY)
            self.common_pipeline.set_state(Gst.State.PAUSED)
            self.common_pipeline.set_state(Gst.State.PLAYING)
            return
        
    def stop_common_stream(self):
        if self.common_pipeline:
            self.common_pipeline.set_state(Gst.State.NULL)
        time.sleep(0.1)
        self.common_pipeline = None

        if self.sample_controller:
            self.sample_controller.stop()
            self.sample_controller = None

    def on_sync_message(self, bus, msg):
        """Биндим контрольное изображение к переданному снаружи виджету."""
        #pass
        if msg.get_structure().get_name() == 'prepare-window-handle':
            name = msg.src.get_parent().get_parent().name
            if name=="videoend":
                self.display.connect_to_sink(msg.src)
            if name=="audioend":
                self.spectroscope.connect_to_sink(msg.src)

    def eos_handle(self, bus, msg):
        """Конец потока вызывает пересборку конвеера.
           Это решает некоторые проблемы srt стрима.
        """
        print("eos handle")
        self.common_pipeline.set_state(Gst.State.PAUSED)
        self.common_pipeline.set_state(Gst.State.READY)
        self.common_pipeline.set_state(Gst.State.PAUSED)
        self.common_pipeline.set_state(Gst.State.PLAYING)

    def on_error_message(self, bus, msg):
        print("on_error_message", msg.parse_error())

class ConnectionControllerZone(QWidget):
    def __init__(self):
        super().__init__()
        self.zones = []
        self.vlayout = QVBoxLayout()

        for i in range(3):
            self.add_zone(i)

        self.setLayout(self.vlayout)

    def add_zone(self, i):
        wdg = ConnectionController(i)
        self.zones.append(wdg)
        self.vlayout.addWidget(wdg)
