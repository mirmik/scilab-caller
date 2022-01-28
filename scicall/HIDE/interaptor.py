""" Страшная чёрная магия позволяет читать ворнинги, которыми нас удивляют
разные библиотеки. """

import os
import io
import sys
import signal
import time
from scicall.finisher import register_destructor

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

if sys.platform == "linux":
    import fcntl
elif sys.platform == "win32":
    from ctypes import wintypes
    PIPE_NOWAIT = wintypes.DWORD(0x00000001)
else:
    raise Exception("Unresolved OS error")


class Listener(QThread):
    newdata = pyqtSignal(str)

    def __init__(self, file, parent=None):
        super().__init__(parent)
        self._file = file
        self._stop_token = False
        self.stream_handler = None
        register_destructor(id(self), self.stop)

    def stop(self):
        self._stop_token = True
        if sys.platform == "win32":
            self.terminate()

    def make_file_nonblockable(self):
        if sys.platform == "linux":
            flags = fcntl.fcntl(self._file.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(self._file.fileno(), fcntl.F_SETFL,
                        flags | os.O_NONBLOCK)
        else:
            raise Exception("Unresolved OS error")

    def run(self):
        sys.stderr.write("RUN")
            
        if sys.platform == "linux":
            self.run_linux()
        elif sys.platform == "win32":
            self.run_windows()
        else:
            raise Exception("Unresolved OS error")

    def run_linux(self):
        self.make_file_nonblockable()

        while True:
            if self._stop_token:
                return

            res = select.select([self._file.fileno()], [self._file.fileno()], [
                self._file.fileno()], 0.3)
            if (len(res[0]) == 0 and len(res[1]) == 0 and len(res[2]) == 0):
                continue

            while True:
                try:
                    data = self._file.readline()
                except Exception as ex:
                    print(ex)
                    continue

                if len(data) == 1 and data == "\n":
                    continue
                if len(data) == 0:
                    break
                self.newdata.emit(data)

                if self.stream_handler:
                    self.stream_handler(data)

    def run_windows(self):
        while True:
            try:
                data = self._file.readline()
            except Exception as ex:
                print(ex)
                continue
            
            if len(data) == 1 and data == "\n":
                continue
            if len(data) == 0:
                break
            self.newdata.emit(data)

            if self.stream_handler:
                self.stream_handler(data)


class Interaptor(QObject):
    """Ретранслятор перехватывает поток вывода на файловый дескриптор
    принадлежащий @stdout и читает данные из него в отдельном потоке,
    перенаправляя их на дескриптор @new_desc.

    Это позволяет перехватывать стандартный вывод в подчинённых процессах и перенаправлять его на встроенную консоль.
    """
    INSTANCE = None
    srt_disconnect = pyqtSignal()

    @classmethod
    def instance(cls):            
        if cls.INSTANCE is None:
            cls.INSTANCE = Interaptor(sys.stderr)

        return cls.INSTANCE

    def __init__(self, stdout, new_desc=None, parent=None):
        super().__init__(parent)
        self.communicator = None
        self.do_retrans(old_file=stdout, new_desc=new_desc)
        self.prevent_mode = False
        self.newdata_stream = None
        self.last_disconnect = time.time()
        #register_destructor(id(self), self.stop_listen)

    def set_communicator(self, comm):
        self.communicator = comm

    def start_listen(self):
        self._listener = Listener(self.r_file, self)
        self._listener.stream_handler = self.newdata_handler
        self._listener.start()

    def stop_listen(self):
        if self._listener:
            self._listener.stop()
            #self._listener.wait()

    def newdata_handler(self, inputdata):
        self.new_file.write(inputdata)
        if " srtlib epoll.cpp:903:update_events: : epoll/update: IPE: update struck" in inputdata:
            if time.time() - self.last_disconnect > 0.5:
                self.srt_disconnect.emit()
            self.last_disconnect = time.time()
        # TODO: Стандартизировать варианты обработки.
        #if self.without_wrap:
        #else:
        #    if self.communicator:
        #        self.communicator.send({"cmd": "console", "data": inputdata})
        #if self.newdata_stream:
        #    print_to_stderr("newdata_stream")
        #    self.newdata_stream(inputdata)

    def do_retrans(self, old_file, new_desc=None):
        old_desc = old_file.fileno()
        if new_desc:
            os.dup2(old_desc, new_desc)
        else:
            new_desc = os.dup(old_desc)

        r, w = os.pipe()
        self.r_fd, self.w_fd = r, w
        self.r_file = os.fdopen(r, "r")
        self.w_file = os.fdopen(w, "w")
        self.old_desc = old_desc
        self.new_desc = new_desc
        self.new_file = os.fdopen(new_desc, "w")
        old_file.close()
        os.close(old_desc)
        os.dup2(w, old_desc)

        sys.stderr = io.TextIOWrapper(
            os.fdopen(old_desc, "wb"), line_buffering=True)
