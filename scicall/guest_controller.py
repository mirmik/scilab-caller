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

from scicall.external_signals import ExternalSignalPanel
from scicall.external_signals import ExternalSignalsZone

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
        self.mtx = threading.RLock()
        self.fb2=None
        self.extvid = None
        self.audio_appsrcs = []
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

        self.cb_get_vmix_srt = QCheckBox("Забирать ndi(видео)")
        self.cb_ndi_output = QCheckBox("Писать ndi поток(видео+звук)")
        self.cb_ndi_output.setChecked(True)

        self.common_channel_cb = QCheckBox("Прямой канал:")
        self.feedback_channel_cb = QCheckBox("Обратный канал:")
        self.srtlatency_edit = QLineEdit("125")
        self.common_channel_cb.setChecked(True)
        self.feedback_channel_cb.setChecked(True)

        self.infowdg = QTextEdit()
        self.enable_disable_button = QPushButton("Включить канал")
        self.restart_button = QPushButton("Перезапустить удалённо")
        
        self.info_layout = QVBoxLayout()
        self.info_layout.addWidget(self.infowdg)
        self.info_layout.addStretch()

        self.port_srt_vmix_edit = QLineEdit(str("ndiinputname"))

        self.control_layout = QVBoxLayout()
        self.control_layout2 = QVBoxLayout()
        self.control_layout2.addWidget(self.enable_disable_button)
        self.control_layout2.addWidget(self.restart_button)
        #self.control_layout2.addWidget(self.common_channel_cb)   
        #self.control_layout2.addWidget(self.feedback_channel_cb)
        self.make_checkboxes_for_sound_feedback()          
        self.control_layout.addWidget(QLabel("srt latency:"))   
        self.control_layout.addWidget(self.srtlatency_edit)
        self.control_layout.addStretch()

        self.control_layout2.addWidget(QLabel("Input NDI name:"))      
        self.control_layout2.addWidget(self.port_srt_vmix_edit)
        self.control_layout2.addWidget(self.cb_get_vmix_srt)

        self.control_layout2.addWidget(self.cb_ndi_output)

        self.control_layout2.addStretch()

        self.layout.addWidget(self.spectroscope)
        self.layout.addWidget(self.display)
        self.layout.addWidget(self.feedback_spectroscope)
        self.layout.addWidget(self.feedback_display)
        self.layout.addLayout(self.info_layout)
        self.layout.addLayout(self.control_layout)
        self.layout.addLayout(self.control_layout2)

        #self.audio_pipeline = StreamPipeline(self.spectroscope)
        #self.video_pipeline = StreamPipeline(self.display)
        #self.feedback_audio_pipeline = StreamPipeline(self.feedback_spectroscope)
        #self.feedback_video_pipeline = StreamPipeline(self.feedback_display)

        self.display.setFixedSize(160,160)
        self.spectroscope.setFixedSize(160,160)
        self.feedback_display.setFixedSize(160,160)
        self.feedback_spectroscope.setFixedSize(160,160)

        self.enable_disable_button.clicked.connect(self.enable_disable_clicked)
        self.restart_button.clicked.connect(self.restart_button_handle)
        self.setLayout(self.layout)
        self.update_info()

        self.common_pipeline=None
        self.feedback_pipeline=None
        self.sample_controller=None
        self.feedback_pipeline_started = False



    def input_ndi_name(self):
        return self.port_srt_vmix_edit.text()

    def get_srt_latency(self):
        return int(self.srtlatency_edit.text())

    def make_checkboxes_for_sound_feedback(self):
        for i in range(3):
            wdg = QCheckBox("Ретранс. звука: " + str(i+1))
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
        self.infowdg.setText(f"""
Контрольный порт: {self.control_port()}
Имя ndi потока: {self.ndi_name()}
srt порты взаимодействия с клиентом:
вход видео: {channel_mpeg_stream_port(self.channelno)}
вход аудио:{channel_mpeg_stream_port(self.channelno)+1}
выход видео:{channel_feedback_mpeg_stream_port(self.channelno)}
выход аудио:{channel_feedback_mpeg_stream_port(self.channelno)+1}
""")

    def control_port(self):
        return channel_control_port(self.channelno)

    def on_server_new_connect(self):
        print("STATION: on_server_connect", self.channelno, self.clients)
        client = self.server.nextPendingConnection()
        client = self.server.sock

        if len(self.clients) == 0:
            client.readyRead.connect(self.client_ready_read)
            client.disconnected.connect(self.client_disconnected)
            self.clients.append(client)
            self.send_to_opposite({"cmd": "hello_from_server"})
            self.create_keepaliver()
        else:
            dct = {"cmd": "client_collision"}
            client.writeData((json.dumps(dct) + "\n").encode("utf-8"))
            client.close()

    def create_keepaliver(self):
        print("create_keepaliver")
        self.keepaliver = QTimer(self)
        self.keepaliver.timeout.connect(self.keepalive_handler)
        self.keepaliver.setInterval(1500)
        self.keepaliver.start()

    def keepalive_handler(self):
        self.send_to_opposite({"cmd": "keepalive", "ch": self.channelno+1})

    def restart_button_handle(self):
        self.send_to_opposite({"cmd": "remote_restart"})

    def start_control_server(self):
        port = channel_control_port(self.channelno)
        self.server.listen(QHostAddress("0.0.0.0"), port)
        
    def client_disconnected(self):
        print("STATION : guest_disconnected")
        self.clients.clear()
        self.stop_streams()
        self.keepaliver.stop()
        self.keepaliver = None

    def client_ready_read(self):
        client = self.clients[0]
        while client.bytesAvailable():
            rawdata = client.readLineData(1024).decode("utf-8")
            data = json.loads(rawdata)
            self.new_opposite_command(data)

    def new_opposite_command(self, data):
        #print("GUEST >>", data)
        cmd = data["cmd"]
        
        if cmd == "keepalive":
            pass

        elif cmd == "hello_from_guest":
            self.send_to_opposite({"cmd": "set_srtlatency", "data": self.get_srt_latency()})
            time.sleep(0.2)

            if self.common_channel_cb.isChecked():
                self.start_common_stream()
                self.send_to_opposite({"cmd": "start_common_stream"})

            time.sleep(0.2)

            if self.feedback_channel_cb.isChecked():
                self.send_to_opposite({"cmd": "start_feedback_stream"})
                #self.start_feedback_stream()
                self.zone.start_restart_feedback_streams()
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
                self.enable_disable_button.setText("Включить канал")
                self.runned = False
            else:
                self.start_control_server()
                self.enable_disable_button.setText("Отключить канал")
                self.runned = True
            self.update_info()
        except Exception as ex:
            traceback.print_exc()
            msgBox = QMessageBox()
            msgBox.setText("Возникла непредвиденная ситуация:\r\n" +
                           traceback.format_exc())
            msgBox.exec()
        
    def ndi_name(self):
        return f"Guest{self.channelno+1}-AudioVideo"

    def get_gpu_type(self):
        return self.zone.get_gpu_type()

    #def soundmixout_new_preroll(self, arg0, arg1):
    #    sample = self.soundmixout.emit("pull-preroll")
    #    if self.soundmixin and  self.feedback_pipeline:
    #        print("PREROLL", sample)
    #        ret = self.soundmixin.emit ("push-buffer", sample)
    #    return Gst.FlowReturn.OK

    def soundmixout_new_buffer(self, arg0, arg1):
        sample = self.soundmixout.emit("pull-sample")
        #for appsrc in audio_appsrcs:
        #    appsrc.emit("push-sample", sample)
        self.zone.push_sample(sample, self.channelno)
        return Gst.FlowReturn.OK

    def push_sample(self, sample, no):
        if self.feedback_pipeline_started and no in self.sound_feedback_list():
            el = self.feedback_pipeline.get_by_name(f"soundmixin{no}")
            #print(dir(sample))
            #print(sample)
            #print(sample.get_info())
            #print(sample.get_buffer())
            #print(dir(sample.get_buffer()))
            #print(sample.get_buffer().get_reference_timestamp_meta())
            buf = sample.get_buffer()
            buf.pts = Gst.CLOCK_TIME_NONE 
            buf.dts = Gst.CLOCK_TIME_NONE 
            buf.duration = Gst.CLOCK_TIME_NONE
            el.emit("push-sample", sample)

    def start_common_stream(self):
        videodecoder = pipeline_utils.video_decoder_type(self.get_gpu_type())
        videocoder = pipeline_utils.video_coder_type(self.get_gpu_type())
        srtport = channel_mpeg_stream_port(self.channelno)
        srtlatency = self.get_srt_latency()

        audiocaps = pipeline_utils.audiocaps()
        udpspam = internal_channel_udpspam_port(self.channelno)

        ndisink = f"ndisink ndi-name={self.ndi_name()}"
        if not self.cb_ndi_output.isChecked():
            ndisink = "fakesink"

        self.common_pipeline = Gst.parse_launch(
            f"""srtsrc uri=srt://:{srtport} wait-for-connection=true latency={srtlatency} 
                    ! queue name=q0 ! h264parse ! {videodecoder} ! tee name=t1 

            srtsrc uri=srt://:{srtport+1} wait-for-connection=true latency={srtlatency} ! 
            queue name=q2 ! opusparse ! opusdec ! {audiocaps}
             ! audioconvert ! audioresample !  tee name=t2 
            
            t1. ! queue name=qt0 ! videoconvert ! autovideosink sync=false name=videoend
            t2. ! queue name=qt1 !audioconvert ! spectrascope ! videoconvert ! 
                autovideosink sync=false name=audioend
            t2. ! queue name=qt3 !audioconvert ! {audiocaps} ! opusenc ! appsink emit-signals=True name=soundmixout
        
            t1. ! queue ! videoconvert ! combiner.
            t2. ! queue ! audioconvert ! audioresample ! combiner.
            ndisinkcombiner name=combiner ! {ndisink} 
        """)
        qs = [ self.common_pipeline.get_by_name(qname) for qname in [
            "q0", "q2", "qt0", "qt1", "qt2", "qt3"
        ]]
        for q in qs:
            pipeline_utils.setup_queuee(q)

