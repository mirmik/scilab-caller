#!/usr/bin/env python3

import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, GstVideo
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from abc import ABC, abstractmethod
from enum import Enum

from scicall.util import get_cameras_list

class SourceMode:
	TEST = 1
	CAMERA = 2

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

class ControlPanel(QWidget):
	def __init__(self):
		super().__init__()
		self.source_type_list = QComboBox()
		self.source_list = QComboBox()
		self.enable_disable_button = QPushButton('Enable/Disable')
		self.source_type_list.addItems(["Camera", "Test"])
		self.layout = QVBoxLayout()
		self.layout.addWidget(self.source_type_list)
		self.layout.addWidget(self.source_list)
		self.layout.addWidget(self.enable_disable_button)
		self.layout.addStretch()
		self.setLayout(self.layout)

		self.items = [
			self.source_list,
			self.source_type_list
		]

	def freeze(self):
		for item in self.items:
			item.setEnabled(False)

	def unfreeze(self):
		for item in self.items:
			item.setEnabled(True)

	def set_cameras_list(self, cameras):
		self.source_list.addItems(cameras)


class StreamPipeline:
	def __init__(self, display_widget):
		self.display_widget = display_widget
		self.pipeline = None
		self.source_mode = SourceMode.CAMERA
		self.source_text = ""
		self.video_width = 640
		self.sink_width = 320
		self.video_height = 480
		self.framerate = 30
		display_widget.setFixedWidth(self.sink_width)

	def make_source(self):
		if self.source_mode == SourceMode.TEST:
			return Gst.ElementFactory.make("videotestsrc", "source")
		elif self.source_mode == SourceMode.CAMERA:
			return self.make_videocam_source()

	def make_videocam_source(self):
		if sys.platform == "linux":
			source = Gst.ElementFactory.make("v4l2src", "source")
			source.set_property("device", self.source_text)
			return source
		else:
			raise Extension("platform is not supported")

	def make_source_capsfilter(self):
		caps = Gst.Caps.from_string(
			f'video/x-raw,width={self.video_width},height={self.video_height},framerate={self.framerate}/1') 
		capsfilter = Gst.ElementFactory.make('capsfilter', None)
		capsfilter.set_property("caps", caps)
		return capsfilter

	def make_feedback_capsfilter(self):
		caps = Gst.Caps.from_string(f"video/x-raw,width={self.sink_width},height={240}") 
		capsfilter = Gst.ElementFactory.make('capsfilter', None)
		capsfilter.set_property("caps", caps)
		return capsfilter

	def make_pipeline(self):
		self.pipeline = Gst.Pipeline()
		self.source = self.make_source()
		self.source_capsfilter = self.make_source_capsfilter()
		self.videoscale = Gst.ElementFactory.make("videoscale", None)
		self.videoconvert = Gst.ElementFactory.make("videoconvert", None)
		self.sink_capsfilter = self.make_feedback_capsfilter()
		self.sink = Gst.ElementFactory.make("autovideosink", None)

		self.pipeline.add(self.source)
		self.pipeline.add(self.source_capsfilter)
		self.pipeline.add(self.videoscale)
		self.pipeline.add(self.videoconvert)
		self.pipeline.add(self.sink_capsfilter)
		self.pipeline.add(self.sink)

		self.source.link(self.source_capsfilter)
		self.source_capsfilter.link(self.videoscale)
		self.videoscale.link(self.videoconvert)
		self.videoconvert.link(self.sink_capsfilter)
		self.sink_capsfilter.link(self.sink)

	def runned(self):
		return self.pipeline is not None

	def setup(self):
		self.state = Gst.State.NULL

		if not self.pipeline or not self.source or not self.videoconvert or not self.sink:
			print("ERROR: Not all elements could be created")
			sys.exit(1)

		# instruct the bus to emit signals for each received message
		# and connect to the interesting signals
		self.bus = self.pipeline.get_bus()

		self.bus.add_signal_watch()
		self.bus.enable_sync_message_emission()
		self.bus.connect('sync-message::element', self.on_sync_message)

	def start(self):
		self.pipeline.set_state(Gst.State.PLAYING)
		
	def on_sync_message(self, bus, msg):
		print("on_sync_message")
		if msg.get_structure().get_name() == 'prepare-window-handle':
			self.display_widget.connect_to_sink(msg.src)

	def stop(self):
		self.pipeline.set_state(Gst.State.NULL)
		self.pipeline = None

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
		self.control_panel.source_type_list.currentTextChanged.connect(self.source_type_changed)
		self.control_panel.source_list.currentTextChanged.connect(self.source_changed)
		self.control_panel.setFixedWidth(165)

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
			self.start_pipeline()

	def setup_pipeline(self):
		self.pipeline.make_pipeline()
		self.pipeline.setup()

	def start_pipeline(self):
		self.pipeline.start()

	def stop_pipeline(self):
		self.pipeline.stop()


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.workzone = WorkZone()
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