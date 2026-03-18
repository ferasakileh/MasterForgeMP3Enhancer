import numpy as np
import scipy.signal as sps
import noisereduce as nr
import argparse
from pathlib import Path

from audio_pipeline import PipelineConfig, enhance_file


def _to_stereo(y: np.ndarray) -> np.ndarray:
    if y.ndim == 1:
        return np.vstack([y, y])
    return y


def normalize_loudness(y: np.ndarray, target_dbfs: float = -16.0) -> np.ndarray:
    y = _to_stereo(y).astype(np.float32)
    rms = np.sqrt(np.mean(y**2) + 1e-12)
    current_db = 20 * np.log10(rms + 1e-12)
    gain_db = target_dbfs - current_db
    gain = 10 ** (gain_db / 20.0)
    out = y * gain
    peak = np.max(np.abs(out)) + 1e-12
    if peak > 0.99:
        out = out / peak * 0.99
    return out


def reduce_noise(y: np.ndarray, sr: int, strength: float = 0.6) -> np.ndarray:
    y = _to_stereo(y)
    out = np.zeros_like(y)
    for ch in range(y.shape[0]):
        out[ch] = nr.reduce_noise(
            y=y[ch], sr=sr, prop_decrease=strength, stationary=False, n_jobs=1
        )
    return out


def apply_eq(
    y: np.ndarray,
    sr: int,
    low_shelf_db: float = 2.5,
    presence_db: float = 2.0,
    air_db: float = 2.0,
) -> np.ndarray:
    y = _to_stereo(y)
    out = np.zeros_like(y)
    for ch in range(y.shape[0]):
        x = y[ch]
        n = x.shape[0]
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(n, d=1 / sr)

        # Low shelf around 100 Hz
        low_curve = 1.0 / (1.0 + (f / 100.0) ** 2)

        # Presence bell around 4.5 kHz
        presence_center = 4500.0
        presence_width = 0.6  # in log2 space
        f_safe = np.maximum(f, 1.0)
        bell = np.exp(-0.5 * ((np.log2(f_safe / presence_center)) / presence_width) ** 2)

        # Air shelf above 8 kHz
        air_curve = 1.0 / (1.0 + np.exp(-(f - 8000.0) / 1200.0))

        gain_db = low_shelf_db * low_curve + presence_db * bell + air_db * air_curve
        gain = 10 ** (gain_db / 20.0)
        out[ch] = np.fft.irfft(X * gain, n=n).astype(np.float32)
    return out


def compress(
    y: np.ndarray,
    threshold_db: float = -18.0,
    ratio: float = 3.0,
    attack_ms: float = 8.0,
    release_ms: float = 120.0,
    makeup_db: float = 2.0,
    sr: int = 44100,
) -> np.ndarray:
    y = _to_stereo(y)
    out = np.zeros_like(y)

    attack = np.exp(-1.0 / max(1, int(sr * attack_ms / 1000.0)))
    release = np.exp(-1.0 / max(1, int(sr * release_ms / 1000.0)))
    makeup = 10 ** (makeup_db / 20.0)

    for ch in range(y.shape[0]):
        x = y[ch]
        env = 0.0
        gain = np.ones_like(x, dtype=np.float32)

        for i, s in enumerate(np.abs(x)):
            coef = attack if s > env else release
            env = coef * env + (1 - coef) * s
            env_db = 20 * np.log10(env + 1e-8)
            if env_db > threshold_db:
                over_db = env_db - threshold_db
                gain_reduction_db = over_db * (1.0 - 1.0 / ratio)
                gain[i] = 10 ** (-gain_reduction_db / 20.0)
            else:
                gain[i] = 1.0

        out[ch] = x * gain * makeup

    peak = np.max(np.abs(out)) + 1e-12
    if peak > 0.99:
        out = out / peak * 0.99
    return out


def stereo_widen(y: np.ndarray, amount: float = 1.15) -> np.ndarray:
    y = _to_stereo(y)
    mid = 0.5 * (y[0] + y[1])
    side = 0.5 * (y[0] - y[1]) * amount
    l = mid + side
    r = mid - side
    out = np.vstack([l, r])
    peak = np.max(np.abs(out)) + 1e-12
    if peak > 0.99:
        out = out / peak * 0.99
    return out


def harmonic_exciter(y: np.ndarray, sr: int, drive: float = 2.0, mix: float = 0.08) -> np.ndarray:
    y = _to_stereo(y)
    b, a = sps.butter(2, 2000 / (sr / 2), btype="highpass")
    out = np.zeros_like(y)
    for ch in range(y.shape[0]):
        hp = sps.lfilter(b, a, y[ch])
        excited = np.tanh(hp * drive)
        out[ch] = y[ch] * (1 - mix) + excited * mix
    return out


def high_freq_synthesis(y: np.ndarray, sr: int, mix: float = 0.05) -> np.ndarray:
    y = _to_stereo(y)
    b, a = sps.butter(2, 8000 / (sr / 2), btype="highpass")
    out = np.zeros_like(y)
    for ch in range(y.shape[0]):
        nonlinear = np.tanh(3.0 * y[ch]) - y[ch]
        hf = sps.lfilter(b, a, nonlinear)
        out[ch] = y[ch] + hf * mix
    peak = np.max(np.abs(out)) + 1e-12
    if peak > 0.99:
        out = out / peak * 0.99
    return out


def saturate(y: np.ndarray, drive: float = 1.2, mix: float = 0.07) -> np.ndarray:
    y = _to_stereo(y)
    sat = np.tanh(y * drive)
    return y * (1 - mix) + sat * mix


def main():
    parser = argparse.ArgumentParser(description="AI Audio Enhancer")
    parser.add_argument("inputs", nargs="+", help="Input audio file(s): mp3/wav/flac")
    parser.add_argument("--mode", choices=["music", "speech", "aggressive"], default="music")
    parser.add_argument("--music", action="store_true", help="Alias for --mode music")
    parser.add_argument("--speech", action="store_true", help="Alias for --mode speech")
    parser.add_argument("--aggressive", action="store_true", help="Alias for --mode aggressive")
    parser.add_argument("--demucs", action="store_true", help="Enable Demucs source separation")
    parser.add_argument("--rnnoise", action="store_true", help="Enable RNNoise if available")
    parser.add_argument("--no-exciter", action="store_true")
    parser.add_argument("--no-hf-synth", action="store_true")
    parser.add_argument("--no-saturation", action="store_true")
    args = parser.parse_args()

    mode = args.mode
    if args.music:
        mode = "music"
    if args.speech:
        mode = "speech"
    if args.aggressive:
        mode = "aggressive"

    cfg = PipelineConfig(
        mode=mode,
        use_demucs=args.demucs,
        use_rnnoise=args.rnnoise,
        enable_exciter=not args.no_exciter,
        enable_hf_synth=not args.no_hf_synth,
        enable_saturation=not args.no_saturation,
    )

    for inp in args.inputs:
        if not Path(inp).exists():
            print(f"[ERROR] File not found: {inp}")
            continue

        def progress(p, msg):
            print(f"[{p:3d}%] {msg}")

        out = enhance_file(inp, config=cfg, progress_cb=progress)
        print(f"[OK] Enhanced file: {out}")


if __name__ == "__main__":
    main()