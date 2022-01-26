from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from gi.repository import GObject, Gst, GstVideo

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
    channel_video_port, 
    channel_audio_port,
    channel_feedback_video_port,
    channel_feedback_audio_port,
    channel_mpeg_stream_port
)

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

        self.connect_button = QPushButton("ТестовоеДействие")
        self.test_button = QPushButton("ТестовоеДействие2")

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
        self.main_layout.addWidget(self.connect_button)
        self.main_layout.addWidget(self.test_button)

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

        self.connect_button.clicked.connect(self.test_action)

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

    def setup_common_stream(self):
        pipeline = Gst.Pipeline()
        self.common_pipeline = pipeline

        self.fakevideosrc = pipeline_utils.imagesource("c:/users/asus/test.png")
        self.fakeaudiosrc = pipeline_utils.quiteaudio()
        self.videosrc = pipeline_utils.capture_video(self.input_device(MediaType.VIDEO))
        self.audiosrc = pipeline_utils.capture_audio(self.input_device(MediaType.AUDIO))
        
        self.fakevideosrc.add_to_pipeline(pipeline)
        self.fakeaudiosrc.add_to_pipeline(pipeline)
        self.videosrc_tee = pipeline_utils.tee_from(pipeline, self.fakevideosrc)
        self.audiosrc_tee = pipeline_utils.tee_from(pipeline, self.fakeaudiosrc)

        self.disp_video = pipeline_utils.display_video_from_tee(pipeline, self.videosrc_tee)
        self.disp_audio = pipeline_utils.display_specter_from_tee(pipeline, self.audiosrc_tee)

        h264 = pipeline_utils.h264_encode_from_tee(pipeline, self.videosrc_tee)
        opus = pipeline_utils.opus_encode_from_tee(pipeline, self.audiosrc_tee)
        mpeg = pipeline_utils.mpeg_combine_from(pipeline, [h264, opus])

        #srtsink = pipeline_utils.output_sender_srtstream(
        #    pipeline, 
        #    mpeg, 
        #    host=self.station_ip.text(),
        #    port=channel_mpeg_stream_port(self.channelno()))

        #pipeline_utils.output_udpstream(
        #    pipeline, 
        #    mpeg, 
        #    host=self.station_ip.text(),
        #    port=channel_mpeg_stream_port(self.channelno()))
        
        self.sink = pipeline_utils.fakestub_from(pipeline, mpeg)
        
    def on_sync_message(self, bus, msg):
        """Биндим контрольное изображение к переданному снаружи виджету."""
        if msg.get_structure().get_name() == 'prepare-window-handle':
            if msg.src.get_name()[-1]=='1':
                self.display_widget.connect_to_sink(msg.src)
            if msg.src.get_name()[-1]=='0':
                self.spectroscope_widget.connect_to_sink(msg.src)
        
    def start_common_stream(self):
        self.bus = self.common_pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        
        self.common_pipeline.set_state(Gst.State.PLAYING)
        
        #self.videosrc.set_state(Gst.State.NULL)

    def stop_common_stream(self):
        self.common_pipeline.set_state(Gst.State.PAUSED)
        self.common_pipeline = None

    def test_action(self):
        self.setup_common_stream()
        self.start_common_stream()

    def enable_disable_video_input(self):
        self.videosrc_tee.set_state(Gst.State.PAUSED)
        if self.fakevideosrc.is_enabled():
            self.fakevideosrc.set_state(Gst.State.NULL)
            self.fakevideosrc.unlink(self.videosrc_tee)
            self.fakevideosrc.remove_from_pipeline(self.common_pipeline)
            self.videosrc.add_to_pipeline(self.common_pipeline)
            self.videosrc.link(self.videosrc_tee)
            self.videosrc.set_state(Gst.State.PLAYING)
        else:
            self.videosrc.set_state(Gst.State.NULL)
            self.videosrc.unlink(self.videosrc_tee)
            self.videosrc.remove_from_pipeline(self.common_pipeline)
            self.fakevideosrc.add_to_pipeline(self.common_pipeline)
            self.fakevideosrc.link(self.videosrc_tee)
            self.fakevideosrc.set_state(Gst.State.PLAYING)
        self.videosrc_tee.set_state(Gst.State.PLAYING)
        
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
        