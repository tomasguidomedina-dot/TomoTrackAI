/* TomoTrackAI 0.3 - ÚNICO PANEL: máscara AE + PlateTrack local + Null. */
(function(){
"use strict";
var el=function(id){return document.getElementById(id);};
var cep=window.__adobe_cep__;
var req=(window.cep_node&&window.cep_node.require)||window.require||window.nodeRequire;
var fs,os,path,spawn,readline,proc=null,ready=false,starting=null,queue=[],job=null;
var resultFile="",busy=false,stopping=false,hasData=false,bootStart=0,clock=null;
var lastScore=1;
var EXPECTED_BRIDGE="platetrack-0.5.0-bridge-20261012",bridgeVerified=false;
function status(s){el("status").textContent=String(s);}
function controls(){
  el("start").disabled=busy;
  el("single").disabled=busy;
  el("pause").disabled=!busy;
  el("correct").disabled=busy||!hasData;
  el("null").disabled=busy||!hasData;
  el("new").disabled=busy;
  el("reconnect").disabled=busy||ready;
  el("previewMode").disabled=busy;
}
function lock(v){busy=v;controls();}
function bridge(method,args){
 return new Promise(function(resolve,reject){
   if(!cep||!cep.evalScript)return reject(Error("Abrí TomoTrackAI dentro de After Effects."));
   var code="tomoMask."+method+"("+(args||[]).map(function(x){return JSON.stringify(x);}).join(",")+")";
   cep.evalScript(code,function(text){
     try{var r=JSON.parse(text);r.ok?resolve(r):reject(Error(r.error||"Error en After Effects"));}
     catch(e){reject(Error("Respuesta de After Effects: "+String(text).slice(0,240)));}
   });
 });
}
async function verifyBridge(){
  // El motor es local. Esta comprobación evita ejecutar ExtendScript viejo
  // que puede quedar cacheado en AE después de instalar una nueva versión.
  try{
    var v=await bridge("version",[]);
    if(v.bridge_id!==EXPECTED_BRIDGE)throw Error("Puente "+String(v.version||"?")+
       " (esperado 0.5).");
    bridgeVerified=true;
    el("bridgeVersion").textContent="Puente AE: v"+v.version+" verificado";
    return v;
  }catch(e){
    bridgeVerified=false;
    el("bridgeVersion").textContent="Puente AE: versión sin verificar";
    throw Error("After Effects ejecuta un puente viejo o incompatible. "+
      "Cerrá completamente AE, reinstalá TomoTrackAI v0.5 y reabrilo. Detalle: "+e.message);
  }
}
function disconnect(reason){
  ready=false;proc=null;starting=null;clearInterval(clock);
  while(queue.length)queue.shift().reject(Error(reason));
  controls();
}
function launch(){
 if(ready&&proc)return Promise.resolve();
 if(starting)return starting;
 bootStart=Date.now();
 status("Cargando motor LOCAL (sin Internet)... podés dibujar la máscara mientras se inicia.");
 starting=new Promise(function(resolve,reject){
   var settled=false,log="",timeout=null,child=null;
   function bad(err){
     if(settled)return;settled=true;clearTimeout(timeout);clearInterval(clock);
     try{if(child)child.kill();}catch(ignore){}
     disconnect("Motor sin conexión");
     reject(err instanceof Error?err:Error(String(err)));
   }
   clock=setInterval(function(){
     if(!settled)el("boot").textContent="Motor local: "+((Date.now()-bootStart)/1000).toFixed(1)+" s"+
       ((Date.now()-bootStart)>12000?" · inicio lento, sin conexión a Internet":"");
   },500);
   timeout=setTimeout(function(){
      bad(Error("PlateTrack no respondió después de 60 segundos. Pulsá Reconectar."));
   },60000);
   try{
     if(!req)throw Error("El panel no tiene acceso al motor local (Node de CEP).");
     fs=req("fs");os=req("os");path=req("path");
     spawn=req("child_process").spawn;readline=req("readline");
     var root=path.join(os.homedir(),"Library","Application Support","TomoTrackAI5");
     var exe=path.join(root,"engine","TomoPlateTrack","TomoPlateTrack");
     resultFile=path.join(root,"jobs","current-mask-track.json");
     if(!fs.existsSync(exe))throw Error("Falta el motor local. Volvé a ejecutar Instalar_TomoTrackAI.command.");
     fs.mkdirSync(path.dirname(resultFile),{recursive:true});
     child=spawn(exe,[],{cwd:path.dirname(exe),stdio:["pipe","pipe","pipe"]});
     proc=child;
     child.stderr.on("data",function(buf){
       log+=String(buf);if(log.length>2500)log=log.slice(-2500);
     });
     child.on("error",function(e){bad(Error("No se pudo iniciar el motor: "+e.message));});
     child.on("exit",function(code){
       if(!settled)bad(Error("PlateTrack se cerró durante inicio: "+code+" "+log.slice(-450)));
       else{disconnect("PlateTrack finalizó: "+code+" "+log.slice(-400));
         if(!busy)status("Motor detenido. Pulsá Reconectar.");}
     });
     var stream=readline.createInterface({input:child.stdout});
     stream.on("line",function(line){
       var response;
       try{response=JSON.parse(line);}catch(e){if(!settled)bad(Error("Respuesta no válida del motor"));return;}
       if(!settled){
         if(response.ok&&response.ready){
           settled=true;clearTimeout(timeout);clearInterval(clock);
           ready=true;controls();
           var elapsed=((Date.now()-bootStart)/1000).toFixed(1);
           el("boot").textContent="Motor listo en "+elapsed+" s";
           status("PlateTrack listo. Dibujá una máscara cerrada sobre el objeto y pulsá Analizar.");
           resolve();
         }else bad(Error(response.error||"PlateTrack no inició correctamente"));
         return;
       }
       var item=queue.shift();
       if(item)response.ok?item.resolve(response):item.reject(Error(response.error||"Error del motor"));
     });
   }catch(e){bad(e);}
 }).catch(function(e){disconnect(e.message);status("Error al iniciar: "+e.message);throw e;});
 return starting;
}
async function rpc(cmd){
 await launch();
 return new Promise(function(resolve,reject){
   if(!proc||!ready)return reject(Error("Motor desconectado."));
   var item={resolve:resolve,reject:reject};
   queue.push(item);
   try{proc.stdin.write(JSON.stringify(cmd)+"\n");}
   catch(e){queue.pop();reject(e);}
 });
}
function progress(r){
 el("count").textContent=r.total+" cuadros";
 if(job){
  var end=job.end_seconds-job.start_seconds;
  var done=((r.frame/job.fps)-job.start_seconds);
  if(end>0)el("bar").value=Math.max(0,Math.min(100,100*done/end));
 }
}
async function snapshot(){
 await rpc({cmd:"snapshot",output:resultFile});
 return bridge("applyProgress",[resultFile]);
}
function previewPolicy(){
  var v=el("previewMode").value;
  // No guarantees a rendered frame: yield the main thread between analysis steps.
  return v==="fast"?{batch:4,delay:55}:v==="balanced"?{batch:2,delay:160}:{batch:1,delay:350};
}
function waitForPreview(ms){return new Promise(function(resolve){setTimeout(resolve,ms);});}
async function startSession(){
 var selection=await bridge("useMask",[]);
 job=selection.job;
 job.confidence_threshold=0.24;
 job.tracking_model="similarity";
 job.ecc_refine=true;
 var r;
 try { r=await rpc({cmd:"init",job:job}); }
 catch(e){job=null;hasData=false;controls();throw e;}
 job.fps=r.fps;
 hasData=true;
 await snapshot();
 el("count").textContent="1 cuadro";
 el("bar").value=0;
 return r;
}
async function track(continuous){
 if(busy)return;
 lock(true);stopping=false;
 try{
   await verifyBridge();
   await launch();
   if(!job)await startSession();
   var r;
   do{
     // Lotes pequeños: los keyframes y la máscara aparecen mientras se rastrea.
     var policy=previewPolicy();
     r=await rpc({cmd:"step",count:continuous?policy.batch:1});
     if(r.new&&r.new.length){
       await snapshot();
       progress(r);
       var latest=r.new[r.new.length-1];
       lastScore=latest.confidence;
       el("quality").textContent="PlateTrack "+Math.round(lastScore*100)+" % · "+latest.points+
         " puntos · "+(latest.ecc_score===null?"ECC sin convergencia":"ECC "+Number(latest.ecc_score).toFixed(2))+
         " · cuadro "+latest.frame;
       await waitForPreview(continuous?policy.delay:180);
     }
     if(stopping){status("Pausado en el último fotograma solicitado. Esperá a que el visor termine de dibujarlo antes de corregir.");break;}
     if(r.needs_correction){
       status("El objeto perdió confianza. Ajustá la máscara en el fotograma visible y pulsá Corregir.");
       break;
     }
     if(r.ended||!r.new||!r.new.length){
       status("Track terminado: "+r.total+" cuadros. Podés crear el Null.");
       break;
     }
     if(!continuous){
       status("Avanzó un fotograma. Podés continuar, corregir o crear el Null.");
       break;
     }
     status("Siguiendo el objeto... "+r.total+" cuadros. Pausar para ajustar.");
     await waitForPreview(0);
   }while(!stopping);
   if(stopping)status("Track pausado. Mové o ajustá la máscara aquí y pulsá Corregir.");
 }catch(e){status("Error: "+e.message);}
 finally{lock(false);}
}
async function correct(){
 if(busy||!hasData)return;
 lock(true);
 try{
   await verifyBridge();
   var c=await bridge("correction",[]);
   await rpc({cmd:"reseed",source_seconds:c.source_seconds,bbox:c.bbox,mask_shape:c.mask_shape});
   await rpc({cmd:"snapshot",output:resultFile});
   await bridge("rewind",[resultFile]);
   await bridge("applyProgress",[resultFile]);
   status("Corrección registrada. Pulsá Analizar para continuar desde ese fotograma.");
 }catch(e){status("Error al corregir: "+e.message);}
 finally{lock(false);}
}
async function nullFromMask(){
 if(busy||!hasData)return;
 lock(true);
 try{
   await rpc({cmd:"snapshot",output:resultFile});
   await verifyBridge();
   var r=await bridge("makeNull",[resultFile]);
   status("PlateTrack: Null con "+r.keyframes+" keyframes · Position, Scale, Rotation.");
 }catch(e){status("Error creando Null: "+e.message);}
 finally{lock(false);}
}
el("start").onclick=function(){track(true);};
el("single").onclick=function(){track(false);};
el("pause").onclick=function(){stopping=true;status("Pausando al terminar el fotograma actual...");};
el("correct").onclick=correct;
el("null").onclick=nullFromMask;
el("new").onclick=function(){
 if(busy)return;job=null;hasData=false;el("count").textContent="0 cuadros";el("bar").value=0;
 el("quality").textContent="Confianza y estimación de giro aparecerán durante el seguimiento.";
 status("Nueva sesión: dibujá una máscara nueva o elegí otra capa.");
 controls();
};
el("reconnect").onclick=function(){launch().catch(function(){});};
window.addEventListener("beforeunload",function(){if(proc)try{proc.kill();}catch(ignore){}});
controls();
verifyBridge()
 .then(function(){return launch();})
 .catch(function(e){status(e.message);});
 // El motor NO envía video ni fotogramas a Internet.
})();