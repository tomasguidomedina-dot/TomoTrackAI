#!/usr/bin/env python3
"""TomoTrackAI 0.5: PlateTrack core (LK/RANSAC/ECC), no NanoTrack/ONNX.

Pure local JSONL engine. Adapted STREAMING consumer of upstream PlateTrack
modules; never loads a complete HD video into RAM. Source time stays in the
original video clock. Corrections re-anchor the tracked polygon in-place.

PlateTrack: https://github.com/edgarciavfx/comfyui-platetrack
Upstream pyproject.toml declares MIT; bundled upstream modules preserved.
"""
import json
import math
import os
import sys
from pathlib import Path

def finite(v, name):
    result=float(v)
    if not math.isfinite(result):
        raise ValueError("Valor no finito en "+name)
    return result

def emit(**d):
    sys.stdout.write(json.dumps(d,separators=(",",":"),allow_nan=False)+"\n")
    sys.stdout.flush()

def polygon_bbox(shape):
    v=shape.get("vertices",[])
    if not shape.get("closed") or len(v)<3:
        raise ValueError("Dibujá una máscara cerrada sobre el objeto.")
    x=[finite(p[0],"x") for p in v]; y=[finite(p[1],"y") for p in v]
    return [min(x),min(y),max(x)-min(x),max(y)-min(y)]

def to_gray(frame,cv2):
    return cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

def homogeneous_point(matrix,point):
    import numpy as np
    x,y=float(point[0]),float(point[1])
    p=np.asarray(matrix,dtype=np.float64)@np.array([x,y,1.0])
    if not math.isfinite(float(p[2])) or abs(float(p[2]))<1e-8:
        raise ValueError("Transformación geométrica inválida.")
    return [float(p[0]/p[2]),float(p[1]/p[2])]

def corners_from_bbox(box):
    x,y,w,h=[float(i) for i in box]
    return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]

