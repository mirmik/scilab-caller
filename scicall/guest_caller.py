from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class GuestCaller:
	""" Пользовательский виджет реализует удалённой станции. """

	def __init__(self):
		self.display_widget = DisplayWidget()
		self.channel_list = QListWidget()
		self.station_ip = QTextEdit("")
		self.video_source = QListWidget()
		self.audio_source = QListWidget()
		self.video_enable_button = QPushButton()
		self.audio_enable_button = QPushButton()

		self.main_layout = QVBoxLayout()
		self.tpanel_layout = QHBoxLayout()
		self.rpanel_layout = QVBoxLayout()
		self.bpanel_layout = QHBoxLayout()

		self.tpanel_layout.addWidget(self.display_widget)
		self.tpanel_layout.addLayout(self.rpanel_layout)
		self.main_layout.addLayout(self.tpanel_layout)
		self.main_layout.addLayout(self.bpanel_layout)

		self.audio_pipeline = StreamPipeline()
		self.video_pipeline = StreamPipeline()
		self.setLayout(self.main_layout)

		self.video_started = False
		self.audio_started = False
		self.client = QTCPServer()

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
			display_enabled : self.video_pipeline is pipeline
		)
	