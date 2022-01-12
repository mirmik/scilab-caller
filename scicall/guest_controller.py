from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from scicall.stream_pipeline import StreamPipeline
from scicall.display_widget import DisplayWidget

class GuestController:
	PORT_BASE = 10100

	def __init__(self, number):
		self.number = number
		self.display = DisplayWidget()
		self.video_port = self.PORT_BASE + number * 2
		self.audio_port = self.PORT_BASE + number * 2 + 1 
		self.layout = QGridLayout()

		self.input_video_port_lbl = QLabel(f"Видео порт: {self.video_port}")
		self.input_audio_port_lbl = QLabel(f"Аудио порт: {self.video_port}")
		self.input_ndi_video_name_lbl = QLabel("NDI видео": self.ndi_video_name())
		self.input_ndi_audio_name_lbl = QLabel("NDI аудио": self.ndi_audio_name())
		
		self.layout.addWidget(self.display, 0, 0)

		self.audio_pipeline = StreamPipeline(None)
		self.video_pipeline = StreamPipeline(self.display)
		self.enable_disable_button = QPushButton("Включить")

    def enable_disable_clicked(self):
        if self.pipeline.runned():
            self.unfreeze()
            self.stop_pipeline()        	
            self.enable_disable_button.setText("Включить")

        else:
            self.freeze()
            self.start_pipeline()
        	self.enable_disable_button.setText("Отключить")

	def start_stream(self)
		self.video_pipeline.make_pipeline(...)
		self.audio_pipeline.make_pipeline(...)
		
		for pipeline in [self.video_pipeline, self.audio_pipeline]:
			pipeline.setup_pipeline()
			pipeline.start_pipeline()

	def stop_stream(self)
		for pipeline in [self.video_pipeline, self.audio_pipeline]:
			pipeline.stop_pipeline()


class GuestControllerZone:
	def __init__(self):
		self.zones = []
		self.vlayout = QVBoxLayout()

		for i in range(3)
			self.add_zone(i)

	def add_zone(self, i):
		wdg = GuestController(i)
		zones.append(wdg)
		self.vlayout.addWidget(wdg)