#!/usr/bin/env python3
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *

import gi
import os
import time
import sys
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, GstVideo

class GstreamerDisplay(QWidget):
	""" Виджет, в котором рисует выходной элемент видоконвеера """

	def __init__(self):
		super().__init__()
		self.winid = self.winId()
		palette = QPalette()
		palette.setColor(QPalette.Window, Qt.black)
		self.setAutoFillBackground(True)
		self.setPalette(palette)
		self.setFixedSize(160,240)

	def connect_to_sink(self, source):
		source.set_window_handle(self.winid)

	def on_sync_message(self, bus, msg):
		if msg.get_structure().get_name() == 'prepare-window-handle':
			self.connect_to_sink(msg.src)

app = QApplication(sys.argv)        
strm = GstreamerDisplay()

Gst.init(sys.argv)
pipeline=Gst.parse_launch("videotestsrc ! autovideosink")
pipeline.set_state(Gst.State.PLAYING)
bus = pipeline.get_bus()
bus.add_signal_watch()
bus.enable_sync_message_emission()
bus.connect('sync-message::element', strm.on_sync_message)
		
strm.show()
app.exec()