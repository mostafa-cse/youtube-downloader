function stripAnsi(s){
  if(!s) return s;
  s = String(s);
  s = s.replace(/\x1b\[[0-9;]*[A-Za-z]/g,'');
  s = s.replace(/\[[0-9;]*[mGKHFJABCDsu]/g,'');
  s = s.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g,'');
  return s.trim();
}

let curFolder='', poll=null, autoRefresh=null, curTid=null, hostOS='';

function setupBrowserOptions(sys){
  hostOS = sys || '';
}

fetch('/get-system-info').then(r=>r.json()).then(d=>{
  curFolder = d.dir||'';
  document.getElementById('folderDisp').textContent = curFolder;
  setupBrowserOptions(d.system);
  loadFiles();
}).catch(()=>{
  fetch('/get-dir').then(r=>r.json()).then(d=>{
    curFolder = d.dir||'';
    document.getElementById('folderDisp').textContent = curFolder;
    setupBrowserOptions(d.system);
    loadFiles();
  });
});

function pickFolder(){
  fetch('/pick-folder',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.success && d.folder){
      curFolder = d.folder;
      const el = document.getElementById('folderDisp');
      el.textContent = d.folder;
      el.classList.add('ok');
      loadFiles();
      appendLog({time:new Date().toLocaleTimeString('en-GB'),level:'INFO',msg:'Save location changed to: '+d.folder});
    } else {
      appendLog({time:new Date().toLocaleTimeString('en-GB'),level:'INFO',msg:'Folder selection was cancelled or dialog unavailable.'});
    }
  }).catch(()=>{
    appendLog({time:new Date().toLocaleTimeString('en-GB'),level:'WARN',msg:'Unable to reach server for folder picker.'});
  });
}

function updateUrlBadge(val){
  const badge = document.getElementById('urlBadge');
  if(!badge) return;
  const v = (val || '').trim().toLowerCase();
  if(!v){
    badge.style.display = 'none';
    return;
  }
  if(v.includes('playlist?list=') || (v.includes('list=') && !v.includes('watch?v='))){
    badge.textContent = '📋 Playlist';
    badge.style.display = 'inline-block';
    badge.style.color = '#38bdf8';
  } else if(v.includes('watch?v=') && v.includes('list=')){
    badge.textContent = '🎬 Video in Playlist';
    badge.style.display = 'inline-block';
    badge.style.color = '#a78bfa';
  } else if(v.includes('watch?v=') || v.includes('youtu.be/') || v.includes('shorts/')){
    badge.textContent = '🎬 Single Video';
    badge.style.display = 'inline-block';
    badge.style.color = '#34d399';
  } else if(v.startsWith('http://') || v.startsWith('https://')){
    badge.textContent = '🔗 URL';
    badge.style.display = 'inline-block';
    badge.style.color = '#cbd5e1';
  } else {
    badge.style.display = 'none';
  }
}

function onUrl(el){
  document.getElementById('xBtn').style.display = el.value ? 'flex' : 'none';
  updateUrlBadge(el.value);
}

function clearUrl(){
  const i=document.getElementById('urlInput');
  i.value=''; i.focus();
  document.getElementById('xBtn').style.display='none';
  updateUrlBadge('');
}

async function pasteFromClipboard(){
  try {
    if(navigator.clipboard && navigator.clipboard.readText){
      const text = await navigator.clipboard.readText();
      if(text){
        const el = document.getElementById('urlInput');
        el.value = text.trim();
        onUrl(el);
        el.focus();
      }
    } else {
      document.getElementById('urlInput').focus();
    }
  } catch(e) {
    document.getElementById('urlInput').focus();
  }
}

document.addEventListener('keydown', function(e){
  if(e.key === 'Enter' && document.activeElement && document.activeElement.id === 'urlInput'){
    startDownload();
  }
});

