"""FastAPI app builder. Serves /game (2D top-down) and /world (3D walkable)
plus /api/cards (the data endpoint both frontends consume) and a couple
of small static endpoints.

Three.js is loaded from a public CDN to keep the package small. If you
need an offline / air-gapped deploy, drop your own three.module.js into
src/wander_around/static/ and the server prefers the local copy.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

if TYPE_CHECKING:
    from .core import Wander


# esm.sh resolves the bare `three` specifier inside PointerLockControls,
# which unpkg does not — using esm.sh keeps the CDN fallback functional
# even with an empty local static/.
_THREE_CDN = "https://esm.sh/three@0.164.1/build/three.module.js"
_PLC_CDN = "https://esm.sh/three@0.164.1/examples/jsm/controls/PointerLockControls.js"


def build_app(w: "Wander") -> FastAPI:
    app = FastAPI(title=w.title)
    static_dir = Path(__file__).parent / "static"

    # Title and description flow into HTML templates; escape to prevent
    # HTML injection from user-supplied dataset metadata.
    safe_title = html.escape(w.title)
    safe_desc = html.escape(w.description)

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return HTMLResponse(_INDEX_HTML.replace("{TITLE}", safe_title)
                             .replace("{DESC}", safe_desc))

    @app.get("/api/cards")
    async def api_cards():
        # Returns the entire dataset; for very large datasets, replace this
        # with a viewport-bounded /api/region endpoint.
        return JSONResponse([c.to_dict() for c in w.cards])

    @app.get("/api/manifest")
    async def api_manifest():
        cats: dict[str, int] = {}
        for c in w.cards:
            cats[c.category or "_uncat"] = cats.get(c.category or "_uncat", 0) + 1
        return JSONResponse({
            "n_cards": len(w.cards),
            "title": w.title,
            "description": w.description,
            "categories": sorted(cats.items(), key=lambda kv: -kv[1]),
            "palette": w.palette,
            "three_module_url": _local_or_cdn(static_dir, "three.module.js", _THREE_CDN),
            "pointer_lock_url": _local_or_cdn(static_dir, "PointerLockControls.js", _PLC_CDN),
        })

    @app.get("/game", response_class=HTMLResponse)
    async def game_page():
        return HTMLResponse(_GAME_HTML.replace("{TITLE}", w.title))

    @app.get("/game/main.js")
    async def game_js():
        return _js_response(_GAME_JS)

    @app.get("/world", response_class=HTMLResponse)
    async def world_page():
        return HTMLResponse(_WORLD_HTML.replace("{TITLE}", w.title))

    @app.get("/world/main.js")
    async def world_js():
        return _js_response(_WORLD_JS)

    # StaticFiles handles path-traversal safety properly (resolves and
    # confirms the file is under static_dir on every request, including
    # the encoded-backslash and percent-decoded variants Windows would
    # otherwise let through a naive single-segment route).
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    else:
        @app.get("/static/{name:path}")
        async def static_file_missing(name: str):
            return JSONResponse({"error": "static directory not present"},
                                 status_code=404)

    return app


def _local_or_cdn(static_dir: Path, name: str, cdn_url: str) -> str:
    return f"/static/{name}" if (static_dir / name).exists() else cdn_url


def _js_response(s: str):
    from fastapi.responses import Response
    return Response(content=s, media_type="application/javascript")


# ── INDEX ──────────────────────────────────────────────────────────────

_INDEX_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<style>
:root { --fg:#ece8df; --bg:#0c0c0e; --line:#2a2a32; --accent:#cff0c8; }
body { margin:0; padding:0; min-height:100vh; background:var(--bg); color:var(--fg);
       font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
       display:flex; flex-direction:column; align-items:center; justify-content:center;
       padding: 2rem; line-height:1.55; }
.card { max-width: 36rem; text-align: center; }
h1 { font-size: 2rem; margin: 0 0 0.5rem; }
p { color: #b0a89d; }
.btns { display:flex; gap:0.6rem; flex-wrap:wrap; justify-content:center; margin-top:1.4rem; }
a.btn { background: rgba(20,20,26,0.85); border:1px solid var(--line);
         padding: 0.7rem 1.2rem; border-radius:8px; color:var(--fg);
         text-decoration:none; font-size:0.95rem; }
a.btn.primary { background:rgba(40,52,46,0.85); border-color:#2c4030; color:var(--accent); }
</style></head><body>
<div class="card">
  <h1>{TITLE}</h1>
  <p>{DESC}</p>
  <div class="btns">
    <a class="btn primary" href="/world">Walk in (3D)</a>
    <a class="btn" href="/game">Top-down map (2D)</a>
  </div>
</div></body></html>"""


