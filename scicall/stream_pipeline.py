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

class SourceTransportBuilder:
	def make(self, pipeline, settings):
		builders = {
			TransportType.SRT: self.srt,
			TransportType.SRTREMOTE: self.srt_remote,
			TransportType.UDP: self.udp,
			TransportType.RTPUDP: self.rtpudp
		}
		return builders[settings.transport](pipeline, settings)
		
	def srt(self, pipeline, settings):
		srtsrc = Gst.ElementFactory.make("srtsrc", None)
		srtsrc.set_property('uri', f"srt://:{settings.port}")
		srtsrc.set_property('wait-for-connection', False)
		pipeline.add(srtsrc)
		return (srtsrc, srtsrc)

	def srt_remote(self, pipeline, settings):
		srtsrc = Gst.ElementFactory.make("srtsrc", None)
		srtsrc.set_property('uri', f"srt://{settings.ip}:{settings.port}")
		srtsrc.set_property('wait-for-connection', False)
		pipeline.add(srtsrc)
		return (srtsrc, srtsrc)

	def udp(self, pipeline, settings):
		udpsrc = Gst.ElementFactory.make("udpsrc", None)
		udpsrc.set_property('port', settings.port)
		pipeline.add(udpsrc)
		return (udpsrc, udpsrc)

	def rtpudp(self, pipeline, settings):
		udpsrc = Gst.ElementFactory.make("udpsrc", None)
		q = Gst.ElementFactory.make("queue", None)
		caps = Gst.Caps.from_string("application/x-rtp, encoding-name=JPEG,payload=26")
		capsfilter = Gst.ElementFactory.make('capsfilter', None)
		capsfilter.set_property("caps", caps)
		rtpjpegdepay = Gst.ElementFactory.make("rtpjpegdepay", None)
		udpsrc.set_property('port', settings.port)
		pipeline.add(udpsrc)
		pipeline.add(rtpjpegdepay)
		pipeline.add(q)
		pipeline.add(capsfilter)
		udpsrc.link(capsfilter)
		capsfilter.link(rtpjpegdepay)
		rtpjpegdepay.link(q)
		return (q, udpsrc)

class SourceCodecBuilder:
	def make(self, pipeline, settings):
		if settings.codec == VideoCodecType.MJPEG:
			return self.mjpeg_codec(pipeline, settings)		

	def mjpeg_codec(self, pipeline, settings):
		jpegparse = Gst.ElementFactory.make("jpegparse", None)
		jpegdec = Gst.ElementFactory.make("jpegdec", None)
		pipeline.add(jpegparse)
		pipeline.add(jpegdec)
		jpegparse.link(jpegdec)
		return (jpegparse, jpegdec)

class SourceBuilder:
	def __init__(self):
		self.video_width = 640
		self.video_height = 480
		self.framerate = 30

	def make(self, pipeline, settings):
		builders = {
			SourceMode.TEST: self.test,
			SourceMode.CAPTURE: self.capture,
			SourceMode.STREAM: self.stream,
		}
		return builders[settings.mode](pipeline, settings)

	def test(self, pipeline, settings):
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
		
	def capture(self, pipeline, settings):
		if sys.platform == "linux":
			source = Gst.ElementFactory.make("v4l2src", "source")
			source.set_property("device", settings.device)
			pipeline.add(source)
			return source, source
		elif sys.platform == "win32":
			source = Gst.ElementFactory.make("ksvideosrc", "source")
			pipeline.add(source)
			return source, source
		else:
			raise Extension("platform is not supported")

	#def make_source_capsfilter(self):
	#	caps = Gst.Caps.from_string(
	#		f'video/x-raw,width={self.video_width},height={self.video_height},framerate={self.framerate}/1') 
	#	capsfilter = Gst.ElementFactory.make('capsfilter', None)
	#	capsfilter.set_property("caps", caps)
	#	return capsfilter

class TranslationTransportBuilder:
	def make(self, pipeline, settings):
		builders = {
			TransportType.SRT: self.srt,
			TransportType.SRTREMOTE: self.srt_remote,
			TransportType.UDP: self.udp,
			TransportType.RTPUDP: self.rtpudp
		}
		return builders[settings.transport](pipeline, settings)

	def srt(self, pipeline, settings):
		srtsink = Gst.ElementFactory.make("srtsink", None)
		srtsink.set_property('uri', f"srt://:{settings.port}")
		srtsink.set_property('wait-for-connection', False)
		pipeline.add(srtsink)
		return srtsink, srtsink
		
	def srt_remote(self, pipeline, settings):
		srtsink = Gst.ElementFactory.make("srtsink", None)
		srtsink.set_property('uri', f"srt://{settings.ip}:{settings.port}")
		srtsink.set_property('wait-for-connection', False)
		pipeline.add(srtsink)
		return srtsink, srtsink

	def udp(self, pipeline, settings):
		udpsink = Gst.ElementFactory.make("udpsink", None)
		udpsink.set_property('port', settings.port)
		udpsink.set_property('host', settings.ip)
		pipeline.add(udpsink)
		return udpsink, udpsink

	def rtpudp(self, pipeline, settings):
		udpsink = Gst.ElementFactory.make("udpsink", None)
		udpsink.set_property('port', settings.port)
		udpsink.set_property('host', settings.ip)
		rtpjpegpay = Gst.ElementFactory.make("rtpjpegpay", None)
		pipeline.add(udpsink)
		pipeline.add(rtpjpegpay)
		rtpjpegpay.link(udpsink)
		return rtpjpegpay, udpsink


