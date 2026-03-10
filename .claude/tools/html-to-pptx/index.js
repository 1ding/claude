#!/usr/bin/env node
/**
 * html-to-pptx  v4  (component-template architecture)
 *
 * Browser : getBoundingClientRect() → exact positions
 *           + structured content extraction per component
 * Node.js : predefined style templates per data-block type
 *           → pptxgenjs rendering
 *
 * Dispatch order:
 *   1. data-block attribute  (explicit, preferred)
 *   2. CSS class name        (fallback)
 *   3. tag name              (table)
 *   4. data-ppt attribute    (legacy)
 *   5. Placeholder           (unrecognized → grey box + label)
 *
 * Usage: node index.js <input.html> <output.pptx>
 */
const puppeteer = require('puppeteer-core');
const pptxgen   = require('pptxgenjs');
const path      = require('path');
const fs        = require('fs');

const CHROME     = '/usr/bin/google-chrome';
const SLIDE_W_IN = 13.333;
const SLIDE_PX   = 1280;

const inOf  = px => +(px / SLIDE_PX * SLIDE_W_IN).toFixed(4);
const ptOf  = px => +(px * 0.75).toFixed(2);

/* ── Parse browser computed color "rgb(r,g,b)" → 6-char HEX ─────────────── */
function parseComputedColor(rgbStr) {
  if (!rgbStr) return null;
  const m = rgbStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return null;
  const hex = [m[1],m[2],m[3]].map(n=>parseInt(n).toString(16).padStart(2,'0')).join('').toUpperCase();
  // Ignore if it matches the slide background (near-black navy)
  if (hex === '0A1628') return null;
  return hex;
}

/* ── Detect serif from computed fontFamily string ─────────────────────────── */
function isSerifFont(ff) {
  return /serif/i.test(ff) && !/sans/i.test(ff);
}

/* ── Design tokens ─────────────────────────────────────────────────────── */
const C = {
  navy:'0A1628', navyMid:'132240', navyLight:'1A3058',
  gold:'C9A84C', goldL:'E8CC6A',
  white:'F0ECE4', muted:'8A9BB5',
  red:'D94F4F', blue:'3B7DD8', green:'3AAD6B',
  teal:'2BA8A8', orange:'E08A3C',
  border:'1E2C48', goldLine:'2A2414',
};
// Cross-platform Chinese fonts: Microsoft YaHei (Windows) / WenQuanYi Micro Hei (Linux)
// YaHei Light for body text (lighter weight), YaHei for headers/labels
const F = {
  sans:  'Microsoft YaHei',        // headers, labels, emphasis
  body:  'Microsoft YaHei Light',  // body / running text (lighter)
  serif: 'Microsoft YaHei',        // previously Noto Serif, now YaHei for compatibility
};
// Font size scale — titles always ≥ body + 1pt; same-size titles are bolded
const FS = { heading:14, subheading:13, body:12, small:11, xsmall:10 };

const TAG_COLOR = {
  'tag-done':C.green, 'tag-attack':C.red,
  'tag-base':C.blue,  'tag-tbd':C.orange,
  'tag-break':C.goldL,'tag-deep':C.teal,
};
const I_COLOR = {
  'i-attack':'FF8A8A','i-break':C.goldL,'i-deep':C.teal,
  'i-base':C.blue,'i-mature':C.green,'i-lead':'6CE89A','i-tbd':C.orange,
};
const HEAT_BG = {
  'h-attack':'2E1515','h-break':'2A2414','h-deep':'122428',
  'h-base':'121C30','h-mature':'12241C','h-lead':'14281E','h-tbd':'281E12',
};
const HEAT_FG = {
  'h-attack':'FF8A8A','h-break':C.goldL,'h-deep':C.teal,
  'h-base':C.blue,'h-mature':C.green,'h-lead':'6CE89A','h-tbd':C.orange,
};
const HEAT_BOLD = new Set(['h-attack','h-break','h-lead']);