function onFormatChange(){
  const ft = g('ft');
  const rg = document.getElementById('resGroup');
  const rl = document.getElementById('resLbl');
  if(!rg || !rl) return;
  if(ft === 'mp3' || ft === 'm4a'){
    rg.style.opacity = '0.35';
    rg.style.pointerEvents = 'none';
    rl.textContent = 'Resolution (Audio Only - 320kbps)';
  } else {
    rg.style.opacity = '1';
    rg.style.pointerEvents = 'auto';
    rl.textContent = 'Resolution / Quality';
  }
}

function clearLog(){
  const tb = document.getElementById('termBody');
  if(!tb) return;
  tb.innerHTML = '<div class="tl"><span class="tl-t">[--:--:--]</span><span class="tl-k tag-INFO">INFO</span><span class="tl-m msg-INFO">Console cleared. Paste a URL and click Download Now.</span></div><span class="cursor" id="cursor"></span>';
}
document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('input[name="ft"]').forEach(r=>{
    r.addEventListener('change', onFormatChange);
  });
});

function g(n){ return document.querySelector(`input[name="${n}"]:checked`)?.value||''; }

function cancelDownload(){
  if(!curTid) return;
  fetch('/cancel/'+curTid,{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.success){
      clearInterval(poll); poll=null;
      setBadge('s-err','Cancelled');
      resetBtn(); showCancelBtn(false); showProg(false); hideSpeedWidget(); stopAutoRefresh();
      appendLog({time:new Date().toLocaleTimeString('en-GB'),level:'ERROR',msg:'Download cancelled by user.'});
    }
  });
}

function startDownload(){
  let url=document.getElementById('urlInput').value.trim();
  if(!url){
    const i=document.getElementById('urlInput');
    i.style.borderColor='rgba(230,0,0,.5)';
    i.style.boxShadow='0 0 0 3px rgba(230,0,0,.1)';
    setTimeout(()=>{ i.style.borderColor=''; i.style.boxShadow=''; },700);
    return;
  }
  if(!url.startsWith('http://') && !url.startsWith('https://')){
    url = 'https://' + url;
    document.getElementById('urlInput').value = url;
  }
  const btn=document.getElementById('dlBtn');
  btn.disabled=true; btn.textContent='Starting…';
  showCancelBtn(true); setBadge('s-dl','Downloading');
  clearTerminal(); showProg(true); setProgWidth(3);
  fetch('/download',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({url, folder:curFolder, browser:'none', quality:g('q'), filetype:g('ft')})
  })
  .then(r=>r.json())
  .then(d=>{ if(d.task_id){ curTid=d.task_id; pollStatus(d.task_id); } else showErr('Failed to start.'); })
  .catch(()=>showErr('Server error.'));
}

function pollStatus(tid){
  let last=0, fp=3;
  if(poll) clearInterval(poll);
  startAutoRefresh();
  poll=setInterval(()=>{
    fetch('/status/'+tid).then(r=>r.json()).then(d=>{
      if(d.log && d.log.length > 0){
        if(d.log.length > last){
          for(let i=last; i<d.log.length; i++){
            if(d.log[i].level !== 'DL'){
              const old = document.getElementById('activeDlRow');
              if(old) old.removeAttribute('id');
            }
            appendLog(d.log[i]);
          }
          last = d.log.length;
        } else if(last > 0 && d.log[last-1].level === 'DL'){
          updateLastLog(d.log[last-1]);
        }
      }
      if(d.status==='downloading'){
        updateSpeedWidget(d);
        if(fp<90){ fp=d.progress>fp?Math.min(d.progress,90):fp+0.8; }
        setProgWidth(fp);
      }
      if(d.status==='done'){
        clearInterval(poll);
        setBadge('s-done','Complete');
        resetBtn(); showCancelBtn(false); setProgWidth(100); hideCursor();
        document.getElementById('sw-pct').textContent = '100%';
        document.getElementById('sw-bar').style.width = '100%';
        document.getElementById('sw-speed').textContent = 'Done';
        document.getElementById('sw-eta').textContent = '0s';
        setTimeout(()=>hideSpeedWidget(), 2500);
        setTimeout(()=>showProg(false),2500);
        loadFiles(); stopAutoRefresh();
      } else if(d.status==='error'||d.status==='cancelled'){
        clearInterval(poll);
        setBadge('s-err',d.status==='cancelled'?'Cancelled':'Failed');
        resetBtn(); showCancelBtn(false); showProg(false); hideCursor();
        hideSpeedWidget(); stopAutoRefresh();
      }
    });
  },1200);
}

