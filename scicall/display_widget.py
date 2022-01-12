from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class GstreamerDisplay(QWidget):
	""" Виджет, в котором рисует выходной элемент видоконвеера """

	def __init__(self):
		super().__init__()
		self.winid = self.winId()
		palette = QPalette()
		palette.setColor(QPalette.Window, Qt.black)
		self.setAutoFillBackground(True)
		self.setPalette(palette)

	def connect_to_sink(self, source):
		source.set_window_handle(self.winid)