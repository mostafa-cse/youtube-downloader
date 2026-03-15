function stripAnsi(s){
  if(!s) return s;
  s = String(s);
  s = s.replace(/\x1b\[[0-9;]*[A-Za-z]/g,'');
  s = s.replace(/\[[0-9;]*[mGKHFJABCDsu]/g,'');
  s = s.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g,'');
  return s.trim();
}

let curFolder='', poll=null, autoRefresh=null, curTid=null;

fetch('/get-dir').then(r=>r.json()).then(d=>{
  curFolder = d.dir||'';
  document.getElementById('folderDisp').textContent = curFolder;
  loadFiles();
});

function pickFolder(){
  fetch('/pick-folder',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.success && d.folder){
      curFolder = d.folder;
      const el = document.getElementById('folderDisp');
      el.textContent = d.folder;
      el.classList.add('ok');
      loadFiles();
    }
  });
}

function onUrl(el){ document.getElementById('xBtn').style.display=el.value?'block':'none'; }
function clearUrl(){
  const i=document.getElementById('urlInput');
  i.value=''; i.focus();
  document.getElementById('xBtn').style.display='none';
}
function g(n){ return document.querySelector(`input[name="${n}"]:checked`)?.value||''; }

function cancelDownload(){
  if(!curTid) return;
  fetch('/cancel/'+curTid,{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.success){
      clearInterval(poll); poll=null;
      setBadge('s-err','Cancelled');
      resetBtn(); showProg(false); hideSpeedWidget(); stopAutoRefresh();
      appendLog({time:new Date().toLocaleTimeString('en-GB'),level:'ERROR',msg:'Download cancelled by user.'});
    }
  });
}

function startDownload(){
  const url=document.getElementById('urlInput').value.trim();
  if(!url){
    const i=document.getElementById('urlInput');
    i.style.borderColor='rgba(230,0,0,.5)';
    i.style.boxShadow='0 0 0 3px rgba(230,0,0,.1)';
    setTimeout(()=>{ i.style.borderColor=''; i.style.boxShadow=''; },700);
    return;
  }
  const btn=document.getElementById('dlBtn');
  btn.disabled=true; btn.textContent='Starting…';
  showCancelBtn(true); setBadge('s-dl','Downloading');
  clearTerminal(); showProg(true); setProgWidth(3);
  fetch('/download',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({url, folder:curFolder, browser:g('br'), quality:g('q'), filetype:g('ft')})
  })
  .then(r=>r.json())
  .then(d=>{ if(d.task_id){ curTid=d.task_id; pollStatus(d.task_id); } else showErr('Failed to start.'); })
  .catch(()=>showErr('Server error.'));
}

function pollStatus(tid){
  let last=0, fp=3;
  startAutoRefresh();
  poll=setInterval(()=>{
    fetch('/status/'+tid).then(r=>r.json()).then(d=>{
      if(d.log && d.log.length>last){
        for(let i=last;i<d.log.length;i++) appendLog(d.log[i]);
        last=d.log.length;
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
        hideSpeedWidget(); setTimeout(()=>showProg(false),2500);
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
}
function hideSpeedWidget(){ document.getElementById('speedWidget').style.display='none'; }

function clearTerminal(){
  document.getElementById('termBody').innerHTML='<span class="cursor" id="cursor"></span>';
}
function appendLog(e){
  const body=document.getElementById('termBody'), cur=document.getElementById('cursor');
  const row=document.createElement('div'); row.className='tl';
  row.innerHTML=`<span class="tl-t">[${e.time}]</span><span class="tl-k tag-${e.level}">${e.level}</span><span class="tl-m msg-${e.level}">${stripAnsi(e.msg)}</span>`;
  if(cur) body.insertBefore(row,cur); else body.appendChild(row);
  body.scrollTop=body.scrollHeight;
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

const EXT_DOTS={mp4:'mp4',mkv:'mkv',mp3:'mp3',m4a:'m4a'};
let prevCount=-1;

function loadFiles(){
  const folder=curFolder||'';
  fetch('/files?folder='+encodeURIComponent(folder))
  .then(r=>r.json()).then(files=>{
    const list=document.getElementById('flist');
    const countEl=document.getElementById('filesCount');
    if(!list) return;
    if(files.length!==prevCount && prevCount>=0){
      countEl.classList.add('updated');
      setTimeout(()=>countEl.classList.remove('updated'),1800);
    }
    prevCount=files.length;
    countEl.textContent=files.length+' file'+(files.length!==1?'s':'');
    if(!files.length){
      list.innerHTML='<li class="empty"><div class="empty-label">No Downloads Yet</div>Start a download above to see files here</li>';
      return;
    }
    list.innerHTML='';
    files.forEach((f,i)=>{
      const ext=f.split('.').pop().toLowerCase();
      const fp2=f.startsWith('/')?f:folder+'/'+f;
      const fname=f.includes('/')?f.split('/').pop():f;
      const li=document.createElement('li'); li.className='fi';
      li.style.animationDelay=(i*.03)+'s';
      li.innerHTML=`
        <div class="fi-row">
          <span class="fi-idx">${String(i+1).padStart(2,'0')}</span>
          <span class="fi-dot ${EXT_DOTS[ext]||'other'}"></span>
          <div class="fi-meta">
            <div class="fi-name" title="${fname}">${fname}</div>
            <span class="fi-tag">${ext.toUpperCase()}</span>
          </div>
          <button class="fi-open-btn" onclick="openFile(this)">⬡ Open</button>
        </div>`;
      li.querySelector('.fi-open-btn').dataset.path = fp2;
      list.appendChild(li);
    });
  }).catch(err=>console.error('loadFiles error:',err));
}

function openFile(btn){
  const fp = btn.dataset.path;
  fetch('/open-file?path='+encodeURIComponent(fp))
    .then(r=>r.json())
    .then(d=>{ if(!d.success) alert('Could not open: '+fp); });
}

function clearHistory(){
  fetch('/clear-history',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({folder: curFolder})
  })
  .then(r=>r.json())
  .then(()=>loadFiles());
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
