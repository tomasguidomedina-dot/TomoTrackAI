/* TomoTrackAI v0.2.1 — una única interfaz; motor local + efecto nativo interno. */
(function(){
"use strict";
var $=function(id){return document.getElementById(id);};
var cep=window.__adobe_cep__;
var req=(window.cep_node&&window.cep_node.require)||window.require||window.nodeRequire;
var fs,os,path,spawn,readline,proc=null,ready=false,starting=null;
var requests=[],job=null,resultPath="",busy=false,cancel=false;
function status(s){$("status").textContent=String(s);}
function refresh(n){$("count").textContent=String(n)+" cuadros";}
function controls(){
  $("start").disabled=busy||!ready;
  $("step").disabled=busy||!ready;
  $("stop").disabled=!busy;
  $("correct").disabled=busy||!ready||!job;
  $("null").disabled=busy||!ready||!job;
  $("prepare").disabled=busy;
  $("region").disabled=busy;
  $("new").disabled=busy;
  $("connect").disabled=busy||ready;
}
function lock(b){busy=b;controls();}
function bridge(method,args){
 return new Promise(function(resolve,reject){
   if(!cep||!cep.evalScript)return reject(Error("Abrí el panel dentro de After Effects."));
   var code="tomoBridge."+method+"("+(args||[]).map(function(x){return JSON.stringify(x);}).join(",")+")";
   cep.evalScript(code,function(str){
     try{var r=JSON.parse(str);if(r.ok)resolve(r);else reject(Error(r.error||"Error After Effects"));}
     catch(e){reject(Error("Respuesta AE: "+String(str).slice(0,300)));}
   });
 });
}
function launch(){
 if(ready&&proc)return Promise.resolve();
 if(starting)return starting;
 status("Inicializando NanoTrack... el primer arranque puede tardar unos segundos.");
 starting=new Promise(function(resolve,reject){
   var settled=false,stderr="",timer=null,child=null;
   function fail(e){
     if(settled)return;
     settled=true;clearTimeout(timer);
     ready=false;proc=null;controls();
     try{if(child)child.kill();}catch(ignore){}
     reject(e instanceof Error?e:Error(String(e)));
   }
   timer=setTimeout(function(){fail(Error("El motor no respondió en 30 segundos. Pulsá Reintentar."));},30000);
   try{
     if(!req)throw Error("El panel no puede acceder al motor local de CEP.");
     fs=req("fs");os=req("os");path=req("path");
     spawn=req("child_process").spawn;readline=req("readline");
     var root=path.join(os.homedir(),"Library","Application Support","TomoTrackAI2");
     var exe=path.join(root,"engine","TomoTrackNano","TomoTrackNano");
     resultPath=path.join(root,"jobs","current-track.json");
     if(!fs.existsSync(exe))throw Error("No encuentro NanoTrack. Volvé a ejecutar Instalar_TomoTrackAI_02.command.");
     fs.mkdirSync(path.dirname(resultPath),{recursive:true});
     child=spawn(exe,[],{cwd:path.dirname(exe),stdio:["pipe","pipe","pipe"]});
     proc=child;
     child.stderr.on("data",function(b){
       stderr+=String(b);if(stderr.length>1800)stderr=stderr.slice(-1800);
     });
     child.on("error",function(e){fail(Error("No se pudo iniciar NanoTrack: "+e.message));});
     child.on("exit",function(code){
       if(!settled)fail(Error("NanoTrack se cerró al iniciar ("+code+"): "+stderr.slice(-500)));
       else{
         ready=false;proc=null;starting=null;
         while(requests.length)requests.shift().reject(Error("NanoTrack se cerró: "+stderr.slice(-300)));
         if(!busy)status("Motor detenido. Pulsá Reintentar para conectarlo.");
         controls();
       }
     });
     var input=readline.createInterface({input:child.stdout});
     input.on("line",function(line){
       var response;
       try{response=JSON.parse(line);}
       catch(e){if(!settled)fail(Error("Respuesta de arranque ilegible"));return;}
       if(!settled){
         if(response.ok&&response.ready){
           settled=true;clearTimeout(timer);ready=true;controls();
           status("Motor listo. Seleccioná una capa y pulsá Preparar objetivo.");
           resolve();
         }else fail(Error(response.error||"NanoTrack no pudo inicializarse."));
         return;
       }
       var item=requests.shift();
       if(item){
         if(response.ok)item.resolve(response);
         else item.reject(Error(response.error||"Error de NanoTrack"));
       }
     });
   }catch(e){fail(e);}
 }).catch(function(e){
   starting=null;ready=false;
   status("No se pudo iniciar NanoTrack: "+e.message+" · Pulsá Reintentar.");
   controls();throw e;
 });
 return starting;
}
async function rpc(cmd){
 await launch(); // ESPERAR handshake real; no dar error por arranque en curso.
 return new Promise(function(resolve,reject){
   if(!ready||!proc)return reject(Error("NanoTrack se desconectó. Pulsá Reintentar."));
   requests.push({resolve:resolve,reject:reject});
   try{proc.stdin.write(JSON.stringify(cmd)+"\n");}
   catch(e){requests.pop();reject(e);}
 });
}
function applyFields(r){
 if(r.width!==undefined)$("roiW").value=Math.round(r.width);
 if(r.height!==undefined)$("roiH").value=Math.round(r.height);
 if(r.show!==undefined)$("roiShow").checked=!!r.show;
}
async function prepare(){
 try{
   var p=await bridge("prepare",[]);
   applyFields(p);
   status("Objetivo listo en "+p.layer_name+". Arrastrá el punto sobre el video. Luego pulsá Analizar.");
 }catch(e){status("Error al preparar: "+e.message);}
}
async function setRegion(){
 try{
   var r=await bridge("setRegion",[
      Number($("roiW").value),Number($("roiH").value),$("roiShow").checked]);
   applyFields(r);
   status("Selección actualizada. Mové el punto en el visor para elegir el objetivo.");
 }catch(e){status("Error de selección: "+e.message);}
}
async function begin(){
 var s=await bridge("selection",[]);
 job={video:s.video,comp_name:s.comp_name,layer_name:s.layer_name,
      layer_start:s.layer_start,source_width:s.source_width,
      source_height:s.source_height,start_seconds:s.start_seconds,end_seconds:s.end_seconds,
      bbox:s.bbox,confidence_threshold:.24};
 var r=await rpc({cmd:"init",job:job});
 await updateAE();
 refresh(1);
 return r;
}
async function updateAE(){
 await rpc({cmd:"snapshot",output:resultPath});
 return bridge("applyProgress",[resultPath]);
}
async function run(automatic){
 if(busy)return;
 lock(true);cancel=false;
 try{
   await launch(); // Si el motor tarda, esperar antes de seguir.
   if(!job){await bridge("prepare",[]);await begin();}
   do{
     var r=await rpc({cmd:"step",count:automatic?8:1});
     await updateAE();refresh(r.total);
     if(r.needs_correction){
       status("Confianza baja: ajustá el punto en el fotograma problemático y pulsá Corregir.");
       break;
     }
     if(r.ended||!r.new.length){
       status("Seguimiento finalizado: "+r.total+" cuadros. Pulsá Crear Null.");
       break;
     }
     status("Siguiendo... "+r.total+" cuadros. Podés detener y corregir.");
     if(!automatic)break;
     await new Promise(function(ok){setTimeout(ok,0);});
   }while(!cancel);
   if(cancel)status("Seguimiento detenido. Podés corregir o generar el Null.");
 }catch(e){status("Error: "+e.message);}
 finally{lock(false);}
}
async function correct(){
 if(busy||!job)return status("Primero iniciá el seguimiento.");
 try{
   var s=await bridge("currentCorrection",[]);
   var r=await rpc({cmd:"reseed",source_seconds:s.source_seconds,bbox:s.bbox});
   await updateAE();
   status("Corrección guardada en cuadro "+r.corrected.frame+". Podés continuar.");
 }catch(e){status("Error de corrección: "+e.message);}
}
async function makeNull(){
 if(busy||!job)return status("Primero iniciá el seguimiento.");
 try{
   await rpc({cmd:"snapshot",output:resultPath});
   var r=await bridge("makeNull",[resultPath]);
   status("Null creado: "+r.keyframes+" keyframes de posición.");
 }catch(e){status("Error creando Null: "+e.message);}
}
$("prepare").onclick=prepare;
$("region").onclick=setRegion;
$("connect").onclick=function(){launch().catch(function(){});};
$("start").onclick=function(){run(true);};
$("step").onclick=function(){run(false);};
$("stop").onclick=function(){cancel=true;};
$("correct").onclick=correct;
$("null").onclick=makeNull;
$("new").onclick=function(){if(!busy){
  job=null;refresh(0);controls();
  status("Nueva sesión. Seleccioná el video y usá Preparar objetivo.");
}};
window.addEventListener("beforeunload",function(){if(proc)try{proc.kill();}catch(ignore){}});
controls();
launch().catch(function(){}); // Se anuncia el error en la UI, sin rechazos sueltos.
})();