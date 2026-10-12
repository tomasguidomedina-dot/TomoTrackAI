/* Regression: final stabilization button cannot be wedged by UI-only
   trackCompleted and must always let native engine explain invalid sessions. */
"use strict";
const assert=require("assert");
const fs=require("fs");
const vm=require("vm");
const path=require("path");
const {EventEmitter}=require("events");

function harness(steps,stabilizerAllowed) {
 const elems={};
 const commands=[];
 const element=function(id){
   if (!elems[id])elems[id]={
     id,textContent:"",disabled:false,hidden:false,className:"",
     value:id==="workMode"?"object":id==="previewMode"?"live":
         id==="stabMode"?"smooth":id==="stabRadius"?"15":id==="stabStrength"?"100":"",
     checked:id==="stabCrop",
     setAttribute(name,value){this[name]=value;},
     getAttribute(name){return this[name];}
   };
   return elems[id];
 };
 const win={
    addEventListener(){},
    __adobe_cep__:{
      evalScript(code,callback){
       const name=(code.match(/^tomoMask\.(\w+)\(/)||[])[1];
       if(name==="version")callback(JSON.stringify({ok:true,version:"0.6.0",bridge_id:"platetrack-0.6.0-bridge-20261012"}));
       else if(name==="useMask")callback(JSON.stringify({ok:true,job:{
         video:"/video.mp4",layer_name:"Video",comp_name:"Comp",mask_name:"Mask",
         source_width:400,source_height:300,layer_start:0,start_seconds:0,end_seconds:1}}));
       else if(name==="applyStabilization")callback(JSON.stringify({ok:true,keyframes:4,zoom:1.03,mode:"smooth",layer_name:"Estabilizada"}));
       else callback(JSON.stringify({ok:true}));
      }
    },
    require(name){
      if(name==="fs")return {existsSync(){return true;},mkdirSync(){}};
      if(name==="os")return {homedir(){return "/tmp";}};
      if(name==="path")return path;
      if(name==="readline")return {createInterface({input}){return input;}};
      if(name==="child_process")return {spawn(){
          const child=new EventEmitter();
          child.stderr=new EventEmitter();
          child.stdout=new EventEmitter();
          child.stdin={write(value){
            const req=JSON.parse(value);
            commands.push(req.cmd);
            let reply;
            if(req.cmd==="init")reply={ok:true,fps:30,last_frame:3};
            else if(req.cmd==="snapshot")reply={ok:true};
            else if(req.cmd==="step")reply=steps.shift()||{ok:true,new:[],total:4,frame:3,ended:true,needs_correction:false};
            else if(req.cmd==="stabilize")reply=stabilizerAllowed?
              {ok:true,frames:4,zoom:1.03}:
              {ok:false,error:"Finalizá el análisis de la secuencia antes de estabilizar."};
            else reply={ok:false,error:"Unsupported "+req.cmd};
            setTimeout(()=>child.stdout.emit("line",JSON.stringify(reply)),0);
          }};
          child.kill=()=>{};
          setTimeout(()=>child.stdout.emit("line",JSON.stringify({ok:true,ready:true,engine:"PlateTrack"})),0);
          return child;
      }};
      throw Error("Unmocked "+name);
    }
 };
 const ctx={document:{getElementById:element},window:win,Date,Promise,JSON,Math,
   setTimeout,clearTimeout,setInterval,clearInterval,console};
 vm.createContext(ctx);
 vm.runInContext(fs.readFileSync("bridge/extension/panel.js","utf8"),ctx);
 return {element,commands,steps};
}
async function until(fn,label){
 const started=Date.now();
 while(!fn()){
   if(Date.now()-started>3500)throw Error("Timed out: "+label);
   await new Promise(resolve=>setTimeout(resolve,5));
 }
}
async function test(){
   // Incomplete session: button is NOT grey, motor gives concrete failure.
   const early=harness([
     {ok:true,new:[{frame:1,confidence:0.9,points:150,ecc_score:null}],
      total:2,frame:1,ended:false,needs_correction:false}
   ],false);
   await until(()=>early.element("boot").textContent.includes("Motor listo"),"ready early");
   early.element("modeStabilize").onclick();
   early.element("single").onclick();
   await until(()=>early.element("status").textContent.includes("Avanzó"),"single done");
   assert.strictEqual(early.element("stabilize").hidden,false);
   assert.strictEqual(early.element("stabilize").disabled,false,"Data exist; no false disabled.");
   early.element("stabilize").onclick();
   await until(()=>early.element("status").textContent.includes("Finalizá el análisis"),"explain unfinished");
   assert(early.commands.includes("stabilize"),"The motor was asked to validate");

   // Last backend step has ended=true and new=[]; old UI would never enable.
   const finished=harness([
     {ok:true,new:[{frame:2,confidence:0.97,points:170,ecc_score:0.96}],
      total:3,frame:2,ended:false,needs_correction:false},
     {ok:true,new:[],total:4,frame:3,ended:true,needs_correction:false}
   ],true);
   await until(()=>finished.element("boot").textContent.includes("Motor listo"),"ready final");
   finished.element("modeStabilize").onclick();
   finished.element("start").onclick();
   await until(()=>finished.element("status").textContent.includes("Análisis completo"),"finalized empty batch");
   assert.strictEqual(finished.element("stabilize").disabled,false,
       "Final export must be enabled even if final batch is empty");
   finished.element("stabilize").onclick();
   await until(()=>finished.element("status").textContent.includes("Cámara estabilizada"),"export successful");
   assert.strictEqual(finished.element("stabilize").disabled,true,
       "Export cannot be repeated on finished session");

   // ended=true but physical EOF before last_frame is NOT reported as completed.
   const cut=harness([
     {ok:true,new:[],total:2,frame:1,ended:true,needs_correction:false}
   ],false);
   await until(()=>cut.element("boot").textContent.includes("Motor listo"),"ready EOF");
   cut.element("modeStabilize").onclick();
   cut.element("start").onclick();
   await until(()=>cut.element("status").textContent.includes("detenido antes del último"),"EOF warning");
   assert.strictEqual(cut.element("stabilize").disabled,false,
       "Show motor reason rather than disabled button");
   cut.element("stabilize").onclick();
   await until(()=>cut.element("status").textContent.includes("Finalizá el análisis"),"backend rejection");
   console.log("PASS — botón activo con datos, fin en lote vacío, rechazo temprano y EOF sin falsa completitud");
}
test().catch(err=>{console.error(err.stack||err);process.exitCode=1;});
