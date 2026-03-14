let curFolder = '', poll = null, autoRefresh = null;

// Init
fetch('/get-dir').then(r => r.json()).then(d => {
  curFolder = d.dir;
  document.getElementById('folderDisp').textContent = d.dir;
  loadFiles();
});

// Folder picker
function pickFolder() {
  fetch('/pick-folder', { method: 'POST' }).then(r => r.json()).then(d => {
    if (d.success && d.folder) {
      curFolder = d.folder;
      const el = document.getElementById('folderDisp');
      el.textContent = d.folder; el.classList.add('active');
      loadFiles();
    }
  });
}

// URL helpers
function onUrl(el) { document.getElementById('xBtn').style.display = el.value ? 'block' : 'none'; }
function clearUrl() {
  const i = document.getElementById('urlInput');
  i.value = ''; i.focus();
  document.getElementById('xBtn').style.display = 'none';
}
function g(n) { return document.querySelector(`input[name="${n}"]:checked`)?.value || ''; }

// Start download
function startDownload() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) {
    const i = document.getElementById('urlInput');
    i.style.borderColor = 'rgba(230,0,0,.5)';
    i.style.boxShadow = '0 0 0 3px rgba(230,0,0,.1)';
    setTimeout(() => { i.style.borderColor = ''; i.style.boxShadow = ''; }, 700);
    return;
  }
  const btn = document.getElementById('dlBtn');
  btn.disabled = true; btn.textContent = 'Starting…';
  setBadge('s-dl', 'Downloading');
  clearTerminal();
  showProg(true);
  setProgWidth(3);

  fetch('/download', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, folder: curFolder, browser: g('br'), quality: g('q'), filetype: g('ft') })
  })
    .then(r => r.json())
    .then(d => { if (d.task_id) pollStatus(d.task_id); else showErr('Failed to start.'); })
    .catch(() => showErr('Server error.'));
}

// Poll
function pollStatus(tid) {
  let last = 0, fp = 3;
  startAutoRefresh();
  poll = setInterval(() => {
    fetch('/status/' + tid).then(r => r.json()).then(d => {
      if (d.log && d.log.length > last) {
        for (let i = last; i < d.log.length; i++) appendLog(d.log[i]);
        last = d.log.length;
      }
      // Update speed widget
      if (d.status === 'downloading') {
        updateSpeedWidget(d);
        if (fp < 90) { fp = d.progress > fp ? Math.min(d.progress, 90) : fp + 0.8; }
        setProgWidth(fp);
      }
      if (d.status === 'done') {
        clearInterval(poll);
        setBadge('s-done', 'Complete');
        resetBtn(); setProgWidth(100); hideCursor();
        hideSpeedWidget();
        setTimeout(() => showProg(false), 2500);
        loadFiles();
        stopAutoRefresh();
      } else if (d.status === 'error') {
        clearInterval(poll);
        setBadge('s-err', 'Failed');
        resetBtn(); showProg(false); hideCursor();
        hideSpeedWidget();
        stopAutoRefresh();
      }
    });
  }, 1200);
}

// Speed widget
function updateSpeedWidget(d) {
  const w = document.getElementById('speedWidget');
  w.style.display = 'block';
  const spd = d.speed || '—';
  const eta = d.eta || '—';
  const pct = (d.percent || '0%').replace('%','').trim();
  const file = d.current_file || '';
  const item = d.item || 0;
  const total = d.total || 0;
  document.getElementById('sw-speed').textContent = spd;
  document.getElementById('sw-eta').textContent = eta;
  document.getElementById('sw-pct').textContent = (pct||'0') + '%';
  document.getElementById('sw-file').textContent = file || 'Fetching info…';
  document.getElementById('sw-bar').style.width = (pct||0) + '%';
  if (total > 1) document.getElementById('sw-item').textContent = `Item ${item} / ${total}`;
}
function hideSpeedWidget() { document.getElementById('speedWidget').style.display = 'none'; }