function updateSpeedWidget(d){
  const w=document.getElementById('speedWidget');
  w.style.display='block';
  document.getElementById('sw-speed').textContent=stripAnsi(d.speed)||'—';
  document.getElementById('sw-eta').textContent=stripAnsi(d.eta)||'—';
  const pct=stripAnsi(d.percent||'0%').replace('%','').trim();
  document.getElementById('sw-pct').textContent=(pct||'0')+'%';
  document.getElementById('sw-file').textContent=d.current_file||'Fetching info…';
  document.getElementById('sw-bar').style.width=(pct||0)+'%';
  if(d.total>1) document.getElementById('sw-item').textContent=`Item ${d.item} / ${d.total}`;
  else document.getElementById('sw-item').textContent='';
}
function hideSpeedWidget(){ document.getElementById('speedWidget').style.display='none'; }

function clearTerminal(){
  document.getElementById('termBody').innerHTML='<span class="cursor" id="cursor"></span>';
}
function appendLog(e){
  const body=document.getElementById('termBody'), cur=document.getElementById('cursor');
  const row=document.createElement('div'); row.className='tl';
  if(e.level === 'DL') row.id = 'activeDlRow';
  row.innerHTML=`<span class="tl-t">[${e.time}]</span><span class="tl-k tag-${e.level}">${e.level}</span><span class="tl-m msg-${e.level}">${stripAnsi(e.msg)}</span>`;
  if(cur) body.insertBefore(row,cur); else body.appendChild(row);
  body.scrollTop=body.scrollHeight;
}
function updateLastLog(e){
  let row = document.getElementById('activeDlRow');
  if(!row){
    appendLog(e);
    return;
  }
  row.innerHTML=`<span class="tl-t">[${e.time}]</span><span class="tl-k tag-${e.level}">${e.level}</span><span class="tl-m msg-${e.level}">${stripAnsi(e.msg)}</span>`;
}
function hideCursor(){ const c=document.getElementById('cursor'); if(c) c.style.display='none'; }

function setBadge(c,t){
  const b=document.getElementById('badge');
  b.className='badge '+c;
  b.innerHTML='<span class="dot"></span>'+t;
}
function resetBtn(){ const b=document.getElementById('dlBtn'); b.disabled=false; b.textContent='Download Now'; }
function showProg(v){ document.getElementById('prog-wrap').style.display=v?'block':'none'; }
function setProgWidth(w){ document.getElementById('prog-bar').style.width=w+'%'; }
function showCancelBtn(v){
  const cb=document.getElementById('cancelBtn');
  if(cb) cb.style.display=v?'flex':'none';
}
function showErr(m){
  appendLog({time:new Date().toLocaleTimeString('en-GB'),level:'ERROR',msg:m});
  setBadge('s-err','Failed'); resetBtn(); showCancelBtn(false); showProg(false); hideSpeedWidget();
}

function startAutoRefresh(){
  stopAutoRefresh();
  autoRefresh=setInterval(loadFiles,3500);
}
function stopAutoRefresh(){
  if(autoRefresh){ clearInterval(autoRefresh); autoRefresh=null; }
}

const EXT_DOTS={mp4:'mp4',mkv:'mkv',mp3:'mp3',m4a:'m4a',aac:'m4a',webm:'mkv',mov:'mp4'};
let prevCount=-1;