# ── 2D GAME PAGE ──────────────────────────────────────────────────────

_GAME_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
<title>{TITLE} — 2D map</title>
<style>
:root { --fg:#ece8df; --bg:#0c0c0e; --line:#2a2a32; --accent:#cff0c8; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; height:100%; background:var(--bg); color:var(--fg);
             font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
             overflow:hidden; touch-action:none; }
canvas#world { position: fixed; inset: 0; }
.topbar { position:fixed; top:0; left:0; right:0; z-index:5; padding:0.7rem 1rem;
          display:flex; justify-content:space-between; align-items:baseline; gap:1rem;
          background: linear-gradient(to bottom, rgba(12,12,14,0.85), transparent);
          pointer-events:none; }
.brand { font-size:0.85rem; opacity:0.85; }
.stats { font-size:0.7rem; opacity:0.55; }
.legend { position:fixed; left:1rem; bottom:1rem; z-index:5; background:rgba(12,12,14,0.85);
          padding:0.6rem 0.8rem; border:1px solid var(--line); border-radius:6px;
          font-size:0.7rem; line-height:1.5; max-width:14rem; }
.toggles { position:fixed; right:1rem; bottom:1rem; z-index:5; display:flex; gap:0.4rem; }
.toggles a { background:rgba(12,12,14,0.85); border:1px solid var(--line); border-radius:6px;
              padding:0.5rem 0.8rem; color:var(--fg); text-decoration:none; font-size:0.75rem; }
.modal { position:fixed; inset:0; background:rgba(0,0,0,0.7); z-index:10;
         display:none; align-items:center; justify-content:center; padding:1rem; }
.modal.show { display:flex; }
.modal .panel { background:#14141a; border:1px solid var(--line); border-radius:10px;
                max-width:480px; width:100%; padding:1.4rem; line-height:1.5; }
.mobile-pad { position:fixed; bottom:1rem; right:0.6rem; z-index:8; display:none;
              grid-template-columns: 56px 56px 56px; grid-template-rows: 56px 56px 56px;
              gap:5px; opacity:0.85; }
.mobile-pad button { background:rgba(20,20,26,0.92); color:var(--fg);
                     border:1px solid var(--line); border-radius:10px; font-family:inherit;
                     font-size:1.4rem; user-select:none; touch-action:manipulation;
                     cursor:pointer; -webkit-tap-highlight-color: transparent; }
