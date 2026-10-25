// flow.frag — the S8 flow field (SPEC §7: fbm curl noise; uniforms u_thr / u_bad / u_det; half resolution, 30 Hz, fx 2 only).
// Readable source; 56-field.js carries the same text as a template string (the build inlines js only).
precision mediump float;
uniform vec2  u_res;    // canvas size in device pixels (half resolution)
uniform float u_time;   // seconds since the field was created
uniform float u_thr;    // blank threshold (MATRIX.fieldUniforms: 0.005) → streak density
uniform float u_bad;    // fraction of released live chains invalid at the end (0..1) → warm tint + turbulence
uniform float u_det;    // S.detected (integrity detections) → pulse rings
uniform vec3  u_c0;     // --acc token
uniform vec3  u_c1;     // --bad token
uniform vec3  u_c2;     // --ok token
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
  // streaks: advect the position along the field and sample a sparse line texture
  vec2 q=p+v*0.12*sin(u_time*0.7);
  float lane=fract(q.y*7.0+fbm(q*1.7)*0.9);
  float dens=clamp(u_thr*120.0,0.25,0.9);           // 0.005 → 0.6
  float streak=smoothstep(dens,dens+0.08,1.0-abs(lane-0.5)*2.0)*smoothstep(0.0,0.6,length(v)*0.25);
  float glow=fbm(q*0.8+u_time*0.03)*0.35;
  // detections ring the field: u_det pulses at 1 Hz, decaying with distance from the left edge
  float det=min(u_det,6.0)*0.08*(0.5+0.5*sin(u_time*6.2832))*smoothstep(1.2,0.0,uv.x);
  vec3 col=mix(u_c0,u_c1,clamp(u_bad*1.6,0.0,1.0));
  col=mix(col,u_c2,streak*0.35);
  col=mix(col,u_c1,det);
  float a=streak*0.55+glow*0.6+det*0.5;
  gl_FragColor=vec4(col*a,a*0.75);
}
