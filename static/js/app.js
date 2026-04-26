// ── State ─────────────────────────────────────────────────────────────────────
let currentMode   = 'upload';
let cameraStream  = null;
let currentBase64 = null;
let activeUtt     = null;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Mode buttons
  document.getElementById('btnUpload').addEventListener('click', () => switchMode('upload'));
  document.getElementById('btnScan').addEventListener('click',   () => switchMode('scan'));

  // Upload actions
  document.getElementById('detectBtn').addEventListener('click', runDetection);
  document.getElementById('resetBtn').addEventListener('click',  resetUpload);

  // Camera actions
  document.getElementById('captureBtn').addEventListener('click', captureFrame);
  document.getElementById('stopCamBtn').addEventListener('click', stopCamera);

  // File input
  document.getElementById('fileInput').addEventListener('change', function () {
    if (this.files && this.files[0]) loadFile(this.files[0]);
  });

  // Drop zone
  const dz = document.getElementById('dropZone');
  dz.addEventListener('click', () => document.getElementById('fileInput').click());
  dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith('image/')) loadFile(f);
  });

  // Pre-load TTS voices
  if ('speechSynthesis' in window) {
    speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
  }
});

// ── Mode Switch ───────────────────────────────────────────────────────────────
function switchMode(mode) {
  currentMode = mode;
  document.getElementById('btnUpload').classList.toggle('active', mode === 'upload');
  document.getElementById('btnScan').classList.toggle('active',   mode === 'scan');
  document.getElementById('uploadPanel').style.display = mode === 'upload' ? '' : 'none';
  document.getElementById('scanPanel').style.display   = mode === 'scan'   ? '' : 'none';

  if (mode === 'scan') startCamera();
  else stopCamera();
}

// ── File Load ─────────────────────────────────────────────────────────────────
function loadFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    currentBase64 = e.target.result;
    const img = document.getElementById('previewImg');
    img.src = currentBase64;
    img.onload = () => clearCanvas();
    document.getElementById('dropZone').style.display    = 'none';
    document.getElementById('previewArea').style.display = '';
    clearResults();
  };
  reader.readAsDataURL(file);
}

function resetUpload() {
  currentBase64 = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('dropZone').style.display    = '';
  document.getElementById('previewArea').style.display = 'none';
  clearCanvas();
  clearResults();
}

// ── Camera ────────────────────────────────────────────────────────────────────
async function startCamera() {
  const errEl = document.getElementById('cameraError');
  const video  = document.getElementById('videoFeed');
  errEl.style.display = 'none';

  // Stop any existing stream first
  stopCamera();

  // Try rear camera first, fall back to any camera
  const constraints = [
    { video: { facingMode: { ideal: 'environment' } }, audio: false },
    { video: true, audio: false }
  ];

  for (const c of constraints) {
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia(c);
      video.srcObject = cameraStream;
      await video.play();
      return; // success
    } catch (err) {
      cameraStream = null;
      // try next constraint
    }
  }

  // All attempts failed
  errEl.style.display = 'block';
  errEl.textContent = '⚠️ Camera not available. Make sure you are on localhost or HTTPS, and have granted camera permission.';
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(t => t.stop());
    cameraStream = null;
  }
  const video = document.getElementById('videoFeed');
  if (video) {
    video.srcObject = null;
    video.load(); // reset video element
  }
  // Switch back to upload mode UI without triggering startCamera again
  currentMode = 'upload';
  document.getElementById('btnUpload').classList.add('active');
  document.getElementById('btnScan').classList.remove('active');
  document.getElementById('uploadPanel').style.display = '';
  document.getElementById('scanPanel').style.display   = 'none';
}

function captureFrame() {
  const video  = document.getElementById('videoFeed');
  const canvas = document.getElementById('scanCanvas');

  if (!cameraStream || !video.srcObject) {
    startCamera();
    return;
  }

  if (video.readyState < 2) {
    showError('Camera not ready yet, please wait.');
    return;
  }

  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  currentBase64 = canvas.toDataURL('image/jpeg', 0.92);
  sendToServer(currentBase64);
}

// ── Detection ─────────────────────────────────────────────────────────────────
function runDetection() {
  if (!currentBase64) {
    alert('Please select an image first.');
    return;
  }
  sendToServer(currentBase64);
}