class TranslateCodecBuilder:
	def make(self, pipeline, settings):
		if settings.codec == VideoCodecType.MJPEG:
			return self.mjpeg_codec(pipeline, settings)		

	def mjpeg_codec(self, pipeline, settings):
		jpegenc = Gst.ElementFactory.make("jpegenc", None)
		jpegenc.set_property('quality', 50)
		pipeline.add(jpegenc)
		return (jpegenc, jpegenc)

class TranslationBuilder:
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
		codec_src, codec_sink = TranslateCodecBuilder().make(pipeline, settings)
		trans_src, trans_sink = TranslationTransportBuilder().make(pipeline, settings)
		codec_sink.link(trans_src)
		return codec_src, trans_sink

	def station(self, pipeline, settings):
		msgBox = QMessageBox()
		msgBox.setWindowTitle("Неоконченное строительство");
		msgBox.setText("Режим автоматического согласования портов в разработке.");
		msgBox.exec();
		return self.fake()

class StreamPipeline:
	def __init__(self, display_widget):
		self.display_widget = display_widget
		self.pipeline = None
		self.sink_width = 320
		display_widget.setFixedWidth(self.sink_width)

	def make_video_feedback_capsfilter(self):
		caps = Gst.Caps.from_string(f"video/x-raw,width={self.sink_width},height={240}") 
		capsfilter = Gst.ElementFactory.make('capsfilter', None)
		capsfilter.set_property("caps", caps)
		return capsfilter

	def make_audio_pipeline(self, input_settings, translation_settings):
		print("make_audio_pipeline")
		tee = Gst.ElementFactory.make("tee", None)
		sink = Gst.ElementFactory.make("autoaudiosink", None)
		queue1 = Gst.ElementFactory.make("queue", "q1")
		queue2 = Gst.ElementFactory.make("queue", "q2")
		
		self.pipeline.add(tee)
		self.pipeline.add(sink)
		self.pipeline.add(queue1)
		self.pipeline.add(queue2)
		
		self.source_sink.link(tee)
		tee.link(queue1)
		
		if self.output_src is not None:
			tee.link(queue2)
			queue2.link(self.output_src)

		#if self.translation_builder.srclink is not None:
		#	self.tee.link(self.queue2)
		#	self.queue2.link(self.translation_builder.srclink)
		queue1.link(sink)

	def make_video_pipeline(self, input_settings, translation_settings):
		tee = Gst.ElementFactory.make("tee", None)
		videoscale = Gst.ElementFactory.make("videoscale", None)
		videoconvert = Gst.ElementFactory.make("videoconvert", None)
		sink = Gst.ElementFactory.make("autovideosink", None)
		sink_capsfilter = self.make_video_feedback_capsfilter()

		queue1 = Gst.ElementFactory.make("queue", "q1")
		queue2 = Gst.ElementFactory.make("queue", "q2")

		self.pipeline.add(tee)
		self.pipeline.add(videoscale)
		self.pipeline.add(videoconvert)
		self.pipeline.add(sink_capsfilter)
		self.pipeline.add(sink)
		self.pipeline.add(queue1)
		self.pipeline.add(queue2)

		self.source_sink.link(tee)
		tee.link(queue1)
		queue1.link(videoscale)

		if self.output_src is not None:
			tee.link(queue2)
			queue2.link(self.output_src)

		videoscale.link(videoconvert)
		videoconvert.link(sink_capsfilter)
		sink_capsfilter.link(sink)

	def make_pipeline(self, input_settings, translation_settings):
		assert input_settings.mediatype == translation_settings.mediatype

		self.last_input_settings = input_settings
		self.last_translation_settings = translation_settings

		self.pipeline = Gst.Pipeline()
		srcsrc, srcsink = SourceBuilder().make(self.pipeline, input_settings)
		outsrc, outsink = TranslationBuilder().make(self.pipeline, translation_settings)
		self.source_sink = srcsink
		self.output_src = outsrc

		if input_settings.mediatype == MediaType.VIDEO:
			return self.make_video_pipeline(input_settings, translation_settings)
		elif input_settings.mediatype == MediaType.AUDIO:
			return self.make_audio_pipeline(input_settings, translation_settings)

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
		if msg.get_structure().get_name() == 'prepare-window-handle':
			self.display_widget.connect_to_sink(msg.src)

	def stop(self):
		if self.pipeline:
			self.pipeline.set_state(Gst.State.NULL)
		self.pipeline = None

	def eos_handle(self, bus, msg):
		self.stop()
		self.make_pipeline(self.last_input_settings, self.last_translation_settings)
		self.setup()
		self.start()
    