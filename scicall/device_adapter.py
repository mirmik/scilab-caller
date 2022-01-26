import os
import sys
import re
from gi.repository import GObject, Gst, GstVideo

class SizeCaps:
    def __init__(self, caps):
        self.caps = caps

    def width(self):
        v = re.findall("width=\(int\)[0-9]+", self.caps)[0]
        v = re.findall("[0-9]+", v)[0]
        return int(v)

    def height(self):
        v = re.findall("width=\(int\)[0-9]+", self.caps)[0]
        v = re.findall("[0-9]+", v)[0]
        return int(v)

    def sizestr(self):
        return str(self.width()) + "x" + str(self.height())  

    def __repr__(self):
        return self.sizestr()

class DeviceAdapter:
    """ Адаптер для получения доступа к объектом устройств разных типов """
    def is_supported(self):
        return True

    def __init__(self, gstdevice):
        self.gstdevice = gstdevice

    def user_readable_name(self):
        return self.gstdevice.get_display_name()

    def make_gst_element(self):
        return Gst.ElementFactory.make("fakesrc", None)

    def has_framerate30(self, x):
        afrate = re.findall("framerate=\(fraction\)(\{.*\}|\[.*\]|[0-9]*/[0-9]*)", x)[0]
        return "30/1" in afrate

    def filtered_video_caps(self):
        if self.gstdevice is None:
            return []
        caps = self.gstdevice.get_caps()
        strcaps = caps.to_string()
        splitted = strcaps.split(";")
        xrawcaps = [ x for x in splitted if "x-raw" in x]
        frated = [ SizeCaps(x) for x in xrawcaps if self.has_framerate30(x)]
        return frated

    def audio_caps(self):
        if self.gstdevice is None:
            return []
        caps = self.gstdevice.get_caps().to_string()
        return caps

class DefaultVideoDeviceAdapter(DeviceAdapter):
    def __init__(self):
        super().__init__(None)

    def user_readable_name(self):
        return "По умолчанию"

    def make_gst_element(self):
        if sys.platform == "linux":
            return Gst.ElementFactory.make("v4l2src", None)
        elif sys.platform == "win32":
            return Gst.ElementFactory.make("ksvideosrc", None)
        else:
            raise Exception("Unsuported platform")


class DefaultAudioDeviceAdapter(DeviceAdapter):
    def __init__(self):
        super().__init__(None)

    def user_readable_name(self):
        return "По умолчанию"

    def make_gst_element(self):
        if sys.platform == "linux":
            return Gst.ElementFactory.make("alsasrc", None)
        elif sys.platform == "win32":
            return Gst.ElementFactory.make("wasapisrc", None)
        else:
            raise Exception("Unsuported platform")


class GstKsDeviceAdapter(DeviceAdapter):
    #def user_readable_name(self):
    #    return self.gstdevice.get_name()

    def make_gst_element(self):
        ksname = self.gstdevice.get_name()
        subs = ksname[8:len(ksname)]
        el = Gst.ElementFactory.make("ksvideosrc", None)
        el.set_property("device-index", int(subs))
        return el


class GstDirectSoundSrcDeviceAdapter(DeviceAdapter):
    def is_supported(self):
        return True

    def make_gst_element(self):
        el = Gst.ElementFactory.make("directsoundsrc", None)
        el.set_property(
            "device", self.gstdevice.get_properties().get_string("device.strid"))
        return el


class GstWasapiDeviceAdapter(DeviceAdapter):
    def make_gst_element(self):
        el = Gst.ElementFactory.make("wasapisrc", None)
        el.set_property(
            "device", self.gstdevice.get_properties().get_string("device.strid"))
        return el


class GstV4l2DeviceAdapter(DeviceAdapter):
    def make_gst_element(self):
        el = Gst.ElementFactory.make("v4l2src", None)
        el.set_property(
            "device", self.gstdevice.get_properties().get_string("device.path"))
        return el


class GstAlsaDeviceAdapter(DeviceAdapter):
    def make_gst_element(self):
        el = Gst.ElementFactory.make("alsasrc", None)
        # TODO : MIC choise
        return el

class TestVideoSrcDeviceAdapter(DeviceAdapter):
    def __init__(self):
        super().__init__(None)

    def user_readable_name(self):
        return "Тестовый источник"

    def make_gst_element(self):
        el = Gst.ElementFactory.make("videotestsrc", None)
        return el

class TestAudioSrcDeviceAdapter(DeviceAdapter):
    def __init__(self):
        super().__init__(None)

    def user_readable_name(self):
        return "Тестовый источник"

    def make_gst_element(self):
        el = Gst.ElementFactory.make("audiotestsrc", None)
        return el

class DeviceAdapterFabric:
    def make_adapter(self, gstdevice):
        typename = type(gstdevice).__name__
        if typename == "GstKsDevice":
            return GstKsDeviceAdapter(gstdevice)
        elif typename == "GstDirectSoundSrcDevice":
            return GstDirectSoundSrcDeviceAdapter(gstdevice)
        elif typename == "GstWasapiDevice":
            return GstWasapiDeviceAdapter(gstdevice)
        elif typename == "GstV4l2Device":
            return GstV4l2DeviceAdapter(gstdevice)
        elif typename == "GstAlsaDevice":
            return GstAlsaDeviceAdapter(gstdevice)

        print("undefined device type:", typename)
        return DeviceAdapter(gstdevice)

