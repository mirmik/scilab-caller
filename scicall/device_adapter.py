import os
import sys
from gi.repository import GObject, Gst, GstVideo

class DeviceAdapter:
	""" Адаптер для получения доступа к объектом устройств разных типов """

	def __init__(self, gstdevice):
		self.gstdevice = gstdevice

	def user_readable_name(self):
		return "TODO: user_readable_name"

	def make_gst_element(self):
		return Gst.ElementFactory.make("fakesrc", None)

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
	def user_readable_name(self):
		return self.gstdevice.get_name()

	def make_gst_element(self):
		ksname = self.gstdevice.get_name()
		subs = ksname[8:len(ksname)]
		el = Gst.ElementFactory.make("ksvideosrc", None)
		el.set_property("device-index", int(subs))
		return el

class GstDirectSoundSrcDeviceAdapter(DeviceAdapter):
	def user_readable_name(self):
		return self.gstdevice.get_name()

	def make_gst_element(self):
		raise Exception("TODO: GstDirectSoundSrcDevice")

class GstWasapiDeviceAdapter(DeviceAdapter):
	def user_readable_name(self):
		return self.gstdevice.get_name()

	def make_gst_element(self):
		el = Gst.ElementFactory.make("wasapisrc", None)
		el.set_property("device", self.gstdevice.get_properties().get_string("device.strid"))
		return el

class GstV4l2DeviceAdapter(DeviceAdapter):
	def user_readable_name(self):
		return self.gstdevice.get_name()

	def make_gst_element(self):
		el = Gst.ElementFactory.make("v4l2src", None)
		el.set_property("device", self.gstdevice.get_properties().get_string("device.path"))
		return el	

class GstAlsaDeviceAdapter(DeviceAdapter):
	def user_readable_name(self):
		return self.gstdevice.get_name()

	def make_gst_element(self):
		el = Gst.ElementFactory.make("alsasrc", None)
		el.set_property("device", self.gstdevice.get_properties().get_string("device.path"))
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