/* ── Browser extractor (injected via page.evaluate) ────────────────────── */
const EXTRACTOR = `
(function(){
function clsList(el){return [...(el.classList||[])]}
function hasCls(el,c){return el.classList&&el.classList.contains(c)}
function pos(el,cr){
  const r=el.getBoundingClientRect();
  return {x:r.left-cr.left,y:r.top-cr.top,w:r.width,h:r.height};
}

// Identify component type: data-block first, then CSS class, then tag
function compType(el){
  const db=el.dataset&&el.dataset.block;
  if(db) return db;
  const cls=clsList(el);
  const tag=el.tagName.toLowerCase();
  const dp=el.dataset&&el.dataset.ppt||'';
  if(cls.includes('col-card'))     return 'col-card';
  if(cls.includes('emphasis-box')) return 'emphasis-box';
  if(cls.includes('metric-card'))  return 'metric-card';
  if(cls.includes('phase-block'))  return 'phase-block';
  if(cls.includes('arrow-right'))  return 'arrow-right';
  if(cls.includes('section-header'))return 'section-header';
  if(cls.includes('section-label')) return 'section-label';
  if(cls.includes('bullet-list')||tag==='ul')return 'bullet-list';
  if(tag==='table'||cls.includes('mini-table'))return 'table';
  if(cls.includes('toc-item'))     return 'toc-item';
  if(cls.includes('slide-header')) return 'slide-header';
  if(cls.includes('slide-footer')) return 'slide-footer';
  if(dp==='text')                  return 'text';
  if(dp==='shape'||dp==='group')   return 'panel';
  return null;
}

// Extract styled runs (strong, span, br)
// Uses getComputedStyle to capture CSS-class-based colors (e.g. .bullet-list li strong)
function styledRuns(el){
  const runs=[];
  for(const n of el.childNodes){
    if(n.nodeType===3){const t=n.textContent.trim();if(t)runs.push({text:t});}
    else if(n.nodeType===1){
      const tag=n.tagName.toLowerCase();
      const cls=clsList(n);
      if(tag==='strong'||tag==='b'){
        const st=window.getComputedStyle(n);
        runs.push({text:n.textContent.trim(),bold:true,
          computedColor:st.color||'',
          computedFont:st.fontFamily||''});
      } else if(tag==='span'){
        const iCls=cls.find(c=>c.startsWith('i-'));
        const tCls=cls.find(c=>c.startsWith('tag-'));
        if(cls.includes('intensity-tag'))
          runs.push({text:n.textContent.trim(),bold:true,intensityCls:iCls||'i-base'});
        else if(cls.includes('status-tag'))
          runs.push({text:n.textContent.trim(),bold:true,tagCls:tCls||''});
        else {
          const st=window.getComputedStyle(n);
          runs.push({text:n.textContent.trim(),
            computedColor:st.color||'',
            computedFont:st.fontFamily||''});
        }
      } else if(tag==='br'){
        runs.push({text:'\\n'});
      } else {
        // recurse into other inline elements
        runs.push(...styledRuns(n));
      }
    }
  }
  return runs.filter(r=>r.text);
}

function listItems(ul){
  return [...ul.querySelectorAll('li')].map(li=>{
    const liSt=window.getComputedStyle(li);
    return{runs:styledRuns(li),
           fsComputed:parseFloat(liSt.fontSize)||0,
           fwComputed:parseInt(liSt.fontWeight)||400};
  });
}

function tableData(tbl){
  const result={hasHeader:!!tbl.querySelector('thead'),rows:[]};
  for(const tr of tbl.querySelectorAll('tr')){
    const trH=Math.max(tr.getBoundingClientRect().height,24); // actual row height
    const cells=[];
    for(const cell of tr.querySelectorAll('th,td')){
      const cls=clsList(cell);
      const heatCls=cls.find(c=>c.startsWith('h-'))||'';
      const stEl=cell.querySelector('.status-tag');
      const stCls=stEl?clsList(stEl).find(c=>c.startsWith('tag-'))||'':'';
      cells.push({
        text:cell.textContent.trim(),
        runs:styledRuns(cell),
        isTh:cell.tagName==='TH',
        heatCls, tagCls:stCls,
        colW:parseFloat(cell.style&&cell.style.width||'0'),
        rowH:trH,
      });
    }
    if(cells.length)result.rows.push({cells,height:trH});
  }
  return result;
}

function extractEl(el,cr){
  const st=window.getComputedStyle(el);
  if(st.display==='none'||st.visibility==='hidden')return null;
  const cls=clsList(el);
  const tag=el.tagName.toLowerCase();
  if(el.id==='navBar'||cls.some(c=>c.startsWith('nav-')))return null;
  const p=pos(el,cr);
  if(p.w<1||p.h<1)return null;

  const type=compType(el);
  if(!type)return null;

  const isAbsPos=st.position==='absolute';
  const fsComputed=parseFloat(st.fontSize)||0;
  const fwComputed=parseInt(st.fontWeight)||400;
  const base={type,cls,tag,p,isAbsPos,fsComputed,fwComputed};

  switch(type){
    case 'col-card':{
      const bar=el.querySelector('.card-bar');
      const barColor=bar?window.getComputedStyle(bar).backgroundColor:'';
      const h3=el.querySelector('h3');
      const h3St=h3?window.getComputedStyle(h3):null;
      const contents=[];
      for(const child of el.children){
        if(child.tagName==='H3'||clsList(child).includes('card-bar'))continue;
        const childSt=window.getComputedStyle(child);
        if(child.tagName==='P')
          contents.push({kind:'p',runs:styledRuns(child),
                         fsComputed:parseFloat(childSt.fontSize)||0,
                         fwComputed:parseInt(childSt.fontWeight)||400});
        else if(child.tagName==='UL')
          contents.push({kind:'ul',items:listItems(child)});
      }
      return{...base,barColor,h3text:h3?h3.textContent.trim():'',
             h3colorInline:h3?h3.style.color||'':'',
             h3fsComputed:h3St?parseFloat(h3St.fontSize)||0:0,
             h3fwComputed:h3St?parseInt(h3St.fontWeight)||700:700,
             contents};
    }
    case 'emphasis-box':{
      const ps=[];
      for(const p2 of el.querySelectorAll('p')){
        const pSt=window.getComputedStyle(p2);
        ps.push({runs:styledRuns(p2),
                 fsComputed:parseFloat(pSt.fontSize)||0,
                 fwComputed:parseInt(pSt.fontWeight)||400});
      }
      return{...base,ps};
    }
    case 'metric-card':{
      const v=el.querySelector('.metric-value');
      const l=el.querySelector('.metric-label');
      return{...base,value:v?v.textContent.trim():'',label:l?l.textContent.trim():''};
    }
    case 'phase-block':{
      const pt=el.querySelector('.phase-title');
      const ps=el.querySelector('.phase-sub');
      const pd=el.querySelector('.phase-desc');
      return{...base,title:pt?pt.textContent.trim():'',
             sub:ps?ps.textContent.trim():'',desc:pd?pd.textContent.trim():''};
    }
    case 'arrow-right':
      return{...base,text:el.textContent.trim()||'▶'};
    case 'section-header':
      return{...base,text:el.textContent.trim()};
    case 'section-label':
      return{...base,text:el.textContent.trim()};
    case 'bullet-list':{
      const ul=tag==='ul'?el:el.querySelector('ul');
      return{...base,items:ul?listItems(ul):[]};
    }
    case 'table':
      return{...base,data:tableData(el)};
    case 'toc-item':{
      const num=el.querySelector('.toc-num');
      const txt=el.querySelector('.toc-text');
      return{...base,num:num?num.textContent.trim():'',
             text:txt?txt.textContent.trim():el.textContent.trim()};
    }
    case 'slide-header':{
      const ch=el.querySelector('.slide-chapter');
      const ti=el.querySelector('.slide-title');
      return{...base,chapter:ch?ch.textContent.trim():'',
             title:ti?ti.textContent.trim():''};
    }
    case 'slide-footer':{
      const pn=el.querySelector('.page-num');
      const spans=[...el.querySelectorAll('span')];
      return{...base,text:spans[0]?spans[0].textContent.trim():el.textContent.trim(),
             pageNum:pn?pn.textContent.trim():''};
    }
    case 'text':{
      // If this element contains recognizable nested component children, treat as panel
      const nestedTypes=[...el.children].map(ch=>compType(ch)).filter(Boolean);
      if(nestedTypes.length>0){
        const children=[];
        for(const child of el.children){const c=extractEl(child,cr);if(c)children.push(c);}
        if(children.length>0)return{...base,type:'panel',hasBg:false,children};
      }
      return{...base,runs:styledRuns(el),colorInline:el.style.color||''};
    }
    case 'panel':{
      const s2=window.getComputedStyle(el);
      const hasBg=s2.backgroundColor&&s2.backgroundColor!=='transparent'
                  &&!s2.backgroundColor.includes('rgba(0, 0, 0, 0)');
      const children=[];
      for(const child of el.children){
        const c=extractEl(child,cr);
        if(c)children.push(c);
      }
      return{...base,hasBg,children};
    }
    default:
      // Unknown: return placeholder info
      return{...base,type:'placeholder',label:type||cls[0]||tag};
  }
}

window._extractSlide=function(slideIdx){
  const allSlides=document.querySelectorAll('.slide');
  allSlides.forEach((s,i)=>{
    s.classList.remove('active');s.style.display='none';
  });
  const slide=allSlides[slideIdx];
  if(!slide)return null;
  slide.style.display='block';slide.classList.add('active');
  void slide.getBoundingClientRect();

  const cr=document.getElementById('slideContainer').getBoundingClientRect();
  const isCover=slide.classList.contains('slide-cover')||slide.dataset.type==='cover';

  if(isCover){
    const badge=slide.querySelector('.cover-badge');
    const title=slide.querySelector('.cover-title');
    const sub=slide.querySelector('.cover-sub');
    return{type:'cover',
           badge:badge?badge.textContent.trim():'',
           titleRuns:title?styledRuns(title):[],
           sub:sub?sub.textContent.trim():''};
  }

  const body=slide.querySelector('.slide-body');
  const header=slide.querySelector('.slide-header');
  const footer=slide.querySelector('.slide-footer');
  const comps=[];
  if(header){const h=extractEl(header,cr);if(h)comps.push(h);}
  if(body){for(const ch of body.children){const c=extractEl(ch,cr);if(c)comps.push(c);}}
  if(footer){const f=extractEl(footer,cr);if(f)comps.push(f);}
  return{type:slide.dataset.type||'content',comps};
};
})();
`;

