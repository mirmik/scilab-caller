from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from scicall.stream_settings import (
	SourceStreamSettings, 
	TranslationStreamSettings, 
	SourceMode, 
	TranslateMode,
	TransportType,
	CodecType
)

class CommonControlPanel(QWidget):
	def __init__(self, modeenum, other_items):
		super().__init__()
		self.mode_list = QComboBox()
		self.mode_list.addItems(list(modeenum))
		self.mode_list.currentTextChanged.connect(self.mode_changed)
		self.items = other_items + [self.mode_list]
		self.set_mode(self.mode_list.currentText())

	def mode_changed(self):
		self.set_mode(self.mode_list.currentText())

	def hide_all(self):
		for item in self.items:
			item.setHidden(True)	

	def freeze(self):
		for item in self.items:
			item.setEnabled(False)

	def unfreeze(self):
		for item in self.items:
			item.setEnabled(True)	


class SourceControlPanel(CommonControlPanel):
	def __init__(self):
		self.device_list = QComboBox()
		self.transport_list = QComboBox()
		self.codec_list = QComboBox()
		self.transport_list.addItems(list(TransportType))
		self.codec_list.addItems(list(CodecType))
		self.target_ip = QLineEdit()
		self.target_port = QLineEdit()
		self.layout = QGridLayout()
		self.target_ip_label = QLabel("IP:")
		self.target_port_label = QLabel("Порт:")
		self.transport_label = QLabel("Транспорт:")
		self.codec_label = QLabel("Кодек:")
		self.target_ip.setText("127.0.0.1")
		self.target_port.setText("10020")

		items = [
			self.device_list,
			self.target_ip,
			self.target_port,
			self.target_port_label,
			self.target_ip_label,
			self.codec_list,
			self.transport_list,
			self.codec_label,
			self.transport_label,
		]

		super().__init__(SourceMode, items)
		self.layout.addWidget(self.mode_list, 0,0,1,2)
		self.layout.addWidget(self.device_list, 1,0,1,2)
		self.layout.addWidget(self.transport_list, 2,1)
		self.layout.addWidget(self.transport_label, 2,0)
		self.layout.addWidget(self.codec_list, 3,1)
		self.layout.addWidget(self.codec_label, 3,0)
		self.layout.addWidget(self.target_ip_label, 4,0)
		self.layout.addWidget(self.target_ip, 4,1)
		self.layout.addWidget(self.target_port_label, 5,0)
		self.layout.addWidget(self.target_port, 5,1)
		self.setLayout(self.layout)

	def set_mode(self, mode):
		self.hide_all()
		self.mode_list.setHidden(False)
		if mode == SourceMode.TEST:
			pass
		elif mode == SourceMode.CAMERA:
			self.device_list.setHidden(False)
		elif mode == SourceMode.STREAM:
			for el in [
				self.transport_list,
				self.codec_list,
				self.target_ip,
				self.target_port,
				self.target_ip_label,
				self.target_port_label,
				self.codec_label,
				self.transport_label
			]:
				el.setHidden(False)

	def set_devices_list(self, cameras):
		self.device_list.addItems(cameras)

	def settings(self):
		mode = self.mode_list.currentText()
		device = self.device_list.currentText()
		transport = self.transport_list.currentText()
		codec = self.codec_list.currentText()
		ip = self.target_ip.text()
		port = self.target_port.text()
		return SourceStreamSettings(
			mode=mode, 
			device=device,
			transport=transport,
			codec=codec,
			ip=ip,
			port=port)

class TranslationControlPanel(CommonControlPanel):
	def __init__(self):
		self.transport_list = QComboBox()
		self.codec_list = QComboBox()
		self.target_ip = QLineEdit()
		self.target_port = QLineEdit()
		self.transport_label = QLabel("Транспорт:")
		self.codec_label = QLabel("Кодек:")
		self.transport_list.addItems(list(TransportType))
		self.codec_list.addItems(list(CodecType))

		self.layout = QGridLayout()
		self.target_ip_label = QLabel("IP:")
		self.target_port_label = QLabel("Порт:")
		self.target_ip.setText("127.0.0.1")
		self.target_port.setText("10020")

		items = [
			self.transport_list,
			self.codec_list,
			self.target_ip,
			self.target_port,
			self.target_ip_label,
			self.target_port_label,
			self.codec_label,
			self.transport_label
		]

		super().__init__(TranslateMode, items)
		self.layout.addWidget(self.mode_list, 0, 0, 1, 2)
		self.layout.addWidget(self.transport_label, 1,0)
		self.layout.addWidget(self.transport_list, 1, 1)
		self.layout.addWidget(self.codec_list, 2, 1)
		self.layout.addWidget(self.codec_label, 2, 0)
		self.layout.addWidget(self.target_ip_label, 3,0)
		self.layout.addWidget(self.target_ip, 3,1)
		self.layout.addWidget(self.target_port_label, 4,0)
		self.layout.addWidget(self.target_port, 4,1)
		self.setLayout(self.layout)

	def set_mode(self, mode):
		self.hide_all()
		self.mode_list.setHidden(False)
		if mode == TranslateMode.NOTRANS:
			pass
		elif mode == TranslateMode.STREAM:
			for el in [
				self.transport_list,
				self.codec_list,
				self.target_ip,
				self.target_port,
				self.target_ip_label,
				self.target_port_label,
				self.codec_label,
				self.transport_label
			]:
				el.setHidden(False)

	def settings(self):
		mode = self.mode_list.currentText()
		transport = self.transport_list.currentText()
		codec = self.codec_list.currentText()
		ip = self.target_ip.text()
		port = self.target_port.text()
		return TranslationStreamSettings(
			mode=mode, 
			transport=transport,
			codec=codec,
			ip=ip,
			port=port)

class ControlPanel(QWidget):
	def __init__(self):
		super().__init__()
		self.enable_disable_button = QPushButton('Enable/Disable')

		self.input_control_panel = SourceControlPanel()
		self.input_frame = QGroupBox()
		self.input_frame.setTitle("Источник")
		self.input_layout = QVBoxLayout()
		self.input_layout.addWidget(self.input_control_panel)
		self.input_frame.setLayout(self.input_layout)

		self.translation_control_panel = TranslationControlPanel()
		self.translation_frame = QGroupBox()
		self.translation_frame.setTitle("Передача")
		self.translation_layout = QVBoxLayout()
		self.translation_layout.addWidget(self.translation_control_panel)
		self.translation_frame.setLayout(self.translation_layout)

		self.layout2 = QVBoxLayout()
		self.layout2.addWidget(self.input_frame)
		self.layout2.addWidget(self.translation_frame)
		self.layout2.addWidget(self.enable_disable_button)
		self.layout2.addStretch()
		self.setLayout(self.layout2)

		self.setFixedWidth(240)

	def set_cameras_list(self, cameras):
		self.input_control_panel.set_devices_list(cameras)

	def freeze(self):
		self.input_control_panel.freeze()
		self.translation_control_panel.freeze()

	def unfreeze(self):
		self.input_control_panel.unfreeze()
		self.translation_control_panel.unfreeze()

	def translation_settings(self):
		'''Формирует объект с параметрами выбранной передачи сигнала.'''
		return self.translation_control_panel.settings()

	def input_settings(self):
		'''Формирует объект с параметрами выбранного источника сигнала.'''
		return self.input_control_panel.settings()