.mobile-pad button:active { background:rgba(60,72,66,0.95); }
.mobile-pad button.up    { grid-column:2; grid-row:1; }
.mobile-pad button.left  { grid-column:1; grid-row:2; }
.mobile-pad button.right { grid-column:3; grid-row:2; }
.mobile-pad button.down  { grid-column:2; grid-row:3; }
.mobile-pad button.enter { grid-column:2; grid-row:2; background:rgba(40,52,46,0.92);
                            color:var(--accent); border-color:#2c4030; font-size:0.7rem; }
body.is-mobile .mobile-pad { display:grid !important; }
body.is-mobile .legend, body.is-mobile .toggles, body.is-mobile .stats { display:none !important; }
.welcome { position:fixed; inset:0; z-index:30; background:rgba(8,8,12,0.92);
           display:none; align-items:center; justify-content:center; padding:1.2rem;
           backdrop-filter:blur(4px); }
.welcome.show { display:flex; }
.welcome .panel { background:#14141a; border:1px solid var(--line); border-radius:14px;
                   max-width:24rem; padding:1.4rem; text-align:center; }
.welcome h2 { color:var(--accent); margin:0 0 0.6rem; }
.welcome button { margin-top:0.8rem; padding:0.7rem 1.4rem; background:rgba(40,52,46,0.92);
                   color:var(--accent); border:1px solid #2c4030; border-radius:8px;
                   font-family:inherit; cursor:pointer; }
</style></head>
<body>
<canvas id="world"></canvas>
<div class="topbar"><span class="brand">{TITLE}</span><span class="stats" id="stats">loading…</span></div>
<div class="legend" id="legend"></div>
<div class="toggles"><a href="/world">3D world</a></div>
<div class="modal" id="modal"><div class="panel" id="modal-panel"></div></div>
<div class="mobile-pad" id="mpad" aria-hidden="true">
  <button class="up" data-key="w">↑</button>
  <button class="left" data-key="a">←</button>
  <button class="enter" data-key="e">enter</button>
  <button class="right" data-key="d">→</button>
  <button class="down" data-key="s">↓</button>
</div>
<div class="welcome" id="welcome"><div class="panel">
  <h2>{TITLE}</h2>
  <p>Walk through your dataset. WASD or arrow keys; on mobile, the on-screen pad.</p>
  <p style="font-size:0.85rem;opacity:0.7;">Tap <b>enter</b> next to a building to open it.</p>
  <button id="welcome-go">Step in</button>
</div></div>
<script>
(function(){
  if (('ontouchstart' in window) || navigator.maxTouchPoints > 0 || window.innerWidth < 1024) {
    document.body.classList.add('is-mobile');
  }
  const w = document.getElementById('welcome');
  if (!sessionStorage.getItem('wa_welcome')) w.classList.add('show');
  document.getElementById('welcome-go').onclick = () => {
    w.classList.remove('show'); sessionStorage.setItem('wa_welcome', '1');
  };
})();
</script>
<script src="/game/main.js"></script>
</body></html>"""

_GAME_JS = r"""
// 2D top-down map. Canvas + rAF loop. WASD or arrows to walk.
const canvas = document.getElementById('world');
const ctx = canvas.getContext('2d', { alpha: false });
const stats = document.getElementById('stats');
const legend = document.getElementById('legend');
const modal = document.getElementById('modal');
const modalPanel = document.getElementById('modal-panel');

let cards = [];
let manifest = null;
let palette = {};
const player = { x: 0, y: 0, speed: 200 };
const keys = {};
let viewScale = 1.0;
let canvasW = 0, canvasH = 0;

function resize(){ canvasW = canvas.width = innerWidth * devicePixelRatio;
                    canvasH = canvas.height = innerHeight * devicePixelRatio;
                    canvas.style.width = innerWidth + 'px';
                    canvas.style.height = innerHeight + 'px'; }
window.addEventListener('resize', resize); resize();

function pickColor(cat){
  if (palette[cat]) return palette[cat];
  // Hash the cat name to a stable hue
  let h = 0;
  for (let i = 0; i < (cat||'').length; i++) h = (h * 31 + cat.charCodeAt(i)) | 0;
  return `hsl(${Math.abs(h) % 360}, 50%, 55%)`;
}

async function load(){
  manifest = await fetch('/api/manifest').then(r => r.json());
  palette = manifest.palette || {};
  cards = await fetch('/api/cards').then(r => r.json());
  // Scale to fit
  let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
  for (const c of cards) {
    if (c.x < xmin) xmin = c.x; if (c.x > xmax) xmax = c.x;
    if (c.y < ymin) ymin = c.y; if (c.y > ymax) ymax = c.y;
  }
  const w = xmax - xmin || 1, h = ymax - ymin || 1;
  viewScale = Math.min(canvas.width / (w * 1.4), canvas.height / (h * 1.4));
  player.x = (xmin + xmax) / 2;
  player.y = (ymin + ymax) / 2;
  legend.innerHTML = `<div style="opacity:0.7;margin-bottom:0.3rem">categories</div>` +
    (manifest.categories || []).slice(0, 8).map(([cat, n]) =>
      `<div style="display:flex;align-items:center;gap:0.4rem">` +
      `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${pickColor(cat)}"></span>` +
      `${esc(String(cat||''))} <span style="opacity:0.5">${(+n)|0}</span></div>`
    ).join('');
  stats.textContent = `${cards.length.toLocaleString()} entities`;
  requestAnimationFrame(frame);
}

document.addEventListener('keydown', (e) => {
  const k = e.key.toLowerCase();
  if (['w','a','s','d','arrowup','arrowleft','arrowdown','arrowright','e'].includes(k)) {
    keys[k] = true; e.preventDefault();
  }
});
document.addEventListener('keyup', (e) => {
  keys[e.key.toLowerCase()] = false;
});

// Mobile-pad: dispatch synthetic key events
const mpad = document.getElementById('mpad');
if (mpad) {
  mpad.querySelectorAll('button').forEach(btn => {
    const k = btn.dataset.key;
    const press = (e) => { e.preventDefault(); keys[k] = true;
      if (k === 'e') openNearest(); };
    const release = (e) => { e.preventDefault(); keys[k] = false; };
    btn.addEventListener('touchstart', press, { passive: false });
    btn.addEventListener('mousedown', press);
    btn.addEventListener('touchend', release, { passive: false });
    btn.addEventListener('mouseup', release);
    btn.addEventListener('mouseleave', release);
  });
}

let lastT = 0;
function frame(now){
  const dt = Math.min(0.05, (now - lastT) / 1000) || 0;
  lastT = now;
  // Move player
  let mx = 0, my = 0;
  if (keys.w || keys.arrowup) my -= 1;
  if (keys.s || keys.arrowdown) my += 1;
  if (keys.a || keys.arrowleft) mx -= 1;
  if (keys.d || keys.arrowright) mx += 1;
  if (mx || my) {
    const mag = Math.hypot(mx, my);
    player.x += (mx / mag) * player.speed * dt;
    player.y += (my / mag) * player.speed * dt;
  }
  if (keys.e) { keys.e = false; openNearest(); }
  // Draw
  ctx.fillStyle = '#0c0c0e';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const cx = canvas.width / 2, cy = canvas.height / 2;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(viewScale, viewScale);
  ctx.translate(-player.x, -player.y);
  for (const c of cards) {
    ctx.fillStyle = pickColor(c.category || '_uncat');
    const r = 4 + (c.score || 0) * 0.5;
    ctx.beginPath(); ctx.arc(c.x, c.y, r / viewScale, 0, Math.PI * 2); ctx.fill();
  }
  // Player marker
  ctx.fillStyle = '#cff0c8';
  ctx.beginPath(); ctx.arc(player.x, player.y, 6 / viewScale, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
  requestAnimationFrame(frame);
}

function openNearest(){
  let nearest = null, minD = 50 * 50 / (viewScale * viewScale);
  for (const c of cards) {
    const d = (c.x - player.x) ** 2 + (c.y - player.y) ** 2;
    if (d < minD) { minD = d; nearest = c; }
  }
  if (nearest) {
    modalPanel.innerHTML = `<h3 style="margin:0 0 0.5rem">${esc(nearest.label)}</h3>` +
      (nearest.category ? `<div style="opacity:0.6;font-size:0.85rem">${esc(nearest.category)}</div>` : '') +
      (safeUrl(nearest.link) ? `<p style="margin-top:1rem"><a href="${esc(safeUrl(nearest.link))}" target="_blank" rel="noopener noreferrer" style="color:#cff0c8">Open ↗</a></p>` : '') +
      `<p style="margin-top:1rem;text-align:right"><a href="#" onclick="document.getElementById('modal').classList.remove('show');return false" style="color:#888">close</a></p>`;
    modal.classList.add('show');
  }
}
function esc(s){ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function safeUrl(u){
  if (!u || typeof u !== 'string') return '';
  try {
    const parsed = new URL(u, window.location.href);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : '';
  } catch (e) { return ''; }
}

load();
"""


# ── 3D WORLD PAGE ──────────────────────────────────────────────────────

_WORLD_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
<title>{TITLE} — walkable 3D world</title>
<style>
:root { --fg:#ece8df; --bg:#0c0c0e; --line:#2a2a32; --accent:#cff0c8; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; height:100%; background:var(--bg); color:var(--fg);
             font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow:hidden;
             touch-action: none; }
#world { position: fixed; inset: 0; }
.topbar { position:fixed; top:0; left:0; right:0; z-index:5; padding:0.7rem 1rem;
          display:flex; justify-content:space-between; align-items:baseline;
          background: linear-gradient(to bottom, rgba(12,12,14,0.85), transparent);
          pointer-events:none; }
.brand { font-size:0.85rem; opacity:0.85; }
.stats { font-size:0.7rem; opacity:0.55; }
.hint { position:fixed; left:50%; top:60%; transform:translateX(-50%); z-index:5;
        background:rgba(12,12,14,0.92); border:1px solid var(--line); border-radius:8px;
        padding:1rem 1.4rem; font-size:0.85rem; max-width:24rem; text-align:center;
        display:none; }
.hint.show { display:block; }
.legend { position:fixed; left:1rem; bottom:1rem; z-index:5; background:rgba(12,12,14,0.85);
          padding:0.6rem 0.8rem; border:1px solid var(--line); border-radius:6px;
          font-size:0.7rem; max-width:14rem; }
.toggles { position:fixed; right:1rem; bottom:1rem; z-index:5; display:flex; gap:0.4rem; }
.toggles a { background:rgba(12,12,14,0.85); border:1px solid var(--line); border-radius:6px;
              padding:0.5rem 0.8rem; color:var(--fg); text-decoration:none; font-size:0.75rem; }
.modal { position:fixed; inset:0; background:rgba(0,0,0,0.7); z-index:10;
         display:none; align-items:center; justify-content:center; padding:1rem; }
.modal.show { display:flex; }
.modal .panel { background:#14141a; border:1px solid var(--line); border-radius:10px;
                max-width:520px; width:100%; padding:1.4rem; line-height:1.5; }
.mobile-pad { position:fixed; bottom:1rem; right:0.6rem; z-index:8; display:none;
              grid-template-columns: 56px 56px 56px; grid-template-rows: 56px 56px 56px;
              gap:5px; opacity:0.85; }
.mobile-pad button { background:rgba(20,20,26,0.92); color:var(--fg);
                     border:1px solid var(--line); border-radius:10px; font-family:inherit;
                     font-size:1.4rem; user-select:none; touch-action:manipulation;
                     cursor:pointer; -webkit-tap-highlight-color: transparent; }
.mobile-pad button:active { background:rgba(60,72,66,0.95); }
.mobile-pad button.up    { grid-column:2; grid-row:1; }
.mobile-pad button.left  { grid-column:1; grid-row:2; }
.mobile-pad button.right { grid-column:3; grid-row:2; }
.mobile-pad button.down  { grid-column:2; grid-row:3; }
.mobile-pad button.enter { grid-column:2; grid-row:2; background:rgba(40,52,46,0.92);
                            color:var(--accent); border-color:#2c4030; font-size:0.7rem; }
body.is-mobile .mobile-pad { display:grid !important; }
body.is-mobile .stats, body.is-mobile .legend, body.is-mobile .toggles,
body.is-mobile .hint { display:none !important; }
.welcome { position:fixed; inset:0; z-index:30; background:rgba(8,8,12,0.92);
           display:none; align-items:center; justify-content:center; padding:1.2rem;
           backdrop-filter:blur(4px); }
.welcome.show { display:flex; }
.welcome .panel { background:#14141a; border:1px solid var(--line); border-radius:14px;
                   max-width:26rem; padding:1.6rem; text-align:center; }
.welcome h2 { color:var(--accent); margin:0 0 0.6rem; }
.welcome button { margin-top:0.8rem; padding:0.7rem 1.4rem; background:rgba(40,52,46,0.92);
                   color:var(--accent); border:1px solid #2c4030; border-radius:8px;
                   font-family:inherit; cursor:pointer; }
</style></head>
<body>
<canvas id="world"></canvas>
<div class="topbar"><span class="brand">{TITLE}</span><span class="stats" id="stats">loading…</span></div>
<div class="hint" id="hint">Click to enter the world. <b>WASD</b> walk · <b>mouse</b> look · <b>E</b> open · <b>ESC</b> release</div>
<div class="legend" id="legend"></div>
<div class="toggles"><a href="/game">2D map</a></div>
<div class="modal" id="modal"><div class="panel" id="modal-panel"></div></div>
<div class="mobile-pad" id="mpad" aria-hidden="true">
  <button class="up" data-code="KeyW">↑</button>
  <button class="left" data-code="KeyA">←</button>
  <button class="enter" data-code="KeyE">enter</button>
  <button class="right" data-code="KeyD">→</button>
  <button class="down" data-code="KeyS">↓</button>
</div>
<div class="welcome" id="welcome"><div class="panel">
  <h2>{TITLE}</h2>
  <p>Walk through your dataset in 3D. WASD to walk · mouse to look · E to open. On mobile, use the on-screen pad and drag to look.</p>
  <button id="welcome-go">Step in</button>
</div></div>
<script>
(function(){
  if (('ontouchstart' in window) || navigator.maxTouchPoints > 0 || window.innerWidth < 1024) {
    document.body.classList.add('is-mobile');
  }
  const w = document.getElementById('welcome');
  if (!sessionStorage.getItem('wa_welcome3d')) w.classList.add('show');
  document.getElementById('welcome-go').onclick = () => {
    w.classList.remove('show'); sessionStorage.setItem('wa_welcome3d', '1');
  };
})();
</script>
<script type="module" src="/world/main.js"></script>
</body></html>"""


_WORLD_JS = r"""
// 3D walkable world. Three.js + PointerLockControls (or touch-drag on mobile).
const manifest = await fetch('/api/manifest').then(r => r.json());
const cards = await fetch('/api/cards').then(r => r.json());

const THREE = await import(manifest.three_module_url);
const PLCmod = await import(manifest.pointer_lock_url);
const PointerLockControls = PLCmod.PointerLockControls;

const stats = document.getElementById('stats');
const hint = document.getElementById('hint');
const legend = document.getElementById('legend');
const modal = document.getElementById('modal');
const modalPanel = document.getElementById('modal-panel');

const IS_TOUCH = ('ontouchstart' in window) || navigator.maxTouchPoints > 0;

// Scene
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c0c0e);
scene.fog = new THREE.Fog(0x0c0c0e, 200, 1500);
const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.5, 3000);
camera.position.set(0, 4, 0);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('world'), antialias: true });
renderer.setPixelRatio(devicePixelRatio);
renderer.setSize(innerWidth, innerHeight);
window.addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// Light + ground
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 0.7);
sun.position.set(120, 200, 80); scene.add(sun);
const groundGeo = new THREE.PlaneGeometry(4000, 4000);
const groundMat = new THREE.MeshStandardMaterial({ color: 0x16161c });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2; scene.add(ground);

// Buildings
function colorFor(cat){
  if (manifest.palette && manifest.palette[cat]) return new THREE.Color(manifest.palette[cat]);
  let h = 0;
  for (let i = 0; i < (cat||'').length; i++) h = (h * 31 + cat.charCodeAt(i)) | 0;
  return new THREE.Color().setHSL((Math.abs(h) % 360) / 360, 0.5, 0.55);
}
const cardMeshes = [];
for (const c of cards) {
  const h = 8 + (c.score || 0) * 1.2;
  const w = 6 + Math.min(20, (c.score || 0) * 0.4);
  const geo = new THREE.BoxGeometry(w, h, w);
  const mat = new THREE.MeshStandardMaterial({ color: colorFor(c.category || '_uncat') });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(c.x, h / 2, c.y);
  mesh.userData = c;
  scene.add(mesh);
  cardMeshes.push(mesh);
}
stats.textContent = `${cards.length.toLocaleString()} entities`;
legend.innerHTML = `<div style="opacity:0.7;margin-bottom:0.3rem">categories</div>` +
  (manifest.categories || []).slice(0, 8).map(([cat, n]) => {
    const c = colorFor(cat);
    return `<div style="display:flex;align-items:center;gap:0.4rem"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:rgb(${(c.r*255)|0},${(c.g*255)|0},${(c.b*255)|0})"></span>${esc(String(cat||''))} <span style="opacity:0.5">${(+n)|0}</span></div>`;
  }).join('');

// Controls (desktop pointer-lock + mobile touch-drag)
const controls = new PointerLockControls(camera, document.body);
if (!IS_TOUCH) hint.classList.add('show');
document.body.addEventListener('click', (e) => {
  if (e.target.closest('.toggles, .modal, .legend, .mobile-pad, .welcome')) return;
  if (!IS_TOUCH && !controls.isLocked) controls.lock();
});
controls.addEventListener('lock', () => hint.classList.remove('show'));
controls.addEventListener('unlock', () => { if (!IS_TOUCH) hint.classList.add('show'); });

if (IS_TOUCH) {
  const PI_2 = Math.PI / 2;
  const euler = new THREE.Euler(0, 0, 0, 'YXZ');
  let dragId = null, lastX = 0, lastY = 0;
  document.body.addEventListener('touchstart', (e) => {
    if (e.touches.length !== 1) return;
    const t = e.touches[0];
    if (t.target.closest('.mobile-pad, .modal, .welcome, .toggles')) return;
    dragId = t.identifier; lastX = t.clientX; lastY = t.clientY;
  }, { passive: true });
  document.body.addEventListener('touchmove', (e) => {
    if (dragId == null) return;
    let t = null;
    for (let i = 0; i < e.touches.length; i++)
      if (e.touches[i].identifier === dragId) { t = e.touches[i]; break; }
    if (!t) return;
    const dx = t.clientX - lastX, dy = t.clientY - lastY;
    lastX = t.clientX; lastY = t.clientY;
    euler.setFromQuaternion(camera.quaternion);
    euler.y -= dx * 0.0035;
    euler.x -= dy * 0.0035;
    euler.x = Math.max(-PI_2 + 0.001, Math.min(PI_2 - 0.001, euler.x));
    camera.quaternion.setFromEuler(euler);
  }, { passive: true });
  document.body.addEventListener('touchend', (e) => {
    for (let i = 0; i < e.changedTouches.length; i++)
      if (e.changedTouches[i].identifier === dragId) { dragId = null; break; }
  }, { passive: true });
}

// Keyboard + mobile-pad-as-keys
const keys = {};
window.addEventListener('keydown', (e) => { keys[e.code] = true;
  if (e.code === 'KeyE') openNearest();
});
window.addEventListener('keyup', (e) => { keys[e.code] = false; });

const mpad = document.getElementById('mpad');
if (mpad) {
  mpad.querySelectorAll('button').forEach(btn => {
    const code = btn.dataset.code;
    const press = (e) => { e.preventDefault(); keys[code] = true;
      const ev = new KeyboardEvent('keydown', { code, bubbles: true });
      window.dispatchEvent(ev); };
    const release = (e) => { e.preventDefault(); keys[code] = false; };
    btn.addEventListener('touchstart', press, { passive: false });
    btn.addEventListener('mousedown', press);
    btn.addEventListener('touchend', release, { passive: false });
    btn.addEventListener('mouseup', release);
    btn.addEventListener('mouseleave', release);
  });
}

// Frame loop
const tmpV = new THREE.Vector3(), tmpFwd = new THREE.Vector3(), tmpRight = new THREE.Vector3();
let lastT = 0;
function frame(now){
  const dt = Math.min(0.05, (now - lastT) / 1000) || 0;
  lastT = now;
  if (controls.isLocked || IS_TOUCH) {
    let mx = 0, mz = 0;
    if (keys['KeyW']) mz -= 1;
    if (keys['KeyS']) mz += 1;
    if (keys['KeyA']) mx -= 1;
    if (keys['KeyD']) mx += 1;
    if (mx || mz) {
      camera.getWorldDirection(tmpFwd); tmpFwd.y = 0; tmpFwd.normalize();
      tmpRight.copy(tmpFwd).cross(camera.up).normalize();
      tmpV.set(0,0,0).addScaledVector(tmpFwd, -mz).addScaledVector(tmpRight, mx)
          .normalize().multiplyScalar(80 * dt);
      camera.position.x += tmpV.x; camera.position.z += tmpV.z;
    }
  }
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

function openNearest(){
  let nearest = null, minD = 30 * 30;
  for (const m of cardMeshes) {
    const dx = m.position.x - camera.position.x, dz = m.position.z - camera.position.z;
    const d = dx * dx + dz * dz;
    if (d < minD) { minD = d; nearest = m.userData; }
  }
  if (nearest) {
    modalPanel.innerHTML = `<h3 style="margin:0 0 0.5rem">${esc(nearest.label)}</h3>` +
      (nearest.category ? `<div style="opacity:0.6;font-size:0.85rem">${esc(nearest.category)}</div>` : '') +
      (safeUrl(nearest.link) ? `<p style="margin-top:1rem"><a href="${esc(safeUrl(nearest.link))}" target="_blank" rel="noopener noreferrer" style="color:#cff0c8">Open ↗</a></p>` : '') +
      `<p style="margin-top:1rem;text-align:right"><a href="#" onclick="document.getElementById('modal').classList.remove('show');return false" style="color:#888">close</a></p>`;
    modal.classList.add('show');
  }
}
function esc(s){ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function safeUrl(u){
  if (!u || typeof u !== 'string') return '';
  try {
    const parsed = new URL(u, window.location.href);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : '';
  } catch (e) { return ''; }
}
"""