/* ── PPT helpers ──────────────────────────────────────────────────────────── */
function addRect(s,x,y,w,h,fill,line={pt:0}){
  s.addShape('rect',{x:inOf(x),y:inOf(y),w:inOf(w),h:inOf(h),
    fill:{color:fill},line});
}
function addRRect(s,x,y,w,h,fill,{line={pt:0.5,color:C.border},radius=0.06}={}){
  s.addShape('roundRect',{x:inOf(x),y:inOf(y),w:inOf(w),h:inOf(h),
    fill:{color:fill},line,rectRadius:radius});
}

// Select font face based on CSS font-weight (300=light→YaHei Light, 600+=bold→YaHei regular)
function fontFaceForWeight(fw){ return (fw>=600)?F.sans:F.body; }

// Build pptxgenjs text-run array from styledRuns[]
// defFs: px (from computed style), defFont: base font for non-bold runs
function makeRuns(styledRuns, defColor=C.white, defFs=FS.body, defFont=F.body){
  const out=[];
  for(const r of styledRuns){
    if(!r.text) continue;
    if(r.text==='\n'){
      out.push({text:'', options:{breakLine:true}});
      continue;
    }
    let color=defColor;
    // Bold runs always use F.sans (YaHei regular displays bold well); non-bold use defFont
    const font=(r.bold||r.tagCls)?F.sans:defFont;
    if(r.intensityCls) color=I_COLOR[r.intensityCls]||C.goldL;
    else if(r.tagCls)  color=TAG_COLOR[r.tagCls]||C.white;
    else if(r.computedColor){
      const hex=parseComputedColor(r.computedColor);
      if(hex) color=hex;
    } else if(r.colorInline&&!r.colorInline.includes('var(')){
      const m=r.colorInline.match(/#([0-9a-fA-F]{6})/);
      if(m) color=m[1].toUpperCase();
    }
    out.push({text:r.text, options:{
      color, bold:r.bold||false,
      fontSize:ptOf(defFs), fontFace:font, breakLine:false}});
  }
  return out;
}

function addTB(s,x,y,w,h,text,opts={}){
  if(!text&&!opts.runs)return;
  const safeH=Math.max(h,12);
  const base={
    x:inOf(x),y:inOf(y),w:inOf(w),h:inOf(safeH),
    color:opts.color||C.white,
    fontSize:opts.fontSize||ptOf(14),
    bold:opts.bold||false,
    fontFace:opts.fontFace||F.body,
    align:opts.align||'left',
    valign:opts.valign||'top',
    wrap:true,
    margin:opts.margin||[2,4,2,4],
    charSpacing:opts.charSpacing||0,
    lineSpacingMultiple: opts.lineSpacing||1.4,  // line-height consistency
  };
  // Shape background support: combine text + shape into one PPT object
  if(opts.shape){
    base.shape=opts.shape;
    if(opts.rectRadius!=null)base.rectRadius=opts.rectRadius;
    base.fill=opts.fill||{color:C.navyMid};
    base.line=opts.line||{pt:0};
  }
  if(opts.runs) s.addText(opts.runs,base);
  else          s.addText(text,base);
}

/* ── Component renderers ─────────────────────────────────────────────────── */

function renderHeader(slide,c){
  const{p}=c;
  if(c.chapter) addTB(slide,p.x,p.y,p.w,18,c.chapter,
    {color:C.gold,fontSize:ptOf(FS.small),bold:true,fontFace:F.sans,charSpacing:4});
  if(c.title)   addTB(slide,p.x,p.y+20,p.w,38,c.title,
    {color:C.white,fontSize:ptOf(28),bold:true,fontFace:F.sans});
}

function renderFooter(slide,c){
  const{p}=c;
  addTB(slide,p.x,p.y,p.w-80,24,c.text,{color:C.muted,fontSize:ptOf(FS.small),fontFace:F.body});
  if(c.pageNum) addTB(slide,p.x+p.w-80,p.y,80,24,c.pageNum,
    {color:C.gold,fontSize:ptOf(FS.small+1),bold:true,fontFace:F.sans,align:'right'});
}

function renderColCard(slide,c){
  const{p}=c;
  const pad=20;
  // Build all runs: h3 title + body — one shape object = background + text combined
  const runs=[];
  if(c.h3text){
    const h3color=(c.h3colorInline&&!c.h3colorInline.includes('var('))?
      (()=>{const m=c.h3colorInline.match(/#([0-9a-fA-F]{6})/);return m?m[1].toUpperCase():C.goldL;})()
      :C.goldL;
    const h3Fs=c.h3fsComputed||FS.heading;
    runs.push({text:c.h3text,options:{color:h3color,bold:c.h3fwComputed>=600,fontSize:ptOf(h3Fs),fontFace:fontFaceForWeight(c.h3fwComputed||700),breakLine:true}});
  }
  for(const item of c.contents){
    if(item.kind==='p'){
      const fs=item.fsComputed||FS.body;
      runs.push(...makeRuns(item.runs,C.muted,fs,fontFaceForWeight(item.fwComputed||300)));
      runs.push({text:'',options:{breakLine:true}});
    } else if(item.kind==='ul'){
      const bOpt={color:C.gold};
      for(const li of item.items){
        const liRuns=makeRuns(li.runs,C.white,li.fsComputed||FS.body,fontFaceForWeight(li.fwComputed||300));
        if(!liRuns.length)continue;
        runs.push({text:liRuns[0].text,options:{...liRuns[0].options,bullet:bOpt}});
        for(let j=1;j<liRuns.length;j++)runs.push(liRuns[j]);
        runs.push({text:'',options:{breakLine:true}});
      }
    }
  }
  // One shape = background + text (no separate addRRect + addTB)
  if(runs.length) addTB(slide,p.x,p.y,p.w,p.h,null,{
    runs, valign:'top', margin:[pad,pad,pad,pad], lineSpacing:1.65,
    shape:'roundRect', rectRadius:0.04, fill:{color:C.navyMid}
  });
  else addRRect(slide,p.x,p.y,p.w,p.h,C.navyMid);
  // Gold top bar (thin accent line, separate object)
  addRect(slide,p.x,p.y,p.w,3,C.gold);
}

function renderEmphasisBox(slide,c){
  const{p}=c;
  // Merge all paragraphs into one shape (background + text combined)
  const runs=[];
  for(let i=0;i<c.ps.length;i++){
    const para=c.ps[i];
    const fs=para.fsComputed||FS.body;
    if(i>0)runs.push({text:'',options:{breakLine:true,fontSize:ptOf(fs)}});
    runs.push(...makeRuns(para.runs,C.white,fs,fontFaceForWeight(para.fwComputed||400)));
  }
  if(runs.length) addTB(slide,p.x,p.y,p.w,p.h,null,{
    runs, valign:'top', margin:[10,14,10,18], lineSpacing:1.6,
    shape:'roundRect', rectRadius:0.04, fill:{color:'111C2D'}
  });
  else addRRect(slide,p.x,p.y,p.w,p.h,'111C2D',{radius:0.04});
  // Left gold accent bar (separate thin shape)
  addRect(slide,p.x,p.y,3,p.h,C.gold);
}

function renderMetricCard(slide,c){
  const{p}=c;
  const runs=[];
  if(c.value) runs.push({text:c.value,options:{color:C.gold,bold:true,fontSize:ptOf(24),fontFace:F.sans,breakLine:true}});
  if(c.label) runs.push({text:c.label,options:{color:C.muted,fontSize:ptOf(FS.small),fontFace:F.body}});
  if(runs.length) addTB(slide,p.x,p.y,p.w,p.h,null,{
    runs, valign:'middle', align:'center', margin:[6,4,6,4],
    shape:'roundRect', rectRadius:0.04, fill:{color:C.navyMid}
  });
  else addRRect(slide,p.x,p.y,p.w,p.h,C.navyMid);
}

function renderPhaseBlock(slide,c){
  const{p}=c;
  const runs=[];
  if(c.title) runs.push({text:c.title,options:{color:C.gold,bold:true,fontSize:ptOf(FS.heading),fontFace:F.sans,breakLine:true}});
  if(c.sub)   runs.push({text:c.sub,  options:{color:C.white,fontSize:ptOf(FS.small),fontFace:F.sans,breakLine:true}});
  if(c.desc)  runs.push({text:c.desc, options:{color:C.muted,fontSize:ptOf(FS.xsmall),fontFace:F.body}});
  if(runs.length) addTB(slide,p.x,p.y,p.w,p.h,null,{
    runs, valign:'middle', align:'center', margin:[4,4,4,4], lineSpacing:1.5,
    shape:'roundRect', rectRadius:0.05, fill:{color:C.navyMid}
  });
  else addRRect(slide,p.x,p.y,p.w,p.h,C.navyMid,{radius:0.05});
}

function renderArrowRight(slide,c){
  const{p}=c;
  addTB(slide,p.x,p.y,p.w,p.h,'▶',
    {color:C.gold,fontSize:ptOf(18),align:'center',valign:'middle'});
}

function renderSectionHeader(slide,c){
  const{p}=c;
  addTB(slide,p.x,p.y,p.w,22,c.text,
    {color:C.gold,fontSize:ptOf(FS.heading-1),bold:true,fontFace:F.sans});
  addRect(slide,p.x,p.y+22,p.w,1,C.goldLine);
}

function renderSectionLabel(slide,c){
  const{p}=c;
  addTB(slide,p.x,p.y,p.w,20,c.text,
    {color:C.gold,fontSize:ptOf(FS.body),bold:true,fontFace:F.sans,charSpacing:3});
}

function renderBulletList(slide,c){
  const{p}=c;
  const fs=c.fsComputed||FS.body;
  const baseFont=fontFaceForWeight(c.fwComputed||300);
  const bulletOpt = { color:C.gold };
  const runs=[];
  for(const item of c.items){
    const itemFs=item.fsComputed||fs;
    const itemFont=fontFaceForWeight(item.fwComputed||c.fwComputed||300);
    const itemRuns=makeRuns(item.runs,C.white,itemFs,itemFont);
    if(!itemRuns.length) continue;
    // First run of each item: attach native bullet
    runs.push({
      text: itemRuns[0].text,
      options: { ...itemRuns[0].options, bullet:bulletOpt }
    });
    // Remaining runs of same item: no bullet (same paragraph)
    for(let j=1;j<itemRuns.length;j++) runs.push(itemRuns[j]);
    // New paragraph for next item
    runs.push({text:'', options:{breakLine:true}});
  }
  if(runs.length) addTB(slide,p.x,p.y,p.w,Math.max(p.h,30),null,
    {runs,fontSize:ptOf(fs),fontFace:baseFont,valign:'top',lineSpacing:1.65});
}

function renderTable(slide,c){
  const{p,data}=c;
  if(!data||!data.rows.length)return;
  const firstRow=data.rows[0];
  const nc=firstRow.cells.length;
  const totalW=firstRow.cells.reduce((s,cell)=>s+(cell.colW||0),0);
  const colW=firstRow.cells.map(cell=>
    cell.colW?inOf(cell.colW):inOf(p.w/nc));
  if(totalW===0)colW.fill(inOf(p.w/nc));

  // Use browser-measured row heights
  const rowH=data.rows.map(row=>inOf(Math.max(row.height||28,22)));

  const rows=data.rows.map((row,ri)=>row.cells.map(cell=>{
    const isTh=cell.isTh||(data.hasHeader&&ri===0);
    const bg=isTh?C.navyMid:(HEAT_BG[cell.heatCls]||C.navy);
    let fg=isTh?C.gold:(HEAT_FG[cell.heatCls]||C.white);
    if(cell.tagCls)fg=TAG_COLOR[cell.tagCls]||C.white;
    const bold=isTh||HEAT_BOLD.has(cell.heatCls);
    const fs=isTh?FS.small:FS.body;
    const ff=isTh?F.sans:F.body;

    let textRuns;
    if(cell.tagCls){
      textRuns=[{text:cell.text,options:{color:fg,bold:true,fontSize:ptOf(FS.small),fontFace:F.sans}}];
    } else if(cell.runs&&cell.runs.length){
      textRuns=makeRuns(cell.runs,fg,fs,ff);
    } else {
      textRuns=[{text:cell.text,options:{color:fg,fontSize:ptOf(fs),fontFace:ff,bold}}];
    }

    return{text:textRuns,options:{
      fill:{color:bg},
      border:[{pt:0},{pt:0},{pt:0.5,color:'1A2030'},{pt:0}],
      align:'left',valign:'middle',margin:[4,8,4,8],fontFace:ff}};
  }));

  try{
    slide.addTable(rows,{
      x:inOf(p.x),y:inOf(p.y),w:inOf(p.w),
      colW,rowH,border:{pt:0}});
  }catch(e){
    console.warn('  Table warn:',e.message.slice(0,80));
  }
}

function renderTocItem(slide,c){
  const{p}=c;
  addRRect(slide,p.x,p.y,p.w,p.h,C.navyMid,{radius:0.04});
  const runs=[];
  if(c.num)  runs.push({text:c.num+'   ',options:{color:C.gold,bold:true,fontSize:ptOf(14),fontFace:F.serif}});
  if(c.text) runs.push({text:c.text,options:{color:C.white,fontSize:ptOf(14),fontFace:F.sans}});
  if(runs.length) addTB(slide,p.x+14,p.y+4,p.w-28,p.h-8,null,{runs});
}

function renderText(slide,c){
  const{p}=c;
  if(!c.runs||!c.runs.length)return;
  const fs=c.fsComputed||FS.body;
  const font=fontFaceForWeight(c.fwComputed||400);
  let color=C.white;
  if(c.colorInline&&!c.colorInline.includes('var(')){
    const m=c.colorInline.match(/#([0-9a-fA-F]{6})/);
    if(m)color=m[1].toUpperCase();
    else if(c.colorInline.includes('muted'))color=C.muted;
  }
  const runs=makeRuns(c.runs,color,fs,font);
  if(runs.length) addTB(slide,p.x,p.y,p.w||600,Math.max(p.h,18),null,
    {runs,fontSize:ptOf(fs),valign:'top',margin:[2,0,2,0]});
}

const PANEL_GOLD_BORDER={pt:0.75,color:C.gold,transparency:88};
const PANEL_MERGE_TYPES=new Set(['section-header','section-label','bullet-list','text']);

function buildPanelRuns(children){
  const runs=[];
  for(let i=0;i<children.length;i++){
    const ch=children[i];
    if(i>0)runs.push({text:'',options:{breakLine:true}});
    switch(ch.type){
      case 'section-header':
      case 'section-label':
        runs.push({text:ch.text||'',options:{color:C.gold,bold:true,fontSize:ptOf(ch.fsComputed||FS.heading-1),fontFace:F.sans,breakLine:true}});
        break;
      case 'bullet-list':{
        const fs=ch.fsComputed||FS.body;
        const bOpt={color:C.gold};
        for(const item of(ch.items||[])){
          const liRuns=makeRuns(item.runs,C.white,item.fsComputed||fs,fontFaceForWeight(item.fwComputed||ch.fwComputed||300));
          if(!liRuns.length)continue;
          runs.push({text:liRuns[0].text,options:{...liRuns[0].options,bullet:bOpt}});
          for(let j=1;j<liRuns.length;j++)runs.push(liRuns[j]);
          runs.push({text:'',options:{breakLine:true}});
        }
        break;
      }
      case 'text':{
        if(!ch.runs||!ch.runs.length)break;
        runs.push(...makeRuns(ch.runs,C.white,ch.fsComputed||FS.body,fontFaceForWeight(ch.fwComputed||400)));
        break;
      }
      default: return null; // unmergeable child
    }
  }
  return runs;
}

function renderTocList(slide,p,items){
  const runs=[];
  for(let i=0;i<items.length;i++){
    const c=items[i];
    if(i>0)runs.push({text:'',options:{breakLine:true}});
    if(c.num)runs.push({text:c.num+'  ',options:{color:C.gold,bold:true,fontSize:ptOf(FS.body),fontFace:F.sans}});
    if(c.text)runs.push({text:c.text,options:{color:C.white,fontSize:ptOf(FS.body),fontFace:F.body}});
  }
  if(runs.length)addTB(slide,p.x+16,p.y+14,p.w-32,p.h-28,null,{runs,valign:'top',lineSpacing:1.55});
}

function renderPanel(slide,c){
  const{p}=c;
  const children=c.children||[];

  // Special: all toc-items → one merged text box
  if(children.length>0&&children.every(ch=>ch.type==='toc-item')){
    if(c.hasBg)addRRect(slide,p.x,p.y,p.w,p.h,C.navyMid,{line:PANEL_GOLD_BORDER});
    renderTocList(slide,p,children);
    return;
  }

  // Merge: background + all flow text-like children into ONE shape
  if(c.hasBg&&children.length>0&&children.every(ch=>!ch.isAbsPos&&PANEL_MERGE_TYPES.has(ch.type))){
    const merged=buildPanelRuns(children);
    if(merged&&merged.length>0){
      addTB(slide,p.x,p.y,p.w,p.h,null,{
        runs:merged,valign:'top',margin:[14,14,14,14],lineSpacing:1.65,
        shape:'roundRect',rectRadius:0.04,fill:{color:C.navyMid},line:PANEL_GOLD_BORDER
      });
      return;
    }
  }

  // Fallback: background + children separately (e.g. abs-pos mixed layout)
  if(c.hasBg)addRRect(slide,p.x,p.y,p.w,p.h,C.navyMid,{line:PANEL_GOLD_BORDER});
  for(const child of children)renderComponent(slide,child);
}

function renderPlaceholder(slide,c){
  const{p}=c;
  // Grey outlined box + label
  slide.addShape('rect',{
    x:inOf(p.x),y:inOf(p.y),w:inOf(p.w),h:inOf(p.h),
    fill:{color:'1A2030'},
    line:{pt:1,color:'555555',dashType:'dash'}});
  slide.addText('⚠ '+(c.label||'unknown'),{
    x:inOf(p.x+4),y:inOf(p.y+4),w:inOf(p.w-8),h:inOf(Math.max(p.h-8,16)),
    color:'888888',fontSize:ptOf(10),wrap:true});
}

function renderComponent(slide,c){
  if(!c||!c.type)return;
  switch(c.type){
    case 'slide-header':   renderHeader(slide,c);      break;
    case 'slide-footer':   renderFooter(slide,c);      break;
    case 'col-card':       renderColCard(slide,c);     break;
    case 'emphasis-box':   renderEmphasisBox(slide,c); break;
    case 'metric-card':    renderMetricCard(slide,c);  break;
    case 'phase-block':    renderPhaseBlock(slide,c);  break;
    case 'arrow-right':    renderArrowRight(slide,c);  break;
    case 'section-header': renderSectionHeader(slide,c);break;
    case 'section-label':  renderSectionLabel(slide,c); break;
    case 'bullet-list':    renderBulletList(slide,c);  break;
    case 'table':          renderTable(slide,c);       break;
    case 'toc-item':       renderTocItem(slide,c);     break;
    case 'text':           renderText(slide,c);        break;
    case 'panel':          renderPanel(slide,c);       break;
    case 'placeholder':    renderPlaceholder(slide,c); break;
  }
}

function buildSlide(prs,data){
  const slide=prs.addSlide();
  slide.background={color:C.navy};

  if(data.type==='cover'){
    const cx=190,cy=270,cw=900;
    if(data.badge){
      addRRect(slide,(1280-320)/2,210,320,34,C.navy,{line:{pt:0.75,color:C.gold},radius:0.02});
      addTB(slide,(1280-320)/2,210,320,34,data.badge,
        {color:C.gold,fontSize:ptOf(13),align:'center',valign:'middle'});
    }
    if(data.titleRuns&&data.titleRuns.length){
      const runs=[];
      for(const r of data.titleRuns){
        if(r.text==='\n'){runs.push({text:'',options:{breakLine:true}});continue;}
        // Use computedColor to correctly detect CSS-class gold on span
        let color=C.white;
        if(r.computedColor){const hex=parseComputedColor(r.computedColor);if(hex)color=hex;}
        runs.push({text:r.text,options:{
          color,bold:true,fontSize:ptOf(44),fontFace:F.serif,breakLine:false,
          align:'center'}});
      }
      addTB(slide,cx,cy,cw,140,null,
        {runs,fontFace:F.serif,align:'center',valign:'middle',lineSpacing:1.35});
    }
    addRect(slide,600,415,80,2,C.gold);
    if(data.sub) addTB(slide,cx,440,cw,40,data.sub,
      {color:C.muted,fontSize:ptOf(22),align:'center'});
    return;
  }

  for(const comp of (data.comps||[])) renderComponent(slide,comp);
}

/* ── Main ──────────────────────────────────────────────────────────────────── */
async function main(){
  const htmlPath=path.resolve(process.argv[2]);
  const outPath =path.resolve(process.argv[3]);
  if(!fs.existsSync(htmlPath)){console.error('Not found:',htmlPath);process.exit(1);}

  const browser=await puppeteer.launch({
    executablePath:CHROME,headless:'new',
    args:['--no-sandbox','--disable-setuid-sandbox','--allow-file-access-from-files']});
  try{
    const page=await browser.newPage();
    await page.setViewport({width:1280,height:720});
    await page.goto(`file://${htmlPath}`,{waitUntil:'networkidle0',timeout:30000});
    await new Promise(r=>setTimeout(r,1200));
    await page.evaluate(EXTRACTOR);

    const total=await page.evaluate(()=>document.querySelectorAll('.slide').length);
    console.log(`Slides: ${total}`);

    const prs=new pptxgen();
    prs.layout='LAYOUT_WIDE';

    for(let i=0;i<total;i++){
      process.stdout.write(`  Slide ${i+1}/${total}...\r`);
      const data=await page.evaluate(idx=>window._extractSlide(idx),i);
      if(data)buildSlide(prs,data);
    }
    console.log('');

    await prs.writeFile({fileName:outPath});
    const sz=(fs.statSync(outPath).size/1024).toFixed(0);
    console.log(`\n---完成---\n输出: ${outPath}\n大小: ${sz} KB\n页数: ${total}`);
  }finally{
    await browser.close();
  }
}

main().catch(e=>{console.error(e.stack||e);process.exit(1);});
