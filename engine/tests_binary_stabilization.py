"""Smoke-test PyInstaller x86_64 executable through the actual JSONL protocol."""
import json
import math
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile

import cv2
import numpy as np

def main(binary):
    with tempfile.TemporaryDirectory() as folder:
        folder=Path(folder)
        video=folder/"camera.avi"
        W,H=400,280
        random=np.random.default_rng(714)
        scene=random.integers(22,235,(H,W,3),dtype=np.uint8)
        writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),15,(W,H))
        assert writer.isOpened()
        for i in range(26):
            mat=cv2.getRotationMatrix2D((W/2,H/2),-.3*math.sin(i*.33),1)
            mat[0,2]+=.32*i+1.1*math.sin(i*.53)
            mat[1,2]+=.7*math.cos(i*.68)
            writer.write(cv2.warpAffine(scene,mat,(W,H)))
        writer.release()
        process=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,text=True,bufsize=1)
        def read():
            ready,_,_=select.select([process.stdout],[],[],75)
            if not ready:
                process.kill()
                raise AssertionError("Motor compilado tardó >75 s en responder.")
            line=process.stdout.readline()
            assert line,"Motor finalizó sin respuesta"
            message=json.loads(line)
            assert message.get("ok"),message
            return message
        def ask(command):
            process.stdin.write(json.dumps(command)+"\n")
            process.stdin.flush()
            return read()
        try:
            assert read()["ready"]
            shape={"vertices":[[75,45],[325,45],[325,225],[75,225]],
                   "inTangents":[[0,0]]*4,"outTangents":[[0,0]]*4,"closed":True}
            job={"video":str(video),"comp_name":"BinaryTest","layer_name":"Scene",
                 "layer_start":0,"run_id":"integration-v06",
                 "mask_name":"TomoTrackAI - OBJETIVO","source_width":W,"source_height":H,
                 "start_seconds":0,"end_seconds":26/15,
                 "bbox":{"x":75,"y":45,"w":250,"h":180},"mask_shape":shape,
                 "mode":"stabilize","tracking_model":"similarity","ecc_refine":True}
            first=ask({"cmd":"init","job":job})
            assert first.get("fps",0)>10,first
            for i in range(8):
                state=ask({"cmd":"step","count":8})
                assert not state["needs_correction"], state
                if state["ended"]:break
            assert state["ended"] and state["total"]==26,state
            stab=ask({"cmd":"stabilize","mode":"smooth","strength":1,
                      "radius":8,"auto_crop":True})
            assert stab["frames"]==26 and stab["zoom"]>=1.,stab
            file=folder/"output.json"
            ask({"cmd":"snapshot","output":str(file)})
            data=json.loads(file.read_text())
            assert data["tracking_mode"]=="stabilize"
            assert len(data["stabilization"]["samples"])==26
            assert "matrix" in data["stabilization"]["samples"][-1]
            assert not any("nanotrack" in key.lower() for key in data)
            print("PASS — binary JSONL init+26 steps+stabilize+snapshot, zoom",stab["zoom"])
            ask({"cmd":"close"})
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=4)
                except subprocess.TimeoutExpired:process.kill()

if __name__=="__main__":
    main(Path(sys.argv[1]).resolve())
