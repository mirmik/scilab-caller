#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, GstVideo

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from scicall.control_panel import ControlPanel
from scicall.stream_pipeline import StreamPipeline
from scicall.util import get_cameras_list
from scicall.stream_settings import SourceMode, TranslateMode

class GstreamerDisplay(QWidget):
	def __init__(self):
		super().__init__()
		self.winid = self.winId()
		palette = QPalette()
		palette.setColor(QPalette.Window, Qt.black)
		self.setAutoFillBackground(True)
		self.setPalette(palette)

	def connect_to_sink(self, source):
		source.set_window_handle(self.winid)


class WorkZone(QWidget):
	def __init__(self):
		super().__init__()
		self.display = GstreamerDisplay()
		self.control_panel = ControlPanel()
		self.pipeline = StreamPipeline(self.display)
		self.main_layout = QHBoxLayout()
		self.main_layout.addWidget(self.display)
		self.main_layout.addWidget(self.control_panel)
		self.setLayout(self.main_layout)

		self.control_panel.enable_disable_button.clicked.connect(self.enable_disable_clicked)

		cameras = get_cameras_list()
		self.pipeline.source_text = cameras[0]
		self.control_panel.set_cameras_list(cameras)

	def source_type_changed(self, text):
		if text == "Test":
			self.pipeline.source_mode = SourceMode.TEST
		elif text == "Camera":
			self.pipeline.source_mode = SourceMode.CAMERA

	def source_changed(self, text):
		self.pipeline.source_text = text
		
	def enable_disable_clicked(self):
		print("enable_disable_button", self.pipeline.runned())
		if self.pipeline.runned():
			self.control_panel.unfreeze()
			self.stop_pipeline()
		else:
			self.control_panel.freeze()
			self.setup_pipeline()

	def setup_pipeline(self):
		input_settings = self.control_panel.input_settings()
		translation_settings = self.control_panel.translation_settings()
		self.pipeline.make_pipeline(input_settings, translation_settings)
		self.pipeline.setup()
		self.pipeline.start()

	def stop_pipeline(self):
		self.pipeline.stop()

class MultiWorkZone(QWidget):
	def __init__(self):
		super().__init__()
		self.zones = []
		self.layout = QHBoxLayout()
		self.setLayout(self.layout)

	def add_zone(self):
		zone = WorkZone()
		self.zones.append(zone)
		self.layout.addWidget(zone)

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.workzone = MultiWorkZone()
		self.workzone.add_zone()
		self.workzone.add_zone()
		self.setGeometry(100, 100, 640, 480)
		self.setCentralWidget(self.workzone)

def main():
	Gst.init(sys.argv)
	app = QApplication(sys.argv)
	window = MainWindow()
	#window.workzone.setup_pipeline()
	#window.workzone.start_pipeline()
	window.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()