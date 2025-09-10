// app.js (cliente)
const API_BASE = (location.origin); // asume backend en el mismo host (ajusta si es necesario)

const $ = id => document.getElementById(id);
const tbody = document.querySelector('#agentTable tbody');
const gStatus = $('globalStatus');
const logWin = $('logWindow');

async function api(path, opts){
  try{
    const r = await fetch(API_BASE + path, opts);
    if(!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return await r.json();
  } catch(e){
    appendLog(`API error ${path}: ${e}`);
    throw e;
  }
}

function appendLog(msg){
  const ts = new Date().toISOString();
  logWin.textContent = `${ts} ${msg}\n` + logWin.textContent;
}

async function refreshStatus(){
  try{
    gStatus.textContent = "Consultando agentes...";
    const s = await api('/api/status');
    gStatus.textContent = JSON.stringify(s.summary, null, 2);
    populateAgents(s.agents || []);
  } catch(e){
    gStatus.textContent = "Error al consultar estado.";
  }
}

function populateAgents(list){
  tbody.innerHTML = '';
  for(const a of list){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${a.host}</td><td>${a.os}</td><td>${a.last_seen}</td><td>${a.state}</td>
      <td>
        <button onclick="doAction('${a.host}','scan')">Scan</button>
        <button onclick="doAction('${a.host}','repair')">Repair</button>
      </td>`;
    tbody.appendChild(tr);
  }
}

async function doAction(host, act){
  appendLog(`Solicitando ${act} al agente ${host}`);
  try{
    const r = await api('/api/agent/action', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({host, action:act})
    });
    appendLog(`Acción enviada: ${r.result}`);
    refreshStatus();
  } catch(e){
    appendLog(`Error acción: ${e}`);
  }
}

$('refreshBtn').onclick = refreshStatus;
$('scanAll').onclick = ()=>api('/api/scanall',{method:'POST'}).then(r=>appendLog('ScanAll: '+r.result)).catch(e=>appendLog(e));
$('repairAll').onclick = ()=>api('/api/repairall',{method:'POST'}).then(r=>appendLog('RepairAll: '+r.result)).catch(e=>appendLog(e));
$('rotateNow').onclick = ()=>api('/api/rotate',{method:'POST'}).then(r=>appendLog('Rotate: '+r.result)).catch(e=>appendLog(e));
$('syncRepos').onclick = async ()=>{
  const u = $('ghUser').value.trim();
  if(!u) return appendLog('Escribe usuario/org de GitHub');
  const r = await api('/api/syncrepos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:u})});
  appendLog('Sync: '+r.result);
  $('repoResult').textContent = JSON.stringify(r.repos || [], null, 2);
  refreshStatus();
};

refreshStatus();
