"""Optical rotation estimator independent from NanoTrack.

Design goals:
- never fabricate angle when tracking confidence or feature geometry is poor;
- never integrate small noisy frame-to-frame rotations;
- model angle relative to a keyframe of actual object feature coordinates;
- constrain tracking to the observed NanoTrack ROI and initial mask;
- protect static/translation/scale-only footage against apparent rotation.

No cv2/numpy imports at module import time: keep the known-good NanoTrack
startup path unchanged until the user explicitly enables rotation.
"""
import math


class StableRotation:
    def __init__(self, cv2, *, deadband_degrees=1.25, smoothing=0.42):
        self.cv2 = cv2
        self.deadband = deadband_degrees
        self.smoothing = smoothing
        self.reset()

    def reset(self):
        self.prev_gray = None
        self.prev_points = None
        self.ref_points = None
        self.ref_box = None
        self.anchor_angle = 0.0
        self.angle = 0.0
        self.last_raw = 0.0
        self.inliers = 0
        self.reliable = False
        self.reason = "Sin análisis"
        self.good_frames = 0

    def _mask_corners(self, gray, box, polygon=None):
        import numpy as np
        height, width = gray.shape[:2]
        x, y, w, h = [float(v) for v in box]
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1 = min(width, int(math.ceil(x+w)))
        y1 = min(height, int(math.ceil(y+h)))
        if x1-x0 < 20 or y1-y0 < 20:
            return None
        mask = np.zeros(gray.shape[:2], dtype=np.uint8)
        mask[y0:y1, x0:x1] = 255
        if polygon and len(polygon) >= 3:
            vertices = np.rint(np.asarray(polygon, dtype=np.float32)).astype(np.int32)
            poly = np.zeros_like(mask)
            self.cv2.fillPoly(poly, [vertices], 255)
            mask = self.cv2.bitwise_and(mask, poly)
        return self.cv2.goodFeaturesToTrack(
            gray, maxCorners=110, qualityLevel=0.012, minDistance=5,
            blockSize=5, mask=mask)

    def start(self, frame, box, polygon=None, angle=0.0):
        self.reset()
        self.anchor_angle = float(angle)
        self.angle = float(angle)
        self.prev_gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        corners = self._mask_corners(self.prev_gray, box, polygon)
        self.prev_points = corners
        self.ref_points = corners.copy() if corners is not None else None
        self.ref_box = [float(v) for v in box]
        self.reason = "Sin textura suficiente" if corners is None or len(corners)<16 else "Analizando"

    def _reanchor(self, gray, box):
        points = self._mask_corners(gray, box)
        self.anchor_angle = self.angle
        self.ref_box = [float(v) for v in box]
        self.prev_gray = gray
        self.prev_points = points
        self.ref_points = points.copy() if points is not None else None
        self.good_frames = 0

    @staticmethod
    def _coverage(points, box):
        import numpy as np
        if len(points)<3:
            return 0.0
        x, y, w, h = [float(v) for v in box]
        span = np.ptp(points, axis=0)
        return float((span[0]*span[1]) / max(1.0,w*h))

    def step(self, frame, box, nanotrack_score):
        import numpy as np
        gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        self.inliers = 0
        self.reliable = False

        if nanotrack_score < 0.50:
            self.reason = "Objeto con baja confianza"
            self.prev_gray = gray
            self.prev_points = None  # never keep optical points through an occlusion
            return self._result()

        if (self.prev_gray is None or self.prev_points is None
                or self.ref_points is None or len(self.prev_points)<16):
            self._reanchor(gray, box)
            self.reason = "Recalibrando puntos"
            return self._result()

        prev = self.prev_points
        nxt, status, _ = self.cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, prev, None, winSize=(21,21), maxLevel=3,
            criteria=(self.cv2.TERM_CRITERIA_EPS|self.cv2.TERM_CRITERIA_COUNT,30,0.015))
        if nxt is None or status is None:
            self._reanchor(gray, box)
            self.reason = "No se encontraron correspondencias"
            return self._result()

        back, reverse_status, _ = self.cv2.calcOpticalFlowPyrLK(
            gray, self.prev_gray, nxt, None, winSize=(21,21), maxLevel=3,
            criteria=(self.cv2.TERM_CRITERIA_EPS|self.cv2.TERM_CRITERIA_COUNT,30,0.015))
        if back is None or reverse_status is None:
            self._reanchor(gray, box)
            self.reason = "Flujo óptico no confirmado"
            return self._result()

        forward_error = np.linalg.norm(back.reshape(-1,2)-prev.reshape(-1,2),axis=1)
        good = ((status.reshape(-1)==1)&(reverse_status.reshape(-1)==1)
                & np.isfinite(forward_error)&(forward_error<1.0))
        # A landmark must still be inside NanoTrack's current object box.
        x,y,w,h = [float(v) for v in box]
        updated=nxt.reshape(-1,2)
        inside=((updated[:,0]>=x+1)&(updated[:,0]<=x+w-1)
                &(updated[:,1]>=y+1)&(updated[:,1]<=y+h-1))
        good &= inside
        after=updated[good]
        refs=self.ref_points.reshape(-1,2)[good]
        self.prev_gray=gray
        self.prev_points=after.reshape(-1,1,2).astype(np.float32)
        self.ref_points=refs.reshape(-1,1,2).astype(np.float32)

        if (len(after)<16 or self._coverage(after,box)<0.16
                or self._coverage(refs,self.ref_box)<0.16):
            self._reanchor(gray, box)
            self.reason = "Pocos puntos bien distribuidos"
            return self._result()

        transform, accepted=self.cv2.estimateAffinePartial2D(
            refs,after,method=self.cv2.RANSAC,
            ransacReprojThreshold=1.8,maxIters=1200,confidence=0.995,
            refineIters=15)
        if transform is None or accepted is None:
            self.reason = "Movimiento no consistente"
            return self._result()

        n=int(np.count_nonzero(accepted))
        self.inliers=n
        ratio=n/len(after)
        a=float(transform[0,0]); b=float(transform[1,0])
        scale=math.hypot(a,b)
        raw=self.anchor_angle+math.degrees(math.atan2(b,a))
        # An affine transform estimated from static points should have
        # near-zero rotation regardless of pure translations / uniform zooms.
        if (n<14 or ratio<0.78 or not 0.60<scale<1.75 or
                not math.isfinite(raw) or abs(raw-self.angle)>9.0):
            self.reason = "Giro no confiable"
            # Don't publish a spurious angle; reanchor if far from known pose.
            if abs(raw-self.angle)>9.0:
                self._reanchor(gray,box)
            return self._result()

        # Deadband is evaluated relative to the *last output*, not accumulated
        # frame-to-frame; it absorbs sub-degree noise without drift.
        delta=raw-self.angle
        if abs(delta)<self.deadband:
            self.good_frames=0
            self.reason = "Estable (sin giro)"
            self.reliable=True
            return self._result()

        # Require two consistent frames before committing a substantial turn.
        if self.good_frames==0:
            self.good_frames=1
            self.last_raw=raw
            self.reason="Confirmando giro"
            return self._result()
        if abs(raw-self.last_raw)>6.0 or (raw-self.angle)*(self.last_raw-self.angle)<0:
            self.good_frames=1
            self.last_raw=raw
            self.reason="Giro inestable"
            return self._result()

        self.good_frames+=1
        self.last_raw=raw
        self.angle+=max(-4.0,min(4.0,delta*self.smoothing))
        self.reliable=True
        self.reason="Giro confirmado"
        if self.good_frames>=18 or len(after)<25:
            self._reanchor(gray,box)
        return self._result()

    def _result(self):
        return dict(rotation_deg=round(float(self.angle),4),
                    rotation_valid=bool(self.reliable),
                    rotation_inliers=int(self.inliers),
                    rotation_reason=self.reason)
