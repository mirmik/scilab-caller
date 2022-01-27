from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from gi.repository import GObject, Gst, GstVideo
import json
import time

from scicall.stream_pipeline import StreamPipeline, SourceBuilder
from scicall.display_widget import GstreamerDisplay
from scicall.util import get_video_captures_list, get_audio_captures_list
from scicall.stream_settings import (
    StreamSettings,
    SourceMode,
    TranslateMode,
    VideoCodecType,
    AudioCodecType,
    TransportType,
    MediaType,
    MiddleSettings
)

from scicall.util import (
    channel_control_port, 
    channel_video_port, 
    channel_audio_port,
    channel_feedback_video_port,
    channel_feedback_audio_port,
    channel_mpeg_stream_port
)

import traceback
import scicall.pipeline_utils as pipeline_utils

class GuestCaller(QWidget):
    """ Пользовательский виджет реализует удалённой станции. """

    def __init__(self):
        super().__init__()
        self.videos = get_video_captures_list(default=True,test=True)
        self.audios = [ a for a in get_audio_captures_list(default=True,test=True) if a.is_supported() ]

        for v in self.videos:
            print(v.filtered_video_caps())

        for v in self.audios:
            print(v.audio_caps())

        self.runned = False
        self.display_widget = GstreamerDisplay()
        self.display_widget.setFixedSize(320,240)
        self.spectroscope_widget = GstreamerDisplay()
        self.spectroscope_widget.setFixedSize(320,240)
        self.feedback_display_widget = GstreamerDisplay()
        self.feedback_display_widget.setFixedSize(320,240)
        self.feedback_spectroscope_widget = GstreamerDisplay()
        self.feedback_spectroscope_widget.setFixedSize(320,240)
        self.channel_list = QComboBox()
        self.channel_list.addItems(["1", "2", "3"])
        self.station_ip = QLineEdit("127.0.0.1")
        self.video_source = QComboBox()
        self.video_source.addItems([ r.user_readable_name() for r in self.videos ])
        self.audio_source = QComboBox()
        self.audio_source.addItems([ r.user_readable_name() for r in self.audios ])
        self.video_enable_button = QPushButton("Видео")
        self.audio_enable_button = QPushButton("Аудио")
        self.feed_video_enable_button = QPushButton("Видео(обратный)")
        self.feed_audio_enable_button = QPushButton("Аудио(обратный)")

        self.connect_label_text = "Установить соединение"
        self.disconnect_label_text = "Разорвать соединение"
        self.connect_button = QPushButton(self.connect_label_text)

        self.main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.left_feed_layout = QVBoxLayout()
        self.control_layout = QGridLayout()
        self.avpanel_layout = QHBoxLayout()
        self.avpanel_feed_layout = QHBoxLayout()

        #self.info_layout.addWidget(self.status_label)

        self.control_layout.addWidget(QLabel("IP адрес сервера:"), 0, 0)
        self.control_layout.addWidget(QLabel("Номер канала:"), 1, 0)
        self.control_layout.addWidget(QLabel("Источник видео:"), 2, 0)
        self.control_layout.addWidget(QLabel("Источник звука:"), 3, 0)
        self.control_layout.addWidget(self.station_ip, 0, 1)
        self.control_layout.addWidget(self.channel_list, 1, 1)
        self.control_layout.addWidget(self.video_source, 2, 1)
        self.control_layout.addWidget(self.audio_source, 3, 1)
        self.control_layout.addWidget(self.connect_button, 4, 0, 1, 2)

        self.avpanel_layout.addWidget(self.video_enable_button)
        self.avpanel_layout.addWidget(self.audio_enable_button)
        self.avpanel_feed_layout.addWidget(self.feed_video_enable_button)
        self.avpanel_feed_layout.addWidget(self.feed_audio_enable_button)
        self.left_layout.addWidget(self.display_widget)     
        self.left_layout.addWidget(self.spectroscope_widget)
        self.left_feed_layout.addWidget(self.feedback_display_widget)       
        self.left_feed_layout.addWidget(self.feedback_spectroscope_widget)
        self.left_layout.addLayout(self.avpanel_layout)
        self.left_feed_layout.addLayout(self.avpanel_feed_layout)

        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addLayout(self.left_feed_layout)
        self.main_layout.addLayout(self.control_layout)

        self.audio_pipeline = StreamPipeline(self.spectroscope_widget)
        self.video_pipeline = StreamPipeline(self.display_widget)
        self.feedback_audio_pipeline = StreamPipeline(self.feedback_spectroscope_widget)
        self.feedback_video_pipeline = StreamPipeline(self.feedback_display_widget)
        self.setLayout(self.main_layout)
        self.client = QTcpSocket()

        self.audio_enable_button.clicked.connect(self.audio_clicked)
        self.video_enable_button.clicked.connect(self.video_clicked)
        self.feed_audio_enable_button.clicked.connect(self.feed_audio_clicked)
        self.feed_video_enable_button.clicked.connect(self.feed_video_clicked)

        self.client = QTcpSocket()
        self.client.connected.connect(self.on_client_connect)
        self.client.disconnected.connect(self.on_client_disconnect)
        self.client.readyRead.connect(self.client_ready_read)
        self.connect_button.clicked.connect(self.connect_action)

    def opposite_ip(self):
        return self.station_ip.text()

    def on_client_disconnect(self):
        self.stop_common_stream()
        print("GUEST : disconnect")
        self.connect_button.setText(self.connect_label_text)

    def on_client_connect(self):
        self.connect_button.setText(self.disconnect_label_text)


    def client_ready_read(self):
        rawdata = self.client.readLineData(1024).decode("utf-8")
        data = json.loads(rawdata)
        self.new_opposite_command(data)

    def new_opposite_command(self, data):
        print("STATION >>", data)
        cmd = data["cmd"]
        
        if cmd == "hello_from_server":
            self.send_to_opposite({"cmd": "hello_from_guest"})
        elif cmd == "start_common_stream":
            time.sleep(0.2)
            self.start_common_stream()
        else:
            print("unresolved command")        

    def send_to_opposite(self, dct):
        self.client.writeData(json.dumps(dct).encode("utf-8"))

    def connect_action(self):
        if self.client.state() == QTcpSocket.ConnectedState:
            self.client.disconnectFromHost()
            self.stop_common_stream()
            return 

        print("tryConnectTo server")
        self.client.connectToHost(QHostAddress(self.opposite_ip()), channel_control_port(self.channelno()))
        success = self.client.waitForConnected(400)
        if success:
            print("success")
        else:            
            msgBox = QMessageBox()
            msgBox.setText("Не удалось установить соединение с сервером.")
            msgBox.exec()



    def video_device(self):
        return self.videos[self.video_source.currentIndex()]

    def audio_device(self):
        return self.audios[self.audio_source.currentIndex()]

    def on_connect_button_clicked(self):
        self.client.open(self.ip, channel_connect_port(self.channelno()))

    def on_message(self, msg):
        print(msg)

    def on_connect(self):
        print("on_connect")

    def on_disconnect(self):
        print("on_disconnect")

    def video_clicked(self):
        self.enable_disable_video_input()

    def audio_clicked(self):
        self.enable_disable_audio_input()

    def feed_video_clicked(self):
        if self.feedback_video_pipeline.runned():
            self.stop_pipeline(self.feedback_video_pipeline)
        else:
            self.start_feedback_pipeline(self.feedback_video_pipeline, MediaType.VIDEO)

    def feed_audio_clicked(self):
        if self.feedback_audio_pipeline.runned():
            self.stop_pipeline(self.feedback_audio_pipeline)
        else:
            self.start_feedback_pipeline(self.feedback_audio_pipeline, MediaType.AUDIO)

    def set_info(self):
        self.status_label.setText(f"""Статус:
Подключено: нет
Видео: {self.video_status()}
Аудио: {self.audio_status()}
""")

    def start_pipeline(self, pipeline):
        pipeline.make_pipeline(
            self.input_settings(pipeline),
            self.output_settings(pipeline),
            self.middle_settings(pipeline))
        pipeline.setup()
        pipeline.start()

        self.set_info()

    def start_feedback_pipeline(self, pipeline, mediatype):
        pipeline.make_pipeline(
            self.feedback_input_settings(mediatype),
            self.feedback_output_settings(mediatype),
            self.feedback_middle_settings(mediatype))
        pipeline.setup()
        pipeline.start()

    def stop_pipeline(self, pipeline):
        pipeline.stop()

    def pipeline_codec(self, pipeline):
        if pipeline is MediaType.VIDEO:
            return VideoCodecType.H264
        if pipeline is MediaType.AUDIO:
            return AudioCodecType.OPUS          
        if pipeline is self.video_pipeline:
            return VideoCodecType.H264
        else:
            return AudioCodecType.OPUS
        
    def pipeline_mediatype(self, pipeline):
        if pipeline is self.video_pipeline:
            return MediaType.VIDEO
        else:
            return MediaType.AUDIO

    def pipeline_port(self, pipeline):
        if pipeline is self.video_pipeline:
            return channel_video_port(self.channelno())
        else:
            return channel_audio_port(self.channelno())

    def pipeline_feedback_port(self, pipeline):
        if pipeline is MediaType.VIDEO:
            return channel_feedback_video_port(self.channelno())
        else:
            return channel_feedback_audio_port(self.channelno())

    def channelno(self):
        return int(self.channel_list.currentText()) - 1

    def input_device(self, mediatype):
        if mediatype is MediaType.VIDEO:
            return self.video_device()
        else:
            return self.audio_device()

    def input_settings(self, mediatype):
        return StreamSettings(
            mediatype= mediatype,
            mode = SourceMode.CAPTURE,
            device = self.input_device(mediatype)
        )

    def output_settings(self, pipeline):
        return StreamSettings(
            mediatype= self.pipeline_mediatype(pipeline),
            mode = TranslateMode.STREAM,
            transport = TransportType.SRTREMOTE,
            codec = self.pipeline_codec(pipeline),
            port = self.pipeline_port(pipeline),
            ip = self.station_ip.text()
        )       

    def middle_settings(self, pipeline):
        return MiddleSettings(
            display_enabled = True,
            mediatype = self.pipeline_mediatype(pipeline)
        )
    

    def feedback_input_settings(self, mediatype):
        return StreamSettings(
            mediatype= mediatype,
            mode = SourceMode.STREAM,
            codec = self.pipeline_codec(mediatype),
            transport = TransportType.SRTREMOTE,
            ip = self.station_ip.text(),
            port = self.pipeline_feedback_port(mediatype)
        )

    def feedback_output_settings(self, mediatype):
        return StreamSettings(
            mode=TranslateMode.NOTRANS
        )       

    def feedback_middle_settings(self, mediatype):
        return MiddleSettings(
            display_enabled = True,
            mediatype = mediatype
        )

    def start_common_stream(self):
        """ gst-launch-1.0 videotestsrc ! videoconvert ! x264enc ! mpegtsmux name=mux ! srtsink uri=srt://127.0.0.1:20106 audiotestsrc ! audioconvert ! opusenc ! mux. """

        video_device = self.input_device(MediaType.VIDEO).to_pipeline_string()
        audio_device = self.input_device(MediaType.AUDIO).to_pipeline_string()

        srtport = channel_mpeg_stream_port(self.channelno())
        srtlatency = 80
        srthost = self.station_ip.text()
        self.common_pipeline = Gst.parse_launch(
            f"""mpegtsmux name=m ! queue name=q0 
                ! srtsink uri=srt://{srthost}:{srtport} name=srtout wait-for-connection=true latency={srtlatency} sync=false async=true
                {video_device} name=cam ! videoscale name=vconv ! videoconvert ! queue name=l0 ! tee name=t1 ! queue name=qt0 ! videoconvert ! x264enc tune=zerolatency ! queue name=q1 ! m. 
                {audio_device} name=mic ! audioconvert name=aconv ! queue name=l1 ! tee name=t2 ! queue name=qt1 ! audioconvert ! opusenc ! queue name=q2 ! m.
                t1. ! queue name=qt2 ! videoconvert ! autovideosink sync=false name=videoend
                t2. ! queue name=qt3 ! audioconvert ! spectrascope ! videoconvert ! autovideosink sync=false name=audioend
             """)

        qs = [ self.common_pipeline.get_by_name(qname) for qname in [
            "q0", "q1", "q2", "qt0", "qt1", "qt2", "qt3", "l1", "l0"
        ]]
        for q in qs:
            q.set_property("max-size-bytes", 100000) 
            q.set_property("max-size-buffers", 0) 

        self.bus = self.common_pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.common_pipeline.set_state(Gst.State.PLAYING)

        #self.fakevideosrc = pipeline_utils.imagesource("c:/users/asus/test.png")
        self.fakevideosrc = pipeline_utils.videotestsrc()

        self.videosrc = pipeline_utils.GstSubchain(self.common_pipeline.get_by_name("cam")) 
        self.audiosrc = self.common_pipeline.get_by_name("mic")
        self.vconv = pipeline_utils.GstSubchain(self.common_pipeline.get_by_name("vconv")) 
        self.aconv = pipeline_utils.GstSubchain(self.common_pipeline.get_by_name("aconv")) 
        self.srtout = pipeline_utils.GstSubchain(self.common_pipeline.get_by_name("srtout"))
        self.videosrc.enabled=True
        self.audiosrc.enabled=True

    def on_sync_message(self, bus, msg):
        """Биндим контрольное изображение к переданному снаружи виджету."""
        #pass
        if msg.get_structure().get_name() == 'prepare-window-handle':
            name = msg.src.get_parent().get_parent().name
            if name=="videoend":
                self.display_widget.connect_to_sink(msg.src)
            if name=="audioend":
                self.spectroscope_widget.connect_to_sink(msg.src)
        
    def stop_common_stream(self):
        if self.common_pipeline:
            self.common_pipeline.set_state(Gst.State.NULL)
        self.common_pipeline = None

    def enable_disable_video_input_part1(self):
        if self.fakevideosrc.is_enabled():
            self.common_pipeline.set_state(Gst.State.NULL)
            self.fakevideosrc.unlink(self.vconv)
            self.fakevideosrc.remove_from_pipeline(self.common_pipeline)
            self.videosrc.add_to_pipeline(self.common_pipeline)
            self.videosrc.link(self.vconv)
            self.common_pipeline.set_state(Gst.State.PLAYING)
        else:
            self.common_pipeline.set_state(Gst.State.NULL)
            self.videosrc.unlink(self.vconv)
            self.videosrc.remove_from_pipeline(self.common_pipeline)
            self.fakevideosrc.add_to_pipeline(self.common_pipeline)
            self.fakevideosrc.link(self.vconv)
            self.common_pipeline.set_state(Gst.State.PLAYING)
        
    def enable_disable_audio_input(self):
        self.audiosrc_tee.set_state(Gst.State.PAUSED)
        if self.fakeaudiosrc.is_enabled():
            self.fakeaudiosrc.set_state(Gst.State.NULL)
            self.fakeaudiosrc.unlink(self.audiosrc_tee)
            self.fakeaudiosrc.remove_from_pipeline(self.common_pipeline)
            self.audiosrc.add_to_pipeline(self.common_pipeline)
            self.audiosrc.link(self.audiosrc_tee)
            self.audiosrc.set_state(Gst.State.PLAYING)
        else:
            self.audiosrc.set_state(Gst.State.NULL)
            self.audiosrc.unlink(self.audiosrc_tee)
            self.audiosrc.remove_from_pipeline(self.common_pipeline)
            self.fakeaudiosrc.add_to_pipeline(self.common_pipeline)
            self.fakeaudiosrc.link(self.audiosrc_tee)
            self.fakeaudiosrc.set_state(Gst.State.PLAYING)
        self.audiosrc_tee.set_state(Gst.State.PLAYING)
        
    def test_action(self):
        try:
            #self.start_control_server()
            if self.runned:
                self.stop_common_stream()
            #    self.stop_recv_pipeline()       
            #    self.stop_feedback_pipeline() 
                #self.enable_disable_button.setText("Включить")
                self.runned = False
            else:
                self.setup_common_stream()
                self.start_common_stream()
            #    self.start_recv_pipeline()
            #    self.start_feedback_pipeline()
                #self.enable_disable_button.setText("Отключить")
                self.runned = True
            #self.update_info()
        except Exception as ex:
            traceback.print_exc()
            msgBox = QMessageBox()
            msgBox.setText("Возникла непредвиденная ситуация:\r\n" +
                           traceback.format_exc())
            msgBox.exec()
