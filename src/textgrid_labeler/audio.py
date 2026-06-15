import os
import subprocess
import threading
import io
import tempfile
import platform
import soundfile as sf


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
        self.samples = None
        if filepath:
            self.load(filepath)

    def load(self, filepath: str):
        self.filepath = filepath
        self.samples, self.sample_rate = sf.read(filepath, dtype='float32')
        self.n_channels = self.samples.ndim > 1 and self.samples.shape[1] or 1
        if self.samples.ndim > 1:
            self.samples = self.samples.mean(axis=1)
        self.sample_width = 4
        self.n_frames = len(self.samples)
        self.duration = self.n_frames / self.sample_rate
        self.max_possible = 1.0

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

    def get_section(self, start_time: float, end_time: float):
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

    def _play_array(self, samples):
        buf = io.BytesIO()
        sf.write(buf, samples, self.sample_rate, format='WAV', subtype='PCM_16')
        AudioPlayer.play_wav_data(buf.getvalue())
