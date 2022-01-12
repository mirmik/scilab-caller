from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *

from scicall.stream_pipeline import StreamPipeline
from scicall.display_widget import GstreamerDisplay

from scicall.util import channel_control_port, channel_video_port, channel_audio_port

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
		self.runned = False
		self.channelno = number
		self.display = GstreamerDisplay()
		self.display.setFixedSize(200,160)
		self.layout = QHBoxLayout()
		self.server = QTcpServer()
		self.listener = None

		self.channelno_lbl = QLabel(f"Канал: {self.channelno}")
		self.control_port_lbl = QLabel(f"Контрольный порт: {self.control_port()}")
		self.input_video_port_lbl = QLabel(f"Видео порт: {self.video_port()}")
		self.input_audio_port_lbl = QLabel(f"Аудио порт: {self.audio_port()}")
		self.ndi_video_name_lbl = QLabel(f"NDI видео: {self.ndi_video_name()}")
		self.ndi_audio_name_lbl = QLabel(f"NDI аудио: {self.ndi_audio_name()}")
		self.enable_disable_button = QPushButton("Включить")
		
		self.info_layout = QVBoxLayout()
		self.info_layout.addWidget(self.control_port_lbl)
		self.info_layout.addWidget(self.input_video_port_lbl)
		self.info_layout.addWidget(self.input_audio_port_lbl)
		self.info_layout.addWidget(self.ndi_video_name_lbl)
		self.info_layout.addWidget(self.ndi_audio_name_lbl)
		self.info_layout.addStretch()

		self.control_layout = QVBoxLayout()
		self.control_layout.addWidget(self.enable_disable_button)

		self.layout.addWidget(self.display)
		self.layout.addLayout(self.info_layout)
		self.layout.addLayout(self.control_layout)

		self.audio_pipeline = StreamPipeline(None)
		self.video_pipeline = StreamPipeline(self.display)

		self.enable_disable_button.clicked.connect(self.enable_disable_clicked)
		self.setLayout(self.layout)

	def control_port(self):
		return channel_control_port(self.channelno)

	def video_port(self):
		return channel_video_port(self.channelno)

	def audio_port(self):
		return channel_audio_port(self.channelno)

	def on_server_new_connect(self):
		print("Station: on_server_connect")

	def send_greetings(self):
		self.listener.send(json.dumps(
			{"cmd" : "hello"}
		))

	def enable_disable_clicked(self):
		#self.start_server()

		if self.runned:
			#self.unfreeze()
			self.stop_pipeline()        	
			self.enable_disable_button.setText("Включить")

		else:
			#self.freeze()
			self.start_pipeline()
			self.enable_disable_button.setText("Отключить")

	def start_pipeline(self):
		self.runned = True
		self.video_pipeline.make_pipeline(
			self.input_settings(self.video_pipeline),
			self.output_settings(self.video_pipeline),
			self.middle_settings(self.video_pipeline))
		self.audio_pipeline.make_pipeline(
			self.input_settings(self.audio_pipeline),
			self.output_settings(self.audio_pipeline),
			self.middle_settings(self.audio_pipeline))
		
		for pipeline in [
			self.video_pipeline, 
			self.audio_pipeline
		]:
			pipeline.setup()
			pipeline.start()

	def stop_pipeline(self):
		self.runned = False
		for pipeline in [self.video_pipeline, self.audio_pipeline]:
			pipeline.stop()

	def input_settings(self, pipeline):
		return StreamSettings(
			mediatype = self.pipeline_mediatype(pipeline),
			mode = SourceMode.STREAM,
			transport = TransportType.RTPUDP,
			codec = self.pipeline_codec(pipeline),
			port = self.pipeline_port(pipeline)
		)

	def output_settings(self, pipeline):
		return StreamSettings(
			mediatype = self.pipeline_mediatype(pipeline),
			mode = TranslateMode.STREAM,
			transport = TransportType.NDI,
			codec = VideoCodecType.NOCODEC,
			ndi_name = self.ndi_name(pipeline)
		)		

	def middle_settings(self, pipeline):
		return MiddleSettings(
			display_enabled = self.video_pipeline is pipeline
		)

	def pipeline_codec(self, pipeline):
		if pipeline is self.video_pipeline:
			return VideoCodecType.MJPEG
		else:
			return AudioCodecType.OPUS

	def pipeline_port(self, pipeline):
		if pipeline is self.video_pipeline:
			return self.video_port()
		else:
			return self.audio_port()

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

	def ndi_video_name(self):
		return f"Guest{self.channelno+1}-Video0"

	def ndi_audio_name(self):
		return f"Guest{self.channelno+1}-Audio0"

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