#        appsink = self.common_pipeline.get_by_name("appsink")
#        appsink.set_property("sync", False)
#        appsink.set_property("emit-signals", True)
#        appsink.set_property("max-buffers", 1)
#        appsink.set_property("drop", True)
#        appsink.set_property("emit-signals", True)
#        appsink.connect("new-sample", self.new_sample, None)

        soundmixout = self.common_pipeline.get_by_name("soundmixout")
        soundmixout.set_property("sync", False)
        soundmixout.set_property("emit-signals", True)
        soundmixout.set_property("max-buffers", 1)
        soundmixout.set_property("drop", True)
        soundmixout.set_property("emit-signals", True)
        #soundmixout.connect("new-preroll", self.soundmixout_new_preroll, None)
        soundmixout.connect("new-sample", self.soundmixout_new_buffer, None)
        self.soundmixout = soundmixout

        self.last_sample = time.time()
        self.bus = self.common_pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.bus.connect('message::error', self.on_error_message)
        self.bus.connect("message::eos", self.eos_handle)
        self.common_pipeline.set_state(Gst.State.PLAYING)

    #def appaud_new_sample(self, a, b):
        #print("AUD", a, b)
    #    return Gst.FlowReturn.OK

    def mpegtscleaner_new_sample(self, a, b):
        print("HERE")
        sample = self.mpegtscleaner_in.emit("pull-sample")
        buf = sample.get_buffer()
        buf.pts = Gst.CLOCK_TIME_NONE 
        buf.dts = Gst.CLOCK_TIME_NONE 
        buf.duration = Gst.CLOCK_TIME_NONE
        self.mpegtscleaner_out.emit("push-sample", sample)
        return Gst.FlowReturn.OK

    def appvidsink_need_data(self, a, b):
        return Gst.FlowReturn.OK

    def feedback_videoport(self):
        return channel_feedback_mpeg_stream_port(self.channelno)

    def start_feedback_stream(self):
        with self.mtx:
            srtport = channel_feedback_mpeg_stream_port(self.channelno)
            srtlatency = self.get_srt_latency()
    
            h264caps = "video/x-h264,profile=baseline,stream-format=byte-stream,alignment=au,framerate=30/1"
            h264caps2 = "video/x-h264,profile=baseline,stream-format=byte-stream,alignment=au"
            videocoder = pipeline_utils.video_coder_type(self.get_gpu_type())
            audiocaps = pipeline_utils.audiocaps()
            videocaps = pipeline_utils.global_videocaps()
            videodecoder = pipeline_utils.video_decoder_type(self.get_gpu_type())
    
            appaudiomix = ""
            for i in self.sound_feedback_list():
                appaudiomix = appaudiomix + f"""
                appsrc name=soundmixin{i} emit-signals=True max-bytes=10000 is-live=true do-timestamp=true caps={audiocaps} 
                    ! opusparse ! opusdec ! {audiocaps} ! queue name=quu{i} ! audioconvert ! audioresample 
                    ! queue name=uq{i} ! amixer. 
                \n"""
    
            pstr = f"""
                liveadder latency=0 name=amixer ! audioresample ! audioconvert ! tee name=audiotee
    
                audiotee. ! queue name=q3 ! audioconvert ! audioresample ! spectrascope ! 
                    videoconvert ! autovideosink name=fbaudioend sync=false            
    
                audiotee. ! queue name=q1 ! audioconvert ! audioresample ! {audiocaps} ! opusenc
                        ! srtsink  wait-for-connection=true uri=srt://:{srtport+1} latency={srtlatency} sync=false
    
                {appaudiomix}
            """
    
            self.feedback_pipeline = Gst.parse_launch(pstr)
    
            qs = [ "q0", "q1", "q2", "q3", "qq" ] + [f"uq{i}" for i in self.sound_feedback_list()] + [f"quu{i}" for i in self.sound_feedback_list()] + [f"quuu{i}" for i in self.sound_feedback_list()]
            print(qs)
            qs = [ self.feedback_pipeline.get_by_name(qname) for qname in qs ]
            for q in qs:
                pipeline_utils.setup_queuee(q)     
    
            self.fbbus = self.feedback_pipeline.get_bus()
            self.fbbus.add_signal_watch()
            self.fbbus.enable_sync_message_emission()
            self.fbbus.connect('sync-message::element', self.on_sync_message)
            self.fbbus.connect('message::error', self.on_error_message)
            self.fbbus.connect("message::eos", self.eos_handle)
            #self.feedback_pipeline.set_state(Gst.State.PLAYING)
    
            # appsrc is-live=true name=extvid
            fb2str = f"""
                appsrc caps={h264caps} emit-signals=True name=extvid is-live=true do-timestamp=true ! queue ! tee name=videotee
                     videotee. ! queue ! h264parse ! avdec_h264 ! queue name=q4 ! autovideosink name=fbvideoend
            """
 #                   videotee. ! queue !
