"""Pruebas sin frameworks externos y smoke con NanoTrack real opcional."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from nanotrack_engine import Engine, finite, scaled_roi


class TestCore(unittest.TestCase):
    def test_scaling(self):
        self.assertEqual(scaled_roi({"x": 20, "y": 10, "w": 40, "h": 20},
                                    100, 50, 200, 100), [40, 20, 80, 40])

    def test_aspect(self):
        with self.assertRaises(ValueError):
            scaled_roi({"x": 1, "y": 1, "w": 10, "h": 10}, 100, 100, 200, 100)

    def test_nan(self):
        with self.assertRaises(ValueError):
            finite("nan", "test")

    def test_bounds(self):
        with self.assertRaises(ValueError):
            scaled_roi({"x": -2, "y": 0, "w": 30, "h": 30}, 100, 100, 100, 100)


def smoke_real():
    """Genera un video sintético y rastrea frames con dos ONNX reales."""
    import cv2
    import numpy as np
    fd, video = tempfile.mkstemp(suffix=".avi")
    os.close(fd)
    writer = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (320, 240))
    if not writer.isOpened():
        raise RuntimeError("No se pudo abrir VideoWriter")
    rng = np.random.default_rng(7)
    pattern = rng.integers(0, 255, (56, 56, 3), dtype=np.uint8)
    try:
        for f in range(10):
            img = np.zeros((240, 320, 3), dtype=np.uint8)
            # Un objeto con textura desplazado realmente en el tiempo.
            x, y = 80 + f * 4, 75 + f * 2
            img[y:y + 56, x:x + 56] = pattern
            writer.write(img)
        writer.release()
        engine = Engine(cv2)
        try:
            data = engine.init(dict(
                video=video, comp_name="CI", layer_name="video",
                layer_start=0.0, source_width=320, source_height=240,
                mask_name="TomoTrackAI - OBJETIVO",
                run_id="ci-test-mask-0001",
                mask_shape={"vertices": [[80,75],[136,75],[136,131],[80,131]],
                            "inTangents": [[0,0]]*4,"outTangents": [[0,0]]*4,"closed": True},
                start_seconds=0.0, end_seconds=0.7,
                bbox={"x":80, "y":75, "w":56, "h":56},
                confidence_threshold=0.0))
            assert data["first"]["frame"] == 0, data
            result = engine.step(3)
            assert result["total"] >= 2, result
            for s in result["new"]:
                assert 0 <= s["confidence"] <= 1
                assert s["bbox"][2] > 0 and s["bbox"][3] > 0
            with tempfile.TemporaryDirectory() as td:
                engine.snapshot(str(Path(td) / "motion.json"))
                serialized = json.loads((Path(td) / "motion.json").read_text())
                assert len(serialized["samples"]) >= 2
                assert serialized["engine"] == "OpenCV NanoTrack V2"
                assert serialized["run_id"] == "ci-test-mask-0001"
                assert len(serialized["anchors"]) == 1
                assert len(serialized["anchors"][0]["shape"]["vertices"]) == 4
            # Comprobar que reseed mantiene máscara corregida y corta trayectoria futura
            correction = {"vertices": [[92,81],[146,81],[146,138],[92,138]],
                          "inTangents": [[0,0]]*4, "outTangents": [[0,0]]*4,"closed": True}
            restored = engine.reseed({"source_seconds": 2/12,
                                     "bbox": {"x":92,"y":81,"w":54,"h":57},
                                     "mask_shape": correction})
            assert restored["corrected"]["frame"] == 2, restored
            assert len(engine.anchors) == 2, engine.anchors
            assert engine.samples[-1]["frame"] == 2
            print("SMOKE NanoTrack real: OK, muestras", result["total"])
        finally:
            engine.close()
    finally:
        try:
            writer.release()
        except Exception:
            pass
        os.unlink(video)


if __name__ == "__main__":
    unittest.main(exit=False, verbosity=2)
    if os.environ.get("TOMOTRACK_SMOKE_REAL") == "1":
        smoke_real()
