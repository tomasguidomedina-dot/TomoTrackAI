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


class OpticalRotation:
    """KLT + RANSAC para ángulos relativos; NanoTrack sigue controlando la posición.

    Si faltan puntos fiables, conserva el último ángulo en vez de inventar una
    rotación. Se usa una máscara poligonal para sembrar las esquinas del objeto.
    """

    def __init__(self, cv2, enabled):
        self.cv2 = cv2
        self.enabled = bool(enabled)
        self.prev_gray = None
        self.points = None
        self.angle = 0.0
        self.valid = False
        self.inliers = 0
        self.iteration = 0

    def _corners(self, gray, box, polygon=None):
        import numpy as np
        h, w = gray.shape[:2]
        x, y, bw, bh = [float(v) for v in box]
        mask = np.zeros((h, w), dtype=np.uint8)
        xa, ya = max(0, int(x)), max(0, int(y))
        xb, yb = min(w, int(math.ceil(x + bw))), min(h, int(math.ceil(y + bh)))
        if xb - xa < 10 or yb - ya < 10:
            return None
        mask[ya:yb, xa:xb] = 255
        if polygon is not None and len(polygon) >= 3:
            poly = np.rint(np.asarray(polygon, dtype=np.float32)).astype(np.int32)
            poly_mask = np.zeros_like(mask)
            self.cv2.fillPoly(poly_mask, [poly], 255)
            mask = self.cv2.bitwise_and(mask, poly_mask)
        pts = self.cv2.goodFeaturesToTrack(
            gray, maxCorners=110, qualityLevel=0.015,
            minDistance=4, blockSize=5, mask=mask)
        return pts if pts is not None and len(pts) >= 8 else None

    def start(self, frame, box, polygon=None, angle=0.0):
        self.angle = float(angle)
        self.prev_gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY) if self.enabled else None
        self.points = self._corners(self.prev_gray, box, polygon) if self.enabled else None
        self.valid = False
        self.inliers = 0
        self.iteration = 0

    def step(self, frame, box, confidence=1.0):
        if not self.enabled:
            return 0.0, False, 0
        import numpy as np
        gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        self.iteration += 1
        self.valid = False
        self.inliers = 0
        if self.prev_gray is not None and self.points is not None and confidence >= 0.18:
            nxt, status, _ = self.cv2.calcOpticalFlowPyrLK(
                self.prev_gray, gray, self.points, None,
                winSize=(21, 21), maxLevel=2,
                criteria=(self.cv2.TERM_CRITERIA_EPS | self.cv2.TERM_CRITERIA_COUNT, 20, 0.03))
            if nxt is not None and status is not None:
                good = status.ravel() == 1
                before = self.points.reshape(-1, 2)[good]
                after = nxt.reshape(-1, 2)[good]
                if len(before) >= 8:
                    transform, accepted = self.cv2.estimateAffinePartial2D(
                        before, after, method=self.cv2.RANSAC,
                        ransacReprojThreshold=3.0, maxIters=1500, confidence=0.995)
                    if transform is not None and accepted is not None:
                        count = int(np.count_nonzero(accepted))
                        ratio = count / len(before)
                        a, b = float(transform[0, 0]), float(transform[1, 0])
                        scale = math.hypot(a, b)
                        delta = math.degrees(math.atan2(b, a))
                        if (count >= 6 and ratio >= 0.58 and
                                0.82 <= scale <= 1.22 and abs(delta) <= 13.0):
                            if abs(delta) >= 0.1:
                                self.angle += delta
                            self.valid = True
                            self.inliers = count
                # Reseleccionar si restan pocos puntos o cada 10 frames.
                if len(after) >= 12 and self.iteration % 10 != 0:
                    self.points = after.reshape(-1, 1, 2).astype(np.float32)
                else:
                    self.points = self._corners(gray, box)
            else:
                self.points = self._corners(gray, box)
        else:
            self.points = self._corners(gray, box)
        self.prev_gray = gray
        return round(self.angle, 5), self.valid, self.inliers



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
        self.anchors = []
        self.index = 0
        self.end_index = 0
        self.bad = 0
        self.threshold = 0.24
        self.rotation = OpticalRotation(cv2, True)
        self.track_rotation = True
        self.track_scale = True

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

    def record(self, box, confidence, tracked=True, rotation=None):
        b = [finite(v, "bbox") for v in box]
        if len(b) != 4 or b[2] < 1 or b[3] < 1:
            raise ValueError("NanoTrack produjo una caja invalida")
        score = max(0.0, min(1.0, finite(confidence, "confidence")))
        low = not tracked or score < self.threshold
        self.bad = self.bad + 1 if low else 0
        angle, rot_ok, inliers = rotation if rotation is not None else (self.rotation.angle, False, 0)
        record = dict(frame=self.index, source_time=round(self.index / self.fps, 8),
                      bbox=b, cx=round(b[0] + b[2] / 2, 5),
                      cy=round(b[1] + b[3] / 2, 5),
                      rotation_deg=round(angle, 5),
                      rotation_valid=bool(rot_ok), rotation_inliers=int(inliers),
                      confidence=round(score, 5), low_confidence=low)
        self.samples.append(record)
        return record

    def init(self, job):
        self.close()
        self.samples = []
        self.metadata = None
        self.anchors = []
        self.cv2.setNumThreads(2)
        root = Path(os.environ.get("TOMOTRACK_MODELS", str(Path.home() /
                       "Library/Application Support/TomoTrackAI3/models")))
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
        self.track_scale = bool(job.get("track_scale", True))
        self.track_rotation = bool(job.get("track_rotation", True))
        self.create_tracker(frame, roi)
        self.metadata = {k: job[k] for k in ("video", "comp_name", "layer_name", "layer_start", "run_id", "mask_name")}
        shape = job.get("mask_shape")
        if not isinstance(shape, dict) or not shape.get("closed") or len(shape.get("vertices", [])) < 3:
            raise ValueError("Falta una máscara poligonal cerrada")
        self.rotation = OpticalRotation(self.cv2, self.track_rotation)
        # Vértices AE en coordenadas de fuente -> frame OpenCV.
        polygon = [[finite(x, "vertexX") * self.width / self.source_width,
                    finite(y, "vertexY") * self.height / self.source_height]
                   for x, y in shape["vertices"]]
        self.rotation.start(frame, roi, polygon=polygon, angle=0.0)
        self.anchors = [dict(frame=self.index, bbox=dict(job["bbox"]),
                             shape=shape, rotation_deg=0.0)]
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
            rot = self.rotation.step(frame, bbox, score if tracked else 0.0)
            records.append(self.record(bbox, score, tracked, rotation=rot))
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
        shape = cmd.get("mask_shape")
        if not isinstance(shape, dict) or len(shape.get("vertices", [])) < 3:
            raise ValueError("No hay contorno corregido")
        self.anchors = [a for a in self.anchors if a["frame"] < index]
        # El contorno corregido es una nueva referencia geométrica, pero el
        # ángulo global acumulado continúa para que el Null no salte.
        base_angle = self.samples[-1]["rotation_deg"] if self.samples else 0.0
        self.rotation.start(frame, box,
                            polygon=[[float(x) * self.width / self.source_width,
                                      float(y) * self.height / self.source_height]
                                     for x, y in shape["vertices"]],
                            angle=base_angle)
        self.anchors.append(dict(frame=index, bbox=dict(cmd["bbox"]),
                                 shape=shape, rotation_deg=base_angle))
        self.bad = 0
        return dict(corrected=self.record(box, 1.0), total=len(self.samples))

    def snapshot(self, path):
        if self.metadata is None:
            raise ValueError("No existe trayectoria")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = dict(version="0.4", engine="OpenCV NanoTrack V2 + KLT RANSAC",
                    source_file=self.metadata["video"],
                    comp_name=self.metadata["comp_name"],
                    layer_name=self.metadata["layer_name"],
                    layer_start=self.metadata["layer_start"],
                    mask_name=self.metadata["mask_name"],
                    run_id=self.metadata["run_id"],
                    track_scale=self.track_scale, track_rotation=self.track_rotation,
                    anchors=self.anchors,
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
