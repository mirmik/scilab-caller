import os
import sys
import time
from gi.repository import GObject, Gst, GstVideo
from scicall.stream_settings import MediaType
from scicall.device_adapter import (
    DeviceAdapterFabric,
    DefaultVideoDeviceAdapter,
    DefaultAudioDeviceAdapter,
    TestVideoSrcDeviceAdapter,
    TestAudioSrcDeviceAdapter
)

NDI_DEVICE_PROVIDER = None
MONITOR = None


def start_device_monitor():
    global MONITOR
    MONITOR = Gst.DeviceMonitor()
    MONITOR.start()


def stop_device_monitor():
    global MONITOR
    MONITOR.stop()
    MONITOR = None


def get_video_captures_list(default=True, test=True):
    devs = MONITOR.get_devices()
    filtered_devs = [
        dev for dev in devs if dev.get_device_class() == "Video/Source"]
    defaults = [DefaultVideoDeviceAdapter()]
    adapters = [DeviceAdapterFabric().make_adapter(dev)
                for dev in filtered_devs]
    if test:
        adapters.append(TestVideoSrcDeviceAdapter())

    if default:
        adapters.insert(0, DefaultVideoDeviceAdapter())
    return adapters


def get_audio_captures_list(default=True, test=True):
    devs = MONITOR.get_devices()
    filtered_devs = [
        dev for dev in devs if dev.get_device_class() == "Audio/Source"]
    defaults = []
    adapters = [DeviceAdapterFabric().make_adapter(dev)
                for dev in filtered_devs]
    
    if test:
        adapters.append(TestAudioSrcDeviceAdapter())

    if default:
        adapters.insert(0, DefaultAudioDeviceAdapter())

    return adapters


def get_devices_list(mediatype, default=True, test=True):
    """ К счастью, gststreamer умеет добывать списки устройств,
        и довольно много о них знает. """
    if mediatype == MediaType.VIDEO:
        return get_video_captures_list(default, test)
    elif mediatype == MediaType.AUDIO:
        return get_audio_captures_list(default, test)

def get_filtered_devices_list(mediatype, default=True, test=True):
    """ К счастью, gststreamer умеет добывать списки устройств,
        и довольно много о них знает. """
    if mediatype == MediaType.VIDEO:
        return get_video_captures_list(default, test)
    elif mediatype == MediaType.AUDIO:
        return [ a for a in get_audio_captures_list(default) if a.is_supported() ]

def pipeline_chain(pipeline, *args):
    if pipeline is None:
        return

    for el in args:
        pipeline.add(el)

    for i in range(len(args) - 1):
        args[i].link(args[i+1])

    return args[0], args[-1]

#def pipeline_chain_bin(pipeline, *args):
#    bin = Gst.Bin(None)
#    for el in args:
        #pipeline.add(el)
#        bin.add(el)
#    pipeline.add(bin)

#    for i in range(len(args) - 1):
#        args[i].link(args[i+1])
#    pad = args[-1].get_static_pad("sink")
#    print(pad)
#    ghost_pad = Gst.GhostPad.new("sink", pad)
#    bin.add_pad(ghost_pad)
#    return bin

def start_ndi_device_provider():
    global NDI_DEVICE_PROVIDER
    NDI_DEVICE_PROVIDER = Gst.DeviceProviderFactory.find("ndideviceprovider").get()
    NDI_DEVICE_PROVIDER.start()

def ndi_device_list():
    return NDI_DEVICE_PROVIDER.get_devices()

def ndi_device_list_names():
    return [ dev.get_property("display-name") for dev in ndi_device_list() ]