function loadFiles(){
  const folder=curFolder||'';
  fetch('/files?folder='+encodeURIComponent(folder))
  .then(r=>r.json()).then(files=>{
    const list=document.getElementById('flist');
    const countEl=document.getElementById('filesCount');
    const ftypeRow=document.getElementById('ftypeRow');
    if(!list) return;
    if(files.length!==prevCount && prevCount>=0){
      countEl.classList.add('updated');
      setTimeout(()=>countEl.classList.remove('updated'),1800);
    }
    prevCount=files.length;
    countEl.textContent=files.length+' file'+(files.length!==1?'s':'');

    // Populate format badges
    if(ftypeRow){
      if(!files.length){
        ftypeRow.innerHTML='';
      } else {
        const counts={};
        files.forEach(f=>{
          const ext=f.split('.').pop().toUpperCase();
          counts[ext]=(counts[ext]||0)+1;
        });
        ftypeRow.innerHTML=Object.entries(counts)
          .map(([ext,count])=>`<span class="ftype">${count} ${ext}</span>`)
          .join('');
      }
    }

    if(!files.length){
      list.innerHTML='<li class="empty"><div class="empty-icon">🎬</div><div class="empty-sub">No Downloads Yet</div><span>Completed video and audio downloads will be displayed here.</span></li>';
      return;
    }
    list.innerHTML='';
    files.forEach((f,i)=>{
      const ext=f.split('.').pop().toLowerCase();
      const sep = folder.includes('\\') ? '\\' : '/';
      const fp2 = (f.startsWith('/') || /^[A-Za-z]:[\\/]/.test(f)) ? f : (folder ? folder.replace(/[\\/]+$/, '') + sep + f : f);
      const fname=f.includes('/')?f.split('/').pop():(f.includes('\\')?f.split('\\').pop():f);
      const isAudio = ext === 'mp3' || ext === 'm4a' || ext === 'aac' || ext === 'wav' || ext === 'flac';
      const mediaIcon = isAudio ? '🎵' : '🎬';
      const li=document.createElement('li'); li.className='fi';
      li.style.animationDelay=(i*.03)+'s';
      li.innerHTML=`
        <div class="fi-row">
          <span class="fi-idx">${String(i+1).padStart(2,'0')}</span>
          <span class="fi-media-icon">${mediaIcon}</span>
          <div class="fi-meta">
            <div class="fi-name" title="${fname}">${fname}</div>
            <div class="fi-sub">
              <span class="fi-tag fi-tag-${ext}">${ext.toUpperCase()}</span>
            </div>
          </div>
          <button class="fi-open-btn" onclick="openFile(this)">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            <span>Play</span>
          </button>
        </div>`;
      li.querySelector('.fi-open-btn').dataset.path = fp2;
      list.appendChild(li);
    });
  }).catch(err=>console.error('loadFiles error:',err));
}

function openFile(btn){
  const fp = btn.dataset.path;
  if(!fp) return;
  fetch('/open-file?path='+encodeURIComponent(fp))
    .then(r=>r.json())
    .then(d=>{
      if(!d.success){
        // In browser mode or if native launcher is unavailable, fallback to browser download/play
        window.open('/get-file?path='+encodeURIComponent(fp), '_blank');
      }
    })
    .catch(()=>{
      window.open('/get-file?path='+encodeURIComponent(fp), '_blank');
    });
}

function clearHistory(){
  if(!confirm('Clear the download list from view? (Downloaded files on disk will NOT be deleted)')) return;
  fetch('/clear-history',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({folder: curFolder})
  })
  .then(r=>r.json())
  .then(d=>{
    addLog('FILES', `Cleared ${d.cleared || 0} item(s) from view.`, 'done');
    loadFiles();
  })
  .catch(err=>console.error('clearHistory error:', err));
}

let filesVisible=true;
function toggleFiles(){
  filesVisible=!filesVisible;
  const body=document.getElementById('filesBody');
  const icon=document.getElementById('toggleIcon');
  const txt=document.getElementById('toggleTxt');
  if(filesVisible){
    body.classList.remove('collapsed');
    icon.textContent='▾'; txt.textContent='Hide';
  } else {
    body.classList.add('collapsed');
    icon.textContent='▸'; txt.textContent='Show';
  }
}
