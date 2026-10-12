"""Regression: PlateTrack-style keyframe pins for camera stabilization.

All interpolated frames are explicitly flagged and have confidence=0; a pin
is a manual assumption, not a computer measurement. No new tracking engine.
"""
import math
import unittest
import numpy as np
from camera_pins import (checked_quad,similarity_from_quad,pin_samples,
                         MAX_MANUAL_GAP,PIN_BLEND_FRAMES)
from camera_stabilization import pose_matrix,stabilize_samples

Q0=np.array([[125.,90.],[325.,90.],[325.,215.],[125.,215.]])
CENTER=np.mean(Q0,axis=0)

def shape(q):
    return dict(vertices=np.asarray(q).tolist(),closed=True)

def M(dx,dy,ang=0.,scale=1.):
    return pose_matrix((CENTER[0]+dx,CENTER[1]+dy),math.radians(ang),scale,CENTER)

def points(m):
    return (m@np.column_stack([Q0,np.ones(4)]).T).T[:,:2]

def samples(n=27,bad_from=22,rotation=False):
    result=[]
    for i in range(n):
        m=M(i*.65,math.sin(i*.3)*2.,i*.16 if rotation else 0,1+.001*i)
        if bad_from<=i:
            m=M((bad_from-1)*.65,math.sin((bad_from-1)*.3)*2.,
                (bad_from-1)*.16 if rotation else 0,1+.001*(bad_from-1))
        result.append(dict(frame=i,source_time=i/30,matrix=m.tolist(),
                           confidence=0. if i>=bad_from else .92,
                           low_confidence=i>=bad_from,
                           needs_correction=i>=bad_from+4))
    return result

class TestCameraPins(unittest.TestCase):
    def test_four_valid_rect_vertices(self):
        self.assertEqual(checked_quad(shape(Q0)).shape,(4,2))
        for bad in [Q0[:3],np.array([[0.,0.],[4.,4.],[0.,4.],[4.,0.]])]:
            with self.assertRaises(ValueError):
                checked_quad(shape(bad))

    def test_exact_similarity_rotation_zoom(self):
        H=M(16,13,17,1.3)
        recovered=similarity_from_quad(Q0,points(H))
        np.testing.assert_allclose(recovered,H,atol=1e-9)

    def test_reject_nonrigid_pin(self):
        wrong=points(M(8,4,0,1.))
        wrong[3]+=[60,0]
        with self.assertRaisesRegex(ValueError,"rígida"):
            similarity_from_quad(Q0,wrong)

    def test_pin_blend_interpolate_and_mark_provenance(self):
        source=samples()
        pinned=M(17,-5,3,1.07)
        revised,stats=pin_samples(source,26,pinned,Q0)
        self.assertEqual(len(revised),26)
        self.assertEqual(stats["gap"],5)
        self.assertEqual(stats["blend_start"],11)  # 21-10+1
        for frame in range(22,26):
            self.assertTrue(revised[frame]["manual_interpolated"])
            self.assertEqual(revised[frame]["confidence"],0)
            self.assertFalse(revised[frame]["needs_correction"])
        self.assertFalse(revised[20].get("manual_interpolated",False))
        self.assertTrue(revised[20].get("manual_blended"))
        np.testing.assert_array_equal(np.asarray(source[20]["matrix"]),
                                      M(20*.65,math.sin(20*.3)*2,0,1+.001*20))
        self.assertFalse(source[20].get("manual_blended",False),
                        "No mutar samples original")
        # Last interpolated transform approaches exact pinned matrix.
        P=np.asarray(revised[-1]["matrix"])
        self.assertLess(np.linalg.norm(points(P)-points(pinned)),17)

    def test_no_invented_large_gap(self):
        source=samples(n=50,bad_from=22)
        with self.assertRaisesRegex(ValueError,"No interpolaré"):
            pin_samples(source,49,M(20,5),Q0)

    def test_reject_pin_other_than_current_frame(self):
        source=samples()
        with self.assertRaisesRegex(ValueError,"fotograma exacto"):
            pin_samples(source,25,M(16,5),Q0)

    def test_true_lost_tracking_still_fails_without_pin(self):
        ss=samples()
        a=[dict(frame=0,bbox=dict(x=125,y=90,w=200,h=125),
                shape=shape(Q0),source_width=480,source_height=300)]
        with self.assertRaisesRegex(ValueError,"Referencia perdida"):
            stabilize_samples(ss,a,480,300,auto_crop=False)

    def test_pinned_segment_can_be_stabilized_with_explicit_manual_markers(self):
        source=samples()
        pin=M(17,-5,3,1.07)
        revised,stats=pin_samples(source,26,pin,Q0)
        revised.append(dict(frame=26,source_time=26/30,matrix=pin.tolist(),
                            confidence=1.,manual_pin=True,needs_correction=False))
        anchors=[dict(frame=0,bbox=dict(x=125,y=90,w=200,h=125),
                shape=shape(Q0),source_width=480,source_height=300),
                dict(frame=26,manual_pin=True)]
        stab=stabilize_samples(revised,anchors,480,300,auto_crop=False,
                              mode="smooth",radius=10)
        self.assertEqual(stab["manual_frames"],5)
        self.assertEqual(stab["pin_count"],1)
        self.assertEqual(len(stab["samples"]),27)
        self.assertEqual(sum(bool(x["manual_interpolated"]) for x in stab["samples"]),5)
        self.assertLess(stab["min_confidence"],.35,
                        "No inventar confianza visual en intervalos interpolados")

if __name__=="__main__":unittest.main(verbosity=2)
