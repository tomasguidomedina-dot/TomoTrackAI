/* TomoTrackAI v0.3: UNA extensión AE, máscara nativa dibujada con pluma.
   No necesita TomoTrack ROI Select.plugin ni un efecto adicional.
   El contorno de máscara se anima, modo NONE para no recortar el vídeo. */
var tomoMask = tomoMask || {};
(function(){
var TAG="TomoTrackAI - OBJETIVO", state={run:"",lastFrame:-1};
var BUILD_ID="platetrack-0.5.0-bridge-20261012";
function json(v){return JSON.stringify(v);}
function fail(e){return json({ok:false,error:String(e.message||e),bridge_id:BUILD_ID});}
tomoMask.version=function(){return json({ok:true,version:"0.5.0",bridge_id:BUILD_ID});};
function comp(){var x=app.project&&app.project.activeItem;if(!(x instanceof CompItem))throw Error("Abrí una composición de After Effects.");return x;}
function layer(){
 var c=comp(),s=c.selectedLayers;
 if(s.length!==1)throw Error("Seleccioná una sola capa de video en la línea de tiempo.");
 var l=s[0];
 if(!(l instanceof AVLayer)||!l.hasVideo||!(l.source instanceof FootageItem)||
 !l.source.file||!l.source.file.exists)throw Error("Por ahora se necesita una capa de video de archivo (no una precomposición).");
 if(l.timeRemapEnabled||Math.abs(l.stretch-100)>.01||l.threeDLayer)
 throw Error("Se necesita una capa 2D, sin remapeo ni cambio de velocidad.");
 return {c:c,l:l};
}
function masks(l){return l.property("ADBE Mask Parade");}
function chosen(z,allowUnmarked){
 var m=masks(z.l);if(!m||!m.numProperties)throw Error("Dibujá una máscara cerrada sobre el objeto con la herramienta Pluma (G).");
 var tagged=[],selected=[],all=[],i,p;
 for(i=1;i<=m.numProperties;i++){p=m.property(i);if(p.matchName!=="ADBE Mask Atom")continue;all.push(p);
 if(p.name===TAG)tagged.push(p);
 try{if(p.selected||p.property("ADBE Mask Shape").selected)selected.push(p);}catch(ignore){}
 }
 if(selected.length===1)return selected[0];
 if(tagged.length===1)return tagged[0];
 if(allowUnmarked&&all.length===1)return all[0];
 throw Error("Hay varias máscaras: seleccioná una máscara en la línea de tiempo.");
}
function pointArray(a){var out=[],i;for(i=0;i<a.length;i++)out.push([Number(a[i][0]),Number(a[i][1])]);return out;}
function shapeData(sh){return {vertices:pointArray(sh.vertices),inTangents:pointArray(sh.inTangents),
 outTangents:pointArray(sh.outTangents),closed:!!sh.closed};}
function bounds(points){
 if(!points||points.length<3)throw Error("La máscara debe tener al menos tres puntos.");
 var loX=Infinity,loY=Infinity,hiX=-Infinity,hiY=-Infinity;
 for(var i=0;i<points.length;i++){
 var x=Number(points[i][0]),y=Number(points[i][1]);
 if(!isFinite(x)||!isFinite(y))throw Error("La máscara tiene vértices inválidos.");
 loX=Math.min(loX,x);loY=Math.min(loY,y);hiX=Math.max(hiX,x);hiY=Math.max(hiY,y);
 }
 return {x:loX,y:loY,w:hiX-loX,h:hiY-loY};
}
function inspect(){
 var z=layer(),m=chosen(z,true),p=m.property("ADBE Mask Shape");
 var sh=p.valueAtTime(z.c.time,false),s=shapeData(sh),b=bounds(s.vertices);
 if(!s.closed)throw Error("Cerrá la máscara antes de iniciar el seguimiento.");
 if(b.w<12||b.h<12)throw Error("La máscara es demasiado pequeña para rastrear.");
 if(b.x<0||b.y<0||b.x+b.w>z.l.source.width||b.y+b.h>z.l.source.height)
 throw Error("La máscara debe quedar completamente dentro del fotograma.");
 return {z:z,m:m,p:p,sh:s,b:b};
}
function context(z,m){
 return {video:z.l.source.file.fsName,comp_name:z.c.name,layer_name:z.l.name,
 layer_start:z.l.startTime,mask_name:m.name,source_width:z.l.source.width,
 source_height:z.l.source.height};
}
function load(path){var f=new File(path);if(!f.exists||!f.open("r"))throw Error("No puedo leer el tracking.");
 var d=JSON.parse(f.read());f.close();if(!d.samples||!d.samples.length)throw Error("Tracking sin muestras.");return d;}
function locate(d){
 var z=layer(),q=context(z,chosen(z,true));
 if(d.source_file!==q.video||d.comp_name!==q.comp_name||
 d.layer_name!==q.layer_name||Math.abs(d.layer_start-q.layer_start)>.001)
 throw Error("El tracking pertenece a otra capa; seleccioná la capa original.");
 return {z:z,mask:chosen(z,true)};
}
function timeOf(d,s){return Number(d.layer_start)+Number(s.source_time);}
// One PlateTrack matrix produces all transforms. Bounding-box width is NOT scale.
function moved(anchor,s){
 var sh=new Shape(),src=anchor.shape,M=s.matrix;
 if(!M||M.length!==3)throw Error("PlateTrack no devolvió su matriz 3x3.");
 var sx=Number(s.source_scale_x)||1,sy=Number(s.source_scale_y)||1;
 function trans(p){
    var x=Number(p[0])/sx,y=Number(p[1])/sy;
    var z=Number(M[2][0])*x+Number(M[2][1])*y+Number(M[2][2]);
    if(Math.abs(z)<0.0000001)throw Error("Proyección inválida del punto.");
    return [sx*(Number(M[0][0])*x+Number(M[0][1])*y+Number(M[0][2]))/z,
            sy*(Number(M[1][0])*x+Number(M[1][1])*y+Number(M[1][2]))/z];
 }
 var verts=[],ins=[],outs=[];
 for(var i=0;i<src.vertices.length;i++){
    var v=src.vertices[i],iv=src.inTangents[i],ov=src.outTangents[i];
    var q=trans(v),iEnd=trans([v[0]+iv[0],v[1]+iv[1]]),
       oEnd=trans([v[0]+ov[0],v[1]+ov[1]]);
    verts.push(q);ins.push([iEnd[0]-q[0],iEnd[1]-q[1]]);
    outs.push([oEnd[0]-q[0],oEnd[1]-q[1]]);
 }
 sh.vertices=verts;sh.inTangents=ins;sh.outTangents=outs;sh.closed=true;
 return sh;
}
function anchorFor(d,frame){
 var anchors=d.anchors||[],a=null;
 for(var i=0;i<anchors.length;i++)if(anchors[i].frame<=frame)a=anchors[i];else break;
 if(!a)throw Error("No se encontró máscara de referencia para el fotograma "+frame);
 return a;
}
function removeFrom(p,t){
 for(var i=p.numKeys;i>=1;i--)if(p.keyTime(i)>=t-0.000001)p.removeKey(i);
}
tomoMask.useMask=function(){var undo=false;try{
 var a=inspect(),z=a.z,m=a.m,p=a.p;
 if(z.c.time<z.l.inPoint||z.c.time>=z.l.outPoint)
 throw Error("Ubicá el cabezal dentro del video.");
 if(p.numKeys>1)throw Error("Esta máscara ya tiene animación. Dibujá otra máscara para iniciar una sesión nueva.");
 app.beginUndoGroup("TomoTrackAI - Preparar máscara");undo=true;
 // NONE mantiene el fotograma ORIGINAL completo; solo se ve el contorno de AE.
 m.maskMode=MaskMode.NONE;
 m.name=TAG;
 z.l.selected=true;
 p.selected=true;
 state={run:"",lastFrame:-1};
 var job=context(z,m);
 job.start_seconds=z.c.time-z.l.startTime;
 job.end_seconds=z.l.outPoint-z.l.startTime;
 job.bbox=a.b;job.mask_shape=a.sh;
 job.run_id=String(new Date().getTime())+"-"+Math.floor(Math.random()*100000);
 return json({ok:true,job:job,vertices:a.sh.vertices.length});
}catch(e){return fail(e);}finally{if(undo)app.endUndoGroup();}};
tomoMask.applyProgress=function(path){var undo=false;try{
 var d=load(path),r=locate(d),z=r.z,p=r.mask.property("ADBE Mask Shape");
 var ratioX=d.source_width/d.width,ratioY=d.source_height/d.height;
 // Cada snapshot incorpora sólo los fotogramas nuevos: no reescribe miles de claves anteriores.
 if(d.run_id!==state.run){state={run:d.run_id,lastFrame:-1};}
 var applied=0,lastT=z.c.time;
 app.beginUndoGroup("TomoTrackAI - Seguimiento en vivo");undo=true;
 for(var i=0;i<d.samples.length;i++){
    var sample=d.samples[i];
    // Comprobación incremental: actualizar la referencia tras CADA cuadro.
    // Antes se usaba una copia 'lastFrame' que no cambiaba durante el lote.
    // Por eso los lotes de 2+ fotogramas generaban un falso error de secuencia.
    if(sample.frame<=state.lastFrame)continue;
    if(state.lastFrame>=0&&sample.frame>state.lastFrame+1)
       throw Error("v0.5: Faltan cuadros entre "+state.lastFrame+" y "+sample.frame+".");
    var t=timeOf(d,sample);
    if(t<0||t>=z.c.duration||t<z.l.inPoint-0.0001||t>z.l.outPoint+0.0001)continue;
    var anchor=anchorFor(d,sample.frame);
    var scaled={matrix:sample.matrix,source_scale_x:ratioX,source_scale_y:ratioY};
    p.setValueAtTime(t,moved(anchor,scaled));
    state.lastFrame=sample.frame;
    applied++;lastT=t;
 }
 if(applied){
   // Provoca refresco del visor de AE después de cada bloque pequeño.
   z.c.time=lastT;z.l.selected=true;p.selected=true;
 }
 return json({ok:true,applied:applied,total:d.samples.length,last_time:lastT});
}catch(e){return fail(e);}finally{if(undo)app.endUndoGroup();}};
tomoMask.correction=function(){try{
 var a=inspect(),z=a.z,m=a.m;
 return json({ok:true,source_seconds:z.c.time-z.l.startTime,bbox:a.b,
              mask_shape:a.sh});
}catch(e){return fail(e);}};
tomoMask.rewind=function(path){var undo=false;try{
 var d=load(path),r=locate(d),p=r.mask.property("ADBE Mask Shape");
 var frame=d.samples[d.samples.length-1].frame,t=timeOf(d,d.samples[d.samples.length-1]);
 app.beginUndoGroup("TomoTrackAI - Corregir trayectoria");undo=true;
 removeFrom(p,t);
 state.lastFrame=frame-1;
 return json({ok:true,frame:frame});
}catch(e){return fail(e);}finally{if(undo)app.endUndoGroup();}};
tomoMask.makeNull=function(path){var undo=false;try{
 var d=load(path),r=locate(d),z=r.z,l=z.l,c=z.c;
 if(d.samples.length<2)throw Error("Seguí al menos dos fotogramas.");
 var rx=d.source_width/d.width,ry=d.source_height/d.height;
 var times=[],values=[],sxs=[],angles=[],prev=-1;
 for(var i=0;i<d.samples.length;i++){
 var s=d.samples[i],t=timeOf(d,s);
 if(t>=0&&t<=c.duration&&t>prev+0.0000001){
 times.push(t);values.push([s.cx*rx,s.cy*ry]);
 sxs.push(100*Number(s.scale_factor));
 angles.push(Number(s.rotation_deg||0));
 prev=t;
 }
 }
 if(times.length<2)throw Error("No hay suficientes muestras válidas.");
 app.beginUndoGroup("TomoTrackAI - Crear Null");undo=true;
 var nullL=c.layers.addNull();nullL.name="TomoTrackAI - "+l.name;
 nullL.threeDLayer=false;nullL.parent=null;
 var p=nullL.property("ADBE Transform Group").property("ADBE Position");
 p.setValuesAtTimes(times,values);
 p.expression="thisComp.layer("+l.index+").toComp(value);";
 var converted=[];for(var k=0;k<times.length;k++){
 var v=p.valueAtTime(times[k],false);converted.push([v[0],v[1]]);
 }
 p.expression="";p.setValuesAtTimes(times,converted);
 nullL.property("ADBE Transform Group").property("ADBE Scale").setValue([100,100]);
 var tr=nullL.property("ADBE Transform Group");
 var scale=tr.property("ADBE Scale"),rot=tr.property("ADBE Rotate Z");
 var scales=[];
 for(var si=0;si<sxs.length;si++)scales.push([sxs[si],sxs[si]]);
 scale.setValuesAtTimes(times,scales);
 rot.setValuesAtTimes(times,angles);
 nullL.inPoint=Math.max(0,times[0]);
 nullL.outPoint=Math.min(c.duration,times[times.length-1]+1/d.fps);
 nullL.selected=true;
 return json({ok:true,keyframes:times.length,name:nullL.name,scale:true,rotation:true});
}catch(e){return fail(e);}finally{if(undo)app.endUndoGroup();}};
})();