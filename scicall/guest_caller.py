from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *

from scicall.stream_pipeline import StreamPipeline
from scicall.display_widget import GstreamerDisplay
from scicall.util import get_video_captures_list, get_audio_captures_list

class GuestCaller(QWidget):
	""" Пользовательский виджет реализует удалённой станции. """

	def __init__(self):
		super().__init__()
		self.videos = get_video_captures_list()
		self.audios = get_audio_captures_list()

		self.display_widget = GstreamerDisplay()
		self.display_widget.setFixedSize(320,240)
		self.channel_list = QComboBox()
		self.channel_list.addItems(["1", "2", "3"])
		self.station_ip = QTextEdit("gfdgsdfg")
		self.video_source = QComboBox()
		self.video_source.addItems([ r.user_readable_name() for r in self.videos ])
		self.audio_source = QComboBox()
		self.audio_source.addItems([ r.user_readable_name() for r in self.audios ])
		self.video_enable_button = QPushButton("Видео")
		self.audio_enable_button = QPushButton("Аудио")
		self.status_label = QLabel("Hello")

		self.main_layout = QHBoxLayout()
		self.left_layout = QVBoxLayout()
		self.control_layout = QGridLayout()
		self.avpanel_layout = QHBoxLayout()

		#self.info_layout.addWidget(self.status_label)

		self.control_layout.addWidget(QLabel("Номер канала:"), 0, 0)
		self.control_layout.addWidget(QLabel("Источник видео:"), 1, 0)
		self.control_layout.addWidget(QLabel("Источник звука:"), 2, 0)
		self.control_layout.addWidget(self.channel_list, 0, 1)
		self.control_layout.addWidget(self.video_source, 1, 1)
		self.control_layout.addWidget(self.audio_source, 2, 1)
		self.control_layout.addWidget(self.status_label, 3, 1)

		self.avpanel_layout.addWidget(self.video_enable_button)
		self.avpanel_layout.addWidget(self.audio_enable_button)		
		self.left_layout.addWidget(self.display_widget)
		self.left_layout.addLayout(self.avpanel_layout)
		
		self.main_layout.addLayout(self.left_layout)
		self.main_layout.addLayout(self.control_layout)
		
		self.audio_pipeline = StreamPipeline(None)
		self.video_pipeline = StreamPipeline(self.display_widget)
		self.setLayout(self.main_layout)

		self.video_started = False
		self.audio_started = False
		self.client = QTcpSocket()

	def on_connect_button_clicked(self):
		self.client.open(self.ip, channel_connect_port(self.channelno()))

	def on_message(self, msg):
		print(msg)

	def on_connect(self):
		print("on_connect")

	def on_disconnect(self):
		print("on_disconnect")

	def video_clicked(self):
		if video_started:
			self.stop_pipeline(self.video_pipeline)
			self.video_started = False
		else:
			self.start_pipeline(self.video_pipeline)
			self.video_started = True

	def audio_clicked(self):
		if audio_started:
			self.stop_pipeline(self.audio_pipeline)
			self.audio_started = False
		else:
			self.start_pipeline(self.audio_pipeline)
			self.audio_started = True

	def start_pipeline(self, pipeline):
		pipeline.make_pipeline(
			self.input_settings(pipeline),
			self.output_settings(pipeline),
			self.middle_settings(pipeline))
		pipeline.setup()
		pipeline.start()

	def stop_pipeline(self, pipeline):
		pipeline.stop()

	def pipeline_codec(self, codec):
		if pipeline is self.video_pipeline:
			return VideoCodec.MJPEG
		else:
			return AudioCodec.OPUS
			
	def pipeline_port(self, codec):
		if pipeline is self.video_pipeline:
			return channel_video_port(self.channelno())
		else:
			return channel_audio_port(self.channelno())

	def input_device(self, pipeline):
		if pipeline is self.video_pipeline:
			return self.video_device()
		else:
			return self.audio_device()

	def input_settings(self, pipeline):
		return StreamSettings(
			mode = InputMode.CAPTURE,
			device = self.input_device(pipeline)
		)

	def output_settings(self, pipeline):
		return StreamSettings(
			transport = TransportMode.UDPRTP,
			codec = self.pipeline_codec(pipeline),
			port = self.pipeline_port(pipeline),
			ip = self.station_ip()
		)		

	def middle_settings(self, pipeline):
		return MiddleSettings(
			display_enabled = self.video_pipeline is pipeline
		)
	