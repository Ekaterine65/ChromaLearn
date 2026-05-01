/**
 * Этот файл содержит:
 *   - Управление палитрой (palette bar, selectPaletteSlot, applyColorToSlot)
 *   - Обновление макета сайта Aelius (updatePreviewSite)
 *   - Вспомогательные функции цвета (hsl/rgb/hex)
 *   - Цветовой круг (Canvas API) — колесо + яркость + гармония
 *   - Редактируемые поля HEX / RGB
 *   - Симулятор зрения (SVG-фильтры, уровень 3)
 *   - Профиль: календарь активности GitHub-style
 *   - Профиль: пагинация выполненных заданий
 *
 * Переменные, задаваемые шаблонами через window.*:
 *   window.GAME_LEVEL   — номер уровня (1, 2, 3)
 *   window.SHOW_WCAG    — bool, показывать WCAG-блок
 *   window.SHOW_VISION  — bool, показывать симулятор зрения
 *   window.ALL_TASKS    — массив выполненных заданий (profile.html)
 */

'use strict';

/* Управление палитрой */

const ROLES       = ['Фон', 'Поверхность', 'Акцент', 'Текст', 'Доп.'];
const ROLES_SHORT = ['Фон', 'Поверхн.',    'Акцент', 'Текст', 'Доп.'];

const DEFAULT_PALETTE = ['#e4eff5', '#c5dde8', '#3d7db8', '#1b2d3e', '#7a8fa3'];

let palette        = [...DEFAULT_PALETTE];
let activeSlotIndex = 0;
let currentVisionMode = 'normal';
let visionPreviewPalettes = null;
let visionPreviewRequestId = 0;

function getPaletteStorageKey() {
  if (!window.GAME_LEVEL || !window.TASK_ID) return null;
  return `chromalearn.palette.level.${window.GAME_LEVEL}.task.${window.TASK_ID}`;
}

function isValidPaletteColor(color) {
  return color === null || /^#[0-9a-fA-F]{6}$/.test(color);
}

function savePaletteState() {
  const key = getPaletteStorageKey();
  if (!key) return;
  try {
    localStorage.setItem(key, JSON.stringify(palette));
  } catch (error) {
    console.warn('Palette state was not saved', error);
  }
}

function restorePaletteState() {
  const key = getPaletteStorageKey();
  if (!key) return;
  try {
    const stored = JSON.parse(localStorage.getItem(key) || 'null');
    if (!Array.isArray(stored)) return;
    const nextPalette = DEFAULT_PALETTE.map((fallback, index) => {
      const color = stored[index];
      return color && isValidPaletteColor(color) ? color : fallback;
    });
    palette = nextPalette;
    refreshPaletteSlots();
  } catch (error) {
    console.warn('Palette state was not restored', error);
  }
}

function refreshPaletteSlots() {
  for (let index = 0; index < 5; index++) {
    const swatch = document.getElementById('ps' + index + 's');
    if (!swatch) continue;
    const color = palette[index];
    swatch.classList.toggle('filled', Boolean(color));
    swatch.style.background = color || '';
    swatch.innerHTML = color ? '<div class="del-overlay">x</div>' : '+';
  }
}

function selectPaletteSlot(i) {
  activeSlotIndex = i;
  for (let j = 0; j < 5; j++) {
    const ps  = document.getElementById('ps' + j);
    const pss = document.getElementById('ps' + j + 's');
    if (ps)  ps.classList.toggle('selected',  j === i);
    if (pss) pss.classList.toggle('selected', j === i);
  }
  const col = palette[i] || '#888888';
  const role = document.getElementById('arbRole');
  const hex  = document.getElementById('arbHex');
  const sw   = document.getElementById('arbSwatch');
  if (role) role.textContent    = ROLES[i];
  if (hex)  hex.textContent     = col.toUpperCase();
  if (sw)   sw.style.background = col;
  const label = document.getElementById('applyRoleLabel');
  if (label) label.textContent = ROLES[i];
  if (palette[i]) {
    const hsl = hexToHsl(palette[i]);
    currentHue = hsl.h; currentSat = hsl.s; currentLight = hsl.l;
    updateColorUI();
  }
}

