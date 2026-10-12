#!/usr/bin/env python3
"""TomoTrackAI 0.2: NanoTrack V2, motor JSONL independente de AE.

El proceso sigue fotogramas REALES del archivo fuente. El efecto nativo
solo selecciona el ROI; el puente escribe keyframes en AE via ExtendScript.
"""
import json
import math
import os
import sys
from pathlib import Path


def finite(value, name):
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("Valor no finito: " + name)
    return v


def response(**parts):
    sys.stdout.write(json.dumps(parts, separators=(",", ":"), allow_nan=False) + "\n")
    sys.stdout.flush()


def scaled_roi(box, source_w, source_h, frame_w, frame_h):
    sw, sh = finite(source_w, "source_width"), finite(source_h, "source_height")
    if min(sw, sh, frame_w, frame_h) <= 0:
        raise ValueError("Dimensiones del video invalidas")
    if abs((sw / sh) / (frame_w / frame_h) - 1) > 0.015:
        raise ValueError("La relacion de aspecto de AE y del video no coincide")
    fx, fy = frame_w / sw, frame_h / sh
    roi = [int(round(finite(box[k], k) * f)) for k, f in
           zip(("x", "y", "w", "h"), (fx, fy, fx, fy))]
    x, y, w, h = roi
    if w < 8 or h < 8 or x < 0 or y < 0 or x + w > frame_w or y + h > frame_h:
        raise ValueError("Seleccion fuera del video o demasiado pequena")
    return roi


