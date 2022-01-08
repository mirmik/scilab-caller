import os
import sys
from gi.repository import GObject, Gst, GstVideo
from scicall.stream_settings import MediaType

def get_video_captures_list_windows():
	candidates = [ "1", "2" ]
	return sorted(candidates)

def get_video_captures_list_linux():
	monitor = Gst.DeviceMonitor()
	monitor.start()
	devs = monitor.get_devices()
	video_devs = [ dev for dev in devs if dev.get_device_class() == "Video/Source" ]
	monitor.stop()
	pathes = [ dev.get_properties().get_string("device.path") for dev in video_devs ]
	return sorted(pathes)

def get_audio_captures_list_linux():
	return ["hw:0", "hw:1", "hw:2"]

def get_video_captures_list():
	if sys.platform == 'linux':
		return get_video_captures_list_linux()
	elif sys.platform == 'win32':
		return get_video_captures_list_windows()
	else:
		raise Exception("unsupported platform")

def get_audio_captures_list():
	if sys.platform == 'linux':
		return get_audio_captures_list_linux()
	elif sys.platform == 'win32':
		return get_audio_captures_list_windows()
	else:
		raise Exception("unsupported platform")

def get_devices_list(mediatype):
	""" К счастью, gststreamer умеет добывать списки устройств,
	    и довольно много о них знает. """
	if mediatype == MediaType.VIDEO:
		return get_video_captures_list()
	elif mediatype == MediaType.AUDIO:
		return get_audio_captures_list()
