pacman -S \
	mingw-w64-x86_64-toolchain \
	mingw-w64-x86_64-glib2 \
	mingw-w64-x86_64-gnutls \
	mingw-w64-x86_64-gst-python \
	mingw-w64-x86_64-gstreamer \
	mingw-w64-x86_64-gst-plugins-good \
	mingw-w64-x86_64-gst-plugins-bad \
	mingw-w64-x86_64-gst-plugins-ugly \
	mingw-w64-x86_64-gst-libav \
	mingw-w64-x86_64-python-pyqt5 \
	mingw-w64-x86_64-python-pip \
	mingw-w64-x86_64-ninja \
	mingw-w64-x86_64-cmake \
	flex \
	bison \
	mingw-w64-x86_64-ninja \
	git

python3 -m pip install meson wheel


# meson build --prefix c:/msys64/mingw64