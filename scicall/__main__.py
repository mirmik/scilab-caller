#!/usr/bin/env python3

import gi
import os
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, GstVideo

from scicall.stream_settings import SourceMode, TranslateMode, MediaType
from scicall.util import get_filtered_devices_list, start_device_monitor, stop_device_monitor
from scicall.stream_pipeline import StreamPipeline
from scicall.control_panel import ControlPanel
from scicall.guest_caller import GuestCaller
from scicall.guest_controller import ConnectionController, ConnectionControllerZone
from scicall.interaptor import Interaptor
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from enum import Enum
import traceback
import sys
from scicall.finisher import setup_interrupt_handlers, invoke_destructors

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


class WorkZone(QWidget):
    """ Контроллер одного потока.

            @mediatype - определяет тип контроллера - аудио/видео.
    """

    def __init__(self, mediatype):
        super().__init__()

        if mediatype == MediaType.VIDEO:
            self.display = GstreamerDisplay()
        else:
            self.display = GstreamerDisplay()

        self.control_panel = ControlPanel(mediatype)
        self.pipeline = StreamPipeline(self.display)
        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.display)
        self.main_layout.addWidget(self.control_panel)
        self.setLayout(self.main_layout)
        self.control_panel.enable_disable_button.clicked.connect(
            self.enable_disable_clicked)

        captures = get_filtered_devices_list(mediatype)
        self.control_panel.set_devices_list(captures)

    def enable_disable_clicked(self):
        """ По активации кнопки происходит компиляция данных панели управления и
                запускается строительство конвеера. Деактивация уничтожает конвеер.
        """

        if self.pipeline.runned():
            self.control_panel.unfreeze()
            self.stop_pipeline()
        else:
            self.control_panel.freeze()
            self.setup_pipeline()

    def setup_pipeline(self):
        input_settings = self.control_panel.input_settings()
        translation_settings = self.control_panel.translation_settings()
        display_settings = self.control_panel.display_settings()
        try:
            self.pipeline.make_pipeline(
                input_settings, translation_settings, display_settings)
            self.pipeline.setup()
            self.pipeline.start()
        except Exception as ex:
            traceback.print_exc()
            msgBox = QMessageBox()
            msgBox.setText("Запуск конвеера привёл к исключению:\r\n" +
                           traceback.format_exc())
            msgBox.exec()

    def stop_pipeline(self):
        try:
            self.pipeline.stop()
        except Exception as ex:
            traceback.print_exc()
            msgBox = QMessageBox()
            msgBox.setText("Остановка конвеера привела к исключению:\r\n" +
                           traceback.format_exc())
            msgBox.exec()


class MultiWorkZone(QWidget):
    """Рабочая зона состоит из набора однотпных пар аудио/видео контроллеров"""

    def __init__(self):
        super().__init__()
        self.zones = []
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

    def add_zone(self):
        zone_video = WorkZone(MediaType.VIDEO)
        zone_audio = WorkZone(MediaType.AUDIO)
        peer_layout = QVBoxLayout()
        peer_layout.addWidget(zone_video)
        peer_layout.addWidget(zone_audio)
        self.zones.append(zone_video)
        self.zones.append(zone_audio)
        self.layout.addLayout(peer_layout)

class ExpertWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.workzone = MultiWorkZone()
        self.workzone.add_zone()
        self.workzone.add_zone()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.workzone)
        self.setLayout(self.layout)

class Container(QWidget):
    def __init__(self, wdg):
        super().__init__()    
        self.vlayout = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.hlayout.addStretch()
        self.hlayout.addWidget(wdg)
        self.hlayout.addStretch()
        self.vlayout.addStretch()
        self.vlayout.addLayout(self.hlayout)
        self.vlayout.addStretch()
        self.setLayout(self.vlayout)


class CentralWidget(QTabWidget):
    need_resize = pyqtSignal()

    def __init__(self):
        super().__init__()    	
        self.userwdg = GuestCaller()
        self.stantionwdg= ConnectionControllerZone()
        self.experwdg = ExpertWidget()
        self.addTab(Container(self.userwdg), "Гость")
        self.addTab(Container(self.stantionwdg), "Сервер")
        self.addTab(Container(self.experwdg), "Тестовый")

class MainWindow(QMainWindow):
    """Главное окно"""

    def __init__(self):
        super().__init__()
        
        start_device_monitor()  # Монитор необходим, чтобы работали запросы списков устройств
        self.cw = CentralWidget()
        stop_device_monitor()

        self.setCentralWidget(self.cw)
        self.cw.need_resize.connect(self.need_resize_handle)

    def need_resize_handle(self):
        self.setFixedSize(self.minimumSizeHint())
        self.adjustSize()

    def closeEvent(self, event):
        #invoke_destructors()
        os._exit(0)
        pass

def srt_disconnect():
    print("SRT_DISCONNECT")

def main():
    Gst.init(sys.argv)
    #Gst.debug_set_active(True)
    #Gst.debug_set_default_threshold(3)
    #GObject.threads_init()

    #setup_interrupt_handlers()
    #Interaptor.instance().start_listen()
    #Interaptor.instance().srt_disconnect.connect(srt_disconnect)

    app = QApplication(sys.argv)
    app.quitOnLastWindowClosed = False
    window = MainWindow()
    window.show()
    return sys.exit(app.exec())


if __name__ == '__main__':
    main()
