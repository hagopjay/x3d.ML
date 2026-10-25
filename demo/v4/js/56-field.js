/* 56-field.js — S8 GLSL flow field (SPEC §7 "WebGL: the GLSL flow field"; WORKPLAN 56-field). Wave 3.
   Owns: a raw WebGL quad (no library) mounted in MATRIX.fieldSlot() (#matrixField, behind the Sankey canvas .fl-cv inside .wrap) at fx 2 only.
   Created on FX.set(2) (FX.onChange, plus a bounded LOOP.onFrame retry until 28-matrix has mounted the slot); disposed when fx < 2: the WebGL context is lost
   (WEBGL_lose_context), the canvas removed, the slot's data-mode reset to "2d" so 28-matrix's static streamline texture shows again.
   Uniforms u_thr / u_bad / u_det come from MATRIX.fieldUniforms() every draw; u_c0/u_c1/u_c2 from the --acc / --bad / --ok tokens (re-read on THEME / RESIZE).
   Half resolution (devicePixelRatio / 2), 30 Hz through the LOOP panel registry (panel "field", rateHz 30, always; no own rAF), visibility by IO on the slot.
   Graceful without WebGL: no canvas is appended, data-mode stays "2d", __field.err holds the one-line reason.
   Shader source: demo/v4/shaders/flow.frag is the readable copy; the build inlines js only, so the GLSL is embedded here as template strings (FRAG === the .frag file).
   Globals: FIELD = {create(), dispose(), sync(), active, panel}. Test hooks: __field = {canvas, gl, err, frames, uframes, uniforms, mode, lastDraw, size}.
   v3 had no flow field (nothing ported). */
(function(){
"use strict";
const VERT=`attribute vec2 a_pos;void main(){gl_Position=vec4(a_pos,0.0,1.0);}`;
const FRAG=`precision mediump float;
uniform vec2  u_res;
uniform float u_time;
uniform float u_thr;
uniform float u_bad;
uniform float u_det;
uniform vec3  u_c0;
uniform vec3  u_c1;
uniform vec3  u_c2;
float hash(vec2 p){p=fract(p*vec2(127.1,311.7));p+=dot(p,p+19.19);return fract(p.x*p.y);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
  float a=hash(i),b=hash(i+vec2(1,0)),c=hash(i+vec2(0,1)),d=hash(i+vec2(1,1));
  return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);}
float fbm(vec2 p){float v=0.0,a=0.5;mat2 r=mat2(0.8,0.6,-0.6,0.8);
  for(int i=0;i<4;i++){v+=a*noise(p);p=r*p*2.03;a*=0.5;}return v;}
vec2 curl(vec2 p){const float e=0.02;
  float n1=fbm(p+vec2(0,e)),n2=fbm(p-vec2(0,e)),n3=fbm(p+vec2(e,0)),n4=fbm(p-vec2(e,0));
  return vec2(n1-n2,-(n3-n4))/(2.0*e);}
void main(){
  vec2 uv=gl_FragCoord.xy/u_res;float asp=u_res.x/max(u_res.y,1.0);
  vec2 p=vec2(uv.x*asp,uv.y)*2.2+vec2(u_time*0.045,0.0);
  float turb=1.0+u_bad*1.5;
  vec2 v=curl(p*turb);
  vec2 q=p+v*0.12*sin(u_time*0.7);
  float lane=fract(q.y*7.0+fbm(q*1.7)*0.9);
  float dens=clamp(u_thr*120.0,0.25,0.9);
  float streak=smoothstep(dens,dens+0.08,1.0-abs(lane-0.5)*2.0)*smoothstep(0.0,0.6,length(v)*0.25);
  float glow=fbm(q*0.8+u_time*0.03)*0.35;
  float det=min(u_det,6.0)*0.08*(0.5+0.5*sin(u_time*6.2832))*smoothstep(1.2,0.0,uv.x);
  vec3 col=mix(u_c0,u_c1,clamp(u_bad*1.6,0.0,1.0));
  col=mix(col,u_c2,streak*0.35);
  col=mix(col,u_c1,det);
  float a=streak*0.55+glow*0.6+det*0.5;
  gl_FragColor=vec4(col*a,a*0.75);
}`;
const H={canvas:null,gl:null,err:null,frames:0,uframes:0,uniforms:null,mode:"2d",lastDraw:0,size:[0,0]};
let slot=null,prog=null,U={},t0=0,retries=0,ioFn=null,colAt=0,cols=null,lostFn=null;
const level=()=>self.FX?FX.level:0;
function rgb(tok){const v=(self.cssv?cssv(tok):"")||"";const m=/^#([0-9a-f]{6})$/i.exec(v);if(!m)return[0.22,0.78,0.83];const n=parseInt(m[1],16);return[(n>>16&255)/255,(n>>8&255)/255,(n&255)/255]}
function colours(){cols=[rgb("--acc"),rgb("--bad"),rgb("--ok")]}
function shader(gl,type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){const e=gl.getShaderInfoLog(s)||"compile failed";gl.deleteShader(s);throw new Error(e.slice(0,160))}return s}
function create(){
  if(H.canvas||level()<2)return!!H.canvas;
  slot=self.MATRIX&&MATRIX.fieldSlot?MATRIX.fieldSlot():null;
  if(!slot){if(retries++<1200&&self.LOOP)LOOP.onFrame(create);return false}   /* 28-matrix mounts in SECTIONS.mountAll after this script ran: wait for the slot (≤ 1200 frames) */
  const c=document.createElement("canvas");c.className="fl-gl";c.setAttribute("aria-hidden","true");
  let gl=null;try{gl=c.getContext("webgl",{alpha:true,antialias:false,depth:false,stencil:false,premultipliedAlpha:true,powerPreference:"low-power",failIfMajorPerformanceCaveat:false})}catch(e){gl=null}
  if(!gl){H.err="no WebGL context (fx 2 without WebGL: 2D streamlines kept)";H.gl=null;return false}
  try{
    const p=gl.createProgram();gl.attachShader(p,shader(gl,gl.VERTEX_SHADER,VERT));gl.attachShader(p,shader(gl,gl.FRAGMENT_SHADER,FRAG));gl.linkProgram(p);
    if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||"link failed");
    gl.useProgram(p);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
    const a=gl.getAttribLocation(p,"a_pos");gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);
    U={};["u_res","u_time","u_thr","u_bad","u_det","u_c0","u_c1","u_c2"].forEach(n=>U[n]=gl.getUniformLocation(p,n));
    gl.disable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);prog=p}
  catch(e){H.err="shader: "+e.message;try{const x=gl.getExtension("WEBGL_lose_context");if(x)x.loseContext()}catch(_){}H.gl=null;return false}
  lostFn=ev=>{ev.preventDefault();H.err="WebGL context lost";dispose(true)};c.addEventListener("webglcontextlost",lostFn);
  slot.appendChild(c);slot.dataset.mode="gl";H.canvas=c;H.gl=gl;H.err=null;H.mode="gl";H.frames=0;H.uframes=0;t0=performance.now();colAt=0;colours();
  ioFn=v=>{P.visible=v;if(v)P.forceDraw=true};P.visible=false;IO.observe(slot,ioFn,{rootMargin:"120px"});
  FIELD.active=true;if(self.LOOP)LOOP.dirty(LOOP.bits.RESIZE);return true}