function applyColorToSlot() {
  const hex = hslToHex(currentHue, currentSat, currentLight);
  palette[activeSlotIndex] = hex;
  savePaletteState();
  refreshPaletteSlots();
  const sw = document.getElementById('ps' + activeSlotIndex + 's');
  if (sw) {
    sw.style.background = hex;
    sw.textContent = '';
    sw.classList.add('filled');
    sw.innerHTML = '<div class="del-overlay">✕</div>';
  }
  const arbSwatch = document.getElementById('arbSwatch');
  const arbHex    = document.getElementById('arbHex');
  if (arbSwatch) arbSwatch.style.background = hex;
  if (arbHex)    arbHex.textContent = hex.toUpperCase();
  if (window.SHOW_VISION && currentVisionMode !== 'normal') {
    refreshVisionPreview();
    return;
  }
  updatePreviewSite();
}


/* Обновление макета сайта */

function updatePreviewSite() {
  const previewPalette = getPreviewPalette();
  const bg   = previewPalette[0] || '#eff2f5';
  const surf = previewPalette[1] || '#ddeaf2';
  const acc  = previewPalette[2] || '#3d7db8';
  const txtc = previewPalette[3] || '#1b2d3e';
  const extra = previewPalette[4] || blendHex(acc, bg, 0.35);

  const lBg   = getLuminance(bg);
  const lAcc  = getLuminance(acc);
  const lExtra = getLuminance(extra);
  const onAcc = lAcc > 0.35 ? '#1b2d3e' : '#ffffff';
  const onExtra = lExtra > 0.35 ? '#1b2d3e' : '#ffffff';
  const onBg  = txtc || (lBg > 0.45 ? '#1b2d3e' : '#f0f4f7');
  const mutedTxt = extra;
  const borderColor = extra;

  setPreviewSiteVars({
    '--site-bg': bg,
    '--site-surface': surf,
    '--site-accent': acc,
    '--site-extra': extra,
    '--site-text': onBg,
    '--site-muted': mutedTxt,
    '--site-border': borderColor,
    '--site-on-accent': onAcc,
    '--site-on-extra': onExtra
  });

  setStyleById('siteNav',     'background', bg + 'ee'); setStyleById('siteNav',    'color', onBg);
  setStyleById('siteNavCta',  'background', acc);       setStyleById('siteNavCta', 'color', onAcc);
  const heroEl = document.getElementById('siteHero');
  const heroBackground = heroEl && heroEl.classList.contains('site-saas-hero') ? bg : surf;
  setStyleById('siteHero',    'background', heroBackground);      setStyleById('siteHero',   'color', onBg);
  setStyleById('siteHeroTag', 'background', acc + '28'); setStyleById('siteHeroTag','color', acc);
  setStyleById('siteHeroBtnPrimary','background', acc);  setStyleById('siteHeroBtnPrimary','color', onAcc);
  setStyleById('siteHeroBtnSecondary','color', acc);       setStyleById('siteHeroBtnSecondary','borderColor', acc + '88');
  setStyleById('siteFeatures','background', bg);   setStyleById('siteFeatures','color', onBg);

  [['siteFeature1', surf], ['siteFeature2', acc + '1a'], ['siteFeature3', surf]].forEach(([id, bg2], idx) => {
    setStyleById(id, 'background',  bg2);
    setStyleById(id, 'borderColor', idx === 1 ? acc + '44' : 'transparent');
    setStyleById(id, 'color', onBg);
  });

  setStyleById('siteTestimonials','background', surf); setStyleById('siteTestimonials','color', onBg);
  ['siteTestimonialCard1','siteTestimonialCard2'].forEach(id => { setStyleById(id,'background', bg); setStyleById(id,'borderColor', acc + '44'); });
  setStyleById('siteTestimonialAuthor1','color', acc); setStyleById('siteTestimonialAuthor2','color', acc);

  setStyleById('siteCtaBanner','background', acc);  setStyleById('siteCtaBanner','color', onAcc);
  setStyleById('siteCtaButton','background', 'rgba(255,255,255,0.18)');
  setStyleById('siteCtaButton','color', onAcc);
  setStyleById('siteCtaButton','border', '2px solid ' + onAcc + '44');

  setStyleById('siteFooter','background', bg);
  setStyleById('siteFooter','borderColor', acc + '33');
  setStyleById('siteFooter','color', mutedTxt);
  setStyleById('siteFooterLogo','color', acc);
  setStyleById('siteNavLogo','color', acc);

  setStyleById('siteNavLinks','color', onBg);
  setStyleById('siteHeroTitle','color', onBg);
  setStyleById('siteHeroSub','color', mutedTxt);
  setStyleById('siteFeatureText1','color', mutedTxt);
  setStyleById('siteFeatureText2','color', mutedTxt);
  setStyleById('siteFeatureText3','color', mutedTxt);
  setStyleById('siteTestimonialText1','color', mutedTxt);
  setStyleById('siteTestimonialText2','color', mutedTxt);
  setStyleById('siteCtaText','color', onAcc);
  setStyleById('siteFooterLinks','color', onBg);

  updateWcagPanel();
}

