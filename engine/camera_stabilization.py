"""TomoTrackAI v0.6 — camera stabilization from PlateTrack geometry.

PlateTrack stores W_i: original tracked reference -> visible frame i. Its
stabilization code applies W_i^-1; for smooth camera mode we reconstruct a
smooth scene trajectory S_i and apply C_i = S_i @ inv(W_i).

All input/output coordinates are decoded-video pixels, not AE comp coordinates.
No independent optical tracker, no media rendering, no external dependencies
except NumPy (already bundled with PlateTrack).
"""
import math
import numpy as np

def pose_matrix(center, angle, scale, origin):
    """Similarity mapping reference-origin to current center; image y down."""
    x,y=[float(v) for v in center]; ox,oy=[float(v) for v in origin]
    cs=float(scale)*math.cos(float(angle))
    sn=float(scale)*math.sin(float(angle))
    return np.array([[cs,-sn,x-cs*ox+sn*oy],
                     [sn,cs,y-sn*ox-cs*oy],[0.,0.,1.]],dtype=np.float64)

def point(H,p):
    x,y=float(p[0]),float(p[1])
    q=np.asarray(H,dtype=np.float64)@np.array([x,y,1.])
    if abs(q[2])<1e-9:raise ValueError("Matriz no invertible.")
    return q[:2]/q[2]

def _trend_filter(data, confidences, sigma):
    """Gaussian weighted local LINEAR fit: preserves smooth intentional pans,
    including at the sequence edges, unlike a naive moving average.
    """
    data=np.asarray(data,dtype=np.float64)
    n,k=data.shape
    if n<2 or sigma<.5:return data.copy()
    weight=np.asarray(confidences,dtype=np.float64)
    radius=max(2,int(math.ceil(sigma*3)))
    output=np.empty_like(data)
    for i in range(n):
        left=max(0,i-radius);right=min(n,i+radius+1)
        t=np.arange(left,right,dtype=np.float64)-i
        w=np.exp(-.5*(t/sigma)**2)*np.maximum(.05,weight[left:right])
        s0=np.sum(w);s1=np.sum(w*t);s2=np.sum(w*t*t)
        det=s0*s2-s1*s1
        if det<1e-8:
            output[i]=data[i]
            continue
        yi=data[left:right]
        y0=np.sum(w[:,None]*yi,axis=0)
        y1=np.sum((w*t)[:,None]*yi,axis=0)
        output[i]=(s2*y0-s1*y1)/det
    return output

def _valid_on_canvas(C,w,h,z=1.,margin=1.5):
    """All inverse-mapped destination corners must sample inside source."""
    z=max(1.,float(z))
    Z=np.array([[z,0,(1.-z)*w/2],[0,z,(1.-z)*h/2],[0,0,1]],dtype=np.float64)
    back=np.linalg.inv(Z@C)
    pts=np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],dtype=np.float64)
    for p in pts:
        x,y=point(back,p)
        if not(margin-1e-6<=x<=w-1-margin+1e-6 and margin-1e-6<=y<=h-1-margin+1e-6):
            return False
    return True

def auto_zoom(corrections,width,height,max_zoom=2.5):
    """Lowest global uniform zoom that removes black borders from ALL frames.
    Reject impossible crop: we do not silently show black or invent frames.
    """
    w,h=int(width),int(height)
    if w<32 or h<32:raise ValueError("Resolución de video demasiado pequeña.")
    if all(_valid_on_canvas(C,w,h,1.,margin=0.) for C in corrections):
        return 1.
    if not all(_valid_on_canvas(C,w,h,max_zoom,margin=0.) for C in corrections):
        raise ValueError("El movimiento necesita un zoom excesivo para ocultar bordes. Usá menor intensidad, 'sin recorte', o elegí un fragmento más corto.")
    lo,hi=1.,float(max_zoom)
    for _ in range(36):
        mid=(lo+hi)/2
        if all(_valid_on_canvas(C,w,h,mid,margin=0.) for C in corrections):hi=mid
        else:lo=mid
    return min(max_zoom,hi+0.001)