#                    ! srtsink  wait-for-connection=true uri=srt://:{srtport} latency={srtlatency} sync=false

            #     videotee. ! queue ! h264parse ! nvh264dec ! queue name=q4 ! autovideosink name=fbvideoend
                
                
    
            """    videotee. ! queue name=q4 ! autovideosink name=fbvideoend    
            """
            
    
            self.fb2=Gst.parse_launch(fb2str)
            self.fbbus2 = self.fb2.get_bus()
            self.fbbus2.add_signal_watch()
            self.fbbus2.enable_sync_message_emission()
            self.fbbus2.connect('sync-message::element', self.on_sync_message)
            self.fbbus2.connect('message::error', self.on_error_message)
            self.fbbus2.connect("message::eos", self.eos_handle)
            self.extvid = self.fb2.get_by_name("extvid")
            if self.extvid:
                self.extvid.set_property("emit-signals", True)
    
            qs = [ "q0", "q1", "q2", "q3", "q4", "q5" ]
            qs = [ self.fb2.get_by_name(qname) for qname in qs ]
            for q in qs:
                pipeline_utils.setup_queuee(q) 
            
            self.fb2.set_state(Gst.State.PLAYING)
            
            self.feedback_pipelines = [ self.feedback_pipeline, self.fb2 ]

            self.feedback_pipeline_started = True
        
    def stop_common_stream(self):
        with self.mtx:
            if self.common_pipeline:
                self.common_pipeline.set_state(Gst.State.NULL)
            time.sleep(0.1)
            self.common_pipeline = None

            if self.sample_controller:
               self.sample_controller.stop()
            self.sample_controller = None

    def stop_feedback_stream(self):
        with self.mtx:
            self.feedback_pipeline_started = False
            if self.feedback_pipeline:
                for pipeline in self.feedback_pipelines:
                    if pipeline:
                        pipeline.set_state(Gst.State.NULL)
            time.sleep(0.1)
            self.feedback_pipeline = None
            self.fb2=None
            self.extvid = None

    def on_sync_message(self, bus, msg):
        """Биндим контрольное изображение к переданному снаружи виджету."""
        #pass
        with self.mtx:
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

        with self.mtx:
            self.common_pipeline.set_state(Gst.State.PAUSED)
            self.common_pipeline.set_state(Gst.State.READY)
            self.common_pipeline.set_state(Gst.State.PAUSED)
            self.common_pipeline.set_state(Gst.State.PLAYING)

    def on_error_message(self, bus, msg):
        with self.mtx:
            print("on_error_message", msg.parse_error())

    def start_streams(self):
        with self.mtx:
            self.start_common_stream()
            self.start_feedback_stream()
            
    def stop_streams(self):
        with self.mtx:
            self.stop_common_stream()
            self.stop_feedback_stream()
            
    def is_connected(self):
        with self.mtx:
            return self.common_pipeline is not None

    def external_video_enabled(self, chno):
        with self.mtx:
            return True

    def send_external_video_sample(self, chno, sample):
        with self.mtx:
            if self.fb2 and self.extvid and self.feedback_pipeline_started:
                self.extvid.emit("push-sample", sample)

    def stop_external_stream(self):
        with self.mtx:
            if self.fb2:
                self.stop_feedback_stream()
            self.fb2 = None
            self.extvid = None
        
    def start_external_stream(self):
        with self.mtx:
            if self.common_pipeline:
                self.start_feedback_stream()
        
