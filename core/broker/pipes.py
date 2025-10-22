import threading, contextlib, time, win32con
import win32file, win32pipe, pywintypes

class PipeConnection:
    def __init__(self, handle):
        self.handle = handle
        self.closed = False

    def read_frame(self) -> bytes:
        hr, raw_len = win32file.ReadFile(self.handle, 4, None)
        n = int.from_bytes(raw_len, "little")
        hr, data = win32file.ReadFile(self.handle, n, None)
        return data

    def write_frame(self, data: bytes) -> None:
        win32file.WriteFile(self.handle, data)

    def close(self):
        if not self.closed:
            with contextlib.suppress(Exception):
                win32file.FlushFileBuffers(self.handle)
            with contextlib.suppress(Exception):
                win32pipe.DisconnectNamedPipe(self.handle)
            with contextlib.suppress(Exception):
                win32file.CloseHandle(self.handle)
            self.closed = True

class NamedPipeServer:
    def __init__(self, name: str):
        # name example: r"\\.\pipe\buscore-{uuid}"
        self.name = name
        self._stop = threading.Event()
        self._callback = None
        self._thread = None

    def start(self, callback):
        self._callback = callback
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                handle = win32pipe.CreateNamedPipe(
                    self.name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    1024*1024, 1024*1024, 5000, None
                )
            except pywintypes.error as e:
                if getattr(e, "winerror", e.args[0]) == win32con.ERROR_PIPE_BUSY:
                    time.sleep(0.05)
                    continue
                raise

            try:
                win32pipe.ConnectNamedPipe(handle, None)
            except pywintypes.error:
                with contextlib.suppress(Exception): win32file.CloseHandle(handle)
                continue
            conn = PipeConnection(handle)
            t = threading.Thread(target=self._serve_one, args=(conn,), daemon=True)
            t.start()

    def _serve_one(self, conn: PipeConnection):
        try:
            self._callback(conn)
        finally:
            conn.close()
