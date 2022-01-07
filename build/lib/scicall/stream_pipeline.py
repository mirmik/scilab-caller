import sys
from gi.repository import GObject, Gst, GstVideo

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from scicall.stream_settings import SourceMode, TranslateMode, CodecType, TransportType

class SourceBuilder:
	def __init__(self):
		self.video_width = 640
		self.video_height = 480
		self.framerate = 30

	def make(self, pipeline, settings):
		if settings.mode == SourceMode.TEST:
			self.source = Gst.ElementFactory.make("videotestsrc", "source")
			pipeline.add(self.source)
			self.sinklink = self.source
		elif settings.mode == SourceMode.CAMERA:
			self.source = self.make_videocam_source(pipeline, settings)
			self.capsfilter = self.source_capsfilter = self.make_source_capsfilter()
			pipeline.add(self.source)
			pipeline.add(self.capsfilter)
			self.source.link(self.capsfilter)
			self.sinklink = self.capsfilter
		elif settings.mode == SourceMode.STREAM:
			self.make_stream_source(pipeline, settings)

	def make_stream_source(self, pipeline, settings):
		self.make_transport(pipeline, settings)
		self.make_codec(pipeline, settings)
		self.transport_sink.link(self.codec_src)
		self.sinklink = self.codec_sink
		self.srclink = self.transport_src

	def make_videocam_source(self, pipeline, settings):
		if sys.platform == "linux":
			source = Gst.ElementFactory.make("v4l2src", "source")
			source.set_property("device", settings.device)
			return source
		elif sys.platform == "win32":
			source = Gst.ElementFactory.make("ksvideosrc", "source")
		else:
			raise Extension("platform is not supported")

	def make_mjpeg_codec(self, pipeline, settings):
		self.jpegparse = Gst.ElementFactory.make("jpegparse", None)
		self.jpegdec = Gst.ElementFactory.make("jpegdec", None)
		pipeline.add(self.jpegparse)
		pipeline.add(self.jpegdec)
		self.jpegparse.link(self.jpegdec)
		self.codec_sink = self.jpegdec
		self.codec_src = self.jpegparse

	def make_codec(self, pipeline, settings):
		if settings.codec == CodecType.MJPEG:
			self.make_mjpeg_codec(pipeline, settings)		

	def make_transport(self, pipeline, settings):
		if settings.transport == TransportType.SRT:
			self.make_srt_stream(pipeline, settings)
		if settings.transport == TransportType.UDP:
			self.make_udp_stream(pipeline, settings)
		if settings.transport == TransportType.RTPUDP:
			self.make_rtpudp_stream(pipeline, settings)

	def make_srt_stream(self, pipeline, settings):
		self.srtsrc = Gst.ElementFactory.make("srtsrc", None)
		self.srtsrc.set_property('uri', "srt://:10020")
		self.srtsrc.set_property('wait-for-connection', False)
		pipeline.add(self.srtsrc)
		self.transport_sink = self.srtsrc
		self.transport_src = self.srtsrc

	def make_udp_stream(self, pipeline, settings):
		self.udpsrc = Gst.ElementFactory.make("udpsrc", None)
		self.udpsrc.set_property('port', 10020)
		pipeline.add(self.udpsrc)
		self.transport_sink = self.udpsrc
		self.transport_src = self.udpsrc

	def make_rtpudp_stream(self, pipeline, settings):
		self.udpsrc = Gst.ElementFactory.make("udpsrc", None)
		self.q = Gst.ElementFactory.make("queue", None)
		caps = Gst.Caps.from_string("application/x-rtp, encoding-name=JPEG,payload=26")
		self.capsfilter = Gst.ElementFactory.make('capsfilter', None)
		self.capsfilter.set_property("caps", caps)
		self.rtpjpegdepay = Gst.ElementFactory.make("rtpjpegdepay", None)
		self.udpsrc.set_property('port', 10020)
		pipeline.add(self.udpsrc)
		pipeline.add(self.rtpjpegdepay)
		pipeline.add(self.q)
		pipeline.add(self.capsfilter)
		self.udpsrc.link(self.capsfilter)
		self.capsfilter.link(self.rtpjpegdepay)
		self.rtpjpegdepay.link(self.q)
		self.transport_sink = self.q
		self.transport_src = self.udpsrc

	def make_source_capsfilter(self):
		caps = Gst.Caps.from_string(
			f'video/x-raw,width={self.video_width},height={self.video_height},framerate={self.framerate}/1') 
		capsfilter = Gst.ElementFactory.make('capsfilter', None)
		capsfilter.set_property("caps", caps)
		return capsfilter