function dispose(lost){
  if(!H.canvas)return;const c=H.canvas,gl=H.gl;
  if(lostFn)c.removeEventListener("webglcontextlost",lostFn);lostFn=null;
  if(gl&&!lost){try{const x=gl.getExtension("WEBGL_lose_context");if(x)x.loseContext()}catch(e){}}
  if(c.parentNode)c.parentNode.removeChild(c);if(slot){slot.dataset.mode="2d";if(ioFn)IO.unobserve(slot,ioFn,{rootMargin:"120px"})}ioFn=null;
  H.canvas=null;H.gl=null;H.mode="2d";H.uniforms=null;prog=null;U={};FIELD.active=false;P.visible=true;
  if(self.LOOP)LOOP.dirty(LOOP.bits.RESIZE|LOOP.bits.THEME)}  /* 28-matrix redraws its 2D streamlines */
function sync(){if(level()>=2)create();else dispose(false)}
function draw(now){
  const gl=H.gl,c=H.canvas;if(!gl||!c||!prog)return;
  const dpr=Math.max(1,Math.min(2,devicePixelRatio||1))/2,w=Math.max(1,Math.round(c.clientWidth*dpr)),h=Math.max(1,Math.round(c.clientHeight*dpr));
  if(c.width!==w||c.height!==h){c.width=w;c.height=h;gl.viewport(0,0,w,h);H.size=[w,h];colours()}
  if(colAt++%60===0)colours();
  const u=self.MATRIX&&MATRIX.fieldUniforms?MATRIX.fieldUniforms():{u_thr:0.005,u_bad:0,u_det:0};H.uniforms=u;H.uframes++;
  gl.uniform2f(U.u_res,w,h);gl.uniform1f(U.u_time,(now-t0)/1000);gl.uniform1f(U.u_thr,+u.u_thr||0);gl.uniform1f(U.u_bad,+u.u_bad||0);gl.uniform1f(U.u_det,+u.u_det||0);
  gl.uniform3f(U.u_c0,cols[0][0],cols[0][1],cols[0][2]);gl.uniform3f(U.u_c1,cols[1][0],cols[1][1],cols[1][2]);gl.uniform3f(U.u_c2,cols[2][0],cols[2][1],cols[2][2]);
  gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);H.frames++;H.lastDraw=now}
const P=LOOP.register({name:"field",bit:LOOP.bits.RESIZE|LOOP.bits.THEME,always:true,rateHz:30,budgetMs:4,draw,degrade(){P.degraded=true}});
const FIELD={create,dispose:()=>dispose(false),sync,active:false,panel:P,FRAG,VERT};
if(self.FX)FX.onChange(sync);
if(self.LOOP)LOOP.onFrame(sync);   /* FX.init at boot may keep level 2 quietly (no change event): check once the loop runs */
if(self.THEME)THEME.onChange(()=>{if(H.gl)colours()});
Object.assign(self,{FIELD,__field:H});
})();
