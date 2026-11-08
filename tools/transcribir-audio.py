"""Transcribe un adjunto local sin enviar la grabación a terceros."""
import sys
from pathlib import Path

import av
import numpy as np
from faster_whisper import WhisperModel

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1])
target = Path(sys.argv[2])
model_name = sys.argv[3] if len(sys.argv) > 3 else "tiny"
use_vad = "--no-vad" not in sys.argv[4:]
allow_download = "--download-model" in sys.argv[4:]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
samples = []
with av.open(str(source)) as recording:
    print(f"Duración: {recording.duration / av.time_base:.0f} segundos", flush=True)
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    for frame in recording.decode(audio=0):
        for converted in resampler.resample(frame):
            samples.append(converted.to_ndarray().flatten())
    for converted in resampler.resample(None):
        samples.append(converted.to_ndarray().flatten())
print(f"Modelo: {model_name}; filtro de voz: {use_vad}", flush=True)
model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4,
                     download_root=str(root / "tools" / ".media-models"), local_files_only=not allow_download)
segments, _ = model.transcribe(np.concatenate(samples).astype(np.float32) / 32768,
                              language="es", vad_filter=use_vad, beam_size=5,
                              condition_on_previous_text=False)
with target.open("w", encoding="utf-8") as output:
    for segment in segments:
        line = f"[{segment.start:.1f}–{segment.end:.1f}] {segment.text.strip()}"
        print(line, flush=True)
        output.write(line + "\n")
        output.flush()