class TranslationBuilder:
	def make_srt_stream(self, pipeline, settings):
		self.srtsink = Gst.ElementFactory.make("srtsink", None)
		self.srtsink.set_property('uri', "srt://192.168.1.240:10020")
		self.srtsink.set_property('wait-for-connection', False)
		pipeline.add(self.srtsink)
		self.transport_sink = self.srtsink
		self.transport_src = self.srtsink

	def make_udp_stream(self, pipeline, settings):
		self.udpsink = Gst.ElementFactory.make("udpsink", None)
		self.udpsink.set_property('port', 10020)
		self.udpsink.set_property('host', "127.0.0.1")
		pipeline.add(self.udpsink)
		self.transport_sink = self.udpsink
		self.transport_src = self.udpsink

	def make_rtpudp_stream(self, pipeline, settings):
		self.udpsink = Gst.ElementFactory.make("udpsink", None)
		self.udpsink.set_property('port', 10020)
		self.udpsink.set_property('host', "127.0.0.1")
		self.rtpjpegpay = Gst.ElementFactory.make("rtpjpegpay", None)
		pipeline.add(self.udpsink)
		pipeline.add(self.rtpjpegpay)
		self.rtpjpegpay.link(self.udpsink)
		self.transport_sink = self.udpsink
		self.transport_src = self.rtpjpegpay

	def make_mjpeg_codec(self, pipeline, settings):
		self.jpegenc = Gst.ElementFactory.make("jpegenc", None)
		self.jpegenc.set_property('quality', 50)
		pipeline.add(self.jpegenc)
		self.codec_sink = self.jpegenc
		self.codec_src = self.jpegenc

	def make_codec(self, pipeline, settings):
		if settings.codec == CodecType.MJPEG:
			self.make_mjpeg_codec(pipeline, settings)		

	def make_transport(self, pipeline, settings):
		if settings.transport == TransportType.SRT:
			self.make_srt_stream(pipeline, settings)
		if settings.transport == TransportType.UDP:
			self.make_udp_stream(pipeline, settings)
		if settings.transport == TransportType.RTPUDP:
			self.make_rtpudp_stream(pipeline, settings)

	def make_stream(self, pipeline, settings):
		self.make_codec(pipeline, settings)
		self.make_transport(pipeline, settings)
		self.codec_sink.link(self.transport_src)
		self.sinklink = self.transport_sink
		self.srclink = self.codec_src
		
	def make(self, pipeline, settings):
		if settings.mode == TranslateMode.NOTRANS:
			self.srclink = Gst.ElementFactory.make("fakesink", None)
			pipeline.add(self.srclink)
			return

		elif settings.mode == TranslateMode.STREAM:
			self.make_stream(pipeline, settings)

		elif settings.mode == TranslateMode.STATION:
			msgBox = QMessageBox()
			msgBox.setWindowTitle("Неоконченное строительство");
			msgBox.setText("Режим автоматического согласования портов в разработке.");
			msgBox.exec();
			self.srclink = Gst.ElementFactory.make("fakesink", None)
			pipeline.add(self.srclink)
			return	

class StreamPipeline:
	def __init__(self, display_widget):
		self.display_widget = display_widget
		self.pipeline = None
		self.sink_width = 320
		display_widget.setFixedWidth(self.sink_width)

	def make_feedback_capsfilter(self):
		caps = Gst.Caps.from_string(f"video/x-raw,width={self.sink_width},height={240}") 
		capsfilter = Gst.ElementFactory.make('capsfilter', None)
		capsfilter.set_property("caps", caps)
		return capsfilter

	def make_pipeline(self, input_settings, translation_settings):
		self.last_input_settings = input_settings
		self.last_translation_settings = translation_settings

		self.pipeline = Gst.Pipeline()
		self.source_builder = SourceBuilder()
		self.translation_builder = TranslationBuilder()

		self.source_builder.make(self.pipeline, input_settings)
		self.translation_builder.make(self.pipeline, translation_settings)

		self.tee = Gst.ElementFactory.make("tee", None)
		self.videoscale = Gst.ElementFactory.make("videoscale", None)
		self.videoconvert = Gst.ElementFactory.make("videoconvert", None)
		self.sink = Gst.ElementFactory.make("autovideosink", None)
		self.sink_capsfilter = self.make_feedback_capsfilter()

		self.queue1 = Gst.ElementFactory.make("queue", "q1")
		self.queue2 = Gst.ElementFactory.make("queue", "q2")

		self.pipeline.add(self.tee)
		self.pipeline.add(self.videoscale)
		self.pipeline.add(self.videoconvert)
		self.pipeline.add(self.sink_capsfilter)
		self.pipeline.add(self.sink)
		self.pipeline.add(self.queue1)
		self.pipeline.add(self.queue2)

		self.source_builder.sinklink.link(self.tee)
		self.tee.link(self.queue1)
		self.queue1.link(self.videoscale)

		if self.translation_builder.srclink is not None:
			self.tee.link(self.queue2)
			self.queue2.link(self.translation_builder.srclink)

		self.videoscale.link(self.videoconvert)
		self.videoconvert.link(self.sink_capsfilter)
		self.sink_capsfilter.link(self.sink)

	def runned(self):
		return self.pipeline is not None

	def bus_callback(self, bus, msg):
		print("bus_callback", msg.parse_error())

	def setup(self):
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
		print("on_sync_message")
		if msg.get_structure().get_name() == 'prepare-window-handle':
			self.display_widget.connect_to_sink(msg.src)

	def stop(self):
		if self.pipeline:
			self.pipeline.set_state(Gst.State.NULL)
		self.pipeline = None

	def eos_handle(self, bus, msg):
		print("EOS handle")
		self.stop()
		self.make_pipeline(self.last_input_settings, self.last_translation_settings)
		self.setup()
		self.start()
    