function setPreviewSiteVars(vars) {
  const root = document.getElementById('panelCenter');
  if (!root) return;
  Object.entries(vars).forEach(([name, value]) => root.style.setProperty(name, value));
  root.style.background = vars['--site-bg'];
}

function setStyleById(id, prop, val) {
  const el = document.getElementById(id);
  if (el) el.style[prop] = val;
}

function getPreviewPalette() {
  if (currentVisionMode !== 'normal' && visionPreviewPalettes && visionPreviewPalettes[currentVisionMode]) {
    return palette.map((color, index) => visionPreviewPalettes[currentVisionMode][index] || color);
  }
  return palette;
}


/* Вспомогательные функции цвета (hsl/rgb/hex) */

function getLuminance(hex) {
  const [r, g, b] = hexToRgb(hex).map(v => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function hexToRgb(hex) {
  hex = hex.replace('#','');
  if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
  return [parseInt(hex.slice(0,2),16), parseInt(hex.slice(2,4),16), parseInt(hex.slice(4,6),16)];
}
function hexToHsl(hex) {
  let [r, g, b] = hexToRgb(hex); r/=255; g/=255; b/=255;
  const max = Math.max(r,g,b), min = Math.min(r,g,b);
  let h=0, s=0, l=(max+min)/2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d/(2-max-min) : d/(max+min);
    switch(max){
      case r: h=((g-b)/d+(g<b?6:0))/6; break;
      case g: h=((b-r)/d+2)/6; break;
      case b: h=((r-g)/d+4)/6; break;
    }
  }
  return { h: Math.round(h*360), s: Math.round(s*100), l: Math.round(l*100) };
}
function hslToRgb(h, s, l) {
  h/=360; s/=100; l/=100;
  const q = l<0.5 ? l*(1+s) : l+s-l*s, p = 2*l-q;
  const f = (p,q,t) => {
    if(t<0)t+=1; if(t>1)t-=1;
    if(t<1/6)return p+(q-p)*6*t;
    if(t<1/2)return q;
    if(t<2/3)return p+(q-p)*(2/3-t)*6;
    return p;
  };
  return [Math.round(f(p,q,h+1/3)*255), Math.round(f(p,q,h)*255), Math.round(f(p,q,h-1/3)*255)];
}
function hslToHex(h, s, l) {
  const [r,g,b] = hslToRgb(h,s,l);
  return '#' + [r,g,b].map(v => v.toString(16).padStart(2,'0')).join('').toUpperCase();
}
function blendHex(c1, c2, t) {
  const [r1,g1,b1] = hexToRgb(c1), [r2,g2,b2] = hexToRgb(c2);
  return '#' + [r1+Math.round((r2-r1)*t), g1+Math.round((g2-g1)*t), b1+Math.round((b2-b1)*t)]
    .map(v => Math.max(0,Math.min(255,v)).toString(16).padStart(2,'0')).join('');
}


/* Цветовой круг (Canvas API) колесо + яркость + гармония */

const WS = 200, R = 100, CX = 100, CY = 100;
let currentHue = 200, currentSat = 38, currentLight = 80;
let harmonyMode  = 'monochromatic';

let _canvas = null, _ctx = null, _hCanvas = null, _hCtx = null;
function getWheelCanvases() {
  if (!_canvas) {
    _canvas  = document.getElementById('colorWheel');
    _hCanvas = document.getElementById('harmonyCanvas');
    if (_canvas)  _ctx  = _canvas.getContext('2d');
    if (_hCanvas) _hCtx = _hCanvas.getContext('2d');
  }
  return { canvas: _canvas, ctx: _ctx, hCanvas: _hCanvas, hCtx: _hCtx };
}

function drawColorWheel() {
  const { canvas, ctx } = getWheelCanvases();
  if (!canvas || !ctx) return;
  const id = ctx.createImageData(WS, WS);
  for (let y = 0; y < WS; y++) {
    for (let x = 0; x < WS; x++) {
      const dx = x-CX, dy = y-CY, d = Math.sqrt(dx*dx+dy*dy);
      if (d > R) { const i=(y*WS+x)*4; id.data[i+3]=0; continue; }
      const angle = (Math.atan2(dy,dx)*180/Math.PI+360)%360;
      const sat = d/R;
      const h6=angle/60, hi=Math.floor(h6)%6, f=h6-Math.floor(h6);
      const p=1-sat, q=1-f*sat, tv=1-sat*(1-f);
      let rr,gg,bb;
      switch(hi){case 0:rr=1;gg=tv;bb=p;break;case 1:rr=q;gg=1;bb=p;break;case 2:rr=p;gg=1;bb=tv;break;case 3:rr=p;gg=q;bb=1;break;case 4:rr=tv;gg=p;bb=1;break;default:rr=1;gg=p;bb=q;}
      const i=(y*WS+x)*4;
      id.data[i]=Math.round(rr*255); id.data[i+1]=Math.round(gg*255); id.data[i+2]=Math.round(bb*255); id.data[i+3]=255;
    }
  }
  ctx.putImageData(id, 0, 0);
  const lFrac = currentLight/100;
  if (lFrac < 0.5) {
    const a = (0.5-lFrac)*2*0.88;
    ctx.fillStyle = `rgba(0,0,0,${a.toFixed(2)})`;
  } else {
    const a = (lFrac-0.5)*2*0.9;
    ctx.fillStyle = `rgba(255,255,255,${a.toFixed(2)})`;
  }
  ctx.beginPath(); ctx.arc(CX,CY,R,0,Math.PI*2); ctx.fill();
}

function getHarmonyAngles(h) {
  switch(harmonyMode) {
    case 'analogous':     return [h-30, h, h+30];
    case 'complementary': return [h, (h+180)%360];
    case 'triadic':       return [h, (h+120)%360, (h+240)%360];
    case 'monochromatic': return [h, h, h];
    default:              return [h];
  }
}

function drawHarmonyOverlay() {
  const { hCanvas, hCtx } = getWheelCanvases();
  if (!hCanvas || !hCtx) return;
  hCtx.clearRect(0, 0, WS, WS);

  const angles = getHarmonyAngles(currentHue);
  const useDark = currentLight > 50;
  const lineColor = useDark ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.6)';
  const ringColor = useDark ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.9)';

  hCtx.save();
  const pts = angles.map(a => {
    const rad = a * Math.PI / 180, r = currentSat / 100 * R;
    return { x: CX + Math.cos(rad) * r, y: CY + Math.sin(rad) * r };
  });

  if (pts.length > 1) {
    hCtx.strokeStyle = lineColor; hCtx.lineWidth = 1.5; hCtx.setLineDash([3,3]);
    hCtx.beginPath(); hCtx.moveTo(pts[0].x, pts[0].y);
    pts.slice(1).forEach(p => hCtx.lineTo(p.x, p.y));
    if (harmonyMode === 'triadic') hCtx.closePath();
    hCtx.stroke();
  }

  hCtx.setLineDash([]);
  angles.forEach(a => {
    const norm = (a % 360 + 360) % 360;
    const rad = norm * Math.PI / 180, r = currentSat / 100 * R;
    const x = CX + Math.cos(rad) * r, y = CY + Math.sin(rad) * r;
    hCtx.beginPath(); hCtx.arc(x, y, 5, 0, Math.PI * 2);
    hCtx.fillStyle = hslToHex(norm, currentSat, currentLight); hCtx.fill();
    hCtx.strokeStyle = ringColor; hCtx.lineWidth = 1.5; hCtx.stroke();
  });

  const cr = currentHue * Math.PI / 180, cr2 = currentSat / 100 * R;
  const cx2 = CX + Math.cos(cr) * cr2, cy2 = CY + Math.sin(cr) * cr2;
  hCtx.beginPath(); hCtx.arc(cx2, cy2, 7, 0, Math.PI * 2);
  hCtx.fillStyle = hslToHex(currentHue, currentSat, currentLight); hCtx.fill();
  hCtx.strokeStyle = ringColor; hCtx.lineWidth = 2; hCtx.stroke();
  hCtx.restore();
}

