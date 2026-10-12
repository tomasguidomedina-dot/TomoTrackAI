// Real ExtendScript host executed with mocked AE API for stabilization export.
const assert=require("assert"),fs=require("fs"),vm=require("vm");
class CompItem{};class AVLayer{};class FootageItem{};
const seen={};let duplicates=0;
function prop(initial){
  return {
    value: initial,numKeys:0,expressionEnabled:false,dimensionsSeparated:false,
    times:[],values:[],
    setValue(v){this.value=v;},
    setValuesAtTimes(times,values){this.times=times;this.values=values;}
  };
}
function transform(){
  const props={
    "ADBE Anchor Point":prop([320,180]),
    "ADBE Position":prop([320,180]),
    "ADBE Scale":prop([100,100]),
    "ADBE Rotate Z":prop(0),
    "ADBE Opacity":prop(100)
  };
  return {props,property(k){assert(props[k],"Unknown transform "+k);return props[k];}};
}
const footage=new FootageItem();footage.width=640;footage.height=360;
footage.file={exists:true,fsName:"/test/plate.mov"};footage.pixelAspect=1;
const rect={
  vertices:[[160,110],[480,110],[480,270],[160,270]],
  inTangents:[[0,0],[0,0],[0,0],[0,0]],
  outTangents:[[0,0],[0,0],[0,0],[0,0]],closed:true
};
const mask={matchName:"ADBE Mask Atom",name:"TomoTrackAI - OBJETIVO",selected:true,maskMode:"NONE",
 property:n=>n==="ADBE Mask Shape"?{selected:true,valueAtTime:()=>rect}:null};
const source=new AVLayer();const baseTransform=transform();
Object.assign(source,{name:"Video",source:footage,hasVideo:true,stretch:100,threeDLayer:false,
  timeRemapEnabled:false,parent:null,index:1,inPoint:0,outPoint:4,startTime:0,
  enabled:true,selected:true,
  property:k=>k==="ADBE Mask Parade"?{numProperties:1,property:()=>mask}:
     k==="ADBE Transform Group"?baseTransform:null});
source.duplicate=function(){
  duplicates++;
  const d=new AVLayer();const t=transform();
  Object.assign(d,{name:"duplicado",parent:null,enabled:true,selected:false,
    property:k=>k==="ADBE Mask Parade"?{numProperties:1,property:()=>({maskMode:"NONE"})}:
       k==="ADBE Transform Group"?t:null});
  seen.duplicate=d;seen.transform=t;
  return d;
};
const comp=new CompItem();
Object.assign(comp,{name:"VideoComp",width:640,height:360,duration:4,time:0,
   selectedLayers:[source]});
const samples=[],stabs=[];
for(let i=0;i<25;i++){
  samples.push({frame:i,source_time:i/30});
  const radians=(i*.25)*Math.PI/180;
  const c=Math.cos(radians),s=Math.sin(radians),z=1.04;
  stabs.push({frame:i,source_time:i/30,matrix:[
      [z*c,-z*s,1.5*i],[z*s,z*c,1.25*i],[0,0,1]
  ]});
}
let snapshot={
  source_file:"/test/plate.mov",comp_name:"VideoComp",layer_name:"Video",layer_start:0,
  width:640,height:360,source_width:640,source_height:360,
  mask_name:"TomoTrackAI - OBJETIVO",tracking_mode:"stabilize",
  samples,stabilization:{mode:"smooth",zoom:1.04,samples:stabs}
};
const sandbox={
  CompItem,AVLayer,FootageItem,Shape:class {},
  app:{project:{activeItem:comp},beginUndoGroup(){},endUndoGroup(){}},
  JSON,Math,Number,Error,isFinite,
  MaskMode:{NONE:"NONE"},
  File:function(){return{exists:true,open:()=>true,read:()=>JSON.stringify(snapshot),close(){}};}
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("bridge/extension/jsx/host.jsx","utf8"),sandbox);
const version=JSON.parse(sandbox.tomoMask.version());
assert.strictEqual(version.bridge_id,"platetrack-0.6.2-bridge-20261012");
let result=JSON.parse(sandbox.tomoMask.applyStabilization("/virtual.json"));
assert(result.ok,result.error);
assert.strictEqual(result.keyframes,25);
assert.strictEqual(duplicates,1);
assert.strictEqual(source.enabled,false,"Original debe quedar intacto y oculto");
assert.strictEqual(seen.duplicate.enabled,true);
const p=seen.transform.props;
assert.deepEqual(p["ADBE Anchor Point"].value,[0,0]);
assert.strictEqual(p["ADBE Position"].times.length,25);
assert.deepEqual(Array.from(p["ADBE Position"].values[0]),[0,0]);
assert(Math.abs(p["ADBE Position"].values[24][0]-36)<1e-8);
assert(Math.abs(p["ADBE Scale"].values[0][0]-104)<1e-5);
assert(Math.abs(p["ADBE Rotate Z"].values[24]-6)<1e-5);
assert.deepEqual(baseTransform.props["ADBE Anchor Point"].value,[320,180]);
assert.strictEqual(baseTransform.props["ADBE Position"].times.length,0);

// Failure mode: animated original transforms must be rejected BEFORE duplicate.
source.enabled=true;source.selected=true;comp.selectedLayers=[source];
baseTransform.props["ADBE Position"].numKeys=3;
result=JSON.parse(sandbox.tomoMask.applyStabilization("/virtual.json"));
assert(!result.ok && /sin keyframes/.test(result.error),result.error);
assert.strictEqual(duplicates,1,"No duplicar al detectar transform inadecuado");
console.log("PASS — AE estabilizador crea capa duplicada con Position/Scale/Rotation; origen preservado; rechaza keyframes previos");
