'use strict';

/* Deterministic pseudo-random (LCG) */

function adminRng(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => { s = s * 16807 % 2147483647; return (s - 1) / 2147483646; };
}

function adminGen7(base, variance, seed) {
  const r = adminRng(seed);
  return Array.from({ length: 7 }, () =>
    Math.round(base + (r() - 0.5) * 2 * variance)
  );
}

function adminGen12(base, variance, seed) {
  const r = adminRng(seed);
  return Array.from({ length: 12 }, () =>
    Math.round(base + (r() - 0.5) * 2 * variance)
  );
}

/* SVG Sparkline */

function adminSparkline(data, color, height = 28, filled = false) {
  const w = 100, h = height;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = i / (data.length - 1) * w;
    const y = h - (v - min) / range * (h - 4) - 2;
    return `${x},${y}`;
  });
  const path = `M${pts.join('L')}`;
  const fill = filled
    ? `<path d="${path}L${w},${h}L0,${h}Z" fill="${color}" opacity="0.15"/>`
    : '';
  return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"
               style="width:100%;height:${h}px;overflow:visible">
    ${fill}
    <path d="${path}" fill="none" stroke="${color}" stroke-width="1.5"
          stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
}

/* Canvas: Bar chart */

function drawAdminBarChart(canvasId, labels, datasets) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || canvas.width;
  const H = canvas.offsetHeight || canvas.height;
  canvas.width = W * 2; canvas.height = H * 2;
  ctx.scale(2, 2);
  ctx.clearRect(0, 0, W, H);

  const pad = { l:30, r:10, t:10, b:22 };
  const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;
  const maxV = Math.max(...datasets.flatMap(d => d.data)) * 1.1 || 1;
  const step = cw / labels.length;
  const barW = step * 0.55 / datasets.length;

  ctx.strokeStyle = 'rgba(255,255,255,.05)'; ctx.lineWidth = 1;
  [0,.25,.5,.75,1].forEach(f => {
    const y = pad.t + ch * (1 - f);
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cw,y); ctx.stroke();
    ctx.fillStyle='rgba(255,255,255,.9)'; ctx.font='400 9px \"DM Sans\"'; ctx.textAlign='right';
    ctx.fillText(Math.round(f*maxV), pad.l-4, y+3);
  });

  datasets.forEach((ds, di) => {
    ds.data.forEach((v, i) => {
      const x  = pad.l + i*step + (step - barW*datasets.length)/2 + di*barW;
      const bh = v/maxV*ch;
      const y  = pad.t + ch - bh;
      ctx.fillStyle = ds.color;
      ctx.beginPath();
      ctx.roundRect(x, y, barW, bh, [Math.min(3,barW/2), Math.min(3,barW/2), 0, 0]);
      ctx.fill();
    });
  });

  ctx.fillStyle='rgba(255,255,255,.9)'; ctx.font='400 9px \"DM Sans\"'; ctx.textAlign='center';
  labels.forEach((l, i) => ctx.fillText(l, pad.l+(i+.5)*step, H-pad.b+13));
}

/* Canvas Line chart */

function drawAdminLineChart(canvasId, labels, datasets) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || canvas.width;
  const H = canvas.offsetHeight || canvas.height;
  canvas.width = W * 2; canvas.height = H * 2;
  ctx.scale(2, 2);
  ctx.clearRect(0, 0, W, H);

  const pad = { l:30, r:10, t:10, b:22 };
  const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;
  const maxV = Math.max(...datasets.flatMap(d => d.data)) * 1.1 || 1;

  ctx.strokeStyle='rgba(255,255,255,.05)'; ctx.lineWidth=1;
  [0,.25,.5,.75,1].forEach(f => {
    const y = pad.t + ch * (1-f);
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cw,y); ctx.stroke();
    ctx.fillStyle='rgba(255,255,255,.9)'; ctx.font='400 9px \"DM Sans\"'; ctx.textAlign='right';
    ctx.fillText(Math.round(f*maxV), pad.l-4, y+3);
  });

  datasets.forEach(ds => {
    const pts = ds.data.map((v,i) => ({
      x: pad.l + i/(labels.length-1)*cw,
      y: pad.t + ch - v/maxV*ch
    }));
    // Fill
    ctx.beginPath(); ctx.moveTo(pts[0].x, pad.t+ch);
    pts.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length-1].x, pad.t+ch); ctx.closePath();
    ctx.fillStyle = ds.color.startsWith('#')
      ? ds.color + '1f'
      : ds.color.replace(')',',0.12)').replace('rgb(','rgba(');
    ctx.fill();
    // Line
    ctx.beginPath(); ctx.moveTo(pts[0].x, pts[0].y);
    for (let i=1; i<pts.length; i++) {
      const cx1 = (pts[i-1].x + pts[i].x)/2;
      ctx.bezierCurveTo(cx1,pts[i-1].y, cx1,pts[i].y, pts[i].x,pts[i].y);
    }
    ctx.strokeStyle=ds.color; ctx.lineWidth=1.5; ctx.stroke();
    pts.forEach(p => {
      ctx.beginPath(); ctx.arc(p.x,p.y,2.5,0,Math.PI*2);
      ctx.fillStyle=ds.color; ctx.fill();
    });
  });

  ctx.fillStyle='rgba(255,255,255,.9)'; ctx.font='400 9px \"DM Sans\"'; ctx.textAlign='center';
  labels.forEach((l,i) => ctx.fillText(l, pad.l+i/(labels.length-1)*cw, H-pad.b+13));
}