function updateColorUI() {
  const { canvas } = getWheelCanvases();
  if (!canvas) return;
  const hex = hslToHex(currentHue, currentSat, currentLight);
  const [rr,gg,bb] = hslToRgb(currentHue, currentSat, currentLight);

  const fHex=document.getElementById('fHex'), fR=document.getElementById('fR');
  const fG=document.getElementById('fG'),     fB=document.getElementById('fB');
  if (fHex && document.activeElement!==fHex) fHex.value=hex;
  if (fR   && document.activeElement!==fR)   fR.value=rr;
  if (fG   && document.activeElement!==fG)   fG.value=gg;
  if (fB   && document.activeElement!==fB)   fB.value=bb;

  const slL=document.getElementById('slL');
  if (slL) {
    slL.value=currentLight;
    const dk=hslToHex(currentHue,currentSat,0), md=hslToHex(currentHue,currentSat,50), lt=hslToHex(currentHue,currentSat,100);
    slL.style.setProperty('--brightness-gradient', `linear-gradient(to top,${dk},${md},${lt})`);
  }
  const bv=document.getElementById('brightnessVal');
  if (bv) { bv.textContent=Math.round(currentLight)+'%'; }

  const arbSw=document.getElementById('arbSwatch'), arbHx=document.getElementById('arbHex');
  if (arbSw) arbSw.style.background=hex;
  if (arbHx) arbHx.textContent=hex;

  drawColorWheel();
  drawHarmonyOverlay();
}

