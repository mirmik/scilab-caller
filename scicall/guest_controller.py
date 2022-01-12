from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from scicall.stream_pipeline import StreamPipeline
from scicall.display_widget import DisplayWidget

class ConnectionController:
	def __init__(self, number):
		self.channelno = number
		self.display = DisplayWidget()
		self.layout = QGridLayout()
		self.server = QTCPServer()
		self.listener = None

		self.control_port_lbl = QLabel(f"Контрольный порт: {self.control_port()}")
		self.input_video_port_lbl = QLabel(f"Видео порт: {self.video_port()}")
		self.input_audio_port_lbl = QLabel(f"Аудио порт: {self.audio_port()}")
		self.input_ndi_video_name_lbl = QLabel("NDI видео:", self.ndi_video_name())
		self.input_ndi_audio_name_lbl = QLabel("NDI аудио:", self.ndi_audio_name())
		
		self.layout.addWidget(self.display, 0, 0)

		self.audio_pipeline = StreamPipeline(None)
		self.video_pipeline = StreamPipeline(self.display)
		self.enable_disable_button = QPushButton("Включить")

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
    	self.start_server()

        if self.pipeline.runned():
            self.unfreeze()
            self.stop_pipeline()        	
            self.enable_disable_button.setText("Включить")

        else:
            self.freeze()
            self.start_pipeline()
        	self.enable_disable_button.setText("Отключить")

	def start_stream(self)
		self.video_pipeline.make_pipeline(
			self.input_settings(self.video_pipeline),
			self.output_settings(self.video_pipeline),
			self.middle_settings(self.video_pipeline))
		self.audio_pipeline.make_pipeline(
			self.input_settings(self.audio_pipeline),
			self.output_settings(self.audio_pipeline),
			self.middle_settings(self.audio_pipeline))
		
		for pipeline in [self.video_pipeline, self.audio_pipeline]:
			pipeline.setup_pipeline()
			pipeline.start_pipeline()

	def stop_stream(self)
		for pipeline in [self.video_pipeline, self.audio_pipeline]:
			pipeline.stop_pipeline()

	def input_settings(self, pipeline):
		return StreamSettings(
			transport = TransportMode.UDPRTP,
			codec = self.pipeline_codec(pipeline),
			port = self.pipeline_port(pipeline)
		)

	def output_settings(self, pipeline):
		return StreamSettings(
			transport = TransportMode.NDI,
			codec = VideoCodec.NOCODEC
		)		

	def middle_settings(self, pipeline):
		return MiddleSettings(
			display_enabled : self.video_pipeline is pipeline
		)

	def ndi_video_name(self):
		return f"Guest{self.channelno}:Video"

	def ndi_audio_name(self):
		return f"Guest{self.channelno}:Audio"

class ConnectionControllerZone:
	def __init__(self):
		self.zones = []
		self.vlayout = QVBoxLayout()

		for i in range(3)
			self.add_zone(i)

	def add_zone(self, i):
		wdg = ConnectionController(i)
		zones.append(wdg)
		self.vlayout.addWidget(wdg)
