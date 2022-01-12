import os
import sys
from gi.repository import GObject, Gst, GstVideo
from scicall.stream_settings import MediaType
from scicall.device_adapter import (
    DeviceAdapterFabric,
    DefaultVideoDeviceAdapter,
    DefaultAudioDeviceAdapter
)

PORT_BASE = 10100
MONITOR = None


def start_device_monitor():
    global MONITOR
    MONITOR = Gst.DeviceMonitor()
    MONITOR.start()


def stop_device_monitor():
    global MONITOR
    MONITOR.stop()
    MONITOR = None


def get_video_captures_list_windows():
    devs = MONITOR.get_devices()
    filtered_devs = [
        dev for dev in devs if dev.get_device_class() == "Video/Source"]
    defaults = [DefaultVideoDeviceAdapter()]
    adapters = [DeviceAdapterFabric().make_adapter(dev)
                for dev in filtered_devs]
    return defaults + adapters


def get_video_captures_list_linux():
    devs = MONITOR.get_devices()
    filtered_devs = [
        dev for dev in devs if dev.get_device_class() == "Video/Source"]
    defaults = [DefaultVideoDeviceAdapter()]
    adapters = [DeviceAdapterFabric().make_adapter(dev)
                for dev in filtered_devs]
    return defaults + adapters


def get_audio_captures_list_windows():
    devs = MONITOR.get_devices()
    filtered_devs = [
        dev for dev in devs if dev.get_device_class() == "Audio/Source"]
    defaults = [DefaultAudioDeviceAdapter()]
    adapters = [DeviceAdapterFabric().make_adapter(dev)
                for dev in filtered_devs]
    return defaults + adapters


def get_audio_captures_list_linux():
    devs = MONITOR.get_devices()
    filtered_devs = [
        dev for dev in devs if dev.get_device_class() == "Audio/Source"]
    defaults = [DefaultAudioDeviceAdapter()]
    adapters = [DeviceAdapterFabric().make_adapter(dev)
                for dev in filtered_devs]
    return defaults + adapters


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

def channel_video_port(ch):
    return PORT_BASE + ch * 3 + 0

def channel_audio_port(ch):
    return PORT_BASE + ch * 3 + 1

def channel_connect_port(ch):
    return PORT_BASE + ch * 3 + 2