import os
import sys

def get_cameras_list_windows():
	candidates = [ "1", "2" ]
	return sorted(candidates)

def get_cameras_list_linux():
	names = [ os.path.join("/dev", i) for i in os.listdir("/dev") ]
	candidates = [ i for i in names if "video" in i ]
	return sorted(candidates)

def get_cameras_list():
	if sys.platform == 'linux':
		return get_cameras_list_linux()
	elif sys.platform == 'win32':
		return get_cameras_list_windows()
	else:
		raise Exception("unsupported platform")