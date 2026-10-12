// Regression: processing batches of >1 new frame must not report missing frames.
// Runs the actual ExtendScript host code with mocked AE API. No AE installation needed.
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const TAG = "TomoTrackAI - OBJETIVO";
class CompItem {}
class AVLayer {}
class FootageItem {}
class Shape {}
const trace = [];
const maskProperty = {
  selected: false,
  setValueAtTime: (t, v) => {
    assert(Number.isFinite(t), "keyframe must have valid time");
    assert(Array.isArray(v.vertices) && v.vertices.length === 4);
    trace.push([Number(t.toFixed(6)), v.vertices.map(a => a.slice())]);
  }
};
const mask = {
  matchName: "ADBE Mask Atom",
  name: TAG,
  selected: false,
  property: (name) => {
    assert.strictEqual(name, "ADBE Mask Shape");
    return maskProperty;
  }
};
const maskGroup = {numProperties: 1, property: n => n === 1 ? mask : null};
const footage = new FootageItem();
footage.width = 320;
footage.height = 240;
footage.file = {exists: true, fsName: "/video/test.mp4"};
const layer = new AVLayer();
Object.assign(layer, {
  hasVideo: true,
  source: footage,
  name: "Video prueba",
  stretch: 100,
  threeDLayer: false,
  timeRemapEnabled: false,
  startTime: 0,
  inPoint: 0,
  outPoint: 5,
  selected: true,
  property: key => key === "ADBE Mask Parade" ? maskGroup : null
});
const comp = new CompItem();
Object.assign(comp, {
  name: "Comp prueba",
  time: 0,
  duration: 5,
  selectedLayers: [layer]
});
const sandbox = {
  CompItem, AVLayer, FootageItem, Shape,
  app: { project: {activeItem: comp}, beginUndoGroup(){}, endUndoGroup(){} },
  JSON, Math, Number, Error, isFinite,
  File: function() {
    return {
      exists: true,
      open: () => true,
      read: () => JSON.stringify(snapshot),
      close: () => {}
    };
  }
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("bridge/extension/jsx/host.jsx", "utf8"), sandbox);
const version = JSON.parse(sandbox.tomoMask.version());
assert.strictEqual(version.bridge_id, "platetrack-0.6.2-bridge-20261012");
const rect = {
  vertices: [[50,50],[90,50],[90,90],[50,90]],
  inTangents: [[0,0],[0,0],[0,0],[0,0]],
  outTangents: [[0,0],[0,0],[0,0],[0,0]],closed:true
};
const frame = i => ({
  matrix:[[1,0,i*2],[0,1,i],[0,0,1]],scale_factor:1,rotation_deg:0,
  frame: i, source_time: i / 30,
  cx: 70+i*2, cy: 70+i,
  bbox: [50+i*2,50+i,40,40],
  confidence: 0.99,low_confidence:false
});
const snapshot = {
  run_id:"same-job",source_file:"/video/test.mp4",
  comp_name:"Comp prueba",layer_name:"Video prueba",
  layer_start:0,source_width:320,source_height:240,
  width:320,height:240,fps:30,
  anchors:[{frame:0,bbox:{x:50,y:50,w:40,h:40},shape:rect}],
  samples:[frame(0),frame(1),frame(2)] // 3 frames in a single snapshot
};
function apply() {
  const reply = JSON.parse(sandbox.tomoMask.applyProgress("/virtual.json"));
  assert(reply.ok, reply.error);
  return reply;
}
assert.strictEqual(apply().applied, 3, "first 3-frame snapshot");
assert.strictEqual(trace.length, 3);
snapshot.samples.push(frame(3), frame(4), frame(5));
assert.strictEqual(apply().applied, 3, "next 3-frame snapshot");
assert.strictEqual(trace.length, 6);
assert.strictEqual(apply().applied, 0, "idempotent snapshot replay");
assert.strictEqual(trace.length, 6);
snapshot.samples.push(frame(7)); // genuinely missing frame 6
const gap = JSON.parse(sandbox.tomoMask.applyProgress("/virtual.json"));
assert.strictEqual(gap.ok, false, "real missing frame should still be detected");
assert(/Faltan cuadros/.test(gap.error), gap.error);
// Escala y rotación geométricas sobre la MISMA máscara libre.
snapshot.run_id="mask-rotated";
snapshot.samples=[frame(0),Object.assign(frame(1),{
 rotation_deg:8, scale_factor:1.2,
 matrix:[[1.188322,-0.166607,8.49],[0.166607,1.188322,-17.6],[0,0,1]],
 bbox:[52,51,48,44],cx:76,cy:73
})];
snapshot.anchors=[{frame:0,bbox:{x:50,y:50,w:40,h:40},shape:rect,rotation_deg:0}];
snapshot.track_scale=true;
snapshot.track_rotation=true;
const offset=trace.length;
assert.strictEqual(apply().applied,2);
const shape0=trace[offset][1], shape1=trace[offset+1][1];
const initialWidth=Math.hypot(shape0[1][0]-shape0[0][0],shape0[1][1]-shape0[0][1]);
const updatedWidth=Math.hypot(shape1[1][0]-shape1[0][0],shape1[1][1]-shape1[0][1]);
assert(updatedWidth>initialWidth*1.15,"la máscara debería crecer con PlateTrack");
assert(Math.abs(shape1[1][1]-shape1[0][1])>3,"la máscara debería girar con la rotación calculada");
console.log("PASS — lotes de tres cuadros, salto genuino, escala y rotación de máscara.");
