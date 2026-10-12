// Regression: actual JSX host exports Position + Scale + Rotation.
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");
class CompItem {}
class AVLayer {}
class FootageItem {}
const values = {};
function propertyGroup(which) {
  return {
    property: (name) => {
      if(which==="source"){
        if(name==="ADBE Rotate Z")return {valueAtTime:()=>0};
      }else{
        if(!values[name])values[name]={times:[],entries:[],expression:"",
          setValuesAtTimes(t,v){this.times=t.slice();this.entries=v.map(x=>Array.isArray(x)?x.slice():x);},
          setValue(v){this.entries=[v];},
          valueAtTime(t){const i=this.times.findIndex(x=>Math.abs(x-t)<1e-6);return this.entries[i]||[0,0];}};
        return values[name];
      }
      return null;
    }
  };
}
const video = new AVLayer();
const source = new FootageItem();
source.file={exists:true,fsName:"/test/video.mp4"};
source.width=320;source.height=240;
video.source=source;
video.name="Video";
video.hasVideo=true;
video.stretch=100;video.threeDLayer=false;video.timeRemapEnabled=false;
video.index=1;video.inPoint=0;video.outPoint=4;video.startTime=0;
const mask={matchName:"ADBE Mask Atom",name:"TomoTrackAI - OBJETIVO",selected:true,
  property:()=>({selected:true})};
video.property=key=>{
  if(key==="ADBE Mask Parade")return {numProperties:1,property:()=>mask};
  if(key==="ADBE Transform Group")return propertyGroup("source");
  throw Error("Unknown video prop "+key);
};
let nullLayer;
const comp = new CompItem();
comp.selectedLayers=[video];
comp.name="Test";comp.duration=4;comp.time=0;
comp.layers={addNull:()=>{
  video.index=2;
  nullLayer={name:"",threeDLayer:false,parent:null,selected:false,inPoint:0,outPoint:4,
    property:key=>key==="ADBE Transform Group"?propertyGroup("null"):null};
  return nullLayer;
}};
const track={
  source_file:"/test/video.mp4",comp_name:"Test",layer_name:"Video",layer_start:0,
  source_width:320,source_height:240,width:320,height:240,
  fps:30,track_scale:true,track_rotation:true,
  anchors:[{frame:0,rotation_deg:0,bbox:{x:40,y:60,w:60,h:50},shape:{vertices:[[40,60],[100,60],[100,110],[40,110]],inTangents:[[0,0],[0,0],[0,0],[0,0]],outTangents:[[0,0],[0,0],[0,0],[0,0]],closed:true}}],
  samples:[
    {frame:0,source_time:0,cx:70,cy:85,bbox:[40,60,60,50],rotation_deg:0,scale_factor:1},
    {frame:1,source_time:1/30,cx:72,cy:86,bbox:[40,60,66,55],rotation_deg:7.5,scale_factor:1.1},
    {frame:2,source_time:2/30,cx:74,cy:87,bbox:[40,60,72,60],rotation_deg:11.0,scale_factor:1.2}
  ]
};
const sandbox={
  CompItem,AVLayer,FootageItem,JSON,Math,Number,Error,isFinite,Shape:class {},
  app:{project:{activeItem:comp},beginUndoGroup(){},endUndoGroup(){}},
  File:function(){return {exists:true,open:()=>true,read:()=>JSON.stringify(track),close(){}};}
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("bridge/extension/jsx/host.jsx","utf8"),sandbox);
const result=JSON.parse(sandbox.tomoMask.makeNull("/tmp/test.json"));
assert(result.ok,result.error);
assert(result.scale&&result.rotation);
assert.strictEqual(result.keyframes,3);
const scale0=Array.from(values["ADBE Scale"].entries[0]);
const scale1=Array.from(values["ADBE Scale"].entries[1]);
assert(scale0.every(x=>Math.abs(x-100)<0.0001),scale0);
assert(scale1.every(x=>Math.abs(x-110)<0.0001),scale1);
assert(Math.abs(values["ADBE Rotate Z"].entries[1]-7.5)<0.0001);
assert.strictEqual(values["ADBE Position"].times.length,3);
assert(nullLayer&&nullLayer.selected);
console.log("PASS — Null con Position, Scale X/Y y Rotation, 3 keyframes.");
