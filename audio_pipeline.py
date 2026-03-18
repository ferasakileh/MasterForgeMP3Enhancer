import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import librosa
import numpy as np
import soundfile as sf

from ai_models import AIModels
from dsp import (
    apply_eq,
    compress,
    harmonic_exciter,
    high_freq_synthesis,
    normalize_loudness,
    reduce_noise,
    saturate,
    stereo_widen,
)


@dataclass
class PipelineConfig:
    mode: str = "music"
    use_demucs: bool = False
    use_rnnoise: bool = False
    noise_strength: float = 0.6
    enable_exciter: bool = True
    enable_hf_synth: bool = True
    enable_saturation: bool = True
    stereo_amount: float = 1.15


MODE_PRESETS = {
    "music": {
        "target_dbfs": -16.0,
        "noise_strength": 0.50,
        "eq": (2.5, 2.0, 2.0),
        "compressor": (-18.0, 3.0, 8.0, 120.0, 2.0),
        "stereo": 1.15,
    },
    "speech": {
        "target_dbfs": -18.0,
        "noise_strength": 0.70,
        "eq": (1.0, 2.5, 1.0),
        "compressor": (-20.0, 2.5, 6.0, 100.0, 1.5),
        "stereo": 1.02,
    },
    "aggressive": {
        "target_dbfs": -14.5,
        "noise_strength": 0.85,
        "eq": (3.5, 3.5, 3.0),
        "compressor": (-22.0, 4.0, 4.0, 90.0, 3.0),
        "stereo": 1.22,
    },
}


def _call_progress(cb: Optional[Callable[[int, str], None]], pct: int, msg: str):
    if cb:
        cb(pct, msg)


def _output_name(input_path: str) -> str:
    p = Path(input_path)
    return str(p.with_name(f"{p.stem}_enhanced.mp3"))


def _load_audio(path: str):
    y, sr = librosa.load(path, sr=None, mono=False)
    if y.ndim == 1:
        y = np.vstack([y, y])
    return y.astype(np.float32), sr


def _sanitize(y: np.ndarray) -> np.ndarray:
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    return np.clip(y, -1.0, 1.0)


def _save_mp3_320(y: np.ndarray, sr: int, output_mp3: str):
    ffmpeg_bin = os.environ.get("FFMPEG_BINARY") or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError(
            "FFmpeg not found. Install FFmpeg and add it to PATH, "
            "or set FFMPEG_BINARY to full ffmpeg.exe path."
        )

    from pydub import AudioSegment  # lazy import
    AudioSegment.converter = ffmpeg_bin

    y = _sanitize(y)
    y_out = y.T
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav_path = tmp_wav.name
    try:
        sf.write(tmp_wav_path, y_out, sr, subtype="PCM_16")
        audio = AudioSegment.from_wav(tmp_wav_path)
        audio.export(output_mp3, format="mp3", bitrate="320k")
    finally:
        if os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)


def enhance_file(
    input_path: str,
    output_path: Optional[str] = None,
    config: Optional[PipelineConfig] = None,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> str:
    config = config or PipelineConfig()
    if output_path is None:
        output_path = _output_name(input_path)

    presets = MODE_PRESETS.get(config.mode, MODE_PRESETS["music"])
    ai = AIModels(enable_demucs=config.use_demucs, enable_rnnoise=config.use_rnnoise)

    _call_progress(progress_cb, 5, "Loading audio")
    y, sr = _load_audio(input_path)
    y = _sanitize(y)

    _call_progress(progress_cb, 15, "Optional source separation")
    if config.use_demucs:
        with tempfile.TemporaryDirectory() as td:
            stems = ai.separate_stems(input_path, td)
            if stems:
                y_v, sr_v = _load_audio(stems["vocals"])
                y_o, sr_o = _load_audio(stems["other"])
                if sr_v == sr_o:
                    y = y_v + y_o
                    sr = sr_v

    _call_progress(progress_cb, 25, "Loudness normalization")
    y = normalize_loudness(y, target_dbfs=presets["target_dbfs"])

    _call_progress(progress_cb, 38, "Noise reduction")
    y = reduce_noise(y, sr=sr, strength=presets["noise_strength"])

    _call_progress(progress_cb, 50, "RNNoise (optional)")
    y = ai.rnnoise_denoise(y, sr)

    _call_progress(progress_cb, 62, "Equalization")
    low_db, pres_db, air_db = presets["eq"]
    y = apply_eq(y, sr, low_shelf_db=low_db, presence_db=pres_db, air_db=air_db)

    _call_progress(progress_cb, 72, "Compression")
    th, ra, at, rel, makeup = presets["compressor"]
    y = compress(y, threshold_db=th, ratio=ra, attack_ms=at, release_ms=rel, makeup_db=makeup, sr=sr)

    _call_progress(progress_cb, 80, "Stereo widening")
    y = stereo_widen(y, amount=presets["stereo"])

    _call_progress(progress_cb, 88, "Psychoacoustic upscaling")
    if config.enable_exciter:
        y = harmonic_exciter(y, sr, drive=2.0, mix=0.08 if config.mode != "speech" else 0.04)
    if config.enable_hf_synth:
        y = high_freq_synthesis(y, sr, mix=0.05 if config.mode != "speech" else 0.02)
    y = ai.bandwidth_extension(y, sr, amount=0.03)
    if config.enable_saturation:
        y = saturate(y, drive=1.15, mix=0.06)

    _call_progress(progress_cb, 95, "Final normalization")
    y = normalize_loudness(y, target_dbfs=presets["target_dbfs"])

    _call_progress(progress_cb, 98, "Exporting MP3 320 kbps")
    _save_mp3_320(y, sr, output_path)

    _call_progress(progress_cb, 100, f"Done: {output_path}")
    return output_path