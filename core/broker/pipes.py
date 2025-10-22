import threading, contextlib
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
            h = win32pipe.CreateNamedPipe(
                self.name,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                1, 1024*1024, 1024*1024, 5000, None
            )
            try:
                win32pipe.ConnectNamedPipe(h, None)
            except pywintypes.error:
                with contextlib.suppress(Exception): win32file.CloseHandle(h)
                continue
            conn = PipeConnection(h)
            t = threading.Thread(target=self._serve_one, args=(conn,), daemon=True)
            t.start()

    def _serve_one(self, conn: PipeConnection):
        try:
            self._callback(conn)
        finally:
            conn.close()
