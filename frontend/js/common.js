const API_BASE = localStorage.getItem('placifyApiBase') || 'http://127.0.0.1:8000';
const token = () => localStorage.getItem('placifyToken');
const user = () => { try { return JSON.parse(localStorage.getItem('placifyUser') || 'null'); } catch { return null; } };
async function api(path, options={}) {
  const headers = {'Content-Type':'application/json', ...(options.headers||{})};
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(`${API_BASE}${path}`, {...options, headers});
  let data={}; try { data=await response.json(); } catch {}
  if (!response.ok) throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  return data;
}
function showMessage(el, text, kind='error') { if(!el)return; el.textContent=text; el.className=`alert ${kind}`; }
function hideMessage(el) { if(el){el.textContent='';el.className='alert hidden';} }
function requireRole(role) { const u=user(); if(!token() || !u || u.role!==role){ location.href=role==='admin'?'admin-login.html':'login.html'; return false;} return true; }
function setupShell() { const u=user(); const name=document.getElementById('sideName'); if(name&&u) name.textContent=u.name; const avatar=document.getElementById('avatar'); if(avatar&&u) avatar.textContent=(u.name||'S').trim().charAt(0).toUpperCase(); const logout=document.getElementById('logout'); if(logout) logout.addEventListener('click',async()=>{try{await api('/api/auth/logout',{method:'POST'});}catch{} localStorage.removeItem('placifyToken');localStorage.removeItem('placifyUser');location.href='login.html';}); }
function esc(value){return String(value??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fieldValue(id){const el=document.getElementById(id); if(!el)return null; if(el.type==='number')return el.value===''?null:Number(el.value); return el.value;}
function fmtDate(v){if(!v)return '—';const d=new Date(v.replace(' ','T')+'Z');return Number.isNaN(d.getTime())?v:d.toLocaleDateString();}