class Engine:
    def __init__(self, cv2):
        self.cv2 = cv2
        self.cap = None
        self.tracker = None
        self.samples = []
        self.metadata = None
        self.index = 0
        self.end_index = 0
        self.bad = 0
        self.threshold = 0.24

    def close(self):
        if self.cap is not None:
            self.cap.release()
        self.cap, self.tracker = None, None

    def frame_at(self, index):
        self.cap.set(self.cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = self.cap.read()
        if not ok:
            raise ValueError("No se pudo leer el fotograma " + str(index))
        return frame

    def create_tracker(self, frame, roi):
        params = self.cv2.TrackerNano_Params()
        params.backbone, params.neckhead = self.model_paths
        tracker = self.cv2.TrackerNano_create(params)
        tracker.init(frame, tuple(roi))
        self.tracker = tracker

    def record(self, box, confidence, tracked=True):
        b = [finite(v, "bbox") for v in box]
        if len(b) != 4 or b[2] < 1 or b[3] < 1:
            raise ValueError("NanoTrack produjo una caja invalida")
        score = max(0.0, min(1.0, finite(confidence, "confidence")))
        low = not tracked or score < self.threshold
        self.bad = self.bad + 1 if low else 0
        record = dict(frame=self.index, source_time=round(self.index / self.fps, 8),
                      bbox=b, cx=round(b[0] + b[2] / 2, 5),
                      cy=round(b[1] + b[3] / 2, 5),
                      confidence=round(score, 5), low_confidence=low)
        self.samples.append(record)
        return record

    def init(self, job):
        self.close()
        self.samples = []
        self.metadata = None
        self.cv2.setNumThreads(2)
        root = Path(os.environ.get("TOMOTRACK_MODELS", str(Path.home() /
                       "Library/Application Support/TomoTrackAI2/models")))
        self.model_paths = [str(root / x) for x in
                            ("nanotrack_backbone_sim.onnx", "nanotrack_head_sim.onnx")]
        if any(not Path(p).is_file() or Path(p).stat().st_size < 100000 for p in self.model_paths):
            raise ValueError("Faltan modelos NanoTrack V2 en " + str(root) +
                             ". Reejecuta el instalador para descargarlos.")
        video = Path(job["video"])
        if not video.is_file():
            raise ValueError("El archivo de video no existe: " + str(video))
        self.cap = self.cv2.VideoCapture(str(video))
        if not self.cap.isOpened():
            raise ValueError("OpenCV no pudo abrir el video fuente")
        self.fps = finite(self.cap.get(self.cv2.CAP_PROP_FPS), "fps")
        if not 1.0 <= self.fps <= 240.0:
            raise ValueError("FPS del video invalido")
        num_frames = int(self.cap.get(self.cv2.CAP_PROP_FRAME_COUNT))
        start = finite(job["start_seconds"], "start_seconds")
        end = finite(job["end_seconds"], "end_seconds")
        self.index = max(0, int(round(start * self.fps)))
        self.end_index = max(0, int(math.ceil(end * self.fps) - 1))
        if num_frames > 0:
            self.end_index = min(self.end_index, num_frames - 1)
        if self.end_index <= self.index:
            raise ValueError("No quedan fotogramas para analizar")
        frame = self.frame_at(self.index)
        self.height, self.width = frame.shape[:2]
        self.source_width = finite(job["source_width"], "source_width")
        self.source_height = finite(job["source_height"], "source_height")
        roi = scaled_roi(job["bbox"], self.source_width, self.source_height,
                         self.width, self.height)
        self.threshold = max(0.0, min(1.0, finite(job.get("confidence_threshold", .24), "umbral")))
        self.create_tracker(frame, roi)
        self.metadata = {k: job[k] for k in ("video", "comp_name", "layer_name", "layer_start")}
        self.bad = 0
        first = self.record(roi, 1.0)
        return dict(first=first, fps=self.fps, width=self.width, height=self.height,
                    last_frame=self.end_index)

    def step(self, count=4):
        if self.tracker is None:
            raise ValueError("Primero hay que iniciar el seguimiento")
        records = []
        for _ in range(max(1, min(20, int(count)))):
            if self.index >= self.end_index:
                break
            ok, frame = self.cap.read()
            if not ok:
                break
            self.index += 1
            tracked, bbox = self.tracker.update(frame)
            try:
                score = self.tracker.getTrackingScore()
            except Exception:
                score = 1.0 if tracked else 0.0
            if not tracked:
                bbox = self.samples[-1]["bbox"]
            records.append(self.record(bbox, score, tracked))
            if self.bad >= 5:
                break
        return dict(new=records, total=len(self.samples), frame=self.index,
                    ended=(self.index >= self.end_index or not records),
                    needs_correction=(self.bad >= 5))

    def reseed(self, cmd):
        if self.cap is None:
            raise ValueError("No hay ninguna sesion iniciada")
        index = max(0, int(round(finite(cmd["source_seconds"], "source_seconds") * self.fps)))
        if index > self.end_index:
            raise ValueError("El fotograma esta fuera del clip")
        frame = self.frame_at(index)
        box = scaled_roi(cmd["bbox"], self.source_width, self.source_height,
                         self.width, self.height)
        self.create_tracker(frame, box)
        self.index = index
        self.samples = [s for s in self.samples if s["frame"] < index]
        self.bad = 0
        return dict(corrected=self.record(box, 1.0), total=len(self.samples))

    def snapshot(self, path):
        if self.metadata is None:
            raise ValueError("No existe trayectoria")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = dict(version="0.2", engine="OpenCV NanoTrack V2",
                    source_file=self.metadata["video"],
                    comp_name=self.metadata["comp_name"],
                    layer_name=self.metadata["layer_name"],
                    layer_start=self.metadata["layer_start"],
                    fps=self.fps, width=self.width, height=self.height,
                    source_width=self.source_width, source_height=self.source_height,
                    samples=self.samples)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf8")
        tmp.replace(target)
        return dict(file=str(target), samples=len(self.samples))


def serve():
    try:
        import cv2
        if not hasattr(cv2, "TrackerNano_create"):
            raise RuntimeError("OpenCV sin TrackerNano_create")
    except Exception as exc:
        response(ok=False, error="Motor OpenCV no disponible: " + str(exc))
        return 2
    engine = Engine(cv2)
    response(ok=True, ready=True, opencv=cv2.__version__)
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                name = request.get("cmd")
                if name == "init":
                    result = engine.init(request["job"])
                elif name == "step":
                    result = engine.step(request.get("count", 4))
                elif name == "reseed":
                    result = engine.reseed(request)
                elif name == "snapshot":
                    result = engine.snapshot(request["output"])
                elif name == "close":
                    response(ok=True, closed=True)
                    break
                else:
                    raise ValueError("Comando no reconocido: " + str(name))
                response(ok=True, **result)
            except Exception as exc:
                response(ok=False, error=str(exc))
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    sys.exit(serve())
