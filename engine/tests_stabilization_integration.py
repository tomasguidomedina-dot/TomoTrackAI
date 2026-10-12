"""End-to-end stabilizer with a real, encoded AVI plate and JSON track export."""
import math
import os
import tempfile
import unittest
import json
import numpy as np
import cv2
from platetrack_engine import Engine

W,H=400,260
rng=np.random.default_rng(1337)
BASE=rng.integers(16,235,(H,W,3),dtype=np.uint8)
# Distinct stable background features. A moving foreground is deliberately
# outside the chosen reference region (as instructed in the UI).
BOX=[70,45,240,155]
MASK=dict(vertices=[[70,45],[310,45],[310,200],[70,200]],
          inTangents=[[0,0]]*4,outTangents=[[0,0]]*4,closed=True)

class TestStabilizationIntegration(unittest.TestCase):
    def test_encoded_avi_tracks_and_stabilizes_without_replacing_object_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=os.path.join(tmp,"stabilization.avi")
            writer=cv2.VideoWriter(video,cv2.VideoWriter_fourcc(*"MJPG"),15,(W,H))
            self.assertTrue(writer.isOpened())
            try:
                for i in range(37):
                    M=cv2.getRotationMatrix2D((W/2,H/2),-math.sin(i*.28)*.65,1)
                    M[0,2]+=i*.34+math.sin(i*.91)*1.25
                    M[1,2]+=math.cos(i*.93)*1.3
                    frame=cv2.warpAffine(BASE,M,(W,H),flags=cv2.INTER_LINEAR)
                    writer.write(frame)
            finally:writer.release()
            engine=Engine(cv2)
            try:
                engine.init(dict(video=video,source_width=W,source_height=H,
                    comp_name="Scene",layer_name="Video",layer_start=0.,
                    run_id="stabilizer-test",mask_name="TomoTrackAI - OBJETIVO",
                    start_seconds=0,end_seconds=37/15.,
                    mask_shape=MASK,bbox=dict(x=70,y=45,w=240,h=155),
                    mode="stabilize",tracking_model="similarity",ecc_refine=True,
                    confidence_threshold=.24))
                for _ in range(15):
                    r=engine.step(12)
                    if r["ended"] or r["needs_correction"]:break
                self.assertTrue(r["ended"],"No logró seguir una escena sintética simple")
                self.assertEqual(len(engine.samples),37)
                response=engine.stabilize(dict(mode="smooth",radius=8,strength=1.,auto_crop=False))
                self.assertEqual(response["frames"],37)
                with tempfile.NamedTemporaryFile(suffix=".json",delete=False) as fp:
                    outfile=fp.name
                try:
                    engine.snapshot(outfile)
                    track=json.load(open(outfile))
                    self.assertEqual(track["tracking_mode"],"stabilize")
                    self.assertEqual(track["stabilization"]["mode"],"smooth")
                    self.assertEqual(len(track["stabilization"]["samples"]),37)
                    self.assertIn("matrix",track["stabilization"]["samples"][-1])
                    self.assertTrue(np.isfinite(track["stabilization"]["samples"][-1]["matrix"]).all())
                    self.assertNotIn("nanotrack",json.dumps(track).lower())
                finally:os.remove(outfile)
            finally:engine.close()

if __name__=="__main__":
 unittest.main(verbosity=2)
