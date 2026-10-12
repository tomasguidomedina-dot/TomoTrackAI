/* TomoTrackAI 0.3 - ÚNICO PANEL: máscara AE + PlateTrack local + Null. */
(function(){
"use strict";
var el=function(id){return document.getElementById(id);};
var cep=window.__adobe_cep__;
var req=(window.cep_node&&window.cep_node.require)||window.require||window.nodeRequire;
var fs,os,path,spawn,readline,proc=null,ready=false,starting=null,queue=[],job=null;
var resultFile="",busy=false,stopping=false,hasData=false,bootStart=0,clock=null;
var lastScore=1,trackCompleted=false,stabilized=false;
var EXPECTED_BRIDGE="platetrack-0.6.2-bridge-20261012",bridgeVerified=false;
// Sólo interfaz. No afecta el motor, sus parámetros ni sus keyframes.
function badge(state,label){
 var node=el("engineBadge");node.setAttribute("data-state",state);
 el("engineState").textContent=label;
}
function status(s){
 var message=String(s),element=el("status");
 element.textContent=message;
 var tone="";
 if(/error|incompatible|no respondió|no se pudo|motor sin conexión/i.test(message))tone="error";
 else if(/perdió confianza|corregir|pausad/i.test(message))tone="warning";
 else if(/terminado|Null con|Corrección registrada|Track terminado/i.test(message))tone="success";
 element.setAttribute("data-tone",tone);
 if(tone==="error"){badge("error","Error");el("phaseLabel").textContent="Revisar conexión";}
 else if(/cargando|preparando|inicia/i.test(message)&&!ready){badge("loading","Iniciando");el("phaseLabel").textContent="Preparando motor";}
 else if(/pausad|pausando/i.test(message)){badge("paused","Pausado");el("phaseLabel").textContent="En pausa";}
 else if(/terminado|Null con/i.test(message)){badge("done","Finalizado");el("phaseLabel").textContent="Seguimiento terminado";}
 else if(/siguiendo el objeto/i.test(message)){badge("tracking","Analizando");el("phaseLabel").textContent="Seguimiento activo";}
 else if(ready&&!busy){badge("ready","Listo");el("phaseLabel").textContent=hasData?"Sesión preparada":"Listo para analizar";}
}
function populateSource(){
 el("sourceLayer").textContent=job?job.layer_name:"Seleccioná un video y dibujá una máscara cerrada (G).";
 el("sourceLayer").className="source-value"+(job?"":" placeholder");
 el("sourceComp").textContent=job?job.comp_name:"—";
 el("sourceMask").textContent=job?job.mask_name:"—";
}
function inStabMode(){return el("workMode").value==="stabilize";}
function updateMode(){
 var stab=inStabMode();
 el("modeObject").className=stab?"":"active";
 el("modeStabilize").className=stab?"active":"";
 el("stabilizeOptions").hidden=!stab;
 el("stabilize").hidden=!stab;
 el("null").hidden=stab;
 el("modeHint").textContent=stab?
  "Dibujá una máscara sobre un fondo estático con textura. La cámara se estabiliza a partir de ese movimiento.":
  "Dibujá una máscara cerrada sobre el objeto a seguir.";
 el("correct").hidden=false;
 el("correct").textContent=stab?"Fijar 4 puntos del fondo":"Corregir máscara";
 el("single").textContent=stab?"Analizar 1 cuadro":"Avanzar 1 cuadro";
 controls();
}
function controls(){
  el("start").disabled=busy;
  el("single").disabled=busy;
  el("pause").disabled=!busy;
  el("correct").disabled=busy||!hasData;
  el("null").disabled=busy||!hasData||inStabMode();
  // No depender del estado local de fin de sesión para habilitar la acción.
  // El motor PlateTrack valida último frame, confianza y continuidad de muestras.
  // Una sesión parcial puede pulsarse: devuelve un error claro, no un botón gris.
  el("stabilize").disabled=busy||!hasData||stabilized||!inStabMode();
  el("new").disabled=busy;
  el("reconnect").disabled=busy||ready;
  el("previewMode").disabled=busy;
  el("start").textContent=inStabMode()?(job?"▶ Continuar análisis":"▶ Analizar cámara"):(job?"▶ Continuar tracking":"▶ Iniciar tracking");
  el("modeObject").disabled=busy||!!job;
  el("modeStabilize").disabled=busy||!!job;
  if(busy){badge("tracking","Analizando");el("phaseLabel").textContent="Seguimiento activo";}
  else if(ready&&el("engineBadge").getAttribute("data-state")==="loading"){
    badge("ready","Listo");
    el("phaseLabel").textContent=job?"Sesión preparada":"Listo para analizar";
  }
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
       " (esperado 0.6.2).");
    bridgeVerified=true;
    el("bridgeVersion").textContent="Puente AE: v"+v.version+" verificado";
    return v;
  }catch(e){
    bridgeVerified=false;
    el("bridgeVersion").textContent="Puente AE: versión sin verificar";
    throw Error("After Effects ejecuta un puente viejo o incompatible. "+
      "Cerrá completamente AE, reinstalá TomoTrackAI v0.6.2 y reabrilo. Detalle: "+e.message);
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
     var root=path.join(os.homedir(),"Library","Application Support","TomoTrackAI62");
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
 if(job&&job.mode==="stabilize")return {ok:true,skipped_mask_animation:true};
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
 job.mode=el("workMode").value;
 trackCompleted=false;
 stabilized=false;
 populateSource();
 job.confidence_threshold=0.24;
 job.tracking_model="similarity";
 job.ecc_refine=true;
 var r;
 try { r=await rpc({cmd:"init",job:job}); }
 catch(e){job=null;hasData=false;controls();throw e;}
 job.fps=r.fps;
 job.last_frame=r.last_frame; // Ground truth del motor, no del indicador de progreso.
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
     var policy=job&&job.mode==="stabilize"?{batch:12,delay:0}:previewPolicy();
     r=await rpc({cmd:"step",count:continuous?policy.batch:1});
     if(r.new&&r.new.length){
       await snapshot();
       progress(r);
       var latest=r.new[r.new.length-1];
       lastScore=latest.confidence;
       el("quality").setAttribute("data-tone",lastScore<.3?"low":lastScore>=.8?"high":"");
       el("quality").textContent="PlateTrack "+Math.round(lastScore*100)+" % · "+latest.points+
         " puntos · "+(latest.ecc_score===null?"ECC sin convergencia":"ECC "+Number(latest.ecc_score).toFixed(2))+
         " · cuadro "+latest.frame;
       await waitForPreview(continuous?policy.delay:180);
     }
     if(stopping){status("Pausado en el último fotograma solicitado. Esperá a que el visor termine de dibujarlo antes de corregir.");break;}
     if(r.needs_correction){
       if(inStabMode()){
         await bridge("gotoLast",[resultFile]);
         status("PlateTrack perdió confianza en cuadro "+r.frame+". Mové las cuatro esquinas de la máscara para que coincidan con el MISMO fondo y pulsá Fijar 4 puntos. Los cuadros sin referencia se indicarán como interpolados.");
       }else{
         status("El objeto perdió confianza. Ajustá la máscara en el fotograma visible y pulsá Corregir.");
       }
       break;
     }
     if(r.ended||!r.new||!r.new.length){
       // El último lote puede traer CERO cuadros si la sesión ya estaba al final.
       // Y "ended" por sí solo también puede significar lectura cortada del video.
       trackCompleted=!!r.ended&&!r.needs_correction&&r.frame>=job.last_frame;
       status(inStabMode()?
         (trackCompleted?
          "Análisis completo: "+r.total+" cuadros. Podés crear la capa estabilizada.":
          "Análisis detenido antes del último fotograma. Podés pulsar Crear capa estabilizada para conocer el motivo exacto."):
         "Track terminado: "+r.total+" cuadros. Podés crear el Null.");
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
   var result=await rpc({cmd:"reseed",source_seconds:c.source_seconds,
                          bbox:c.bbox,mask_shape:c.mask_shape});
   await rpc({cmd:"snapshot",output:resultFile});
   if(inStabMode()){
     trackCompleted=false;stabilized=false;
     el("quality").textContent="Pin manual en cuadro "+result.pin_frame+
      " · "+result.manual_interpolated+" cuadros interpolados sin medición · verificá el resultado.";
     status("Corrección de cámara fijada en cuadro "+result.pin_frame+
       ". PlateTrack suavizó el enlace desde cuadro "+result.blend_start+
       ". Pulsá Continuar análisis. Revisá visualmente los fotogramas interpolados antes de exportar.");
   }else{
     await bridge("rewind",[resultFile]);
     await bridge("applyProgress",[resultFile]);
     status("Corrección registrada. Pulsá Analizar para continuar desde ese fotograma.");
   }
 }catch(e){status("Error al corregir: "+e.message);}
 finally{lock(false);}
}
async function stabilizeCamera(){
 if(busy||!hasData||stabilized||!inStabMode())return;
 lock(true);
 status(trackCompleted?"Validando la trayectoria y preparando estabilización...":
   "Comprobando si la secuencia terminó correctamente...");

 try{
   await verifyBridge();
   var settings={
     cmd:"stabilize",
     mode:el("stabMode").value,
     strength:Number(el("stabStrength").value)/100,
     radius:Number(el("stabRadius").value),
     auto_crop:el("stabCrop").checked
   };
   var response=await rpc(settings);
   await rpc({cmd:"snapshot",output:resultFile});
   var applied=await bridge("applyStabilization",[resultFile]);
   stabilized=true;
   status("Cámara estabilizada: "+applied.keyframes+" fotogramas. Zoom "+Math.round(response.zoom*100)+
     "%. "+(response.manual_frames?"ATENCIÓN: "+response.manual_frames+" cuadros interpolados entre pins manuales: inspeccionalos en AE. ":"")+"Capa original conservada.");
 }catch(e){status("Error al estabilizar: "+e.message);}
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
el("stabilize").onclick=stabilizeCamera;
el("stabStrength").oninput=function(){el("stabStrengthText").textContent=this.value+"%";};
el("modeObject").onclick=function(){
 if(busy||job)return;
 el("workMode").value="object";updateMode();
};
el("modeStabilize").onclick=function(){
 if(busy||job)return;
 el("workMode").value="stabilize";updateMode();
};
el("new").onclick=function(){
 if(busy)return;job=null;hasData=false;trackCompleted=false;stabilized=false;
 el("count").textContent="0 cuadros";el("bar").value=0;
 el("quality").textContent="Confianza y referencias aparecerán durante el análisis.";
 el("quality").setAttribute("data-tone","");
 populateSource();
 status("Nueva sesión: dibujá una máscara nueva o elegí otra capa.");
 controls();
};
el("reconnect").onclick=function(){launch().catch(function(){});};
window.addEventListener("beforeunload",function(){if(proc)try{proc.kill();}catch(ignore){}});
populateSource();
updateMode();
verifyBridge()
 .then(function(){return launch();})
 .catch(function(e){status(e.message);});
 // El motor NO envía video ni fotogramas a Internet.
})();