/* Canvas: Donut */

function drawAdminDonut(canvasId, data, colors) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const size = 80;
  canvas.width = size*2; canvas.height = size*2;
  ctx.scale(2,2);
  const cx=size/2, cy=size/2, R=size/2-6, inner=R*0.58;
  const total = data.reduce((a,b)=>a+b,0);
  let angle = -Math.PI/2;
  data.forEach((v,i) => {
    const sweep = v/total*Math.PI*2;
    ctx.beginPath(); ctx.moveTo(cx,cy);
    ctx.arc(cx,cy,R,angle,angle+sweep);
    ctx.closePath(); ctx.fillStyle=colors[i]; ctx.fill();
    angle += sweep;
  });
  ctx.beginPath(); ctx.arc(cx,cy,inner,0,Math.PI*2);
  ctx.fillStyle='#12121a'; ctx.fill();
}

/* Heatmap (hour * weekday) */

function drawAdminHeatmap(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const days  = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  const hours = ['0:00','3:00','6:00','9:00','12:00','15:00','18:00','21:00'];
  const r = adminRng(42);
  const vals = Array.from({length:8}, () => Array.from({length:7}, () => r()));

  let html = `<div style="display:grid;grid-template-columns:44px repeat(7,1fr);gap:4px;margin-bottom:4px">
    <div></div>
    ${days.map(d=>`<div style="font-size:9px;color:rgba(232,234,240,.35);text-align:center">${d}</div>`).join('')}
  </div>`;

  vals.forEach((row, hi) => {
    html += `<div style="display:grid;grid-template-columns:44px repeat(7,1fr);gap:4px;margin-bottom:4px">
      <div style="font-size:9px;color:rgba(232,234,240,.3);line-height:20px;text-align:right;padding-right:8px">${hours[hi]}</div>`;
    row.forEach(v => {
      const cls   = v<.2?'': v<.45?'h1': v<.65?'h2': v<.83?'h3':'h4';
      const count = Math.round(v*120);
      html += `<div class="heatmap-cell ${cls}" style="height:20px"
                    onmouseenter="adminShowTip(event,'${count} сессий')"
                    onmouseleave="adminHideTip()"></div>`;
    });
    html += '</div>';
  });
  container.innerHTML = html;
}

/* Tooltip */

function adminShowTip(e, text) {
  const t = document.getElementById('tooltip');
  if (!t) return;
  t.textContent=text; t.style.opacity='1';
  t.style.left=(e.clientX+12)+'px'; t.style.top=(e.clientY-8)+'px';
}
function adminHideTip() {
  const t = document.getElementById('tooltip');
  if (t) t.style.opacity='0';
}

/* Initialization Overview Page */

function initOverviewPage() {
  document.querySelectorAll('.kpi-spark[data-spark]').forEach(el => {
    el.innerHTML = adminSparkline(
      el.dataset.spark.split(',').map(Number),
      el.dataset.color
    );
  });

  const ac = document.getElementById('activityChart');
  if (ac) {
    drawAdminLineChart('activityChart', ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'], [
      { data: ac.dataset.started.split(',').map(Number), color: '#6bffcc' },
      { data: ac.dataset.finished.split(',').map(Number), color: '#c8b4ff' },
    ]);
  }

  const dc = document.getElementById('donutChart');
  if (dc) {
    drawAdminDonut('donutChart',
      dc.dataset.values.split(',').map(Number),
      ['#6bffcc','#c8b4ff','#ff9f6b']
    );
  }

  const rc = document.getElementById('retentionChart');
  if (rc) {
    drawAdminLineChart('retentionChart',
      ['День 1','День 3','День 7','День 14','День 30'],
      [{ data: rc.dataset.values.split(',').map(Number), color: '#c8b4ff' }]
    );
  }
}


document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('activityChart')) initOverviewPage();
  // если будут другие страницы:
  // if (document.getElementById('usersTable'))  initUsersPage();
  // if (document.getElementById('skillsChart')) initSkillsPage();
});