// Terminal
function clearTerminal() {
  document.getElementById('termBody').innerHTML = '<span class="cursor" id="cursor"></span>';
}
function appendLog(e) {
  const body = document.getElementById('termBody'), cur = document.getElementById('cursor');
  const row = document.createElement('div'); row.className = 'tl';
  row.innerHTML = `<span class="tl-t">[${e.time}]</span><span class="tl-k tag-${e.level}">${e.level}</span><span class="tl-m msg-${e.level}">${e.msg}</span>`;
  if (cur) body.insertBefore(row, cur); else body.appendChild(row);
  body.scrollTop = body.scrollHeight;
}
function hideCursor() { const c = document.getElementById('cursor'); if (c) c.style.display = 'none'; }

// Badge / button helpers
function setBadge(c, t) {
  const b = document.getElementById('badge');
  b.className = 'badge ' + c;
  b.innerHTML = '<span class="dot"></span>' + t;
}
function resetBtn() { const b = document.getElementById('dlBtn'); b.disabled = false; b.textContent = 'Download Now'; }
function showProg(v) { document.getElementById('prog-wrap').style.display = v ? 'block' : 'none'; }
function setProgWidth(w) { document.getElementById('prog-bar').style.width = w + '%'; }
function showErr(m) {
  appendLog({ time: new Date().toLocaleTimeString('en-GB'), level: 'ERROR', msg: m });
  setBadge('s-err', 'Failed'); resetBtn(); showProg(false); hideSpeedWidget();
}

// Auto-refresh files
function startAutoRefresh() {
  stopAutoRefresh();
  autoRefresh = setInterval(loadFiles, 3500);
}
function stopAutoRefresh() {
  if (autoRefresh) { clearInterval(autoRefresh); autoRefresh = null; }
  const dot = document.getElementById('refreshDot');
  if (dot) dot.style.display = 'none';
}

// Load files
const EXT_DOTS = { mp4:'mp4', mkv:'mkv', mp3:'mp3', m4a:'m4a' };
let prevCount = -1;

function loadFiles() {
  fetch('/files?folder=' + encodeURIComponent(curFolder))
    .then(r => r.json()).then(files => {
      const list = document.getElementById('flist');
      const countEl = document.getElementById('filesCount');
      const statsEl = document.getElementById('fileStats');

      // Animate count if changed
      if (files.length !== prevCount && prevCount >= 0) {
        countEl.classList.add('updated');
        setTimeout(() => countEl.classList.remove('updated'), 1800);
      }
      prevCount = files.length;
      countEl.textContent = files.length + ' file' + (files.length !== 1 ? 's' : '');

      if (!files.length) {
        list.innerHTML = '<li class="empty"><div class="empty-label">No Downloads Yet</div>Start a download above to see files here</li>';
        statsEl.innerHTML = ''; return;
      }

      // Stats by type
      const ct = {};
      files.forEach(f => { const e = f.split('.').pop().toLowerCase(); ct[e] = (ct[e]||0)+1; });
      statsEl.innerHTML = Object.entries(ct)
        .map(([e,n]) => `<span class="fstat">${n} ${e.toUpperCase()}</span>`).join('');

      list.innerHTML = '';
      files.forEach((f, i) => {
        const ext = f.split('.').pop().toLowerCase();
        const fp2 = curFolder + '/' + f;
        const li = document.createElement('li'); li.className = 'fi';
        li.style.animationDelay = (i * .03) + 's';
        li.innerHTML = `
          <span class="fi-idx">${String(i+1).padStart(2,'0')}</span>
          <span class="fi-dot ${EXT_DOTS[ext]||'other'}"></span>
          <div class="fi-meta">
            <div class="fi-name" title="${f}">${f}</div>
            <span class="fi-tag">${ext}</span>
          </div>
          <a href="/get-file?path=${encodeURIComponent(fp2)}" class="fi-dl" download>Save</a>`;
        list.appendChild(li);
      });

      // Show auto-refresh dot if downloading
      const dot = document.getElementById('refreshDot');
      if (dot && autoRefresh) dot.style.display = 'inline-block';
    });
}
