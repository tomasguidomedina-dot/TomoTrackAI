"""Video-file integration: correction at a low-confidence frame, resume, stabilize."""
import math
import os
import tempfile
import unittest
import numpy as np
import cv2
from platetrack_engine import Engine

W,H=400,280
Q=np.array([[80,55],[320,55],[320,225],[80,225]],dtype=np.float64)

def makematrix(i):
    A=cv2.getRotationMatrix2D((W/2,H/2),-.55*math.sin(i*.19),1+.0009*i)
    A[0,2]+=.28*i+1.15*math.sin(i*.47)
    A[1,2]+=1.0*math.cos(i*.41)
    return np.vstack([A,[0,0,1]])

def vertices(i):
    M=makematrix(i)
    return (M@np.column_stack([Q,np.ones(4)]).T).T[:,:2].tolist()

def shape(pts):
    return dict(vertices=pts,inTangents=[[0,0]]*4,outTangents=[[0,0]]*4,closed=True)

class TestManualPinInVideo(unittest.TestCase):
    def test_manual_pin_resume_with_original_reference_matrix(self):
        rng=np.random.default_rng(518)
        image=rng.integers(15,240,(H,W,3),dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmp:
            video=os.path.join(tmp,"camera.avi")
            vw=cv2.VideoWriter(video,cv2.VideoWriter_fourcc(*"MJPG"),15,(W,H))
            self.assertTrue(vw.isOpened())
            for i in range(34):
                vw.write(cv2.warpPerspective(image,makematrix(i),(W,H)))
            vw.release()
            engine=Engine(cv2)
            try:
                initial=shape(vertices(0))
                job=dict(video=video,source_width=W,source_height=H,comp_name="Camera",
                         layer_name="Video",layer_start=0.,run_id="test-pin",
                         mask_name="TomoTrackAI - OBJETIVO",start_seconds=0,
                         end_seconds=34/15.,bbox=dict(x=80,y=55,w=240,h=170),
                         mask_shape=initial,mode="stabilize",tracking_model="similarity",
                         ecc_refine=True,confidence_threshold=.24)
                engine.init(job)
                for i in range(20):
                    r=engine.step(1)
                    self.assertFalse(r["needs_correction"],"Scene test has rich texture.")
                self.assertEqual(engine.index,20)
                # Simulate 5 consecutive failures ending at frame 20. The
                # correction must not turn these into fake confidence=1.
                for rec in engine.samples[16:21]:
                    rec["confidence"]=0.
                    rec["low_confidence"]=True
                    rec["needs_correction"]=rec["frame"]==20
                original_q=engine.camera_reference_quad.copy()
                pin=shape(vertices(20))
                result=engine.reseed(dict(source_seconds=20/15.,
                                          bbox=dict(x=85,y=55,w=240,h=170),
                                          mask_shape=pin))
                self.assertEqual(result["manual_interpolated"],4)
                self.assertEqual(result["pin_frame"],20)
                np.testing.assert_allclose(engine.camera_reference_quad,original_q)
                self.assertTrue(engine.samples[20]["manual_pin"])
                self.assertTrue(all(engine.samples[i]["manual_interpolated"] for i in range(16,20)))
                self.assertTrue(all(engine.samples[i]["confidence"]==0 for i in range(16,20)))
                self.assertEqual(len(engine.samples),21)
                for i in range(21,34):
                    r=engine.step(1)
                    self.assertFalse(r["needs_correction"],"Tracking did not resume after pin")
                self.assertEqual(len(engine.samples),34)
                self.assertEqual(len(engine.anchors),2)
                self.assertTrue(all(x["frame"]==i for i,x in enumerate(engine.samples)))
                final=np.asarray(engine.samples[-1]["matrix"])
                ground=makematrix(33)
                corners=lambda matrix: (matrix@np.column_stack([Q,np.ones(4)]).T).T[:,:2]
                error=np.linalg.norm(corners(final)-corners(ground),axis=1).max()
                self.assertLess(error,7,("Different reference coordinate systems",error))
                solved=engine.stabilize(dict(mode="smooth",radius=8,strength=1,
                                             auto_crop=False))
                self.assertEqual(solved["manual_frames"],4)
                self.assertEqual(solved["pin_count"],1)
                self.assertEqual(solved["frames"],34)
            finally:
                engine.close()

if __name__=="__main__": unittest.main(verbosity=2)
