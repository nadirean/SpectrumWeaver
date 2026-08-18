"""Lightweight audio I/O: metadata and chunked decoding without librosa/scipy.

Decoding backends:
- WAV/FLAC/OGG (libsndfile formats): soundfile
- MP3/M4A/AAC: audioread -> FFmpeg (binary bundled via imageio-ffmpeg)

All reads happen at the file's native sample rate (no resampling).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator

import numpy as np

_FFMPEG_SETUP_DONE = False


def ensure_ffmpeg_on_path() -> None:
    """Put the bundled FFmpeg binary (imageio-ffmpeg) on PATH for audioread."""
    global _FFMPEG_SETUP_DONE
    if _FFMPEG_SETUP_DONE:
        return
    _FFMPEG_SETUP_DONE = True
    try:
        import imageio_ffmpeg

        ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass  # lossy formats will raise a clear error from audioread


@dataclass
class AudioInfo:
    sample_rate: int
    duration: float
    channels: int


def get_audio_info(path: str) -> AudioInfo:
    """Sample rate, duration and channel count without decoding the whole file."""
    try:
        import soundfile as sf

        info = sf.info(path)
        return AudioInfo(sample_rate=info.samplerate, duration=float(info.duration), channels=info.channels)
    except Exception:
        ensure_ffmpeg_on_path()
        import audioread

        with audioread.audio_open(path) as f:
            return AudioInfo(sample_rate=f.samplerate, duration=f.duration, channels=f.channels)


def iter_mono_chunks(path: str, chunk_size: int) -> Iterator[np.ndarray]:
    """Yield float32 mono chunks (1D) at the native sample rate.

    Tries libsndfile first; falls back to FFmpeg (via audioread) for lossy
    formats. Raises a RuntimeError with a readable message if neither works.
    """
    try:
        import soundfile as sf

        for block in sf.blocks(path, blocksize=chunk_size, dtype="float32", always_2d=True):
            yield block.mean(axis=1)
        return
    except Exception as e:
        sndfile_error = e

    ensure_ffmpeg_on_path()
    try:
        import audioread

        with audioread.audio_open(path) as f:
            channels = f.channels
            frame_bytes = channels * 2  # raw PCM is int16
            buffer = b""
            while True:
                block = f.read(4096 * frame_bytes)
                if not block:
                    break
                buffer += block
                while len(buffer) >= chunk_size * frame_bytes:
                    take = buffer[: chunk_size * frame_bytes]
                    buffer = buffer[chunk_size * frame_bytes:]
                    yield _decode_pcm(take, channels)
            if buffer:
                yield _decode_pcm(buffer, channels)
    except Exception as e:
        raise RuntimeError(
            f"Could not decode audio file: {e} (soundfile error: {sndfile_error})"
        ) from e


def _decode_pcm(raw: bytes, channels: int) -> np.ndarray:
    """Decode a raw int16 PCM buffer into a float32 mono array."""
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples
