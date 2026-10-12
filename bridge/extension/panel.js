/* TomoTrackAI 0.2: panel minimo de control; la ROI es un efecto nativo real. */
(function(){
"use strict";
var $=function(id){return document.getElementById(id);};
var cep=window.__adobe_cep__;
var req=(window.cep_node&&window.cep_node.require)||window.require||window.nodeRequire;
var fs,os,path,spawn,readline,proc=null,ready=false,requests=[],job=null,resultPath="",busy=false,cancel=false;
function status(s){$("status").textContent=String(s);}
function bridge(method,args){
 return new Promise(function(resolve,reject){
   if(!cep||!cep.evalScript)return reject(Error("Abrí el panel dentro de After Effects."));
   var code="tomoBridge."+method+"("+args.map(function(x){return JSON.stringify(x);}).join(",")+")";
   cep.evalScript(code,function(str){
     try {var r=JSON.parse(str);if(r.ok)resolve(r);else reject(Error(r.error||"Error After Effects"));}
     catch(e){reject(Error("Respuesta AE: "+String(str).slice(0,300)));}
   });
 });
}
function rpc(cmd){
 return new Promise(function(resolve,reject){
   if(!ready||!proc)return reject(Error("Motor NanoTrack no iniciado."));
   requests.push({resolve:resolve,reject:reject});
   try{proc.stdin.write(JSON.stringify(cmd)+"\n");}
   catch(e){requests.pop();reject(e);}
 });
}
function lock(state){
 busy=state;
 $("start").disabled=state;
 $("step").disabled=state;
 $("stop").disabled=!state;
 $("correct").disabled=state;
 $("null").disabled=state;
}
function refresh(n){$("count").textContent=String(n)+" cuadros";}
async function launch(){
 try{
   if(!req)throw Error("El panel no tiene acceso al motor Node de CEP.");
   fs=req("fs");os=req("os");path=req("path");spawn=req("child_process").spawn;readline=req("readline");
   var root=path.join(os.homedir(),"Library","Application Support","TomoTrackAI2");
   var exe=path.join(root,"engine","TomoTrackNano","TomoTrackNano");
   resultPath=path.join(root,"jobs","current-track.json");
   if(!fs.existsSync(exe))throw Error("No encuentro el motor instalado. Volvé a ejecutar Instalar_TomoTrackAI_02.command");
   fs.mkdirSync(path.dirname(resultPath),{recursive:true});
   proc=spawn(exe,[],{cwd:path.dirname(exe),stdio:["pipe","pipe","pipe"]});
   var stderr="";
   proc.stderr.on("data",function(b){stderr+=String(b);if(stderr.length>2000)stderr=stderr.slice(-2000);});
   proc.on("error",function(e){ready=false;status("Error al iniciar motor: "+e.message);});
   proc.on("exit",function(c){ready=false;proc=null;while(requests.length)requests.shift().reject(Error("Motor cerrado: "+stderr));
      status("Motor detenido ("+c+"). "+stderr.slice(-250));});
   var input=readline.createInterface({input:proc.stdout});
   input.on("line",function(line){
     try{var r=JSON.parse(line);
       if(!ready){if(r.ready){ready=true;status("NanoTrack listo. Seleccioná la capa con TomoTrack ROI Select.");}
                  else status(r.error||"Error inicializando NanoTrack");return;}
       var it=requests.shift();if(it){if(r.ok)it.resolve(r);else it.reject(Error(r.error||"Error del motor"));}
     }catch(e){status("Respuesta NanoTrack inválida: "+e.message);}
   });
 }catch(e){status(e.message);}
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
   if(!job)await begin();
   do{
     var r=await rpc({cmd:"step",count:automatic?8:1});
     await updateAE();
     refresh(r.total);
     if(r.needs_correction){
       status("Confianza baja. Mové el cabezal al cuadro problemático, corregí el punto y pulsá Corregir.");
       break;
     }
     if(r.ended||!r.new.length){status("Seguimiento finalizado: "+r.total+" cuadros. Podés crear el Null.");break;}
     status("Siguiendo... "+r.total+" cuadros. Detener para revisar.");
     if(!automatic)break;
     await new Promise(function(ok){setTimeout(ok,0);});
   }while(!cancel);
   if(cancel)status("Seguimiento detenido. Podés corregir o exportar.");
 }catch(e){status("Error: "+e.message);}
 finally{lock(false);}
}
async function correct(){
 if(busy||!job)return status("Primero iniciá el seguimiento.");
 try{
   var s=await bridge("currentCorrection",[]);
   var r=await rpc({cmd:"reseed",source_seconds:s.source_seconds,bbox:s.bbox});
   await updateAE();
   status("Corrección confirmada en cuadro "+r.corrected.frame+". Continuá analizando.");
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
$("start").onclick=function(){run(true);};
$("step").onclick=function(){run(false);};
$("stop").onclick=function(){cancel=true;};
$("correct").onclick=correct;
$("null").onclick=makeNull;
$("new").onclick=function(){if(!busy){job=null;refresh(0);status("Nueva sesión. Elegí una capa y situá el cabezal al comienzo.");}};
window.addEventListener("beforeunload",function(){if(proc)try{proc.kill();}catch(ignore){}});
launch();
})();