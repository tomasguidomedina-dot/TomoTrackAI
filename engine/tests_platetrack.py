"""PlateTrack engine acceptance tests (no ONNX and no network).
For every fixture, Scale and Rotation must arise from one fitted 3x3 matrix.
"""
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from platetrack_engine import StreamingPlate, Engine, homogeneous_point

W,H=360,280
BOX=(130,98,100,84)
CENTER=(180,140)

def make_frame(angle=0,scale=1,dx=0,dy=0):
    rng=np.random.default_rng(8675309)
    initial=np.zeros((H,W,3),dtype=np.uint8)
    pattern=rng.integers(20,242,(BOX[3],BOX[2],3),dtype=np.uint8)
    x,y,w,h=BOX
    initial[y:y+h,x:x+w]=pattern
    m=cv2.getRotationMatrix2D(CENTER,-angle,scale)
    m[0,2]+=dx;m[1,2]+=dy
    return cv2.warpAffine(initial,m,(W,H),flags=cv2.INTER_LINEAR)

class TestGeom(unittest.TestCase):
    def sequence(self,gen,model="similarity",ecc=True):
        start=make_frame()
        plate=StreamingPlate(cv2,model=model,ecc=ecc)
        x,y,w,h=BOX
        plate.start(start,[[x,y],[x+w,y],[x+w,y+h],[x,y+h]])
        sample=None
        for i in range(1,31):
            sample=plate.step(make_frame(*gen(i)))
            self.assertTrue(np.isfinite(sample["matrix"]).all())
            self.assertTrue(math.isfinite(sample["scale_factor"]))
            self.assertGreater(sample["points"],0)
        return sample
    def test_stationary_has_no_fake_scale(self):
        sample=self.sequence(lambda i:(0,1,0,0))
        self.assertLess(abs(sample["rotation_deg"]),1.0)
        self.assertLess(abs(sample["scale_factor"]-1),.02)
    def test_translation_without_rotation(self):
        sample=self.sequence(lambda i:(0,1,1.4*i,.7*i))
        self.assertLess(abs(sample["rotation_deg"]),2.0)
        self.assertLess(abs(sample["scale_factor"]-1),.04)
        self.assertLess(abs(sample["cx"]-CENTER[0]-42),4)
    def test_zoom_only(self):
        sample=self.sequence(lambda i:(0,1+.006*i,0,0))
        self.assertLess(abs(sample["rotation_deg"]),2.0)
        self.assertLess(abs(sample["scale_factor"]-1.18),.05)
    def test_pure_rotation_does_not_scale(self):
        sample=self.sequence(lambda i:(i,1,0,0))
        self.assertLess(abs(sample["rotation_deg"]-30),4.0)
        self.assertLess(abs(sample["scale_factor"]-1),.05,
           "AABB inflation must NOT become Null scale.")
    def test_zoom_and_rotation(self):
        sample=self.sequence(lambda i:(i*.7,1+.005*i,0,0))
        self.assertLess(abs(sample["rotation_deg"]-21),4.0)
        self.assertLess(abs(sample["scale_factor"]-1.15),.06)
    def test_actual_engine_snapshot_has_matrix(self):
        fd,p=tempfile.mkstemp(suffix=".avi")
        os.close(fd)
        writer=cv2.VideoWriter(p,cv2.VideoWriter_fourcc(*"MJPG"),15,(W,H))
        self.assertTrue(writer.isOpened())
        try:
            for i in range(24):
                writer.write(make_frame(i*.8,1+i*.004))
            writer.release()
            x,y,w,h=BOX
            shape=dict(vertices=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]],
                       inTangents=[[0,0]]*4,outTangents=[[0,0]]*4,closed=True)
            engine=Engine(cv2)
            try:
                engine.init(dict(video=p,comp_name="test",layer_name="source",layer_start=0,
                    run_id="platetrack-accept",mask_name="TomoTrackAI - OBJETIVO",
                    source_width=W,source_height=H,start_seconds=0,end_seconds=23/15+.05,
                    bbox={"x":x,"y":y,"w":w,"h":h},mask_shape=shape,tracking_model="similarity",ecc_refine=True))
                result=engine.step(12)
                self.assertGreater(len(result["new"]),0)
                with tempfile.TemporaryDirectory() as tmp:
                    output=str(Path(tmp)/"track.json")
                    engine.snapshot(output)
                    track=json.loads(Path(output).read_text())
                    self.assertEqual(track["engine"],"PlateTrack OpenCV (Streaming)")
                    self.assertIn("matrix",track["samples"][-1])
                    self.assertIn("scale_factor",track["samples"][-1])
                    self.assertNotIn("nanotrack",json.dumps(track).lower())
            finally:engine.close()
        finally:
            writer.release()
            os.unlink(p)
if __name__=="__main__":
    unittest.main(verbosity=2)
