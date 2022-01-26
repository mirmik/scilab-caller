from gi.repository import GObject, Gst, GstVideo
from scicall.util import pipeline_chain

def make_tee_from_video(pipeline, videosrc):
    q=buffer_queue()
    tee = Gst.ElementFactory.make("tee", None)
    pipeline.add(tee)
    pipeline.add(q)
    q.link(tee)
    videosrc.link(q)
    return tee

def make_tee_from_audio(pipeline, audiosrc):
    q=buffer_queue()
    tee = Gst.ElementFactory.make("tee", None)
    pipeline.add(tee)
    pipeline.add(q)
    q.link(tee)
    audiosrc.link(q)
    return tee

def buffer_queue():
    q = Gst.ElementFactory.make("queue", None)
    q.set_property("max-size-bytes", 100000) 
    q.set_property("max-size-buffers", 0) 
    return q

def make_video_feedback_capsfilter(width, height):
    """Создаёт capsfilter, определяющий, форматирование ответвления конвеера, идущего
    к контрольному видео виджету."""
    caps = Gst.Caps.from_string(
        f"video/x-raw,width={width},height={height}")
    capsfilter = Gst.ElementFactory.make('capsfilter', None)
    capsfilter.set_property("caps", caps)
    return capsfilter


def display_video_from_tee(pipeline, tee):
    q = buffer_queue()
    videoscale = Gst.ElementFactory.make("videoscale", None)
    videoconvert = Gst.ElementFactory.make("videoconvert", None)
    sink = Gst.ElementFactory.make("autovideosink", None)
    sink.set_property("sync", False)
    sink_capsfilter = make_video_feedback_capsfilter(320, 240)
    pipeline_chain(pipeline, q, videoscale, videoconvert, sink_capsfilter, sink)
    tee.link(q)

def display_specter_from_tee(pipeline, tee):
    q = buffer_queue()
    convert = Gst.ElementFactory.make("audioconvert", None)
    spectrascope = Gst.ElementFactory.make("spectrascope", None)
    vconvert = Gst.ElementFactory.make("videoconvert", None)
    sink = Gst.ElementFactory.make("autovideosink", None)
    sink_capsfilter = make_video_feedback_capsfilter(320, 240)
    pipeline_chain(pipeline, q, convert, spectrascope, vconvert, sink_capsfilter, sink)
    tee.link(q)

def h264_encode_from_tee(pipeline, tee):
    q = buffer_queue()
    vconvert = Gst.ElementFactory.make("videoconvert", None)
    h264 = Gst.ElementFactory.make("x264enc", None)
    h264.set_property('tune', "zerolatency")
    pipeline_chain(pipeline, q, vconvert, h264)
    tee.link(q)
    return h264

def opus_encode_from_tee(pipeline, tee):
    q = buffer_queue()
    vconvert = Gst.ElementFactory.make("audioconvert", None)
    opus = Gst.ElementFactory.make("opusenc", None)
    pipeline_chain(pipeline, q, vconvert, opus)
    tee.link(q)
    return opus

def mpeg_combine(pipeline, inputs):
    mpeg = Gst.ElementFactory.make("mpegtsmux", None)
    pipeline.add(mpeg)
    for i in inputs:
        i.link(mpeg)
    return mpeg

def output_sender_srtstream(pipeline, src, host, port, latency=80):
    srtsink = Gst.ElementFactory.make("srtsink", None)
    srtsink.set_property('uri', f"srt://{host}:{port}")
    srtsink.set_property('wait-for-connection', False)
    srtsink.set_property('latency', latency)
    srtsink.set_property('async', True)
    srtsink.set_property('sync', False)
    pipeline.add(srtsink)
    src.link(srtsink)
    return srtsink

def output_udpstream(pipeline, src, host, port):
    srtsink = Gst.ElementFactory.make("udpsink", None)
    srtsink.set_property('host', host)
    srtsink.set_property('port', port)
    pipeline.add(srtsink)
    src.link(srtsink)
    return srtsink

def fakestub(pipeline, src):
    sink = Gst.ElementFactory.make("fakesink", None)
    pipeline.add(sink)
    src.link(sink)
    sink.set_property("sync", False)

def autovideosink(pipeline, src):
    vconvert = Gst.ElementFactory.make("videoconvert", None)
    sink = Gst.ElementFactory.make("autovideosink", None)
    pipeline.add(sink)
    pipeline.add(vconvert)
    src.link(vconvert)
    vconvert.link(sink)

def imagesource(pipeline, file=None):
    q = buffer_queue()
    filesrc = Gst.ElementFactory.make("filesrc", None)
    parse = Gst.ElementFactory.make("pngparse", None)
    decode = Gst.ElementFactory.make("pngdec", None)
    convert = Gst.ElementFactory.make("videoconvert", None)
    freeze = Gst.ElementFactory.make("imagefreeze", None)
    pipeline_chain(pipeline, filesrc, parse, decode, q, convert, freeze)
    freeze.set_property("is-live", True)
    filesrc.set_property("location", "c:/users/sorok/test.png")
    return freeze