async function sendToServer(base64) {
  showLoading(true);
  try {
    const res = await fetch('/detect', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ image: base64 }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Server ${res.status}: ${text}`);
    }

    const data = await res.json();

    if (data.success) {
      renderResults(data.detections);

      if (currentMode === 'upload') {
        const img = document.getElementById('previewImg');
        const draw = () => drawBoxes(data.detections);
        if (img.complete && img.naturalWidth > 0) draw();
        else img.addEventListener('load', draw, { once: true });
      }

      if (data.demo_mode) {
        document.getElementById('demoBadge').classList.add('visible');
      }
    } else {
      renderError(data.error || 'Detection failed.');
    }
  } catch (err) {
    renderError('Error: ' + err.message);
    console.error(err);
  } finally {
    showLoading(false);
  }
}

// ── BBox Drawing ──────────────────────────────────────────────────────────────
function drawBoxes(detections) {
  const img    = document.getElementById('previewImg');
  const canvas = document.getElementById('overlayCanvas');

  const dw = img.clientWidth;
  const dh = img.clientHeight;
  if (!dw || !dh) return;

  canvas.width  = dw;
  canvas.height = dh;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, dw, dh);

  const sx = dw / img.naturalWidth;
  const sy = dh / img.naturalHeight;

  detections.forEach(d => {
    if (!d.bbox || d.bbox.length < 4) return;
    const [x1, y1, x2, y2] = d.bbox;
    const rx = x1*sx, ry = y1*sy;
    const rw = (x2-x1)*sx, rh = (y2-y1)*sy;
    const col = confColor(d.confidence);

    ctx.strokeStyle = col;
    ctx.lineWidth   = 2.5;
    ctx.strokeRect(rx, ry, rw, rh);
    ctx.fillStyle = col + '22';
    ctx.fillRect(rx, ry, rw, rh);

    ctx.font = 'bold 11px monospace';
    const label = `${d.sign_en}  ${Math.round(d.confidence * 100)}%`;
    const tw    = ctx.measureText(label).width;
    ctx.fillStyle = col;
    ctx.fillRect(rx, ry - 20, tw + 10, 20);
    ctx.fillStyle = '#000';
    ctx.fillText(label, rx + 5, ry - 5);
  });
}

function clearCanvas() {
  const c = document.getElementById('overlayCanvas');
  if (c) {
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
  }
}

// ── Render Results ────────────────────────────────────────────────────────────
function renderResults(detections) {
  const el = document.getElementById('resultsContent');

  if (!detections || detections.length === 0) {
    el.innerHTML = `<div class="no-detect"><span>🔍</span>No traffic signs detected.</div>`;
    return;
  }

  const sorted = [...detections].sort((a, b) => b.confidence - a.confidence);
  let html = '';

  sorted.forEach((d, i) => {
    const pct = Math.round(d.confidence * 100);
    const cls = pct >= 80 ? 'high' : pct < 50 ? 'low' : '';
    html += `
      <div class="detection-card" style="animation-delay:${i * 55}ms">
        <div class="card-top">
          <div class="sign-en">${esc(d.sign_en)}</div>
          <div class="conf-badge ${cls}">${pct}%</div>
        </div>
        <div class="sign-kh">${esc(d.sign_kh)}</div>
        <div class="conf-bar-wrap">
          <div class="conf-bar">
            <div class="conf-fill" style="width:${pct}%"></div>
          </div>
          <div class="conf-pct">${d.confidence.toFixed(3)}</div>
        </div>
        <button class="btn-speak" id="speak${i}">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M15.54 8.46a5 5 0 010 7.07"/>
          </svg>
          ស្ដាប់
        </button>
      </div>`;
  });

  const avg = Math.round(sorted.reduce((s, d) => s + d.confidence, 0) / sorted.length * 100);
  html += `<div class="results-summary">
    <span>${sorted.length} sign${sorted.length !== 1 ? 's' : ''} found</span>
    <span>avg ${avg}%</span>
  </div>`;

  el.innerHTML = html;

  // Wire speak buttons AFTER innerHTML is set
  sorted.forEach((d, i) => {
    const btn = document.getElementById(`speak${i}`);
    if (btn) btn.addEventListener('click', () => speakKhmer(d.sign_kh, btn));
  });

  // Auto-speak top result
  if (document.getElementById('voiceToggle').checked && sorted.length > 0) {
    setTimeout(() => speakKhmer(sorted[0].sign_kh, document.getElementById('speak0')), 700);
  }
}

function renderError(msg) {
  document.getElementById('resultsContent').innerHTML =
    `<div class="no-detect" style="color:var(--danger)">⚠️ ${esc(msg)}</div>`;
}

function clearResults() {
  document.getElementById('resultsContent').innerHTML = `
    <div class="results-empty">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <p>No detections yet</p>
      <span>Upload or capture an image to begin</span>
    </div>`;
}

function showLoading(v) {
  document.getElementById('loadingOverlay').style.display = v ? 'flex' : 'none';
}

// ── TTS ───────────────────────────────────────────────────────────────────────
function speakKhmer(text, btn) {
  if (!('speechSynthesis' in window)) {
    alert('Speech synthesis not supported in this browser.');
    return;
  }

  speechSynthesis.cancel();
  document.querySelectorAll('.btn-speak').forEach(b => b.classList.remove('speaking'));

  if (activeUtt && activeUtt._text === text) {
    activeUtt = null;
    return; // toggle off
  }

  const u = new SpeechSynthesisUtterance(text);
  u._text = text;
  u.lang  = 'km-KH';
  u.rate  = 0.85;
  u.pitch = 1;

  const voices  = speechSynthesis.getVoices();
  const khVoice = voices.find(v => v.lang.startsWith('km') || v.name.toLowerCase().includes('khmer'));
  if (khVoice) u.voice = khVoice;

  u.onstart = () => { if (btn) btn.classList.add('speaking'); };
  u.onend   = () => { if (btn) btn.classList.remove('speaking'); activeUtt = null; };
  u.onerror = () => { if (btn) btn.classList.remove('speaking'); activeUtt = null; };

  activeUtt = u;
  speechSynthesis.speak(u);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}
function confColor(c) {
  return c >= 0.80 ? '#4ae8a0' : c >= 0.50 ? '#5b8dee' : '#e85c5c';
}