def stabilize_samples(samples,anchors,width,height,*,mode="smooth",strength=1.,
                      radius=15,auto_crop=True,max_zoom=2.5,min_confidence=.35):
    """Return stabilized transforms in the ORIGINAL reference coordinate system.
    Bounded manual gaps are allowed only when marked by an explicit 4-corner
    pin; these frames are not portrayed as automatically tracked.
    """
    if mode not in ("smooth","lock"):
        raise ValueError("Modo no soportado: "+str(mode))
    if not (0<=strength<=1):raise ValueError("Intensidad fuera de 0..1")
    if not(2<=radius<=120):raise ValueError("Radio de suavizado fuera de 2..120")
    if len(samples)<5:raise ValueError("Se necesitan al menos 5 fotogramas de tracking.")
    if not anchors or any(not a.get("manual_pin") for a in anchors[1:]):
        raise ValueError("Se encontraron correcciones de referencia sin un pin manual válido.")
    for idx,s in enumerate(samples):
        if idx and s["frame"]!=samples[idx-1]["frame"]+1:
            raise ValueError("Faltan fotogramas del seguimiento de cámara.")
        if s.get("manual_interpolated"):
            if not any(a.get("manual_pin") and int(a["frame"])>int(s["frame"]) for a in anchors):
                raise ValueError("Interpolación manual sin pin posterior verificado.")
        elif (float(s.get("confidence",0))<min_confidence or s.get("needs_correction",False)):
            raise ValueError("Referencia perdida en fotograma %s. Corregí el seguimiento antes de estabilizar."%s["frame"])
    quad=anchors[0]["bbox"]
    ref=np.array([(float(quad["x"])+float(quad["w"])/2)*width/float(anchors[0].get("source_width",width)),
                  (float(quad["y"])+float(quad["h"])/2)*height/float(anchors[0].get("source_height",height))])
    # The reference ROI bbox is source-pixel units. Metadata source dimensions
    # must be attached to anchor by the caller, falling back only at 1:1.
    raw=[];poses=[];conf=[]
    for s in samples:
        H=np.asarray(s["matrix"],dtype=np.float64)
        if H.shape!=(3,3) or not np.isfinite(H).all() or np.linalg.norm(H[2]-[0,0,1])>1e-5:
            raise ValueError("Estabilización 2D requiere matrices de similitud válidas.")
        a,b=H[0,0],H[1,0]
        sc=math.hypot(a,b)
        if not .3<sc<3.3 or abs(a-H[1,1])>.02 or abs(H[0,1]+b)>.02:
            raise ValueError("PlateTrack produjo una matriz no compatible con estabilización 2D.")
        ang=math.atan2(b,a)
        center=point(H,ref)
        raw.append(H)
        poses.append([center[0],center[1],ang,math.log(sc)])
        conf.append(float(s["confidence"]))
    raw=np.asarray(raw,dtype=np.float64)
    poses=np.asarray(poses,dtype=np.float64)
    poses[:,2]=np.unwrap(poses[:,2])
    ideal=np.tile(np.array([ref[0],ref[1],0.,0.]),(len(samples),1)) if mode=="lock" else _trend_filter(poses,conf,radius)
    wanted=poses+strength*(ideal-poses)
    corrections=[]
    for i,H in enumerate(raw):
        cx,cy,angle,log_scale=wanted[i]
        desired=pose_matrix((cx,cy),angle,math.exp(log_scale),ref)
        C=desired@np.linalg.inv(H)
        C[2]=[0,0,1]
        corrections.append(C)
    zoom=auto_zoom(corrections,width,height,max_zoom=max_zoom) if auto_crop else 1.
    zmatrix=np.array([[zoom,0,(1-zoom)*width/2],
                      [0,zoom,(1-zoom)*height/2],[0,0,1]],dtype=np.float64)
    output=[]
    for s,C in zip(samples,corrections):
        corrected=zmatrix@C
        scale=math.hypot(corrected[0,0],corrected[1,0])
        degrees=math.degrees(math.atan2(corrected[1,0],corrected[0,0]))
        output.append(dict(frame=s["frame"],source_time=s["source_time"],
                           matrix=np.round(corrected,9).tolist(),
                           tx=float(corrected[0,2]),ty=float(corrected[1,2]),
                           rotation_deg=float(degrees),scale_percent=float(scale*100),
                           confidence=s["confidence"],
                           manual_interpolated=bool(s.get("manual_interpolated",False)),
                           manual_pin=bool(s.get("manual_pin",False))))
    return dict(mode=mode,strength=float(strength),radius=int(radius),
                auto_crop=bool(auto_crop),zoom=round(zoom,5),
                min_confidence=float(min(conf)),samples=output,
                manual_frames=sum(bool(s.get("manual_interpolated")) for s in samples),
                pin_count=sum(bool(a.get("manual_pin")) for a in anchors),
                source_width=int(width),source_height=int(height))