document.addEventListener('DOMContentLoaded', () => {
  restorePaletteState();
  selectPaletteSlot(activeSlotIndex);
  updatePreviewSite();

  const { canvas } = getWheelCanvases();
  if (canvas) {
    canvas.addEventListener('click', e => {
      const rect=canvas.getBoundingClientRect();
      const x=(e.clientX-rect.left)*WS/rect.width, y=(e.clientY-rect.top)*WS/rect.height;
      const dx=x-CX, dy=y-CY, d=Math.sqrt(dx*dx+dy*dy);
      if (d>R) return;
      currentHue=(Math.atan2(dy,dx)*180/Math.PI+360)%360;
      currentSat=Math.min(d/R*100,100);
      updateColorUI();
    });
  }
});

function setHarmonyMode(btn, type) {
  document.querySelectorAll('.harmony-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  harmonyMode=type; drawHarmonyOverlay();
}

function applyHexInputValue(val) {
  if (/^#[0-9a-fA-F]{6}$/.test(val)) {
    const hsl=hexToHsl(val); currentHue=hsl.h; currentSat=hsl.s; currentLight=hsl.l;
    updateColorUI();
  }
}
function normalizeHexInput() {
  const el=document.getElementById('fHex');
  if (el && !/^#[0-9a-fA-F]{6}$/.test(el.value)) el.value=hslToHex(currentHue,currentSat,currentLight);
}
function applyRgbInputValues() {
  const r=+document.getElementById('fR').value;
  const g=+document.getElementById('fG').value;
  const b=+document.getElementById('fB').value;
  if ([r,g,b].every(v=>v>=0&&v<=255)) {
    const hex='#'+[r,g,b].map(v=>Math.round(v).toString(16).padStart(2,'0')).join('').toUpperCase();
    const hsl=hexToHsl(hex); currentHue=hsl.h; currentSat=hsl.s; currentLight=hsl.l;
    updateColorUI();
  }
}


/* Симулятор зрения */

const VISION_NOTES = {
  normal:       'Нормальное цветовосприятие.',
  protanopia:   'Протанопия: отсутствует восприятие красного. ~1% мужчин.',
  deuteranopia: 'Дейтеранопия: нарушено восприятие зелёного. Самый распространённый тип.',
  tritanopia:   'Тританопия: нарушено восприятие синего. Встречается редко.'
};
async function setVisionMode(btn, type) {
  document.querySelectorAll('.vision-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentVisionMode = type;
  const note=document.getElementById('visionNote');
  if (note) note.textContent=VISION_NOTES[type]||'';

  if (type === 'normal') {
    updatePreviewSite();
    return;
  }

  await refreshVisionPreview();
}

async function refreshVisionPreview() {
  const requestId = ++visionPreviewRequestId;
  try {
    const response = await fetch(window.location.pathname, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'vision_preview',
        palette: palette.filter(Boolean)
      })
    });

    if (!response.ok) throw new Error('Vision preview request failed');

    const result = await response.json();
    if (requestId !== visionPreviewRequestId) return;
    visionPreviewPalettes = result.palettes || null;
    updatePreviewSite();
  } catch (error) {
    console.error(error);
    visionPreviewPalettes = null;
    updatePreviewSite();
  }
}


