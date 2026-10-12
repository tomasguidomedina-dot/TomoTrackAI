/* AE native 4 Point Controls: real draggable effects rather than non-editable
   original ROI mask. Simulates ScriptPath functions in a host mock. */
"use strict";
const assert=require("assert"),fs=require("fs"),vm=require("vm");
class CompItem{}class AVLayer{}class FootageItem{}class Shape{};
const maskVerts=[[150,80],[290,80],[290,200],[150,200]];
const maskShape={vertices:maskVerts,inTangents:[[0,0],[0,0],[0,0],[0,0]],
                 outTangents:[[0,0],[0,0],[0,0],[0,0]],closed:true};
const maskPath={selected:true,valueAtTime:()=>maskShape};
const mask={matchName:"ADBE Mask Atom",name:"TomoTrackAI - OBJETIVO",
            selected:true,property:k=>k==="ADBE Mask Shape"?maskPath:null};
const maskGroup={numProperties:1,property:()=>mask};
const effects=[];
const fxGroup={
 get numProperties(){return effects.length;},
 property(index){return effects[index-1];},
 addProperty(matchName){
   assert.strictEqual(matchName,"ADBE Point Control");
   const p={value:[0,0],selected:false,setValue(v){this.value=v.slice()}};
   const e={matchName,name:"Punto de control",selected:false,property:()=>p,
       remove(){effects.splice(effects.indexOf(this),1);}};
   effects.push(e);return e;
 }
};
const footage=new FootageItem();
footage.file={exists:true,fsName:"/tmp/test-clip.mov"};
footage.width=440;footage.height=280;
const source=new AVLayer();
Object.assign(source,{
 hasVideo:true,source:footage,name:"Video Original",startTime:0,stretch:100,
 timeRemapEnabled:false,threeDLayer:false,index:1,inPoint:0,outPoint:20,
 selected:true,
 property(k){
   if(k==="ADBE Mask Parade")return maskGroup;
   if(k==="ADBE Effect Parade")return fxGroup;
   throw Error("Unexpected property "+k);
 }
});
const comp=new CompItem();
Object.assign(comp,{name:"Prueba",selectedLayers:[source],time:0,duration:20});
const snapshot={
 tracking_mode:"stabilize",run_id:"session-23",source_file:footage.file.fsName,
 comp_name:comp.name,layer_name:source.name,layer_start:source.startTime,
 mask_name:mask.name,source_width:440,source_height:280,width:440,height:280,fps:30,
 samples:[{frame:0,source_time:0,matrix:[[1,0,0],[0,1,0],[0,0,1]],needs_correction:false},
          {frame:181,source_time:181/30,matrix:[[1,0,21],[0,1,8],[0,0,1]],needs_correction:true}],
 anchors:[{frame:0,shape:maskShape}]
};
let begin=0,end=0;
const context={
 CompItem,AVLayer,FootageItem,Shape,Math,Date,JSON,isFinite,Number,
 MaskMode:{NONE:"NONE"},
 File:function(){return {exists:true,open:()=>true,read:()=>JSON.stringify(snapshot),close(){}};},
 app:{project:{activeItem:comp},beginUndoGroup(){begin++},endUndoGroup(){end++}}
};
vm.createContext(context);
vm.runInContext(fs.readFileSync("bridge/extension/jsx/host.jsx","utf8"),context);
function invoke(name,args=[]){let response=JSON.parse(context.tomoMask[name].apply(null,args));
  if(!response.ok)throw Error(name+": "+response.error);
  return response;
}
function failed(name,args,msg){
 let r=JSON.parse(context.tomoMask[name].apply(null,args));
 assert.strictEqual(r.ok,false,name+" unexpectedly succeeded");
 assert(r.error.includes(msg),r.error);
}
// Error case: cannot pin the frame without any moved markers, nor change a
// control outside original video bounds.
const at=invoke("gotoLast",["/tmp/track.json"]);
assert.strictEqual(at.frame,181);
let r=invoke("prepareCameraPins",["/tmp/track.json"]);
assert.strictEqual(r.controls,4);
assert.strictEqual(effects.length,4);
assert.strictEqual(effects[0].name,"TomoTrackAI • 1 Superior izq.");
assert.strictEqual(JSON.stringify(effects[0].property(1).value),JSON.stringify([171,88]));
failed("readCameraPins",["/tmp/track.json"],"Primero mové");
effects[0].property(1).setValue([172,88]);
// Showing the controls again MUST preserve the user edit.
r=invoke("prepareCameraPins",["/tmp/track.json"]);
assert.strictEqual(r.reused,true);
assert.strictEqual(effects[0].property(1).value[0],172);
effects[0].property(1).setValue([441,88]);
failed("readCameraPins",["/tmp/track.json"],"fuera de los límites");
effects[0].property(1).setValue([172,88]);
const vertices=invoke("readCameraPins",["/tmp/track.json"]);
assert.strictEqual(vertices.source_seconds,181/30);
assert.strictEqual(vertices.mask_shape.vertices.length,4);
assert.strictEqual(JSON.stringify(vertices.mask_shape.vertices[0]),JSON.stringify([172,88]));
assert.strictEqual(JSON.stringify(vertices.mask_shape.vertices[1]),JSON.stringify([311,88]));
assert.strictEqual(vertices.mask_shape.closed,true);
const cleaned=invoke("clearCameraPins");
assert.strictEqual(cleaned.removed,4);
assert.strictEqual(effects.length,0);
assert.strictEqual(begin,end);
console.log("PASS — 4 native Point Control editable AE, no stale reset, actual coordinates read, cleanup reversible");
