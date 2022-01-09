import sys
from gi.repository import GObject, Gst, GstVideo

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from scicall.stream_settings import (
    SourceMode,
    TranslateMode,
    VideoCodecType,
    AudioCodecType,
    TransportType,
    MediaType
)

from scicall.stream_transport import SourceTransportBuilder, TranslationTransportBuilder
from scicall.stream_codec import SourceCodecBuilder, TranslationCodecBuilder


class SourceBuilder:
    """ Строитель входного каскада. 

            В зависимости от типа @settings.mode, строит разные типы входных каскадов. 
    """

    def __init__(self):
        self.video_width = 640
        self.video_height = 480
        self.framerate = 30

    def make(self, pipeline, settings):
        builders = {
            SourceMode.TEST: self.test_source,
            SourceMode.CAPTURE: self.capture,
            SourceMode.STREAM: self.stream,
        }
        return builders[settings.mode](pipeline, settings)

    def test_source(self, pipeline, settings):
        source = Gst.ElementFactory.make({
            MediaType.VIDEO: "videotestsrc",
            MediaType.AUDIO: "audiotestsrc"
        }[settings.mediatype], None)
        pipeline.add(source)
        return source, source

    def stream(self, pipeline, settings):
        trans_src, trans_sink = SourceTransportBuilder().make(pipeline, settings)
        codec_src, codec_sink = SourceCodecBuilder().make(pipeline, settings)
        trans_sink.link(codec_src)
        return trans_src, codec_sink

    def capture_video_linux(self, pipeline, settings):
        source = settings.device.make_gst_element()
        capsfilter = self.make_source_capsfilter()
        pipeline.add(source)
        pipeline.add(capsfilter)
        source.link(capsfilter)
        return source, capsfilter

    def capture_audio_linux(self, pipeline, settings):
        source = settings.device.make_gst_element()
        pipeline.add(source)
        return source, source

    def capture_video_windows(self, pipeline, settings):
        source = settings.device.make_gst_element()
        #Gst.ElementFactory.make("mfvideosrc", None)
        #capsfilter = self.make_source_capsfilter()
        #source.set_property("device", settings.device)
        pipeline.add(source)
        # pipeline.add(capsfilter)
        # source.link(capsfilter)
        return source, source

    def capture_audio_windows(self, pipeline, settings):
        source = settings.device.make_gst_element()
        #Gst.ElementFactory.make("wasapisrc", None)
        #source.set_property("device", settings.device)
        pipeline.add(source)
        return source, source

    def capture(self, pipeline, settings):
        if sys.platform == "linux":
            return{
                MediaType.VIDEO: self.capture_video_linux,
                MediaType.AUDIO: self.capture_audio_linux
            }[settings.mediatype](pipeline, settings)
        elif sys.platform == "win32":
            return{
                MediaType.VIDEO: self.capture_video_windows,
                MediaType.AUDIO: self.capture_audio_windows
            }[settings.mediatype](pipeline, settings)
        else:
            raise Extension("platform is not supported")

    def make_source_capsfilter(self):
        caps = Gst.Caps.from_string(
            f'video/x-raw,width={self.video_width},height={self.video_height},framerate={self.framerate}/1')
        capsfilter = Gst.ElementFactory.make('capsfilter', None)
        capsfilter.set_property("caps", caps)
        return capsfilter


class TranslationBuilder:
    """ Строитель выходного каскада. 

            В зависимости от типа @settings.mode, строит разные типы выходных каскадов. 
    """

    def make(self, pipeline, settings):
        builders = {
            TranslateMode.NOTRANS: self.fake,
            TranslateMode.STATION: self.station,
            TranslateMode.STREAM: self.stream,
        }
        return builders[settings.mode](pipeline, settings)

    def fake(self, pipeline, settings):
        fakesink = Gst.ElementFactory.make("fakesink", None)
        pipeline.add(fakesink)
        return fakesink, fakesink

    def stream(self, pipeline, settings):
        codec_src, codec_sink = TranslationCodecBuilder().make(pipeline, settings)
        trans_src, trans_sink = TranslationTransportBuilder().make(pipeline, settings)
        codec_sink.link(trans_src)
        return codec_src, trans_sink

    def station(self, pipeline, settings):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Неоконченное строительство")
        msgBox.setText(
            "Режим автоматического согласования портов в разработке.")
        msgBox.exec()
        return self.fake(pipeline, settings)


