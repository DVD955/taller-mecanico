"""Analiza los adjuntos localmente. No envía grabaciones a un servicio externo."""
from pathlib import Path
import sys
import json

import av
import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analisis' / 'referencias'
OUT.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    audio = Path(sys.argv[1])
    video = Path(sys.argv[2])
    start_at = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    with av.open(str(video)) as container:
        duration = container.duration / av.time_base
        stream = container.streams.video[0]
        metadata = dict(duration_seconds=duration, width=stream.width, height=stream.height)
        for index, time in enumerate((5, duration * .25, duration * .5, duration * .75, max(0, duration - 10))):
            container.seek(int(time * av.time_base))
            for frame in container.decode(stream):
                if float(frame.time or 0) >= time:
                    frame.to_image().save(OUT / f'video-{index + 1}.jpg')
                    break
    (OUT / 'video-metadatos.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Capturas del video preparadas.', metadata, flush=True)
    model = WhisperModel('tiny', device='cpu', compute_type='int8', cpu_threads=4,
                         download_root=str(ROOT / 'tools' / '.media-models'))
    # PyAV 19 retiró metadata_errors; decodificar aquí mantiene la revisión local.
    samples = []
    with av.open(str(audio)) as recording:
        audio_duration = recording.duration / av.time_base
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        for frame in recording.decode(audio=0):
            for converted in resampler.resample(frame):
                samples.append(converted.to_ndarray().flatten())
        for converted in resampler.resample(None):
            samples.append(converted.to_ndarray().flatten())
    waveform = np.concatenate(samples).astype(np.float32) / 32768.0
    print(f'Audio preparado: {audio_duration:.1f} segundos.', flush=True)
    segments, info = model.transcribe(waveform[int(start_at * 16000):], language='es', vad_filter=True, beam_size=3)
    with (OUT / 'audio-transcripcion.txt').open('a' if start_at else 'w', encoding='utf-8') as result:
        for segment in segments:
            line = f'[{segment.start + start_at:.1f}–{segment.end + start_at:.1f}] {segment.text.strip()}'
            result.write(line + '\n')
            result.flush()
            print(line, flush=True)
    print('Transcripción terminada.', flush=True)


if __name__ == '__main__':
    main()