/* Профиль: календарь активности */

const PG_SIZE = 5;
let pgCurrent = 1;

function renderTaskPage(page) {
  pgCurrent = page;
  const tasks      = window.ALL_TASKS || [];
  const total      = tasks.length;
  const totalPages = Math.ceil(total / PG_SIZE);
  const start      = (page - 1) * PG_SIZE;
  const items      = tasks.slice(start, start + PG_SIZE);

  const list   = document.getElementById('tasksList');
  const pgWrap = document.getElementById('tasksPagination');
  if (!list) return;

  list.innerHTML = items.map(t => `
    <div class="task-row">
      <div class="task-row-icon">${t.icon}</div>
      <div class="task-row-info">
        <div class="task-row-name">${t.name}</div>
        <div class="task-row-meta d-flex align-items-center flex-wrap gap-2">
          <span class="level-pill" style="padding:3px 9px;font-size:10px;${t.lv_style}">Ур. ${t.lv}</span>
          <span></span>
          <span>· ${t.ago}</span>
        </div>
      </div>
      <div class="task-row-attempts"><span>${t.attempts}</span><span>попыток</span></div>
      <div class="task-row-score">
        <div class="score-ring ${t.sc}">${t.score}</div>
        <div style="font-size:10px;color:var(--muted);margin-top:2px">балл</div>
      </div>
      <a href="${t.retry_url || '/levels'}" class="retry-btn text-decoration-none">Повторить</a>
    </div>
  `).join('');

  if (!pgWrap) return;
  const from = start + 1, to = Math.min(start + PG_SIZE, total);
  let btns = `<button class="pg-btn pg-arrow" onclick="renderTaskPage(${page-1})" ${page===1?'disabled':''}>‹</button>`;
  for (let p = 1; p <= totalPages; p++) {
    btns += `<button class="pg-btn ${p===page?'active':''}" onclick="renderTaskPage(${p})">${p}</button>`;
  }
  btns += `<button class="pg-btn pg-arrow" onclick="renderTaskPage(${page+1})" ${page===totalPages?'disabled':''}>›</button>`;
  pgWrap.innerHTML = `
    <span class="pagination-info">Показано ${from}–${to} из ${total}</span>
    <div class="pagination-btns d-flex gap-1">${btns}</div>
  `;
}


