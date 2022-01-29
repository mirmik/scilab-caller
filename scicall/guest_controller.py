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

class Server(QTcpServer):
    def __init__(self):
        super().__init__()

    def writeData(self, socket, data):
        socket.writeData(data)

    def incomingConnection(self, socket):
        self.sock = QTcpSocket()
        print(socket)
        self.sock.setSocketDescriptor(socket)
        
class ConnectionController(QWidget):
    write_socket_data = pyqtSignal(QTcpSocket, bytes)

    def __init__(self, number, zone):
        super().__init__()
        self.zone = zone
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
        self.server = Server()
        self.write_socket_data.connect(self.server.writeData, Qt.QueuedConnection)
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

        self.common_pipeline=None
        self.feedback_pipeline=None
        self.sample_controller=None

    def make_checkboxes_for_sound_feedback(self):
        for i in range(3):
            wdg = QCheckBox("Ретранс. звука: " + str(i))
            if self.channelno != i: wdg.setChecked(True)
            self.control_layout.addWidget(wdg)
            self.audio_feedback_checkboxes.append(wdg)

    def sound_feedback_list(self):
        ret=[]
        for i in range(3):
            if self.audio_feedback_checkboxes[i].isChecked():
                ret.append(i)
        return ret

    def update_info(self):
        self.need_update = False
        self.infowdg.setText(f"""Контрольный порт: {self.control_port()}""")

    def control_port(self):
        return channel_control_port(self.channelno)

    def on_server_new_connect(self):
        print("STATION: on_server_connect")
        client = self.server.nextPendingConnection()
        client = self.server.sock

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
        
    def client_disconnected(self):
        print("STATION : guest_disconnected")
        self.clients.clear()
        self.stop_streams()

    def client_ready_read(self):
        client = self.clients[0]
        while client.bytesAvailable():
            rawdata = client.readLineData(1024).decode("utf-8")
            data = json.loads(rawdata)
            self.new_opposite_command(data)

    def new_opposite_command(self, data):
        print("GUEST >>", data)
        cmd = data["cmd"]
        
        if cmd == "hello_from_guest":
            self.send_to_opposite({"cmd": "start_common_stream"})
            self.start_common_stream()

            time.sleep(0.2)

            self.send_to_opposite({"cmd": "start_feedback_stream"})
            self.start_feedback_stream()
        else:
            print("unresolved command")        

    def send_to_opposite(self, dct):
        client = self.clients[0]
        client.writeData((json.dumps(dct) + "\n").encode("utf-8"))
        client.flush()

    def stop_control_server(self):
        for c in self.clients:
            c.close()
        self.server.close()

    def enable_disable_clicked(self):
        try:
            if self.runned:
                self.stop_streams()
                self.stop_control_server()
                self.enable_disable_button.setText("Включить")
                self.runned = False
            else:
                self.start_control_server()
                self.enable_disable_button.setText("Отключить")
                self.runned = True
            self.update_info()
        except Exception as ex:
            traceback.print_exc()
            msgBox = QMessageBox()
            msgBox.setText("Возникла непредвиденная ситуация:\r\n" +
                           traceback.format_exc())
            msgBox.exec()
        
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

    def get_gpu_type(self):
        return self.zone.get_gpu_type()

    def start_common_stream(self):
        videodecoder = pipeline_utils.video_decoder_type(self.get_gpu_type())
        srtport = channel_mpeg_stream_port(self.channelno)
        srtlatency = 80

        audiocaps = "audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1"
        udpspam = internal_channel_udpspam_port(self.channelno)
        self.common_pipeline = Gst.parse_launch(
            f"""srtsrc uri=srt://:{srtport} wait-for-connection=true latency={srtlatency} 
                    ! queue name=q0 ! h264parse ! {videodecoder} ! tee name=t1 

            srtsrc uri=srt://:{srtport+1} wait-for-connection=true latency={srtlatency} ! 
            queue name=q2 ! opusparse ! opusdec ! {audiocaps}
             ! audioconvert ! audioresample !  tee name=t2 
            
            t1. ! queue name=qt0 ! videoconvert ! autovideosink sync=false name=videoend
            t1. ! queue name=qt2 ! appsink name=appsink
        
            t2. ! queue name=qt1 !audioconvert ! spectrascope ! videoconvert ! 
                autovideosink sync=false name=audioend
            t2. ! queue name=qt3 !audioconvert ! {audiocaps} ! opusenc ! udpsink host=127.0.0.1 port={udpspam} sync=false
        """)
        qs = [ self.common_pipeline.get_by_name(qname) for qname in [
            "q0", "q2", "qt0", "qt1", "qt2", "qt3"
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

    def start_feedback_stream(self):
        srtport = channel_feedback_mpeg_stream_port(self.channelno)
        srtlatency = 80

        h264caps = "video/x-h264,profile=baseline,stream-format=byte-stream,alignment=au,framerate=30/1"
        videocoder = pipeline_utils.video_coder_type(self.get_gpu_type())
        audiocaps = "audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1"
        videocaps = pipeline_utils.global_videocaps()

        udpaudiomix = ""
        for i in self.sound_feedback_list():
            udpaudiomix = udpaudiomix + f"""udpsrc port={internal_channel_udpspam_port(i)} reuse=true ! opusparse ! 
                opusdec ! audioconvert ! audioresample ! {audiocaps} ! queue name=uq{i} ! amixer. \n"""

        pstr = f"""
            videotestsrc pattern=snow ! videoconvert ! videoscale ! {videocaps} ! queue name=q0 ! tee name=videotee ! queue name=q2 ! 
                autovideosink name=fbvideoend sync=false

            videotee. ! {videocoder} ! {h264caps}
                ! srtsink uri=srt://:{srtport} latency={srtlatency} sync=false

            audiomixer name=amixer ! tee name=audiotee ! queue name=q1 ! audioconvert ! audioresample ! 
                {audiocaps} ! opusenc
                    ! srtsink uri=srt://:{srtport+1} latency={srtlatency} sync=false                

            audiotee. ! queue name=q3 ! audioconvert ! audioresample ! spectrascope ! 
                videoconvert ! autovideosink name=fbaudioend sync=false

            {udpaudiomix}
        """
        print(pstr)

        self.feedback_pipeline = Gst.parse_launch(pstr)

        qs = [ "q0", "q1", "q2", "q3" ] + [f"uq{i}" for i in self.sound_feedback_list()]
        print(qs)
        qs = [ self.feedback_pipeline.get_by_name(qname) for qname in qs ]
        print(qs)
        for q in qs:
            q.set_property("max-size-bytes", 100000) 
            q.set_property("max-size-buffers", 0) 
                
        self.fbbus = self.feedback_pipeline.get_bus()
        self.fbbus.add_signal_watch()
        self.fbbus.enable_sync_message_emission()
        self.fbbus.connect('sync-message::element', self.on_sync_message)
        self.fbbus.connect('message::error', self.on_error_message)
        self.fbbus.connect("message::eos", self.eos_handle)
        self.feedback_pipeline.set_state(Gst.State.PLAYING)

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

    def stop_feedback_stream(self):
        if self.feedback_pipeline:
            self.feedback_pipeline.set_state(Gst.State.NULL)
        time.sleep(0.1)
        self.feedback_pipeline = None


    def on_sync_message(self, bus, msg):
        """Биндим контрольное изображение к переданному снаружи виджету."""
        #pass
        if msg.get_structure().get_name() == 'prepare-window-handle':
            name = msg.src.get_parent().get_parent().name
            if name=="videoend":
                self.display.connect_to_sink(msg.src)
            if name=="audioend":
                self.spectroscope.connect_to_sink(msg.src)
            if name=="fbvideoend":
                self.feedback_display.connect_to_sink(msg.src)
            if name=="fbaudioend":
                self.feedback_spectroscope.connect_to_sink(msg.src)

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

    def start_streams(self):
        self.start_common_stream()
        time.sleep(0.2)
        self.start_feedback_stream()
        time.sleep(0.2)

    def stop_streams(self):
        self.stop_common_stream()
        time.sleep(0.2)
        self.stop_feedback_stream()
        time.sleep(0.2)

class ConnectionControllerZone(QWidget):
    def __init__(self):
        super().__init__()
        self.zones = []
        self.vlayout = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.gpuchecker = pipeline_utils.GPUChecker()
        self.hlayout.addWidget(QLabel("Использовать аппаратное ускорение: "))
        self.hlayout.addWidget(self.gpuchecker)
        self.vlayout.addLayout(self.hlayout)
        #self.gpuchecker.set(pipeline_utils.GPUType.NVIDIA)
        
        for i in range(3):
            self.add_zone(i, self)

        self.setLayout(self.vlayout)

    def get_gpu_type(self):
        return self.gpuchecker.get()

    def add_zone(self, i, zone):
        wdg = ConnectionController(i, zone)
        self.zones.append(wdg)
        self.vlayout.addWidget(wdg)
