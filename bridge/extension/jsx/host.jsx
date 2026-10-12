/* TomoTrackAI v0.2 — Bridge de NanoTrack al efecto NATIVO ROI Select.
   Solo orquesta el motor externo; imagen y ROI vienen del .plugin Rust.
   Compatible ExtendScript de After Effects 2024. */
var tomoBridge = tomoBridge || {};
(function(){
var MATCH="TMFX TomoTrackROISelect", LABEL="TomoTrack ROI Select";
function q(x){return '"'+String(x).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n')+'"';}
function n(x){var v=Number(x);return isFinite(v)?String(v):"0";}
function err(e){return '{"ok":false,"error":'+q(e.message||String(e))+'}';}
function comp(){var c=app.project&&app.project.activeItem;if(!(c instanceof CompItem))throw Error("Abrí una composición de After Effects.");return c;}
function fx(l){
    if(!(l instanceof AVLayer))return null;
    var all=l.property("ADBE Effect Parade");
    if(!all)return null;
    for(var i=1;i<=all.numProperties;i++){
        var p=all.property(i);
        if(p.matchName===MATCH||p.name===LABEL)return p;
    }
    return null;
}
function picked(){
    var c=comp(),s=c.selectedLayers,layer=null;
    if(s.length===1&&fx(s[0]))layer=s[0];
    if(!layer){for(var i=1;i<=c.numLayers;i++){
        var x=c.layer(i);
        if(fx(x)){if(layer)throw Error("Hay varias capas con ROI Select; seleccioná la que quieras seguir.");layer=x;}
    }}
    if(!layer)throw Error("Seleccioná una capa que tenga aplicado TomoTrack ROI Select.");
    if(!layer.hasVideo || !(layer.source instanceof FootageItem)||
       !(layer.source.file instanceof File)||!layer.source.file.exists)
        throw Error("Esta fase necesita video de archivo. No admite precomposiciones.");
    if(layer.timeRemapEnabled||Math.abs(layer.stretch-100)>.01||layer.threeDLayer)
        throw Error("Usá una capa 2D sin cambio de velocidad ni remapeo de tiempo.");
    return {c:c,l:layer,f:fx(layer)};
}
function readSelection(z,time){
    var pt=z.f.property(1).valueAtTime(time,false);
    var w=z.f.property(2).valueAtTime(time,false);
    var h=z.f.property(3).valueAtTime(time,false);
    var b={x:pt[0]-w/2,y:pt[1]-h/2,w:w,h:h};
    if(w<12||h<12||b.x<0||b.y<0||
       b.x+w>z.l.source.width||b.y+h>z.l.source.height)
       throw Error("El recuadro esta fuera del video; movelo o reducí tamaño.");
    return b;
}
function load(path){
    var file=new File(path);
    if(!file.exists||!file.open("r"))throw Error("No encuentro los datos de NanoTrack.");
    var raw=file.read();file.close();
    var d=JSON.parse(raw);
    if(!d.samples||!d.samples.length)throw Error("Trayectoria vacia.");
    return d;
}
function locate(d){
    var z=picked();
    if(z.c.name!==d.comp_name||z.l.name!==d.layer_name||
       z.l.source.file.fsName!==d.source_file||
       Math.abs(z.l.startTime-d.layer_start)>.002)
       throw Error("Los datos no corresponden a la capa seleccionada.");
    return z;
}
function clearKeys(prop){for(var k=prop.numKeys;k>=1;k--)prop.removeKey(k);}
/* Acceso unico: se invoca desde la ventana TomoTrackAI.
   Prepara el efecto nativo automaticamente en la capa elegida. */
tomoBridge.prepare=function(){var undo=false;try{
    var c=comp(),s=c.selectedLayers;
    if(s.length!==1)throw Error("Seleccioná exactamente una capa de video en la línea de tiempo.");
    var l=s[0];
    if(!(l instanceof AVLayer)||!l.hasVideo)
       throw Error("La capa elegida no es una capa de video.");
    if(!(l.source instanceof FootageItem)||!(l.source.file instanceof File)||
       !l.source.file.exists)
       throw Error("Por ahora seleccioná un video de archivo (no una precomposición).");
    if(l.timeRemapEnabled||Math.abs(l.stretch-100)>.01||l.threeDLayer)
       throw Error("Usá una capa 2D sin remapeo temporal ni cambio de velocidad.");
    var effect=fx(l),added=false;
    if(!effect){
       app.beginUndoGroup("TomoTrackAI - Preparar selección");undo=true;
       var parade=l.property("ADBE Effect Parade");
       if(!parade||!parade.canAddProperty(MATCH))
           throw Error("No encuentro el componente nativo TomoTrack ROI Select. Reinstalá TomoTrackAI.");
       effect=parade.addProperty(MATCH);
       if(!effect)throw Error("After Effects no pudo añadir el componente de selección.");
       added=true;
    }
    l.selected=true;
    try{effect.property(1).selected=true;}catch(ignore){}
    return '{"ok":true,"added":'+(added?"true":"false")+
           ',"layer_name":'+q(l.name)+
           ',"width":'+n(effect.property(2).value)+
           ',"height":'+n(effect.property(3).value)+
           ',"show":'+(effect.property(4).value?"true":"false")+'}';
}catch(e){return err(e);}finally{if(undo)app.endUndoGroup();}};
tomoBridge.region=function(){try{
    var z=picked();
    return '{"ok":true,"width":'+n(z.f.property(2).value)+
           ',"height":'+n(z.f.property(3).value)+
           ',"show":'+(z.f.property(4).value?"true":"false")+'}';
}catch(e){return err(e);}};
tomoBridge.setRegion=function(width,height,show){var undo=false;try{
    var z=picked(),w=Number(width),h=Number(height);
    if(!isFinite(w)||!isFinite(h)||w<16||h<16||w>3000||h>3000)
       throw Error("El ancho y alto del recuadro deben estar entre 16 y 3000 píxeles.");
    if(z.f.property(2).numKeys||z.f.property(3).numKeys)
       throw Error("Esta selección ya está animada. Usá Nueva sesión antes de cambiar el tamaño.");
    app.beginUndoGroup("TomoTrackAI - Ajustar selección");undo=true;
    z.f.property(2).setValue(w);
    z.f.property(3).setValue(h);
    z.f.property(4).setValue(!!show);
    z.l.selected=true;
    try{z.f.property(1).selected=true;}catch(ignore){}
    return '{"ok":true,"width":'+n(w)+',"height":'+n(h)+
           ',"show":'+(show?"true":"false")+'}';
}catch(e){return err(e);}finally{if(undo)app.endUndoGroup();}};
tomoBridge.selection=function(){try{
    var z=picked(),c=z.c,l=z.l;
    if(c.time<l.inPoint||c.time>=l.outPoint)
        throw Error("Colocá el cabezal dentro del clip.");
    var b=readSelection(z,c.time);
    return '{"ok":true,"video":'+q(l.source.file.fsName)+
       ',"comp_name":'+q(c.name)+',"layer_name":'+q(l.name)+
       ',"layer_start":'+n(l.startTime)+',"source_width":'+n(l.source.width)+
       ',"source_height":'+n(l.source.height)+
       ',"start_seconds":'+n(c.time-l.startTime)+
       ',"end_seconds":'+n(l.outPoint-l.startTime)+
       ',"bbox":{"x":'+n(b.x)+',"y":'+n(b.y)+',"w":'+n(b.w)+',"h":'+n(b.h)+'}}';
}catch(e){return err(e);}};
tomoBridge.applyProgress=function(path){var undo=false;try{
    var d=load(path),z=locate(d),c=z.c,l=z.l;
    if(d.samples.length>9000)throw Error("Demasiados fotogramas, dividí el seguimiento en clips.");
    var time=[],points=[],sizesW=[],sizesH=[],rx=d.source_width/d.width,ry=d.source_height/d.height;
    var previous=-1;
    for(var i=0;i<d.samples.length;i++){
        var s=d.samples[i],t=Number(d.layer_start)+Number(s.source_time);
        if(t<0||t>=c.duration||t<=previous+1e-7)continue;
        previous=t;
        time.push(t);points.push([s.cx*rx,s.cy*ry]);
        sizesW.push(s.bbox[2]*rx);sizesH.push(s.bbox[3]*ry);
    }
    if(!time.length)throw Error("No hay keyframes validos");
    app.beginUndoGroup("TomoTrackAI - Trayectoria NanoTrack");undo=true;
    // Es el efecto NATIVO quien dibuja el ROI interpolado.
    var p=z.f.property(1),w=z.f.property(2),h=z.f.property(3);
    clearKeys(p);clearKeys(w);clearKeys(h);
    p.setValuesAtTimes(time,points);
    w.setValuesAtTimes(time,sizesW);
    h.setValuesAtTimes(time,sizesH);
    c.time=time[time.length-1];
    return '{"ok":true,"keyframes":'+n(time.length)+'}';
}catch(e){return err(e);}finally{if(undo)app.endUndoGroup();}};
tomoBridge.currentCorrection=function(){try{
    var z=picked(),b=readSelection(z,z.c.time);
    return '{"ok":true,"source_seconds":'+n(z.c.time-z.l.startTime)+
       ',"bbox":{"x":'+n(b.x)+',"y":'+n(b.y)+',"w":'+n(b.w)+',"h":'+n(b.h)+'}}';
}catch(e){return err(e);}};
tomoBridge.makeNull=function(path){var undo=false;try{
    var d=load(path),z=locate(d),c=z.c,l=z.l;
    if(d.samples.length<2)throw Error("Seguí al menos dos cuadros.");
    var rx=d.source_width/d.width,ry=d.source_height/d.height;
    var times=[],values=[],prev=-1;
    for(var i=0;i<d.samples.length;i++){
        var s=d.samples[i],t=Number(d.layer_start)+Number(s.source_time);
        if(t>=0&&t<=c.duration&&t>prev+1e-7){
           times.push(t);values.push([s.cx*rx,s.cy*ry]);prev=t;
        }
    }
    if(times.length<2)throw Error("No hay suficientes muestras.");
    app.beginUndoGroup("TomoTrackAI - Crear Null");undo=true;
    var nullL=c.layers.addNull();nullL.name="TomoTrack AI - "+l.name;
    nullL.threeDLayer=false;nullL.parent=null;
    var p=nullL.property("ADBE Transform Group").property("ADBE Position");
    p.setValuesAtTimes(times,values);
    // Resuelve el movimiento de la capa original (posición, escala, rotación).
    p.expression="thisComp.layer("+l.index+").toComp(value);";
    var converted=[];for(var j=0;j<times.length;j++){
       var v=p.valueAtTime(times[j],false);converted.push([v[0],v[1]]);
    }
    p.expression="";p.setValuesAtTimes(times,converted);
    nullL.property("ADBE Transform Group").property("ADBE Scale").setValue([100,100]);
    nullL.inPoint=Math.max(0,times[0]);
    nullL.outPoint=Math.min(c.duration,times[times.length-1]+1/d.fps);
    nullL.selected=true;
    return '{"ok":true,"keyframes":'+n(times.length)+',"name":'+q(nullL.name)+'}';
}catch(e){return err(e);}finally{if(undo)app.endUndoGroup();}};
})();