class StreamingPlate:
    """Incremental interpretation of PlateTrack's core fit_motion/LK/ECC pipeline.
    For 2D object tracking the default model is similarity, one uniform scale
    and one rotation computed from the SAME matrix as displacement.
    """
    def __init__(self, cv2, model="similarity", ecc=True):
        from platetrack.features import detect_features
        from platetrack.lk import lk_step
        from platetrack.models import fit_motion
        from platetrack.refine import ecc_refine_to_reference
        import numpy as np
        self.cv2=cv2; self.np=np
        self.detect=detect_features; self.lk=lk_step; self.fit=fit_motion
        self.refine=ecc_refine_to_reference
        if model not in ("similarity","homography"):
            raise ValueError("Modelo PlateTrack no soportado: "+str(model))
        self.model=model; self.ecc=bool(ecc)
        self.ref_gray=None;self.prev_gray=None;self.points=None
        self.ref_quad=None;self.H=None;self.last_confidence=1.
        self.low_count=0;self.last_ecc=None
        self.num_frames=0

    def start(self,frame,quad):
        np=self.np
        self.ref_gray=to_gray(frame,self.cv2)
        self.prev_gray=self.ref_gray
        self.ref_quad=np.asarray(quad,dtype=np.float64)
        self.points=self.detect(self.ref_gray,self.ref_quad,max_corners=240)
        if len(self.points)<12:
            raise ValueError("PlateTrack: menos de 12 puntos visuales fiables dentro de la máscara. Elegí una región con más textura.")
        self.H=np.eye(3,dtype=np.float64) # current -> reference
        self.low_count=0;self.last_confidence=1.;self.last_ecc=None
        self.num_frames=0

    def _quad_current(self):
        np=self.np
        q=self.ref_quad.reshape(-1,1,2).astype(np.float64)
        return self.cv2.perspectiveTransform(q,np.linalg.inv(self.H)).reshape(-1,2)

    def step(self,frame):
        np=self.np
        gray=to_gray(frame,self.cv2)
        good_count=0; total=len(self.points)
        confidence=0.; candidate=None;inliers=None;ecc_cc=None
        try:
            if total>=8:
                new,good,fb=self.lk(self.prev_gray,gray,self.points,fb_thresh=1.5)
                if new is not None and good is not None and int(good.sum())>=10:
                    src=self.points[good];dst=new[good]
                    cand, inliers=self.fit(src,dst,self.model)
                    if cand is not None and inliers is not None:
                        good_count=int(inliers.sum())
                        frac=good_count/max(1,len(src))
                        if good_count>=9 and frac>=0.55 and np.isfinite(cand).all():
                            # PlateTrack convention: matrix maps current image -> reference.
                            new_H=self.H@np.linalg.inv(cand)
                            if np.isfinite(new_H).all() and abs(np.linalg.det(new_H))>1e-9:
                                candidate=new_H
                                confidence=max(0.,min(1.,.72*frac+.28*min(1.,good_count/40)))
                                points_next=dst[inliers]
            if candidate is not None:
                if self.ecc:
                    refined,cc=self.refine(self.ref_gray,gray,candidate,self.ref_quad,self.model)
                    if cc is not None and np.isfinite(refined).all() and cc>=0.72:
                        # Guard against ECC diverging from PlateTrack's LK motion.
                        # With a similarity model ECC MOTION_EUCLIDEAN adjusts
                        # alignment without taking over the uniform-scale fit.
                        p0=homogeneous_point(np.linalg.inv(candidate),self.ref_quad.mean(axis=0))
                        p1=homogeneous_point(np.linalg.inv(refined),self.ref_quad.mean(axis=0))
                        if math.dist(p0,p1)<5.0:
                            candidate=refined
                            ecc_cc=float(cc)
                            confidence=max(confidence,min(1.0,.60*confidence+.40*ecc_cc))
                # Restrict sudden impossible geometry, without fabricating motion.
                m=np.linalg.inv(candidate)
                scale=math.hypot(m[0,0],m[1,0])
                if .68<=scale<=2.2 and np.isfinite(m).all():
                    self.H=candidate
                    self.points=points_next.astype(np.float32)
                    self.low_count=0
                else:
                    confidence=0.;self.low_count+=1
            else:
                self.low_count+=1
        except (ValueError, self.cv2.error, np.linalg.LinAlgError, ZeroDivisionError):
            confidence=0.
            self.low_count+=1
        self.prev_gray=gray
        self.num_frames+=1
        if candidate is None or confidence<=0.0:
            # Do not pretend the previous static transform is a fresh detection.
            self.points=self.detect(gray,self._quad_current(),max_corners=240)
        elif len(self.points)<45 or self.num_frames%12==0:
            # PlateTrack's feature re-seeding. This preserves LK chain geometry
            # while new points will be tracked relative to the current frame.
            self.points=self.detect(gray,self._quad_current(),max_corners=240)
        self.last_confidence=confidence
        self.last_ecc=ecc_cc
        return self.result()

    def result(self):
        np=self.np
        forward=np.linalg.inv(self.H)
        center=homogeneous_point(forward,self.ref_quad.mean(axis=0))
        if self.model=="similarity":
            scale=math.hypot(forward[0,0],forward[1,0])
            angle=math.degrees(math.atan2(forward[1,0],forward[0,0]))
        else:
            # Approximate local similarity at the reference center for a
            # projective transform; four corners are the authoritative output.
            point=self.ref_quad.mean(axis=0)
            c=homogeneous_point(forward,point)
            px=homogeneous_point(forward,point+[1,0])
            py=homogeneous_point(forward,point+[0,1])
            scale=(math.dist(c,px)+math.dist(c,py))/2
            angle=math.degrees(math.atan2(px[1]-c[1],px[0]-c[0]))
        quad=[homogeneous_point(forward,v) for v in self.ref_quad]
        return dict(matrix=forward.tolist(),cx=center[0],cy=center[1],
                    scale_factor=round(float(scale),7),rotation_deg=round(float(angle),5),
                    confidence=round(float(self.last_confidence),5),
                    low_confidence=bool(self.low_count>=1),
                    needs_correction=bool(self.low_count>=5),
                    ecc_score=self.last_ecc,points=int(len(self.points)),
                    quad=quad,model=self.model)