class StreamPipeline:
    """Класс отвечает за строительство работы каскада gstreamer и инкапсулирует
            логику работы с ним.

            NB: Помимо объектов данного класса и подчинённых им объектов, 
            работа с конвеером и элементами ковеера не должна нигда происходить. 

            Схема конвеера:
            source_end --> tee --> queue --> translation_end
                            |
                             ----> queue --> videoscale --> videoconvert --> display_widget 
    """

    def __init__(self, display_widget):
        self.display_widget = display_widget
        self.pipeline = None
        self.sink_width = 320
        display_widget.setFixedWidth(self.sink_width)

    def make_video_feedback_capsfilter(self):
        """Создаёт capsfilter, определяющий, форматирование ответвления конвеера, идущего
        к контрольному видео виджету."""
        caps = Gst.Caps.from_string(
            f"video/x-raw,width={self.sink_width},height={240}")
        capsfilter = Gst.ElementFactory.make('capsfilter', None)
        capsfilter.set_property("caps", caps)
        return capsfilter

    def make_audio_middle_end(self, settings):
        pass

    def make_video_middle_end(self, settings):
        if settings.display_enabled:
            videoscale = Gst.ElementFactory.make("videoscale", None)
            videoconvert = Gst.ElementFactory.make("videoconvert", None)
            sink = Gst.ElementFactory.make("autovideosink", None)
            sink_capsfilter = self.make_video_feedback_capsfilter()
            self.pipeline.add(videoscale)
            self.pipeline.add(videoconvert)
            self.pipeline.add(sink_capsfilter)
            self.pipeline.add(sink)
            videoscale.link(videoconvert)
            videoconvert.link(sink_capsfilter)
            sink_capsfilter.link(sink)
            return (videoscale, sink)
        else:
            sink = Gst.ElementFactory.make("fakesink", None)
            self.pipeline.add(sink)
            return (sink, sink)

    def make_audio_middle_end(self, settings):
        if settings.display_enabled:
            convert = Gst.ElementFactory.make("audioconvert", None)
            sink = Gst.ElementFactory.make("autoaudiosink", None)
            self.pipeline.add(convert)
            self.pipeline.add(sink)
            convert.link(sink)
            return (convert, sink)
        else:
            sink = Gst.ElementFactory.make("fakesink", None)
            self.pipeline.add(sink)
            return (sink, sink)

    def link_pipeline(self):
        tee = Gst.ElementFactory.make("tee", None)

        queue1 = Gst.ElementFactory.make("queue", "q1")
        queue2 = Gst.ElementFactory.make("queue", "q2")

        self.pipeline.add(tee)
        self.pipeline.add(queue1)
        self.pipeline.add(queue2)

        self.source_sink.link(tee)
        tee.link(queue1)
        queue1.link(self.middle_src)

        if self.output_src is not None:
            tee.link(queue2)
            queue2.link(self.output_src)

    def make_pipeline(self, input_settings, translation_settings, middle_settings):
        assert input_settings.mediatype == translation_settings.mediatype

        self.last_input_settings = input_settings
        self.last_translation_settings = translation_settings

        self.pipeline = Gst.Pipeline()
        srcsrc, srcsink = SourceBuilder().make(self.pipeline, input_settings)
        outsrc, outsink = TranslationBuilder().make(self.pipeline, translation_settings)
        middle_src, middle_sink = {
            MediaType.VIDEO: self.make_video_middle_end,
            MediaType.AUDIO: self.make_audio_middle_end
        }[input_settings.mediatype](middle_settings)

        self.source_sink = srcsink
        self.output_src = outsrc
        self.middle_src = middle_src

        self.link_pipeline()

    def runned(self):
        return self.pipeline is not None

    def bus_callback(self, bus, msg):
        print("bus_callback", msg.parse_error())

    def setup(self):
        """Подготовка сконструированного конвеера к работе."""
        self.state = Gst.State.NULL
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.add_watch(0, self.bus_callback, None)
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.bus.connect('message::error', self.on_error_message)
        self.bus.connect("message::eos", self.eos_handle)

    def on_error_message(self, bus, msg):
        print("on_error_message", msg.parse_error())

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_sync_message(self, bus, msg):
        """Биндим контрольное изображение к переданному снаружи виджету."""
        if msg.get_structure().get_name() == 'prepare-window-handle':
            self.display_widget.connect_to_sink(msg.src)

    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None

    def eos_handle(self, bus, msg):
        """Конец потока вызывает пересборку конвеера.
           Это решает некоторые проблемы srt стрима.
        """
        self.stop()
        self.make_pipeline(self.last_input_settings,
                           self.last_translation_settings)
        self.setup()
        self.start()
