"""Anti-regression tests specifically for false rotational jitter.

The old v0.4 KLT implementation accumulated noisy per-frame angles even
when the target did not rotate. These sequences MUST be tested before release.
"""
import math
import unittest
import numpy as np
import cv2
from rotation_estimator import StableRotation


SIZE=(480, 360)
CX,CY=235,165
BOX=[145,90,180,150]


def base_scene(texture=True):
    rng=np.random.default_rng(256)
    image=np.zeros((SIZE[1],SIZE[0],3),dtype=np.uint8)
    if texture:
        region=rng.integers(10,245,(BOX[3],BOX[2],3),dtype=np.uint8)
        image[BOX[1]:BOX[1]+BOX[3],BOX[0]:BOX[0]+BOX[2]]=region
    return image


def motion(base,angle=0,scale=1,dx=0,dy=0):
    # Positive angle is CLOCKWISE in image coordinates (y down).
    mat=cv2.getRotationMatrix2D((CX,CY),-angle,scale)
    mat[0,2]+=dx;mat[1,2]+=dy
    image=cv2.warpAffine(base,mat,SIZE,flags=cv2.INTER_LINEAR)
    pts=np.asarray([[BOX[0],BOX[1]],[BOX[0]+BOX[2],BOX[1]],
                     [BOX[0]+BOX[2],BOX[1]+BOX[3]],[BOX[0],BOX[1]+BOX[3]]],dtype=np.float32)
    points=cv2.transform(pts[None,:,:],mat)[0]
    x0=float(np.min(points[:,0]));x1=float(np.max(points[:,0]))
    y0=float(np.min(points[:,1]));y1=float(np.max(points[:,1]))
    return image, [x0,y0,x1-x0,y1-y0]


def test_series(angles,scales=None,dxs=None,dys=None,confidence=None):
    original=base_scene()
    rotation=StableRotation(cv2)
    polygon=[[BOX[0],BOX[1]],[BOX[0]+BOX[2],BOX[1]],
             [BOX[0]+BOX[2],BOX[1]+BOX[3]],[BOX[0],BOX[1]+BOX[3]]]
    image,box=motion(original)
    rotation.start(image,box,polygon=polygon)
    outputs=[]
    for i,ang in enumerate(angles):
        x=dxs[i] if dxs else 0
        y=dys[i] if dys else 0
        scale=scales[i] if scales else 1
        image,box=motion(original,ang,scale,x,y)
        outputs.append(rotation.step(image,box,confidence[i] if confidence else 0.99))
    return outputs


class TestNoFalseRotation(unittest.TestCase):
    def test_static_target_remains_zero(self):
        outputs=test_series([0.0]*28)
        assert all(abs(x["rotation_deg"])<0.01 for x in outputs),outputs

    def test_translation_remains_zero(self):
        outputs=test_series([0.0]*28,
                            dxs=[i*2 for i in range(28)],
                            dys=[i*0.8 for i in range(28)])
        self.assertLess(max(abs(o["rotation_deg"]) for o in outputs),0.8)

    def test_zoom_without_rotation_remains_zero(self):
        scales=[1+0.012*i for i in range(24)]
        outputs=test_series([0.0]*24,scales=scales)
        self.assertLess(max(abs(o["rotation_deg"]) for o in outputs),1.0)

    def test_sub_degree_camera_noise_does_not_accumulate(self):
        jitter=[0.35*math.sin(0.9*i) for i in range(36)]
        outputs=test_series(jitter)
        self.assertLess(max(abs(o["rotation_deg"]) for o in outputs),1.0)

    def test_true_rotation_detectable(self):
        angles=[1.5*i for i in range(22)]
        outputs=test_series(angles)
        final=outputs[-1]["rotation_deg"]
        self.assertGreater(final,20.0,outputs[-4:])
        self.assertLess(final,38.0,outputs[-4:])
        self.assertGreater(sum(o["rotation_valid"] for o in outputs),8)

    def test_occlusion_holds_last_angle(self):
        track=StableRotation(cv2)
        original=base_scene()
        image,box=motion(original)
        track.start(image,box,polygon=[[145,90],[325,90],[325,240],[145,240]])
        previous=0.0
        for i in range(16):
            image,box=motion(original,i*1.2)
            prior=track.step(image,box,0.99)
            previous=prior["rotation_deg"]
        for i in range(8):
            image=np.zeros_like(image)
            result=track.step(image,box,0.1)
            self.assertEqual(result["rotation_deg"],previous)
            self.assertFalse(result["rotation_valid"])


if __name__=="__main__":
    unittest.main(verbosity=2)
