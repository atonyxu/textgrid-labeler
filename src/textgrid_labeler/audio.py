import wave
import numpy as np
import os
import subprocess
import threading
import io
import tempfile
import platform


class AudioPlayer:
    @staticmethod
    def play_wav_data(wav_data: bytes):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(wav_data)
        tmp_name = tmp.name
        tmp.close()

        def _play_and_clean():
            try:
                system = platform.system()
                if system == "Windows":
                    import winsound
                    winsound.PlaySound(tmp_name, winsound.SND_FILENAME | winsound.SND_ASYNC)
                elif system == "Darwin":
                    subprocess.Popen(["afplay", tmp_name],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    for cmd in ["paplay", "aplay", "ffplay", "play"]:
                        try:
                            subprocess.run([cmd, "--version"],
                                           capture_output=True, timeout=1)
                            subprocess.Popen([cmd, tmp_name],
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)
                            break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                cleanup_after = 5.0
                threading.Timer(cleanup_after, lambda: AudioPlayer._cleanup(tmp_name)).start()
            except Exception as e:
                print(f"Playback error: {e}")

        threading.Thread(target=_play_and_clean, daemon=True).start()

    @staticmethod
    def _cleanup(path: str):
        try:
            os.unlink(path)
        except:
            pass


class AudioData:
    def __init__(self, filepath: str = ""):
        self.filepath = filepath
        self.sample_rate = 0
        self.n_channels = 0
        self.sample_width = 0
        self.n_frames = 0
        self.duration = 0.0
        self.max_possible = 1.0
        self.samples: np.ndarray = None
        if filepath:
            self.load(filepath)

    def load(self, filepath: str):
        self.filepath = filepath
        with wave.open(filepath, "rb") as wf:
            self.sample_rate = wf.getframerate()
            self.n_channels = wf.getnchannels()
            self.sample_width = wf.getsampwidth()
            self.n_frames = wf.getnframes()
            self.duration = self.n_frames / self.sample_rate
            self.max_possible = 2 ** (8 * self.sample_width - 1)
            raw = wf.readframes(self.n_frames)
            dtype = np.int16 if self.sample_width == 2 else np.int32 if self.sample_width == 4 else np.int8
            self.samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
            if self.n_channels > 1:
                self.samples = self.samples.reshape(-1, self.n_channels).mean(axis=1)

    def is_loaded(self) -> bool:
        return self.samples is not None and len(self.samples) > 0

    def unload(self):
        self.filepath = ""
        self.sample_rate = 0
        self.n_channels = 0
        self.sample_width = 0
        self.n_frames = 0
        self.duration = 0.0
        self.max_possible = 1.0
        self.samples = None

    def get_section(self, start_time: float, end_time: float) -> np.ndarray:
        if not self.is_loaded():
            return None
        start_frame = int(start_time * self.sample_rate)
        end_frame = int(end_time * self.sample_rate)
        start_frame = max(0, min(start_frame, self.n_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, self.n_frames))
        return self.samples[start_frame:end_frame]

    def play(self, start_time: float, end_time: float):
        section = self.get_section(start_time, end_time)
        if section is None or len(section) == 0:
            return
        self._play_array(section)

    def _play_array(self, samples: np.ndarray):
        samples = np.clip(samples, -32768, 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(samples.tobytes())

        AudioPlayer.play_wav_data(buf.getvalue())
