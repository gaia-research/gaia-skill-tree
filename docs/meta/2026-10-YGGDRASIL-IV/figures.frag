<style>
.ygg-fig{--y-ink:#111;--y-mute:#666;--y-line:#e3e3df;--y-soft:#f6f6f3;--y-acc:#ef4444;--y-good:#15803d;--y-blue:#1d4ed8;--y-gold:#b45309;--y-grey:#9ca3af;
  margin:2.2rem -2rem;padding:1.4rem 1.6rem 1.5rem;background:#fff;border:1px solid var(--y-line);border-radius:6px;font-family:var(--font-sans);font-size:.92rem;color:var(--y-ink);line-height:1.45;font-variant-numeric:tabular-nums lining-nums}
@media(max-width:760px){.ygg-fig{margin:2rem -.5rem;padding:1rem .9rem}}
.ygg-fig h4{margin:0 0 .15rem;font-size:1.05rem;font-weight:700}
.ygg-fig .sub{color:var(--y-mute);margin:0 0 1rem;font-size:.85rem}
.ygg-fig .tabs,.ygg-fig .chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.2rem 0 1rem}
.ygg-fig button{font:inherit;font-size:.82rem;border:1px solid var(--y-line);background:#fff;color:var(--y-ink);padding:.3rem .7rem;border-radius:999px;cursor:pointer}
.ygg-fig button:hover{border-color:var(--y-ink)}
.ygg-fig button[aria-pressed=true]{background:var(--y-ink);color:#fff;border-color:var(--y-ink)}
.ygg-fig select,.ygg-fig input[type=search]{font:inherit;font-size:.85rem;padding:.35rem .6rem;border:1px solid var(--y-line);border-radius:6px;max-width:100%}
.ygg-fig .note{color:var(--y-mute);font-size:.8rem;margin-top:.8rem}
.ygg-fig .cap{color:var(--y-mute);font-size:.78rem;margin-top:.9rem;border-top:1px solid var(--y-line);padding-top:.6rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.7rem}
.tile{background:var(--y-soft);border-radius:6px;padding:.8rem .9rem}
.tile b{display:block;font-size:1.85rem;line-height:1.1;font-weight:700}
.tile i{font-style:normal;font-size:.78rem;color:var(--y-good);font-weight:600}
.tile span{display:block;font-size:.78rem;color:var(--y-mute);margin-top:.2rem}
.brow{display:grid;grid-template-columns:6.5rem 1fr 6rem;gap:.6rem;align-items:center;margin:.3rem 0}
.brow .l{font-size:.82rem}.brow .v{font-size:.8rem;text-align:right}
.bar{height:.7rem;background:var(--y-soft);border-radius:3px;position:relative;overflow:hidden}
.bar>u{position:absolute;left:0;top:0;bottom:0;border-radius:3px;text-decoration:none;transition:width .5s}
.bar.thin{height:.45rem}
.legend{display:flex;gap:1rem;flex-wrap:wrap;font-size:.78rem;color:var(--y-mute);margin-bottom:.6rem}
.legend s{display:inline-block;width:.7rem;height:.7rem;border-radius:2px;margin-right:.3rem;text-decoration:none;vertical-align:-1px}
.steps{display:flex;gap:0;margin:.4rem 0 1.1rem;overflow-x:auto}
.step{flex:1;min-width:92px;text-align:center;position:relative;padding-top:2.1rem;font-size:.76rem;color:var(--y-mute)}
.step:before{content:"";position:absolute;top:.95rem;left:0;right:0;height:2px;background:var(--y-line)}
.step:first-child:before{left:50%}.step:last-child:before{right:50%}
.step em{position:absolute;top:.35rem;left:50%;margin-left:-.7rem;width:1.4rem;height:1.4rem;border-radius:50%;background:#fff;border:2px solid var(--y-grey);font-style:normal;font-size:.8rem;line-height:1.1rem;color:var(--y-grey);z-index:1}
.step.pass em{border-color:var(--y-good);color:#fff;background:var(--y-good)}
.step.stop em{border-color:var(--y-acc);color:#fff;background:var(--y-acc)}
.step.warn em{border-color:var(--y-gold);color:#fff;background:var(--y-gold)}
.step.pass,.step.stop,.step.warn{color:var(--y-ink)}
.verdict{background:var(--y-soft);border-left:3px solid var(--y-ink);padding:.6rem .8rem;border-radius:0 6px 6px 0;font-size:.86rem;margin-top:.8rem}
.stair{display:flex;align-items:flex-end;gap:.5rem;height:130px;margin:.4rem 0 1rem}
.stair div{flex:1;background:var(--y-soft);border:1px solid var(--y-line);border-radius:4px 4px 0 0;position:relative;text-align:center;font-size:.78rem;display:flex;flex-direction:column;justify-content:flex-end;padding-bottom:.3rem}
.stair div b{font-size:1rem}
.stair div.on{background:var(--y-ink);color:#fff;border-color:var(--y-ink)}
.tbl{width:100%;border-collapse:collapse;font-size:.82rem}
.tbl th{text-align:left;font-weight:600;color:var(--y-mute);border-bottom:1px solid var(--y-ink);padding:.3rem .4rem;font-size:.75rem}
.tbl td{padding:.35rem .4rem;border-bottom:1px solid var(--y-line);vertical-align:middle}
.tbl code{font-size:.78rem;word-break:break-all}
.scroll{overflow-x:auto}
.g{display:inline-block;min-width:1.35rem;text-align:center;border-radius:3px;font-size:.72rem;font-weight:700;padding:.05rem .3rem;color:#fff}
.gS{background:var(--y-gold)}.gA{background:var(--y-good)}.gB{background:var(--y-blue)}.gC{background:var(--y-grey)}.gU{background:var(--y-grey);opacity:.6}
.dumb{position:relative;height:.9rem;background:var(--y-soft);border-radius:3px;min-width:140px}
.dumb i{position:absolute;top:50%;height:2px;background:var(--y-mute);transform:translateY(-50%)}
.dumb b{position:absolute;top:50%;width:.6rem;height:.6rem;border-radius:50%;transform:translate(-50%,-50%)}
.stack{display:flex;height:1.5rem;border-radius:4px;overflow:hidden;background:var(--y-soft)}
.stack span{display:block;height:100%;transition:width .5s}
.ev{display:grid;grid-template-columns:5.4rem 1fr;gap:.2rem .7rem;padding:.4rem 0;border-bottom:1px solid var(--y-line);font-size:.82rem}
.ev .d{color:var(--y-mute);font-size:.76rem}
.ev .t{font-size:.72rem;font-weight:700;letter-spacing:.02em;text-transform:uppercase}
.days{display:flex;align-items:flex-end;gap:.3rem;height:120px;margin:.2rem 0 .3rem}
.days button{flex:1;border-radius:3px 3px 0 0;border:0;padding:0;background:var(--y-soft);display:flex;flex-direction:column-reverse;height:100%;overflow:hidden;position:relative}
.days button[aria-pressed=true]{outline:2px solid var(--y-ink)}
.dl{display:flex;gap:.3rem;font-size:.68rem;color:var(--y-mute)}.dl span{flex:1;text-align:center}
.bk{border:1px solid var(--y-line);border-radius:6px;margin:.35rem 0}
.bk>summary{padding:.45rem .7rem;cursor:pointer;display:flex;justify-content:space-between;gap:.6rem;font-size:.84rem}
.bk[open]>summary{border-bottom:1px solid var(--y-line)}
.bk .in{padding:.4rem .7rem}
.pill{font-size:.7rem;border-radius:999px;padding:.05rem .5rem;background:var(--y-soft);color:var(--y-mute)}
.pill.t{background:var(--y-gold);color:#fff}
.wreath{color:var(--y-gold);font-weight:700}
.calc{display:flex;gap:.8rem;flex-wrap:wrap;align-items:center;margin:.6rem 0}
.big{font-size:1.4rem;font-weight:700}
</style>
<script>
(function(){
var D=JSON.parse(document.getElementById('ygg-data').textContent);
function $(t,a){var e=document.createElement(t);a=a||{};for(var k in a){if(k==='class')e.className=a[k];else if(k==='html')e.innerHTML=a[k];else if(k.slice(0,2)==='on')e.addEventListener(k.slice(2),a[k]);else e.setAttribute(k,a[k]);}
 for(var i=2;i<arguments.length;i++){var c=arguments[i];if(c==null)continue;if(Array.isArray(c))c.forEach(function(x){e.append(x)});else e.append(c.nodeType?c:String(c));}return e;}
var C={S:'var(--y-gold)',A:'var(--y-good)',B:'var(--y-blue)',C:'var(--y-grey)',ungraded:'var(--y-grey)'};
function gchip(g){var k=g==='ungraded'||!g?'U':g;return $('span',{class:'g g'+k},g==='ungraded'||!g?'–':g);}
function fmt(n){return n==null?'–':(Math.round(n*100)/100).toString();}
function tabs(opts,cur,cb){var w=$('div',{class:'tabs',role:'group'});opts.forEach(function(o){var b=$('button',{type:'button','aria-pressed':String(o[0]===cur),onclick:function(){cb(o[0]);}},o[1]);w.append(b);});return w;}
function chips(opts,cur,cb){var w=$('div',{class:'chips',role:'group'});opts.forEach(function(o){w.append($('button',{type:'button','aria-pressed':String(o[0]===cur),onclick:function(){cb(o[0]);}},o[1]));});return w;}
function head(el,t,s){el.append($('h4',{},t),s?$('p',{class:'sub'},s):null);}
var F={};

/* 1 hero numbers */
F.hero=function(el){
 var nAdded=D.added.length, ev=D.events.length, touched=new Set(D.events.map(function(e){return e[0]})).size;
 var T=[[473,'named skills','+'+nAdded+' since ratification'],[311,'generic skills','+12 new, 1 renamed'],[touched,'skills with a changelog entry','between Oct 25 and Nov 3'],[ev,'recorded changes','each one dated and linked to its skill'],[4,'challenges run','0 admitted'],[817,'audit findings that held up','of 930 raised'],[51,'founder-approved decisions','of 190 reviewed'],[0,'skills marked contested','none today']];
 head(el,'October at a glance','Every number below is read from the live registry and the closeout record, not typed by hand.');
 var g=$('div',{class:'tiles'});
 T.forEach(function(t){var b=$('b',{},'0');g.append($('div',{class:'tile'},b,t[2].charAt(0)==='+'?$('i',{},t[2]):null,$('span',{},t[1]+(t[2].charAt(0)==='+'?'':' · '+t[2])))); t.push(b);});
 el.append(g);
 function run(){T.forEach(function(t){var b=t[3],to=t[0];if(matchMedia('(prefers-reduced-motion: reduce)').matches||to===0){b.textContent=to;return;}var s=performance.now();(function f(n){var p=Math.min(1,(n-s)/900);b.textContent=Math.round(to*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(f);})(s);});}
 if('IntersectionObserver' in window){var io=new IntersectionObserver(function(x){if(x[0].isIntersecting){run();io.disconnect();}});io.observe(el);}else run();
 el.append($('div',{class:'cap'},'Baseline is the day Yggdrasil IV was ratified (October 25). Figures run through the October 31 cutoff, the November 2 final ledger and one November 3 correction to frozen skills.'));
};

/* 2 growth */
F.growth=function(el){
 var mode='stars';
 function draw(){el.innerHTML='';head(el,'How the tree shifted','Light bar: October 25. Dark bar: now.');
  el.append(tabs([['stars','Named skills by star level'],['grades','Trust ledger by grade']],mode,function(m){mode=m;draw();}));
  var S=mode==='stars'?D.stars:D.grades;var mx=Math.max.apply(null,S.before.concat(S.after));
  S.labels.forEach(function(l,i){var b=S.before[i],a=S.after[i],d=a-b;
   el.append($('div',{class:'brow'},$('div',{class:'l'},l),$('div',{},
     $('div',{class:'bar thin'},$('u',{style:'width:'+b/mx*100+'%;background:var(--y-grey)'})),
     $('div',{class:'bar',style:'margin-top:3px'},$('u',{style:'width:'+a/mx*100+'%;background:var(--y-ink)'}))),
     $('div',{class:'v'},b+' → '+a+(d?' ('+(d>0?'+':'')+d+')':''))));});
  el.append($('div',{class:'cap'},mode==='stars'?'Counts named skills only (426 now). The 2★ jump is the 75 skills added in October: 73 from the curator topology review and 2 curated earlier in the month.':'The ledger covers '+D.grades.rowsBefore+' entries on October 25 and '+D.grades.rowsAfter+' now. 37 suite skills went from ungraded to B, and several evidence re-derivations moved skills up a grade.'));}
 draw();};

/* 3 challenge lab */
var CASES=[
 {id:'C1',t:'Graphify vs graft',q:'Does Graphify find the callers of a function better than graft?',st:['pass','pass','pass','pass','stop'],lab:['Lead found','Triaged','Test run','Re-checked','Admitted'],
  bars:{title:'Recall on five functions (higher is better)',rows:[['Function 1',.727,.727],['Function 2',1,1],['Function 3',.75,.75],['Function 4',1,1],['Function 5',.667,.667]],a:'Graphify',b:'graft',max:1},
  out:'A tie. The two tools returned identical caller lists on all five functions: 22 correct callers each, and the same 5 call sites missed. Under the rule written before the test, a tie means Graphify showed no advantage. That does not mean graft is better. Not admitted.'},
 {id:'C2',t:'Claude Code deny rules vs git-guardrails',q:'Do Claude Code’s built-in deny rules make the git-guardrails hook unnecessary?',st:['pass','pass','pass','warn','stop'],lab:['Lead found','Triaged','Test run','Re-checked','Admitted'],
  bars:{title:'Of 18 test commands',rows:[['Dangerous blocked (of 12)',10,8],['Safe allowed (of 6)',6,5]],a:'Built-in rules',b:'Hook',max:12},
  out:'The runner said “supported”. An independent re-run reproduced the numbers exactly, then downgraded the verdict to inconclusive: the test set was frozen after the hook’s results were already known, so it leaned toward the built-in rules. Not admitted.'},
 {id:'C3',t:'git log -L vs graft',q:'Does git log -L trace a function’s history as well as graft?',st:['pass','pass','warn','pass','stop'],lab:['Lead found','Triaged','Test run','Re-checked','Admitted'],bars:null,
  out:'Inconclusive by design. The two tools do different jobs, and the Git version that ran differed from the documented one, so the written rule allowed at most “inconclusive”. Not admitted.'},
 {id:'C4',t:'ripgrep vs graft callers',q:'Is ripgrep a challenger to graft’s caller lookup?',st:['pass','stop','skip','skip','skip'],lab:['Lead found','Triaged','Test run','Re-checked','Admitted'],bars:null,
  out:'Rejected at triage. ripgrep is a text search and makes no claim about resolving callers, so there was nothing to test. No experiment ran. Not admitted.'}];
F.lab=function(el){
 var cur=0;
 function draw(){el.innerHTML='';head(el,'Challenge Lab: four cases, step by step','Pick a case to see how far it got. A case only counts once it clears every step.');
  el.append(chips(CASES.map(function(c,i){return [i,c.id+' · '+c.t];}),cur,function(i){cur=i;draw();}));
  var c=CASES[cur];el.append($('p',{},$('b',{},'The question: '),c.q));
  var s=$('div',{class:'steps'});c.lab.forEach(function(l,i){var k=c.st[i];s.append($('div',{class:'step '+k},$('em',{},k==='pass'?'✓':k==='stop'?'✕':k==='warn'?'!':'–'),l));});el.append(s);
  if(c.bars){var b=c.bars;el.append($('div',{class:'legend'},$('span',{},$('s',{style:'background:var(--y-ink)'}),b.a),$('span',{},$('s',{style:'background:var(--y-grey)'}),b.b)));el.append($('div',{class:'note',style:'margin:0 0 .4rem'},b.title));
   b.rows.forEach(function(r){var f=function(v){return b.max===1?v.toFixed(3):v;};el.append($('div',{class:'brow'},$('div',{class:'l'},r[0]),$('div',{},$('div',{class:'bar thin'},$('u',{style:'width:'+r[1]/b.max*100+'%;background:var(--y-ink)'})),$('div',{class:'bar thin',style:'margin-top:3px'},$('u',{style:'width:'+r[2]/b.max*100+'%;background:var(--y-grey)'}))),$('div',{class:'v'},f(r[1])+' / '+f(r[2]))));});}
  el.append($('div',{class:'verdict'},c.out));
  el.append($('div',{class:'cap'},'Across all four: 0 admitted, so 0 skills were marked contested and no star, grade or score moved because of a challenge. Each case has a public review record on the Trust Challenges page.'));}
 draw();};

/* 4 clamp */
F.clamp=function(el){
 var cap=D.clampStaircase, order=['ungraded','C','B','A','S'];
 var stored=4,grade='B';
 head(el,'The grade ceiling: try it','A skill’s displayed stars can never be higher than its Trust Grade allows. Ceilings: ungraded 1★, C 2★, B 3★, A 4★, S 6★.');
 var out=$('div'),st=$('div',{class:'stair'});
 var selS=$('select',{'aria-label':'Stored stars'}),selG=$('select',{'aria-label':'Trust Grade'});
 [1,2,3,4,5,6].forEach(function(n){selS.append($('option',{value:n},n+'★ stored'));});selS.value=4;
 order.forEach(function(g){selG.append($('option',{value:g},'Grade '+g));});selG.value='B';
 function upd(){stored=+selS.value;grade=selG.value;var shown=Math.min(stored,cap[grade]);
  st.innerHTML='';order.forEach(function(g){st.append($('div',{class:g===grade?'on':'',style:'height:'+(cap[g]/6*100)+'%'},$('b',{},cap[g]+'★'),g));});
  out.innerHTML='';out.append($('div',{class:'calc'},$('span',{},'Stored '+stored+'★ on grade '+grade+' → shown '),$('span',{class:'big'},shown+'★'),shown<stored?$('span',{class:'pill t'},'clamped by '+(stored-shown)):$('span',{class:'pill'},'no clamp')));}
 el.append($('div',{class:'calc'},selS,selG),st,out);selS.onchange=selG.onchange=upd;upd();
 el.append($('h4',{style:'margin-top:1.2rem'},'The six skills where it bites today'),$('p',{class:'sub'},'Stored values are never edited. The ledger keeps both.'));
 var t=$('table',{class:'tbl'},$('thead',{},$('tr',{},$('th',{},'Skill'),$('th',{},'Grade'),$('th',{},'Score'),$('th',{},'Stored'),$('th',{},'Shown'))),
  $('tbody',{},D.clamp.map(function(r){return $('tr',{},$('td',{},$('code',{},r.id)),$('td',{},gchip(r.grade)),$('td',{},fmt(r.tm)),$('td',{},r.stored),$('td',{},$('b',{},r.shown)));})));
 el.append($('div',{class:'scroll'},t),$('div',{class:'cap'},'Before October the named-skill pages and the API applied this ceiling, but the trust ledger and the leaderboard showed the stored number. Now every surface agrees. One exception: a frozen skill keeps the stars it was frozen at, so the ceiling never lowers it.'));};

/* 5 evidence mix */
var EVC={arxiv:'#6d28d9','peer-review':'#be185d','github-stars-own':'#1d4ed8','repo-own':'#0f766e','social-signal':'#b45309','self-attestation':'#9ca3af'};
var EVN={arxiv:'Research paper','peer-review':'Peer review','github-stars-own':'GitHub stars','repo-own':'Own repository','social-signal':'Social signal','self-attestation':'Self-attested'};
F.evidence=function(el){
 var ids=['mattpocock/skills','panniantong/agent-reach','browser-use/browser-harness'],cur=ids[0];
 var note={'mattpocock/skills':'One recorded number was wrong: a paper’s citation count had been logged as 500; the live count is 2. The paper’s share fell from 105.2 to 10.6. The score fell from 374.99 to 280.39 and the skill stayed at S and 5★.','panniantong/agent-reach':'Its evidence was re-derived from every source. Before, only social posts and a self-attestation were counted. Now stars, its repository and peer review count too: 53.86 (B) to 260.83 (A). It stays at 3★.','browser-use/browser-harness':'A peer-review source was added. Score 73.59 (B) to 118.59 (A). Stars unchanged at 3★.'};
 function draw(){el.innerHTML='';head(el,'What a score is made of','Each bar is one skill’s Trust score split by evidence type. The pieces add up to the score.');
  el.append(chips(ids.map(function(i){return [i,i];}),cur,function(i){cur=i;draw();}));
  var m=D.movers.filter(function(x){return x.id===cur})[0];var mx=Math.max(m.tmA,m.tmB);var keys={};Object.keys(m.tbB).concat(Object.keys(m.tbA)).forEach(function(k){keys[k]=1;});
  [['Before',m.tbB,m.tmB,m.gB],['After',m.tbA,m.tmA,m.gA]].forEach(function(r){var s=$('div',{class:'stack',style:'width:'+r[2]/mx*100+'%'});Object.keys(keys).forEach(function(k){var v=r[1][k]||0;if(v)s.append($('span',{title:EVN[k]+': '+v,style:'background:'+EVC[k]+';width:'+v/r[2]*100+'%'}));});
   el.append($('div',{style:'margin:.5rem 0'},$('div',{class:'note',style:'margin:0 0 .2rem'},r[0]+': ',$('b',{},fmt(r[2])),' ',gchip(r[3])),s));});
  var lg=$('div',{class:'legend'});Object.keys(keys).forEach(function(k){lg.append($('span',{},$('s',{style:'background:'+EVC[k]}),EVN[k]+' '+fmt(m.tbA[k]||0)));});el.append(lg,$('div',{class:'verdict'},note[cur]));}
 draw();};

/* 6 movers */
F.movers=function(el){
 var f='all',all=D.movers.slice();
 var flt={all:[ 'All '+all.length,function(){return true}],cap:['Suite skills set to 50',function(r){return r.tmA===50&&r.tmB===0}],up:['Score up',function(r){return r.tmA>r.tmB}],down:['Score down',function(r){return r.tmA<r.tmB}],star:['Stars changed',function(r){return r.sA!==r.sB}]};
 var more=false;
 function draw(){el.innerHTML='';head(el,'Every rating that moved','Compared with October 25. Each row is a skill whose score, grade or displayed stars changed.');
  var ks=Object.keys(flt);el.append(chips(ks.map(function(k){return [k,flt[k][0]+' ('+all.filter(flt[k][1]).length+')'];}),f,function(k){f=k;more=false;draw();}));
  var rows=all.filter(flt[f][1]).sort(function(a,b){return Math.abs(b.tmA-b.tmB)-Math.abs(a.tmA-a.tmB);});
  var mx=400;var lim=more?rows.length:12;
  var tb=$('tbody',{});rows.slice(0,lim).forEach(function(r){var l=Math.min(r.tmB,mx)/mx*100,h=Math.min(r.tmA,mx)/mx*100;
   tb.append($('tr',{},$('td',{},$('code',{},r.id)),$('td',{},gchip(r.gB),' → ',gchip(r.gA)),$('td',{},$('div',{class:'dumb',title:fmt(r.tmB)+' → '+fmt(r.tmA)},$('i',{style:'left:'+Math.min(l,h)+'%;width:'+Math.abs(h-l)+'%'}),$('b',{style:'left:'+l+'%;background:var(--y-grey)'}),$('b',{style:'left:'+h+'%;background:'+(r.tmA>=r.tmB?'var(--y-good)':'var(--y-acc)')}))),$('td',{},fmt(r.tmB)+' → '+fmt(r.tmA)),$('td',{},r.sB===r.sA?r.sA:r.sB+' → '+r.sA)));});
  el.append($('div',{class:'scroll'},$('table',{class:'tbl'},$('thead',{},$('tr',{},$('th',{},'Skill'),$('th',{},'Grade'),$('th',{},'Score (0 to 400 scale)'),$('th',{},'Before → after'),$('th',{},'Stars shown'))),tb)));
  if(rows.length>lim)el.append($('button',{type:'button',style:'margin-top:.7rem',onclick:function(){more=true;draw();}},'Show all '+rows.length));
  el.append($('div',{class:'cap'},'Grey dot: October 25. Coloured dot: now. Scores above 400 are drawn at the right edge. “Suite skills set to 50” are the 37 skills that now sit under their parent suite’s per-component cap.'));}
 draw();};

/* 7 origin */
F.origin=function(el){
 var q='',tie=false,open={};
 head(el,'Origin: the highest-merit implementation in each skill family','Origin is computed from merit now, not assigned by hand. Search a family to see who holds it. Ties share it.');
 var inp=$('input',{type:'search',placeholder:'Search a skill family or skill…','aria-label':'Search',style:'width:min(100%,22rem)'});
 var tg=$('button',{type:'button','aria-pressed':'false',onclick:function(){tie=!tie;tg.setAttribute('aria-pressed',String(tie));draw();}},'Shared (tied) Origin only');
 var list=$('div'),sum=$('div',{class:'note'});el.append($('div',{class:'chips'},inp,tg),sum,list,$('div',{class:'cap'},'Showing '+D.buckets.length+' families. 223 hold at least one classified (named) skill and 14 hold only awakened skills (1★ and below, names redacted). Four skills received Origin as clear merit winners this month: vercel-react-best-practices, code-simplification, i-have-adhd and ponytail.'));
 inp.oninput=function(){q=inp.value.toLowerCase();draw();};
 function draw(){list.innerHTML='';var r=D.buckets.filter(function(b){return (!tie||b.tie)&&(!q||b.b.indexOf(q)>-1||b.n.some(function(n){return n.id.toLowerCase().indexOf(q)>-1}));});
  sum.textContent=r.length+' families · '+r.filter(function(b){return b.tie}).length+' with shared Origin';
  r.slice(0,12).forEach(function(b){var d=$('details',{class:'bk'});if(q&&r.length<6)d.open=true;
   d.append($('summary',{},$('span',{},b.b),$('span',{},b.tie?$('span',{class:'pill t'},'shared'):null,' ',$('span',{class:'pill'},b.n.length+' skills'))));
   var t=$('table',{class:'tbl'},$('thead',{},$('tr',{},$('th',{},'Skill'),$('th',{},'Stars'),$('th',{},'Score'),$('th',{},'Origin'))),$('tbody',{},b.n.slice().sort(function(x,y){return (y.org-x.org)||((y.tm||0)-(x.tm||0))}).map(function(n){return $('tr',{},$('td',{},$('code',{},n.id)),$('td',{},n.lvl),$('td',{},fmt(n.tm)),$('td',{},n.org?$('span',{class:'wreath'},'◆ Origin'):''));})));
   d.append($('div',{class:'in scroll'},t));list.append(d);});
  if(r.length>12)list.append($('div',{class:'note'},'Showing first 12. Narrow the search to see the rest.'));}
 draw();};

/* 8 audit */
F.audit=function(el){
 var mode='funnel';
 function draw(){el.innerHTML='';head(el,'The October audit, end to end','Every record in the registry was read. Nothing was changed by the audit itself: findings are proposals until a person approves them.');
  el.append(tabs([['funnel','From records to decisions'],['prio','Findings by priority'],['links','Link check']],mode,function(m){mode=m;draw();}));
  function bars(rows,mx,col){rows.forEach(function(r){el.append($('div',{class:'brow'},$('div',{class:'l',style:'width:auto'},r[0]),$('div',{class:'bar'},$('u',{style:'width:'+r[1]/mx*100+'%;background:'+(r[2]||col)})),$('div',{class:'v'},r[1])));});}
  if(mode==='funnel'){var S=D.sweep,A=D.adj;
   bars([['Records read',S.records],['Findings raised',S.raw],['Findings that survived 2-of-3 review',S.surv],['Decisions drafted',A.cand],['Approved by the founder',A.status.approved,'var(--y-good)'],['Superseded by automatic Origin',A.status.superseded,'var(--y-blue)'],['Still proposed',A.status.proposed,'var(--y-grey)'],['Held for more evidence',A.status.held,'var(--y-gold)'],['Deferred to November',A.status.deferred,'var(--y-grey)']],S.raw,'var(--y-ink)');
   el.append($('div',{class:'cap'},S.named+' named and '+S.generic+' generic records. A finding survived only if at least two of three independent reviewers upheld it. A model-written summary first said 810 survived; a deterministic replay of the run gives 817, and that is what is reported. 45 of the 190 decisions were checked again and found to no longer apply.'));}
  if(mode==='prio'){var P=D.sweep.prio;bars(Object.keys(P).map(function(k){return [k,P[k]];}),Math.max.apply(null,Object.values(P)),'var(--y-ink)');
   el.append($('div',{class:'cap'},'P0 is most urgent. Most findings are low-priority wording, link and evidence-tidying items.'));}
  if(mode==='links'){var L=D.dead;bars([['Links alive',L.alive,'var(--y-good)'],['Links dead',L.total,'var(--y-acc)']],L.all,'var(--y-ink)');
   el.append($('div',{class:'note',style:'margin-top:.8rem'},'What the 59 dead links were:'));var T=L.byType,nm={'links.github':'Install links','github-stars-own':'GitHub star pages','repo':'Repository pages','peer-review':'Peer-review pages','self-attestation':'Self-attestation pages','arxiv':'Paper links','social-signal':'Social posts','B':'Other'};
   bars(Object.keys(T).map(function(k){return [nm[k]||k,T[k]];}),20,'var(--y-grey)');
   el.append($('div',{class:'cap'},'962 links were checked. Of the dead ones, 55 returned “not found” and 4 refused the check. A dead link is review debt with timed re-checks, never an automatic demotion. No rating moved because of a dead link.'));}}
 draw();};

/* 9 added */
F.added=function(el){
 var sel=null;head(el,'75 skills joined the tree','Choose a contributor to see their new skills.');
 var by={};D.added.forEach(function(a){var c=a.id.split('/')[0];(by[c]=by[c]||[]).push(a);});
 var ks=Object.keys(by).sort(function(a,b){return by[b].length-by[a].length});var mx=by[ks[0]].length;var list=$('div');
 ks.forEach(function(k){el.append($('div',{class:'brow',style:'cursor:pointer',role:'button',tabindex:'0',onclick:function(){sel=sel===k?null:k;show();},onkeydown:function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();sel=sel===k?null:k;show();}}},$('div',{class:'l',style:'width:auto'},k),$('div',{class:'bar thin'},$('u',{style:'width:'+by[k].length/mx*100+'%;background:var(--y-ink)'})),$('div',{class:'v'},by[k].length)));});
 el.append(list);
 function show(){list.innerHTML='';if(!sel)return;list.append($('div',{class:'scroll',style:'margin-top:.8rem'},$('table',{class:'tbl'},$('thead',{},$('tr',{},$('th',{},'Skill'),$('th',{},'Stars'),$('th',{},'Grade'),$('th',{},'Score'))),$('tbody',{},by[sel].map(function(a){return $('tr',{},$('td',{},$('code',{},a.id)),$('td',{},a.lvl),$('td',{},gchip(a.g)),$('td',{},fmt(a.tm)));})))));}
 el.append($('div',{class:'cap'},'73 came from the curator topology review. Two more, nvidia/accelerated-computing-cudf and wheresryan22/anatomy, were curated earlier in the month and arrived at 4★ (grade A). The branch also gained 12 generic skills and renamed one: grill-me became the vendor-neutral interview-me.'));};

/* 10 changelog */
F.changelog=function(el){
 var day=null,act=null,q='',lim=30;
 var LAB=D.evLabels;var days=Object.keys(D.evByDay).sort();
 var col={add:'var(--y-good)',recalibrate_trust_magnitude:'var(--y-blue)',evidence_added:'var(--y-ink)',evidence_removed:'var(--y-acc)',suite_ref_set:'var(--y-gold)',upstream_synced:'var(--y-grey)',note:'var(--y-mute)',upstream_deprecated:'var(--y-acc)',rank_up:'var(--y-good)',demote:'var(--y-acc)',evidence_graded:'var(--y-blue)',name:'var(--y-good)'};
 head(el,'The full changelog: every change, every skill','All '+D.events.length+' recorded changes to named skills from October 25 to November 3. Click a day, a type, or search a skill.');
 var dv=$('div',{class:'days'}),dl=$('div',{class:'dl'}),ch=$('div'),inp=$('input',{type:'search',placeholder:'Search a skill, e.g. garrytan or mattpocock/skills','aria-label':'Search changelog',style:'width:min(100%,24rem);margin-bottom:.8rem'}),res=$('div'),cnt=$('div',{class:'note',style:'margin:.2rem 0 .5rem'}),mb=$('div');
 el.append(dv,dl,$('div',{style:'height:.6rem'}),ch,inp,cnt,res,mb);
 inp.oninput=function(){q=inp.value.toLowerCase();lim=30;draw();};
 function filt(skipAct){return D.events.filter(function(e){return(!day||e[1]===day)&&(skipAct||!act||e[2]===act)&&(!q||e[0].toLowerCase().indexOf(q)>-1||e[3].toLowerCase().indexOf(q)>-1);});}
 function draw(){
  var mx=Math.max.apply(null,days.map(function(d){return Object.values(D.evByDay[d]).reduce(function(a,b){return a+b},0)}));
  dv.innerHTML='';dl.innerHTML='';days.forEach(function(d){var tot=0,b=$('button',{type:'button','aria-pressed':String(day===d),title:d,'aria-label':d,style:'height:100%;',onclick:function(){day=day===d?null:d;lim=30;draw();}});var wrap=$('div',{style:'display:flex;flex-direction:column-reverse;height:'+0+'%'});
   var sum=Object.values(D.evByDay[d]).reduce(function(a,b){return a+b},0);wrap.style.height=sum/mx*100+'%';wrap.style.marginTop='auto';wrap.style.flexDirection='column-reverse';wrap.style.display='flex';
   Object.keys(D.evByDay[d]).forEach(function(a){wrap.append($('span',{style:'display:block;background:'+(col[a]||'var(--y-grey)')+';height:'+D.evByDay[d][a]/sum*100+'%'}));});
   b.style.justifyContent='flex-end';b.style.flexDirection='column';b.append(wrap);dv.append(b);dl.append($('span',{},d.slice(5)+' · '+sum));});
  var base=filt(true),c={};base.forEach(function(e){c[e[2]]=(c[e[2]]||0)+1;});
  ch.innerHTML='';var w=$('div',{class:'chips'});w.append($('button',{type:'button','aria-pressed':String(!act),onclick:function(){act=null;lim=30;draw();}},'All ('+base.length+')'));
  Object.keys(c).sort(function(a,b){return c[b]-c[a]}).forEach(function(a){w.append($('button',{type:'button','aria-pressed':String(act===a),onclick:function(){act=act===a?null:a;lim=30;draw();}},LAB[a]+' ('+c[a]+')'));});ch.append(w);
  var r=filt(false).slice().reverse();cnt.textContent=r.length+' changes'+(day?' on '+day:'')+' · '+new Set(r.map(function(e){return e[0]})).size+' skills';
  res.innerHTML='';r.slice(0,lim).forEach(function(e){res.append($('div',{class:'ev'},$('div',{class:'d'},e[1]),$('div',{},$('div',{class:'t',style:'color:'+(col[e[2]]||'var(--y-mute)')},LAB[e[2]]),$('code',{},e[0]),' ',e[3])));});
  mb.innerHTML='';if(r.length>lim)mb.append($('button',{type:'button',style:'margin-top:.7rem',onclick:function(){lim+=60;draw();}},'Show more ('+(r.length-lim)+' left)'));}
 draw();
 el.append($('div',{class:'cap'},'Read straight from each skill’s own history. Every registry change leaves a dated entry, and nothing here was edited to look tidier. Many entries on the busiest day belong to the 37 suite skills: first scored on borrowed host-repository evidence, then linked to their suite and capped at 50.'));};

document.querySelectorAll('.ygg-fig').forEach(function(el){var f=F[el.getAttribute('data-fig')];if(f)f(el);});
})();
</script>
