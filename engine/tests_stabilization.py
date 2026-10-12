"""Camera stabilization acceptance tests with known exact affine transforms."""
import math
import unittest
import numpy as np
import cv2
from camera_stabilization import stabilize_samples,pose_matrix,point,auto_zoom
from platetrack.types import TrackData
from platetrack.stabilize import stabilize as upstream_stabilize

W,H=640,360
REF=np.array([320.,180.])
ANCHORS=[dict(frame=0,bbox=dict(x=200,y=100,w=240,h=160),
              source_width=W,source_height=H)]

def sample_series(n=61,fx=lambda i:(0,0,0,1),confidence=0.98):
    samples=[]
    for i in range(n):
        dx,dy,ang,scale=fx(i)
        m=pose_matrix((REF[0]+dx,REF[1]+dy),math.radians(ang),scale,REF)
        samples.append(dict(frame=i,source_time=i/30,
                    matrix=m.tolist(),confidence=confidence,needs_correction=False))
    return samples

def stabilize_samples_test(samples,**kw):
    return stabilize_samples(samples,ANCHORS,W,H,**kw)

def fwd(c):
    return np.array(c["matrix"],dtype=float)

class TestCameraStabilization(unittest.TestCase):
    def test_static_camera_is_identity(self):
        result=stabilize_samples_test(sample_series(),mode="smooth",radius=12)
        self.assertEqual(result["zoom"],1)
        for s in result["samples"]:
            np.testing.assert_allclose(fwd(s),np.eye(3),atol=1e-8)

    def test_steady_intentional_pan_preserved_even_at_edges(self):
        samples=sample_series(fx=lambda i:(i*1.8,i*0.4,0,1))
        out=stabilize_samples_test(samples,mode="smooth",auto_crop=False,radius=14)
        for s in out["samples"]:
            np.testing.assert_allclose(fwd(s),np.eye(3),atol=1e-5,
                err_msg="Una traslación lineal intencional no debe estabilizarse en modo suave.")

    def test_stationary_lock_removes_translation_rotation_zoom(self):
        samples=sample_series(fx=lambda i:(i*.3,math.sin(i/3)*6,i*.16,1+.001*i))
        out=stabilize_samples_test(samples,mode="lock",auto_crop=False)
        for original,s in zip(samples,out["samples"]):
            Wmat=np.asarray(original["matrix"])
            np.testing.assert_allclose(fwd(s)@Wmat,np.eye(3),atol=1e-6)

    def test_full_strength_smooth_reduces_high_freq_jitter(self):
        samples=sample_series(n=120,fx=lambda i:(
            i*0.65+7*math.sin(i*2.1),
            .2*i+4*math.sin(i*2.45),
            .075*i+1.4*math.sin(i*2.3),
            1+.008*math.sin(i*1.8)))
        out=stabilize_samples_test(samples,mode="smooth",radius=10,auto_crop=False)
        orig=np.array([point(np.array(x["matrix"]),REF) for x in samples])
        corrected=np.array([point(fwd(c)@np.asarray(x["matrix"]),REF)
                            for c,x in zip(out["samples"],samples)])
        accel=lambda x: np.diff(x,axis=0,n=2)
        before=np.mean(np.linalg.norm(accel(orig),axis=1))
        after=np.mean(np.linalg.norm(accel(corrected),axis=1))
        self.assertLess(after,before*.36,(before,after))
        self.assertGreater(corrected[-1,0]-corrected[0,0],60,
                           "El paneo intencional debe mantenerse.")

    def test_strength_zero_does_not_stabilize(self):
        samples=sample_series(fx=lambda i:(7*math.sin(i),5*math.cos(i),i*.2,1))
        out=stabilize_samples_test(samples,strength=0,auto_crop=False)
        for s in out["samples"]:
            np.testing.assert_allclose(fwd(s),np.eye(3),atol=1e-6)

    def test_borders_contained_after_auto_crop(self):
        samples=sample_series(fx=lambda i:(9*math.sin(i*.3),7*math.sin(i*.22),
                                          1.4*math.sin(i*.7),1))
        out=stabilize_samples_test(samples,mode="lock",auto_crop=True,max_zoom=2.5)
        self.assertGreater(out["zoom"],1.02)
        # Every rendered output corner must sample a valid original source px.
        screen=[[0,0],[W-1,0],[0,H-1],[W-1,H-1]]
        for s in out["samples"]:
            back=np.linalg.inv(fwd(s))
            for corner in screen:
                x,y=point(back,corner)
                self.assertTrue(-1e-4<=x<=W-1+1e-4,(out["zoom"],s["frame"],x))
                self.assertTrue(-1e-4<=y<=H-1+1e-4,(out["zoom"],s["frame"],y))

    def test_bad_confidence_prevents_false_stabilization(self):
        samples=sample_series()
        samples[31]["confidence"]=0.12
        with self.assertRaisesRegex(ValueError,"fotograma 31"):
            stabilize_samples_test(samples)

    def test_edited_reference_rejected_instead_of_wrong_coordinates(self):
        samples=sample_series()
        anchors=ANCHORS+[dict(ANCHORS[0],frame=40)]
        with self.assertRaisesRegex(ValueError,"correcciones"):
            stabilize_samples(samples,anchors,W,H)

    def test_drop_frame_rejected(self):
        samples=sample_series()
        del samples[13]
        with self.assertRaisesRegex(ValueError,"Faltan fotogramas"):
            stabilize_samples_test(samples)

    def test_auto_zoom_fails_safely_on_unfillable_camera_pan(self):
        samples=sample_series(fx=lambda i:(i*35,0,0,1))
        with self.assertRaisesRegex(ValueError,"zoom excesivo"):
            stabilize_samples_test(samples,mode="lock",auto_crop=True)

    def test_our_lock_matches_upstream_platetrack_warp(self):
        """We use the same geometry as PlateTrack stabilize.py, but AE keyframes
        perform the warp nondestructively instead of rendering media.
        """
        frames=[]
        rng=np.random.default_rng(12)
        original=rng.integers(0,255,(H,W,3),dtype=np.uint8)
        for dx in (0,4,9,13,19,24,30):
            m=pose_matrix((REF[0]+dx,REF[1]),0,1,REF)
            frames.append(cv2.warpPerspective(original,m,(W,H)))
        samples=sample_series(n=7,fx=lambda i:([0,4,9,13,19,24,30][i],0,0,1))
        result=stabilize_samples_test(samples,mode="lock",auto_crop=False)
        matrices=np.array([np.linalg.inv(np.array(s["matrix"])) for s in samples])
        track=TrackData(plate_size=(W,H),reference_frame=0,frame_count=len(samples),
                    model="similarity",corners_ref=np.array([[200,100],[440,100],[440,260],[200,260]],float),
                    H_to_ref=matrices,confidence=np.ones(len(samples)))
        upstream,_=upstream_stabilize(frames,track,mode="lock_full_frame")
        for source,s,expect in zip(frames,result["samples"],upstream):
            actual=cv2.warpPerspective(source,fwd(s),(W,H),flags=cv2.INTER_CUBIC)
            np.testing.assert_array_equal(actual,expect)

if __name__=="__main__":
    unittest.main(verbosity=2)
