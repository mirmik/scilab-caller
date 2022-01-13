from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from gi.repository import GObject, Gst, GstVideo

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
		self.video_connected = False
		self.audio_connected = False
		self.runned = False
		self.channelno = number
		self.display = GstreamerDisplay()
		self.display.setFixedSize(200,160)
		self.spectroscope = GstreamerDisplay()
		self.spectroscope.setFixedSize(200,160)
		self.layout = QHBoxLayout()
		self.server = QTcpServer()
		self.listener = None

		self.infowdg = QTextEdit()
		self.enable_disable_button = QPushButton("Включить")
		
		self.info_layout = QVBoxLayout()
		self.info_layout.addWidget(self.infowdg)
		self.info_layout.addStretch()

		self.control_layout = QVBoxLayout()
		self.control_layout.addWidget(self.enable_disable_button)

		self.layout.addWidget(self.spectroscope)
		self.layout.addWidget(self.display)
		self.layout.addLayout(self.info_layout)
		self.layout.addLayout(self.control_layout)

		self.audio_pipeline = StreamPipeline(self.spectroscope)
		self.video_pipeline = StreamPipeline(self.display)

		self.enable_disable_button.clicked.connect(self.enable_disable_clicked)
		self.setLayout(self.layout)
		self.update_info()

		self.update_timer = QTimer(self)
		self.update_timer.timeout.connect(self.update_if_need)
		self.update_timer.start(100);

	def update_if_need(self):
		if self.need_update:
			self.update_info()

	def update_info(self):
		self.need_update = False
		self.infowdg.setText(f"""Контрольный порт: {self.control_port()}

Видео:
  порт: {self.video_port()}
  NDI-поток: {self.ndi_video_name()}
  состояние: {self.video_connected}

Аудио:
  порт: {self.audio_port()}
  NDI-поток: {self.ndi_audio_name()}
  состояние: {self.audio_connected}
""")

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
			self.update_info()

		else:
			#self.freeze()
			self.start_pipeline()
			self.enable_disable_button.setText("Отключить")
			self.update_info()

	def start_pipeline(self):
		self.runned = True
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

	def stop_pipeline(self):
		self.runned = False
		for pipeline in [self.video_pipeline, self.audio_pipeline]:
			pipeline.stop()

	def on_srt_video_caller_removed(self, srtsrc, a, pipeline):
		print("ON_SRT_VIDEO_REMOVE")
		self.video_connected = False
		self.need_update = True
		self.raw_video_pipeline.set_state(Gst.State.PAUSED)
		self.raw_video_pipeline.set_state(Gst.State.READY)
		self.raw_video_pipeline.set_state(Gst.State.PAUSED)
		self.raw_video_pipeline.set_state(Gst.State.PLAYING)
		
	def on_srt_audio_caller_removed(self, srtsrc, a, pipeline):
		print("ON_SRT_AUDIO_REMOVE")
		self.audio_connected = False
		self.need_update = True
		self.raw_audio_pipeline.set_state(Gst.State.PAUSED)
		self.raw_audio_pipeline.set_state(Gst.State.READY)
		self.raw_audio_pipeline.set_state(Gst.State.PAUSED)
		self.raw_audio_pipeline.set_state(Gst.State.PLAYING)
	
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
			on_srt_caller_removed = self.on_srt_video_caller_removed if pipeline is self.video_pipeline else self.on_srt_audio_caller_removed,
			on_srt_caller_added = self.on_srt_video_caller_added if pipeline is self.video_pipeline else self.on_srt_audio_caller_added,
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
			display_enabled = True
		)

	def pipeline_codec(self, pipeline):
		if pipeline is self.video_pipeline:
			return VideoCodecType.H264
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
