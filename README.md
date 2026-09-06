# SpectrumWeaver

Real-time acoustic spectrum analyzer built with Python and Qt. Streams audio files in chunks, computes an FFT spectrogram, and renders it progressively with PyQtGraph.

![screenshot](images/screenshot.png)

## Features

- Streaming linear FFT spectrogram with bounded memory usage
- Custom axes with guaranteed boundary ticks (`0:00`/duration, `0 kHz`/Nyquist) and stable density on resize
- Formats: WAV, FLAC, OGG (built-in, via libsndfile) and MP3, M4A, AAC (via the bundled FFmpeg binary)
- Drag & drop or click-to-browse file loading
- Batch size and colormap settings via the context menu
- PNG export and track metadata details dialog

## Requirements

- Python 3.13+
- Windows, macOS, or Linux
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
git clone <repository-url>
cd SpectrumWeaver
uv sync
```

## Running

```bash
uv run python src/spectrum_weaver.py
```

Drag an audio file onto the window, or click anywhere on the empty screen to browse for a file.

## Project structure

```
SpectrumWeaver/
├── src/
│   ├── spectrum_weaver.py            # Entry point
│   ├── analyzers/
│   │   ├── audio_io.py               # Decoding: soundfile (lossless) + FFmpeg fallback (lossy)
│   │   └── spectrum_analyzer.py      # Streaming chunked FFT
│   ├── gui/
│   │   ├── spectrum_viewer.py        # Spectrogram widget (batched, throttled updates)
│   │   ├── custom_title_bar.py
│   │   ├── custom_context_menu.py    # Export / details / settings
│   │   └── custom_axes_items.py      # Time/frequency axis labels
│   └── assets/
│       ├── icon.png
│       └── styles.qss
├── tests/
├── tools/spectrum_weaver.spec        # PyInstaller spec
├── pyproject.toml
└── uv.lock
```

## Building the executable

From the project root:

```bash
uv sync --group dev
uv run pyinstaller tools/spectrum_weaver.spec
```

The one-file executable is written to `dist/spectrum_weaver(.exe)`. The FFmpeg binary
(needed for MP3/M4A/AAC) is bundled automatically via `imageio-ffmpeg`. UPX is disabled
for faster startup (unpacking a compressed payload costs more than the saved space).

## Design notes

- Audio is decoded at the native sample rate in fixed-size chunks (`audio_io.py`).
- Frames are produced with a zero-copy sliding window and processed in batches of
  `fft_size` (2048, Hann window) with `numpy.fft.rfft`.
- Full linear FFT resolution is preserved across all frequency bins (0 Hz to Nyquist),
  providing crisp spectrogram rendering without artificial bin reduction.
- Memory and processing costs for long files are bounded via an adaptive hop length
  (targeting ~1,000 to 3,000 frames), ensuring fast streaming analysis at any duration.
- The viewer writes batch results into a preallocated array and repaints at most
  ~30 times per second, so UI cost is independent of the number of frames.
