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

from scicall.ports import *
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
        self.feedback_spectroscope = GstreamerDisplay() 
        self.layout = QHBoxLayout()
        self.clients = []
        self.server = Server()
        self.write_socket_data.connect(self.server.writeData, Qt.QueuedConnection)
        self.server.newConnection.connect(self.on_server_new_connect)
        self.listener = None

        #self.cb_get_vmix_srt = QCheckBox("Забирать ndi(видео)")
        self.cb_ndi_output = QCheckBox("Конвертировать в ndi поток")
        self.cb_ndi_output.setChecked(True)

        self.common_channel_cb = QCheckBox("Прямой канал:")
        self.feedback_channel_cb = QCheckBox("Обратный канал:")
        self.srtlatency_edit = QLineEdit("80")
        self.common_channel_cb.setChecked(True)
        self.feedback_channel_cb.setChecked(True)

        self.infowdg = QTextEdit()
        self.enable_disable_button = QPushButton("Включить канал")
        self.restart_button = QPushButton("Перезапустить удалённо")
        
        self.info_layout = QVBoxLayout()
        self.info_layout.addWidget(self.infowdg)
        self.info_layout.addStretch()

        self.control_layout = QVBoxLayout()
        self.control_layout2 = QVBoxLayout()
        self.control_layout2.addWidget(self.enable_disable_button)
        self.control_layout2.addWidget(self.restart_button)
        self.make_checkboxes_for_sound_feedback()          
        self.control_layout.addWidget(QLabel("srt latency:"))   
        self.control_layout.addWidget(self.srtlatency_edit)
        self.control_layout.addStretch()

        #self.control_layout2.addWidget(self.cb_get_vmix_srt)
        self.control_layout2.addWidget(self.cb_ndi_output)
        self.control_layout2.addStretch()

        self.layout.addWidget(self.display)
        self.layout.addWidget(self.spectroscope)
        #self.layout.addWidget(self.feedback_spectroscope)
        self.layout.addLayout(self.info_layout)
        self.layout.addLayout(self.control_layout)
        self.layout.addLayout(self.control_layout2)


        self.display.setFixedSize(160,160)
        self.spectroscope.setFixedSize(160,160)
        self.feedback_spectroscope.setFixedSize(160,160)

        self.enable_disable_button.clicked.connect(self.enable_disable_clicked)
        self.restart_button.clicked.connect(self.restart_button_handle)
        self.setLayout(self.layout)
        self.update_info()

        self.common_pipeline=None
        self.feedback_pipeline=None
        self.sample_controller=None
        self.feedback_pipeline_started = False

    def get_audioend(self):
        return self.feedback_spectroscope

    def input_ndi_name(self):
        return self.port_srt_vmix_edit.text()

    def get_srt_latency(self):
        return int(self.srtlatency_edit.text())

    def make_checkboxes_for_sound_feedback(self):
        self.volume_retrans_audio = []
        for i in range(3):
            wdg = QCheckBox("Ретранс. звука: " + str(i+1))
            if self.channelno != i: wdg.setChecked(True)
            self.control_layout.addWidget(wdg)
            self.audio_feedback_checkboxes.append(wdg)
            self.volume_retrans_audio.append(wdg)
            wdg.stateChanged.connect(self.update_volume_helper)
        extwdg = QCheckBox("Внешн. звук ")
        self.control_layout.addWidget(extwdg)
        self.audio_feedback_checkboxes.append(extwdg)
        self.volume_external_audio = extwdg
        extwdg.stateChanged.connect(self.update_volume_helper)

    def update_volume_helper(self):
        self.update_volume()

    def update_volume(self):
        self.send_volumes_instruction()

    def guest_volumes_array(self):
        arr = []
        for i in range(len(self.volume_retrans_audio)):
            enabled = self.volume_retrans_audio[i].isChecked()
            volume = 1 if enabled else 0
            arr.append(volume)
        return arr

    def external_volumes_array(self):
        arr = []
        extenabled = self.volume_external_audio.isChecked()
        extvolume = 1 if extenabled else 0
        arr.append(extvolume)
        return arr

    def send_volumes_instruction(self):
        dct = {
            "cmd" : "set_volumes",
            "guest_channels" : self.guest_volumes_array(),
            "external_channels" : self.external_volumes_array()
        }
        self.send_to_opposite(dct)
        
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
        cmd = data["cmd"]        
        if cmd == "keepalive":
            pass

        elif cmd == "hello_from_guest":
            self.send_to_opposite({"cmd": "set_srtlatency", "data": self.get_srt_latency()})
            time.sleep(0.2)

            if self.common_channel_cb.isChecked():
                #self.start_common_stream()
                self.send_to_opposite({"cmd": "start_common_stream"})

            time.sleep(0.2)

            if self.feedback_channel_cb.isChecked():
                self.send_to_opposite({
                    "cmd": "start_feedback_stream",
                    "count_of_guests" : 3,
                    "count_of_externals" : 1
                })
                self.send_volumes_instruction()
                self.zone.start_restart_feedback_streams()
        else:
            print("unresolved command")        

    def send_to_opposite(self, dct):
        if len(self.clients) == 0:
            return
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
                self.cb_ndi_output.setEnabled(True)
            else:
                self.start_control_server()
                self.start_common_stream()
                self.enable_disable_button.setText("Отключить канал")
                self.runned = True
                self.cb_ndi_output.setEnabled(False)
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

    def start_common_stream(self):
        videodecoder = pipeline_utils.video_decoder_type(self.get_gpu_type())
        videocoder = pipeline_utils.video_coder_type(self.get_gpu_type())
        srtport = channel_mpeg_stream_port(self.channelno)
        audio_mirror_port = channel_audio_mirror_port(self.channelno)
        srtlatency = self.get_srt_latency()

        audiocaps = pipeline_utils.global_audiocaps()
        udpspam = internal_channel_audio_udpspam_port(self.channelno)

        ndisink = f"ndisink ndi-name={self.ndi_name()}"
        if not self.cb_ndi_output.isChecked():
            ndisink = "fakesink"

        audioparser = pipeline_utils.default_audioparser()
        audiodecoder = pipeline_utils.default_audiodecoder()

        self.common_pipeline = Gst.parse_launch(
            f"""srtsrc uri=srt://:{srtport} wait-for-connection=true latency={srtlatency} 
                    ! queue name=q0 ! h264parse ! {videodecoder} ! tee name=t1 

            srtsrc uri=srt://:{srtport+1} wait-for-connection=true latency={srtlatency} ! 
            queue name=q2 ! tee name=opusin ! {audioparser} ! {audiodecoder}
             ! audioconvert ! audioresample !  tee name=t2 
            
            t1. ! queue name=qt0 ! videoconvert ! autovideosink sync=false name=videoend
            t2. ! queue name=qt1 !audioconvert ! spectrascope ! videoconvert ! 
                autovideosink sync=false name=audioend

            t1. ! queue ! videoconvert ! combiner.
            t2. ! queue ! audioconvert ! audioresample ! combiner.
            ndisinkcombiner name=combiner ! {ndisink} 

            opusin. ! queue name=qt5 ! srtsink uri=srt://:{audio_mirror_port} wait-for-connection=false latency={srtlatency}
        """)
        qs = [ self.common_pipeline.get_by_name(qname) for qname in [
            "q0", "q2", "qt0", "qt1", "qt2", "qt3", "qt4", "qt5"
        ]]
        for q in qs:
            pipeline_utils.setup_queuee(q)

        self.last_sample = time.time()
        self.bus = self.common_pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.common_pipeline.set_state(Gst.State.PLAYING)

    def feedback_videoport(self):
        return channel_feedback_mpeg_stream_port(self.channelno)
        
    def stop_common_stream(self):
        with self.mtx:
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
        print("ON_SYNC_MESSAGE")
        with self.mtx:
            if msg.get_structure().get_name() == 'prepare-window-handle':
                print("DFASDFSDFSADGSADGSDFSADFSADFSADFSADFDSAFASFD")
                print("PREPARE_WINDOW_HANDLE", msg.src.get_parent().get_parent().name)
                name = msg.src.get_parent().get_parent().name
                if name=="videoend":
                    self.display.connect_to_sink(msg.src)
                if name=="audioend":
                    self.spectroscope.connect_to_sink(msg.src)
                if name=="fbaudioend":
                    self.feedback_spectroscope.connect_to_sink(msg.src)

    def start_streams(self):
        with self.mtx:
            self.start_common_stream()
            
    def stop_streams(self):
        with self.mtx:
            self.stop_common_stream()
            
    def is_connected(self):
        with self.mtx:
            return self.common_pipeline is not None

class ConnectionControllerZone(QWidget):
    def __init__(self):
        self.feedback_stream_stoped = True
        self.mtx = threading.RLock()
        super().__init__()
        self.zones = []
        self.vlayout = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.gpuchecker = pipeline_utils.GPUChecker()
        self.hlayout.addStretch()
        self.hlayout.addWidget(QLabel("Использовать аппаратное ускорение: "))
        self.hlayout.addWidget(self.gpuchecker)
        self.vlayout.addLayout(self.hlayout)
        
        for i in range(3):
            self.add_zone(i, self)
            self.zones[-1].enable_disable_clicked()
            self.zones[-1].enable_disable_button.setEnabled(False)

        self.external_zone = ExternalSignalsZone(self)
        
        self.vlayout.addWidget(self.external_zone)
        for wdg in self.zones:
            self.vlayout.addWidget(wdg)

        self.setLayout(self.vlayout)

        for wdg in self.zones:
            wdg.update_volume()

    def get_gpu_type(self):
        return self.gpuchecker.get()

    def add_zone(self, i, zone):
        wdg = ConnectionController(i, zone)
        self.zones.append(wdg)
        
    def restart_feedback_streams(self):
        with self.mtx:
            self.feedback_stream_stoped = True
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
            self.feedback_stream_stoped = False
            
    def start_restart_feedback_streams(self):
        with self.mtx:
            QTimer.singleShot(2, self.restart_feedback_streams)

    def get_audioends(self):
        return [ z.get_audioend() for z in self.zones ]

    #def set_volume(self, f, t, val):
    #    self.external_zone.set_volume(f,t,val)
    #    print("set_volume", f, t, val)