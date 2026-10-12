"""Stabilize / destabilize round-trip.

Stabilize warps every frame into reference-locked space with S @ H_to_ref[i];
Destabilize inverts the exact same stored matrix, so the round-trip is exact
by construction. The canvas transform S and size are recorded in
TrackData.stab for Destabilize to consume.
"""

from __future__ import annotations

import cv2
import numpy as np

from .types import TrackData


def _canvas(track: TrackData, mode: str, padding: int):
    w, h = track.plate_size
    if mode == "lock_full_frame":
        S = np.array([[1, 0, padding], [0, 1, padding], [0, 0, 1]], dtype=np.float64)
        size = (w + 2 * padding, h + 2 * padding)
    elif mode == "crop_roi":
        x0, y0 = np.floor(track.corners_ref.min(axis=0)) - padding
        x1, y1 = np.ceil(track.corners_ref.max(axis=0)) + padding
        S = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], dtype=np.float64)
        size = (int(x1 - x0), int(y1 - y0))
    else:
        raise ValueError(f"unknown stabilize mode: {mode}")
    return S, size


def stabilize(frames, track: TrackData, mode: str = "lock_full_frame", padding: int = 0):
    """Warp frames into reference-locked space.

    frames: iterable of (H,W,C) or (H,W) uint8/float arrays at plate size.
    Returns (stabilized_frames list, track copy with .stab set).
    """
    S, size = _canvas(track, mode, padding)
    out = [
        cv2.warpPerspective(f, S @ track.H_to_ref[i], size, flags=cv2.INTER_CUBIC)
        for i, f in enumerate(frames)
    ]
    tr = track.copy()
    tr.stab = {"S": S.tolist(), "canvas_size": list(size), "mode": mode, "padding": padding}
    return out, tr


def destabilize(processed, track: TrackData, originals=None, mask=None, feather: float = 0.0):
    """Reapply original motion to processed stabilized frames.

    processed: frames in stabilized space (canvas size from track.stab).
    originals: optional plate-size frames to composite over.
    mask: optional (H,W) or per-frame (B,H,W) float 0-1 blend mask in
          *stabilized* space; defaults to the warp coverage. Feather blurs
          the mask edge (px, sigma).
    Returns list of plate-size frames.
    """
    if track.stab is None:
        raise ValueError("track has no stabilize info; feed the track_data output of Stabilize")
    S = np.asarray(track.stab["S"], dtype=np.float64)
    cw, ch = track.stab["canvas_size"]
    w, h = track.plate_size

    out = []
    for i, frame in enumerate(processed):
        M = S @ track.H_to_ref[i]
        restored = cv2.warpPerspective(
            frame, M, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP
        )
        if originals is None:
            out.append(restored)
            continue

        if mask is not None:
            m = (mask[i] if mask.ndim == 3 else mask).astype(np.float32)
        else:
            m = np.ones((ch, cw), dtype=np.float32)
        m_plate = cv2.warpPerspective(m, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        if feather > 0:
            # Pull the edge inward before blurring so feather never samples
            # outside the valid warp region.
            k = max(int(feather) | 1, 3)
            m_plate = cv2.erode(m_plate, np.ones((k, k), np.float32))
            m_plate = cv2.GaussianBlur(m_plate, (0, 0), feather)
        m_plate = np.clip(m_plate, 0.0, 1.0)
        if restored.ndim == 3:
            m_plate = m_plate[..., None]

        orig = originals[i].astype(np.float32)
        comp = restored.astype(np.float32) * m_plate + orig * (1.0 - m_plate)
        out.append(comp.astype(originals[i].dtype) if np.issubdtype(originals[i].dtype, np.integer) else comp)
    return out
