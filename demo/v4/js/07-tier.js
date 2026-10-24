/* 07-tier.js — viewer tiers (SPEC §3). Globals: TIER. claude.use(name) resolves a namespace or null and never prompts; nothing blocks first paint.
   BUILD.share → public; user.isOwner() → owner; files non-null → member; else public (badge PRIVATE on a private build).
   Test hooks: TIER.tier, TIER.caps, #tierBadge text; a test installs window.claude.use before load (v4fixture claude=...). */
(function(){
"use strict";
const fns=[];
const TIER={tier:null,private:!(typeof BUILD!=="undefined"&&BUILD&&BUILD.share),caps:{sample:null,files:null,user:null,downloads:null},ready:null,err:null,
  on(f){fns.push(f);if(TIER.tier)try{f(TIER.tier)}catch(e){}},is:t=>TIER.tier===t,
  badgeText(){if(!TIER.private)return"SHARE BUILD";if(!TIER.tier)return"PRIVATE";return TIER.tier==="owner"?"PRIVATE · OWNER":TIER.tier==="member"?"PRIVATE · MEMBER":"PRIVATE"},
  badge(target){const e=typeof target==="string"?$(target):target;if(!e)return;txt(e,TIER.badgeText());e.title=TIER.tier?`tier ${TIER.tier} · sample ${TIER.caps.sample?"✓":"×"} · files ${TIER.caps.files?"✓":"×"} · user ${TIER.caps.user?"✓":"×"} · downloads ${TIER.caps.downloads?"✓":"×"}`:"resolving tier…"},
  show(sel,tiers){const els=typeof sel==="string"?[...document.querySelectorAll(sel)]:[sel];const apply=t=>els.forEach(e=>{if(e&&!tiers.includes(t))e.remove()});if(TIER.tier)apply(TIER.tier);else TIER.on(apply)},
  rank:t=>({public:0,member:1,owner:2}[t]||0)};
async function use(n){try{if(!self.claude||typeof claude.use!=="function")return null;const v=await Promise.race([claude.use(n),new Promise(r=>setTimeout(()=>r(null),12000))]);return v||null}catch(e){TIER.err=(TIER.err||"")+n+": "+String(e&&e.message||e).slice(0,80)+"; ";return null}}
TIER.resolve=function(){if(TIER.ready)return TIER.ready;TIER.ready=(async()=>{
  let tier="public";
  if(!TIER.private){TIER.caps.sample=await use("sample")}
  else{const[sample,files,user,downloads]=await Promise.all([use("sample"),use("files"),use("user"),use("downloads")]);Object.assign(TIER.caps,{sample,files,user,downloads});
    let owner=false;if(user&&typeof user.isOwner==="function"){try{owner=!!(await user.isOwner())}catch(e){}}
    tier=owner?"owner":files?"member":"public"}
  if(self.ENV)Object.assign(ENV.caps,TIER.caps);TIER.tier=tier;
  document.documentElement.dataset.tier=tier;document.querySelectorAll("[data-tier]").forEach(e=>{const need=e.dataset.tier;if(need&&TIER.rank(need)>TIER.rank(tier))e.remove()});
  fns.forEach(f=>{try{f(tier)}catch(e){console.warn("tier listener",e)}});if(self.LOOP)LOOP.dirty(LOOP.bits.TIER);if(self.ENV)ENV._emit();return tier})();return TIER.ready};
Object.assign(self,{TIER});
})();
