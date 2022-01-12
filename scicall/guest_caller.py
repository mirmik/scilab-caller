from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class GuestCaller:
	def __init__(self):
		self.channelno = 0
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

		self.setLayout(self.main_layout)

	def video_clicked(self):
		pass

	def audio_clicked(self):
		pass