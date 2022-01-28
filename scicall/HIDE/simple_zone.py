from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from scicall.display import GstreamerDisplay


class SimpleZone(QWidget):
	def __init__(self):
		super().__init__()
		self.ip_lbl = QLabel("IP:")
		self.video_port_lbl = QLabel("Video port::")
		self.audio_port_lbl = QLabel("Audio port:")
		
		self.controllayout = QGridLayout()
		self.layout = QHBoxLayout()
		self.display = GstreamerDisplay()
		self.display.setFixedSize(320,240)
		self.layout.addWidget(self.display)
		self.setLayout(self.layout)