class Engine:
    def __init__(self,cv2):
        self.cv2=cv2
        self.cap=None;self.tracker=None;self.samples=[]
        self.anchors=[];self.metadata=None
        self.index=0;self.end_index=0
        self.global_scale=1.;self.global_rotation=0.
        self.base_box=None
        self.stabilization=None
        self.tracking_mode="object"
    def close(self):
        if self.cap is not None:self.cap.release()
        self.cap=None;self.tracker=None
    def frame_at(self,frame):
        self.cap.set(self.cv2.CAP_PROP_POS_FRAMES,int(frame))
        ok,img=self.cap.read()
        if not ok:raise ValueError("No se pudo leer el fotograma "+str(frame))
        return img
    def _start_tracker(self,frame,shape):
        # Coordinates of AE mask are in source pixels; convert to decoded video.
        fx=self.width/self.source_width;fy=self.height/self.source_height
        vertices=shape["vertices"]
        quad=corners_from_bbox(polygon_bbox(shape))
        quad_video=[[x*fx,y*fy] for x,y in quad]
        self.tracker=StreamingPlate(self.cv2,self.model,self.ecc_refine)
        self.tracker.start(frame,quad_video)
        self.base_box=polygon_bbox(shape)
    def init(self,job):
        self.close()
        self.samples=[];self.anchors=[];self.metadata=None
        self.stabilization=None
        self.tracking_mode=job.get("mode","object")
        if self.tracking_mode not in ("object","stabilize"):
            raise ValueError("Modo de sesión inválido.")
        self.cv2.setNumThreads(2)
        src=Path(job["video"])
        if not src.is_file():raise ValueError("El video no existe: "+str(src))
        self.cap=self.cv2.VideoCapture(str(src))
        if not self.cap.isOpened():raise ValueError("OpenCV no pudo abrir el archivo.")
        self.fps=finite(self.cap.get(self.cv2.CAP_PROP_FPS),"fps")
        if not 1<=self.fps<=240:raise ValueError("FPS incorrectos")
        self.index=max(0,int(round(finite(job["start_seconds"],"start")*self.fps)))
        self.end_index=max(self.index,int(math.ceil(finite(job["end_seconds"],"end")*self.fps)-1))
        total=int(self.cap.get(self.cv2.CAP_PROP_FRAME_COUNT))
        if total>0:self.end_index=min(self.end_index,total-1)
        if self.end_index<=self.index:raise ValueError("No quedan cuadros para seguir.")
        frame=self.frame_at(self.index)
        self.height,self.width=frame.shape[:2]
        self.source_width=finite(job["source_width"],"source_width")
        self.source_height=finite(job["source_height"],"source_height")
        if abs(self.width/self.height-self.source_width/self.source_height)>0.018:
            raise ValueError("El aspecto del video no coincide con AE.")
        shape=job["mask_shape"]
        polygon_bbox(shape)
        self.model=job.get("tracking_model","similarity")
        self.ecc_refine=bool(job.get("ecc_refine",True))
        self.threshold=max(.1,min(1.,finite(job.get("confidence_threshold",.30),"confianza")))
        self.global_scale=1.;self.global_rotation=0.
        self._start_tracker(frame,shape)
        self.anchors=[dict(frame=self.index,bbox=dict(job["bbox"]),shape=shape,
                           scale_factor=1.,rotation_deg=0.)]
        self.metadata={k:job[k] for k in
            ("video","comp_name","layer_name","layer_start","run_id","mask_name")}
        first=self.record(self.tracker.result())
        return dict(first=first,fps=self.fps,width=self.width,height=self.height,last_frame=self.end_index)

    def record(self,local):
        # Matrix is authoritative, both mask + Null use this SAME solution.
        scale=self.global_scale*local["scale_factor"]
        angle=self.global_rotation+local["rotation_deg"]
        coords=[p for p in local["quad"]]
        xs=[p[0] for p in coords];ys=[p[1] for p in coords]
        conf=local["confidence"]
        rec=dict(frame=self.index,source_time=round(self.index/self.fps,8),
                 matrix=local["matrix"],cx=round(local["cx"],5),cy=round(local["cy"],5),
                 bbox=[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)],
                 scale_factor=round(scale,7),rotation_deg=round(angle,5),
                 local_scale_factor=local["scale_factor"],
                 local_rotation_deg=local["rotation_deg"],
                 confidence=conf,low_confidence=(conf<self.threshold),
                 needs_correction=local["needs_correction"],points=local["points"],
                 ecc_score=local["ecc_score"],quad=coords,model=self.model)
        self.samples.append(rec)
        self.stabilization=None  # cualquier cambio de muestras invalida estabilización previa
        return rec

    def step(self,count=1):
        if self.tracker is None:raise ValueError("No hay sesión PlateTrack.")
        new=[]
        for _ in range(max(1,min(15,int(count)))):
            if self.index>=self.end_index:break
            ok,frame=self.cap.read()
            if not ok:break
            self.index+=1
            local=self.tracker.step(frame)
            new.append(self.record(local))
            if local["needs_correction"]:break
        return dict(new=new,total=len(self.samples),frame=self.index,
                    ended=(self.index>=self.end_index or not new),
                    needs_correction=bool(new and new[-1]["needs_correction"]))

    def reseed(self,cmd):
        if self.cap is None:raise ValueError("No hay sesión para corregir.")
        index=max(0,int(round(finite(cmd["source_seconds"],"source_seconds")*self.fps)))
        if index>self.end_index:raise ValueError("Corrección fuera del video")
        shape=cmd["mask_shape"];polygon_bbox(shape)
        frame=self.frame_at(index)
        prior=[r for r in self.samples if r["frame"]<index]
        self.global_scale=prior[-1]["scale_factor"] if prior else 1.
        self.global_rotation=prior[-1]["rotation_deg"] if prior else 0.
        self.samples=prior
        self.anchors=[a for a in self.anchors if a["frame"]<index]
        self.index=index
        self._start_tracker(frame,shape)
        self.anchors.append(dict(frame=index,bbox=dict(cmd["bbox"]),shape=shape,
                                 scale_factor=self.global_scale,rotation_deg=self.global_rotation))
        return dict(corrected=self.record(self.tracker.result()),total=len(self.samples))

    def stabilize(self,cmd):
        from camera_stabilization import stabilize_samples
        if self.tracker is None or self.metadata is None:
            raise ValueError("No hay trayectoria de cámara para estabilizar.")
        if self.tracking_mode!="stabilize":
            raise ValueError("Iniciá la sesión en modo Estabilizar cámara.")
        if self.index<self.end_index:
            raise ValueError("Finalizá el análisis de la secuencia antes de estabilizar.")
        anchors=[]
        for a in self.anchors:
            copy=dict(a)
            copy["source_width"]=self.source_width
            copy["source_height"]=self.source_height
            anchors.append(copy)
        self.stabilization=stabilize_samples(self.samples,anchors,self.width,self.height,
            mode=cmd.get("mode","smooth"),
            strength=finite(cmd.get("strength",1.),"intensidad"),
            radius=int(cmd.get("radius",15)),
            auto_crop=bool(cmd.get("auto_crop",True)),
            min_confidence=float(cmd.get("min_confidence",.35)))
        return dict(frames=len(self.stabilization["samples"]),
                    zoom=self.stabilization["zoom"],
                    weakest=self.stabilization["min_confidence"],
                    mode=self.stabilization["mode"])

    def snapshot(self,out):
        if not self.metadata:raise ValueError("No existe sesión.")
        target=Path(out);target.parent.mkdir(parents=True,exist_ok=True)
        payload=dict(version="0.5",engine="PlateTrack OpenCV (Streaming)",
                     source_file=self.metadata["video"],comp_name=self.metadata["comp_name"],
                     layer_name=self.metadata["layer_name"],layer_start=self.metadata["layer_start"],
                     mask_name=self.metadata["mask_name"],run_id=self.metadata["run_id"],
                     track_scale=True,track_rotation=True,
                     tracking_mode=self.tracking_mode,stabilization=self.stabilization,
                     anchors=self.anchors,source_width=self.source_width,source_height=self.source_height,
                     width=self.width,height=self.height,fps=self.fps,samples=self.samples)
        tmp=target.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf8")
        tmp.replace(target)
        return dict(file=str(target),samples=len(self.samples))

def serve():
    try:
        import cv2
        import numpy
    except Exception as e:
        emit(ok=False,error="OpenCV/NumPy no disponibles: "+str(e))
        return 2
    engine=Engine(cv2)
    emit(ok=True,ready=True,engine="PlateTrack",opencv=cv2.__version__)
    try:
        for line in sys.stdin:
            try:
                cmd=json.loads(line)
                op=cmd.get("cmd")
                if op=="init":r=engine.init(cmd["job"])
                elif op=="step":r=engine.step(cmd.get("count",1))
                elif op=="reseed":r=engine.reseed(cmd)
                elif op=="snapshot":r=engine.snapshot(cmd["output"])
                elif op=="stabilize":r=engine.stabilize(cmd)
                elif op=="close":emit(ok=True,closed=True);break
                else:raise ValueError("Comando desconocido: "+str(op))
                emit(ok=True,**r)
            except Exception as e:
                emit(ok=False,error=str(e))
    finally:engine.close()
    return 0

if __name__=="__main__":
    sys.exit(serve())