/* Профиль: пагинация выполненных заданий */

let calYear = (window.ACTIVITY_YEARS && window.ACTIVITY_YEARS.length)
  ? window.ACTIVITY_YEARS[0]
  : new Date().getFullYear();

function renderActivityCalendar(year) {
  const allData  = window.ACTIVITY_DATA || {};
  const yearTotals = window.ACTIVITY_TOTALS || {};
  const data = {};
  Object.keys(allData).forEach(key => {
    if (key.startsWith(String(year))) data[key] = allData[key];
  });
  const weeksEl  = document.getElementById('calWeeks');
  const monthsEl = document.getElementById('calMonths');
  const totalEl  = document.getElementById('calTotal');
  if (!weeksEl) return;

  const jan1     = new Date(year, 0, 1);
  const startDow = (jan1.getDay() + 6) % 7;   // Mon=0
  const days = [];
  for (let i = 0; i < startDow; i++) days.push(null);
  for (let d = new Date(jan1); d.getFullYear() === year; d.setDate(d.getDate()+1)) days.push(new Date(d));
  while (days.length % 7 !== 0) days.push(null);

  const numWeeks = days.length / 7;
  let weeksHTML = '', visibleTotal = 0;
  const colW = 14;

  for (let w = 0; w < numWeeks; w++) {
    weeksHTML += '<div class="cal-week">';
    for (let dow = 0; dow < 7; dow++) {
      const day = days[w * 7 + dow];
      if (!day) { weeksHTML += '<div style="width:11px;height:11px"></div>'; continue; }
      const key   = day.toISOString().slice(0, 10);
      const count = data[key] || 0;
      const level = Math.min(4, count);
      visibleTotal += count;
      weeksHTML += `<div class="cal-cell${level > 0 ? ' l'+level : ''}" title="${key}: ${count} задан."></div>`;
    }
    weeksHTML += '</div>';
  }
  weeksEl.innerHTML = weeksHTML;

  if (totalEl) {
    const total = yearTotals[String(year)] ?? visibleTotal;
    totalEl.textContent = `${total} заданий выполнено в ${year} году`;
  }

  if (monthsEl) {
    const MONTHS = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
    let html = '';
    for (let m = 0; m < 12; m++) {
      const firstOfMonth = new Date(year, m, 1);
      const dayIdx  = Math.floor((firstOfMonth - jan1) / 86400000) + startDow;
      const weekIdx = Math.floor(dayIdx / 7);
      html += `<span class="cal-month-label" style="left:${weekIdx * colW}px">${MONTHS[m]}</span>`;
    }
    monthsEl.innerHTML = html;
  }
}

function setCalendarYear(year) {
  calYear = year;
  document.querySelectorAll('.year-option').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.trim() === String(year));
  });
  renderActivityCalendar(year);
}

function initCalendar() {
  renderActivityCalendar(calYear);
}

/* Модальное окно */

async function evaluateCurrentTask(taskId, modalId) {
  try {
    const response = await fetch(window.location.pathname, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        palette: palette.filter(Boolean),
        harmony_type: window.GAME_LEVEL === 1 ? harmonyMode : null
      })
    });

    if (!response.ok) throw new Error('Assessment request failed');

    const result = await response.json();
    updateResultModal(modalId, result);
    showModal(modalId);
  } catch (error) {
    console.error(error);
    showModal(modalId);
  }
}