class ConnectionControllerZone(QWidget):
    def __init__(self):
        self.feedback_stream_stoped = True
        self.mtx = threading.RLock()
        super().__init__()
        self.zones = []
        self.external_zone = ExternalSignalsZone(self)
        self.vlayout = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.gpuchecker = pipeline_utils.GPUChecker()
        self.hlayout.addStretch()
        self.hlayout.addWidget(QLabel("Использовать аппаратное ускорение: "))
        self.hlayout.addWidget(self.gpuchecker)
        self.vlayout.addLayout(self.hlayout)
        self.vlayout.addWidget(self.external_zone)
        self.gpuchecker.set(pipeline_utils.GPUType.NVIDIA)
        
        for i in range(3):
            self.add_zone(i, self)
            #self.zones[i].enable_disable_clicked()

        self.setLayout(self.vlayout)

    def get_gpu_type(self):
        return self.gpuchecker.get()

    def add_zone(self, i, zone):
        wdg = ConnectionController(i, zone)
        self.zones.append(wdg)
        self.vlayout.addWidget(wdg)

    def push_sample(self, sample, chno):
        for z in self.zones:
            z.push_sample(sample, chno)

    def new_sample_external_channel(self, chno, sample):
        pass
        #print(chno, sample)

    def external_video_sample(self, chno, sample):
        if self.feedback_stream_stoped:
            return

        for zone in self.zones:
            if zone.is_connected() and zone.external_video_enabled(chno):
                zone.send_external_video_sample(chno, sample)

    def external_audio_sample(self, chno, sample):
        if self.feedback_stream_stoped:
            return
        
    def stop_external_stream(self):
        with self.mtx:
            for z in self.zones:
                z.stop_external_stream()

    def start_external_stream(self):
        with self.mtx:
            for z in self.zones:
                z.start_external_stream()

    def restart_feedback_streams(self):
        print("R")
            
        with self.mtx:
            self.feedback_stream_stoped = True
            self.stop_external_stream()
            self.external_zone.stop_streams()
            QTimer.singleShot(20, self.restart_feedback_streams_part2)

    def get_feedback_video_ports(self):
        ports = []
        for z in self.zones:
            if z.is_connected():
                ports.append(z.feedback_videoport())
        return ports

    def restart_feedback_streams_part2(self):
        with self.mtx:
            ports = self.get_feedback_video_ports()
            self.external_zone.start_global_streams(ports)
            #self.external_zone.start_streams()
            #self.start_external_stream()
            self.feedback_stream_stoped = False
            
    def start_restart_feedback_streams(self):
        with self.mtx:
            QTimer.singleShot(2, self.restart_feedback_streams)