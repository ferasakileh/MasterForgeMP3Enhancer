import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

import numpy as np


class AIModels:
    def __init__(self, enable_demucs: bool = False, enable_rnnoise: bool = False):
        self.enable_demucs = enable_demucs
        self.enable_rnnoise = enable_rnnoise

    def separate_stems(self, input_file: str, out_dir: str) -> Optional[Dict[str, str]]:
        """Optional Demucs separation. Returns stem paths if successful."""
        if not self.enable_demucs:
            return None
        if shutil.which("python") is None:
            return None

        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            "python",
            "-m",
            "demucs",
            "--two-stems=vocals",
            "-o",
            str(out_path),
            input_file,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            return None

        # demucs output: out_dir/htdemucs/<track_name>/vocals.wav, no_vocals.wav
        track_name = Path(input_file).stem
        search_root = out_path / "htdemucs" / track_name
        vocals = search_root / "vocals.wav"
        other = search_root / "no_vocals.wav"
        if vocals.exists() and other.exists():
            return {"vocals": str(vocals), "other": str(other)}
        return None

    def rnnoise_denoise(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        Optional RNNoise hook.
        If bindings are unavailable, passthrough.
        """
        if not self.enable_rnnoise:
            return y
        return y

    def bandwidth_extension(self, y: np.ndarray, sr: int, amount: float = 0.04) -> np.ndarray:
        """
        Lightweight psychoacoustic bandwidth extension fallback.
        """
        from dsp import high_freq_synthesis
        return high_freq_synthesis(y, sr, mix=amount)