function updateResultModal(modalId, result) {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  const score = modal.querySelector('[data-result-score]');
  const scoreCircle = modal.querySelector('[data-result-score-circle]');
  const title = modal.querySelector('[data-result-title]');
  const sub = modal.querySelector('[data-result-sub]');
  const totalColor = getScoreColor(result.total_score);

  if (score) score.textContent = result.total_score;
  if (scoreCircle) {
    scoreCircle.style.borderColor = totalColor;
    scoreCircle.style.color = totalColor;
  }
  if (title) title.textContent = result.conclusion;
  if (sub) sub.textContent = result.summary;

  updateCriterionRow(modal, 'harmony', result.harmony_score);
  updateCriterionRow(modal, 'emotion', result.emotion_score);
  updateCriterionRow(modal, 'contrast', result.contrast_score);
  updateCriterionRow(modal, 'colorVision', result.color_vision_score);
  updateResultFeedback(modal, result.feedback || []);
}

function updateCriterionRow(modal, key, scoreValue, labelValue) {
  const row = modal.querySelector(`[data-criterion="${key}"]`);
  if (!row) return;

  const hasScore = scoreValue !== null && scoreValue !== undefined;
  row.style.display = hasScore ? '' : 'none';
  if (!hasScore) return;

  const value = row.querySelector('[data-criterion-value]');
  if (!value) return;

  value.style.color = getScoreColor(scoreValue);
  value.textContent = labelValue || `${scoreValue} / 100`;
}

function getScoreColor(scoreValue) {
  if (scoreValue >= 85) return 'var(--success)';
  if (scoreValue >= 70) return 'var(--accent)';
  if (scoreValue >= 50) return 'var(--accent2)';
  return 'var(--danger)';
}

function updateResultFeedback(modal, feedbackItems) {
  const feedback = modal.querySelector('[data-result-feedback]');
  const feedbackList = modal.querySelector('[data-result-feedback-list]');
  if (!feedback || !feedbackList) return;

  const items = Array.isArray(feedbackItems) ? feedbackItems.filter(Boolean) : [];
  feedback.hidden = items.length === 0;
  feedback.open = false;
  if (!items.length) {
    feedbackList.innerHTML = '';
    return;
  }

  feedbackList.innerHTML = items
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join('');
}

function updateWcagPanel() {
  if (!window.SHOW_WCAG) return;

  const rows = document.querySelectorAll('[data-wcag-row]');
  if (!rows.length) return;

  const text = palette[3];
  const surfaces = [palette[0], palette[1], palette[2]];
  const labels = ['Фон', 'Поверхность', 'Акцент'];

  rows.forEach((row, index) => {
    const main = row.querySelector('[data-wcag-main]');
    const sub = row.querySelector('[data-wcag-sub]');
    const dot = row.querySelector('[data-wcag-dot]');
    const background = surfaces[index];

    if (!text || !background) {
      if (main) main.textContent = `${labels[index]} · --`;
      if (sub) sub.textContent = 'Обычный: -- · Крупный: --';
      if (dot) dot.className = 'wcag-dot';
      row.classList.remove('wcag-pass', 'wcag-fail');
      return;
    }

    const ratio = contrastRatioForPair(text, background);
    const normalPassed = ratio >= 4.5;
    const largePassed = ratio >= 3.0;
    const rowPassed = normalPassed && largePassed;

    row.classList.toggle('wcag-pass', rowPassed);
    row.classList.toggle('wcag-fail', !rowPassed);
    if (dot) {
      dot.className = `wcag-dot ${rowPassed ? 'wcag-dot-p' : 'wcag-dot-f'}`;
    }
    if (main) {
      main.textContent = `${labels[index]} · ${ratio.toFixed(2)}:1`;
    }
    if (sub) {
      sub.textContent = `Обычный: ${normalPassed ? 'OK' : 'нужно 4.5'} · Крупный: ${largePassed ? 'OK' : 'нужно 3.0'}`;
    }
  });
}

function contrastRatioForPair(foreground, background) {
  const l1 = getLuminance(foreground);
  const l2 = getLuminance(background);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function showModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
}

function hideModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


