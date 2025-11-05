import { apiGet, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';

const LS_KEY = 'contacts.customers.v1';
const loadCustomers = () => { try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); } catch { return []; } };
const saveCustomers = (arr) => localStorage.setItem(LS_KEY, JSON.stringify(arr));

export async function mountVendors(container) {
  // --- BEGIN SPEC-1 BODY ---
  container.innerHTML = '';
  container.style.background = '#0f1115';
  container.style.color = '#e5e7eb';
  container.style.padding = '16px';
  container.style.borderRadius = '12px';

  let mode = 'vendor'; // 'vendor' | 'customer'

  // Header with toggle + New button
  const header = document.createElement('div');
  header.style.display = 'flex';
  header.style.alignItems = 'center';
  header.style.gap = '10px';
  header.style.marginBottom = '12px';

  const title = document.createElement('h2');
  title.textContent = 'Contacts';
  title.style.margin = '0';

  const toggle = document.createElement('div');
  toggle.style.display = 'inline-flex';
  toggle.style.border = '1px solid #2b3246';
  toggle.style.borderRadius = '10px';
  function mkToggleBtn(txt, val) {
    const b = document.createElement('button');
    b.textContent = txt;
    b.style.padding = '6px 10px';
    b.style.border = '0';
    b.style.cursor = 'pointer';
    b.style.background = val === mode ? '#23293a' : 'transparent';
    b.style.color = '#e5e7eb';
    b.onclick = () => { mode = val; renderToggle(); };
    return b;
  }
  function renderToggle() {
    toggle.innerHTML = '';
    toggle.append(mkToggleBtn('Vendor','vendor'), mkToggleBtn('Customer','customer'));
    loadAndRender();
  }
  renderToggle();

  const newBtn = document.createElement('button');
  newBtn.textContent = 'New';
  styleBtn(newBtn);

  header.append(title, toggle, newBtn);

  // Table
  const table = document.createElement('table');
  table.style.width = '100%';
  table.style.borderCollapse = 'separate';
  table.style.borderSpacing = '0';
  table.style.background = '#111318';
  table.style.borderRadius = '10px';
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Name</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Type</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Contact</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Actions</th>
    </tr>`;
  const tbody = document.createElement('tbody');
  table.append(thead, tbody);

  // Modal
  const modal = createModal();
  document.body.appendChild(modal.root);

  newBtn.onclick = () => {
    modal.open({
      id: null,
      name: '',
      contact: '',
      email: '',
      phone: '',
      notes: '',
      _kind: mode
    });
  };

  modal.onSubmit = async (m) => {
    if ((m._kind || mode) === 'vendor') {
      await ensureToken();
      const payload = { name: m.name.trim() };
      if (m.contact && m.contact.trim()) payload.contact = m.contact.trim();
      try { await apiPost('/app/vendors', payload); } catch {}
    } else {
      const list = loadCustomers();
      list.push({
        id: `c-${crypto.randomUUID()}`,
        name: m.name.trim(),
        contact: (m.contact || '').trim() || null,
        email: (m.email || '').trim() || null,
        phone: (m.phone || '').trim() || null,
        notes: (m.notes || '').trim() || null
      });
      saveCustomers(list);
    }
    modal.close();
    await loadAndRender();
  };

  container.append(header, table);

  async function loadAndRender() {
    // vendors from server
    let vendors = [];
    try {
      vendors = await apiGet('/app/vendors'); // [{id,name}]
    } catch {
      vendors = [];
    }
    // customers from local storage
    const customers = loadCustomers(); // [{id,name,contact,email,phone,notes}]
    renderRows(vendors, customers);
  }

  function renderRows(vendors, customers) {
    tbody.innerHTML = '';
    const rows = [
      ...vendors.map(v => ({ id: v.id, name: v.name, contact: v.contact || '', _type: 'Vendor', _local: false })),
      ...customers.map(c => ({ id: c.id, name: c.name, contact: c.contact || '', _type: 'Customer', _local: true, _full: c }))
    ];
    for (const r of rows) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="padding:10px;border-top:1px solid #222733">${esc(r.name)}</td>
        <td style="padding:10px;border-top:1px solid #222733">${r._type}</td>
        <td style="padding:10px;border-top:1px solid #222733">${esc(r.contact || '')}</td>
        <td style="padding:10px;border-top:1px solid #222733">
          <div style="display:flex;gap:8px;">
            <button class="edit">Edit</button>
            <button class="del">Delete</button>
          </div>
        </td>`;
      tr.querySelectorAll('button').forEach(styleBtn);

      tr.querySelector('.edit').onclick = () => {
        if (r._local) {
          modal.open({ ...r._full, _kind: 'customer' });
        } else {
          // vendors: only name/contact allowed. If edit not supported server-side, disable edit.
          modal.open({ id: r.id, name: r.name, contact: r.contact || '', _kind: 'vendor' });
        }
      };

      tr.querySelector('.del').onclick = async () => {
        if (!confirm(`Delete ${r.name}?`)) return;
        if (r._local) {
          const list = loadCustomers().filter(x => x.id !== r.id);
          saveCustomers(list);
          renderRows(vendors, list);
        } else {
          // Only attempt if DELETE exists; ignore 404
          try {
            await ensureToken();
            await apiDelete(`/app/vendors/${r.id}`);
          } catch {}
          await loadAndRender();
        }
      };

      tbody.appendChild(tr);
    }
  }

  await loadAndRender();
  // --- END SPEC-1 BODY ---
}

function esc(s){ return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function styleBtn(btn){
  btn.style.background = '#23293a';
  btn.style.color = '#e5e7eb';
  btn.style.border = '1px solid #2b3246';
  btn.style.padding = '6px 10px';
  btn.style.borderRadius = '10px';
  btn.style.cursor = 'pointer';
  btn.onmouseenter = () => btn.style.background = '#2a3146';
  btn.onmouseleave = () => btn.style.background = '#23293a';
}
function createModal(){
  const root = document.createElement('div');
  root.style.position='fixed'; root.style.inset='0'; root.style.display='none';
  root.style.alignItems='center'; root.style.justifyContent='center';
  root.style.background='rgba(0,0,0,0.55)'; root.style.zIndex='999';
  const panel=document.createElement('div');
  panel.style.background='#0f1115'; panel.style.border='1px solid #2b3246';
  panel.style.borderRadius='12px'; panel.style.padding='16px';
  panel.style.minWidth='420px'; panel.style.maxWidth='560px';
  panel.addEventListener('click', e=>e.stopPropagation());

  const title=document.createElement('h3'); title.textContent='Contact'; title.style.margin='0 0 10px 0';

  const form=document.createElement('form'); form.style.display='grid'; form.style.gridTemplateColumns='1fr 1fr'; form.style.gap='10px';
  const fields=[
    { key:'name', label:'Name', type:'text', required:true },
    { key:'contact', label:'Contact', type:'text', required:false },
    { key:'email', label:'Email', type:'email', required:false },
    { key:'phone', label:'Phone', type:'text', required:false },
    { key:'notes', label:'Notes', type:'textarea', required:false, span:true }
  ];
  const inputs={};
  for(const field of fields){
    const { key, label, type, required, span } = field;
    const wrap=document.createElement('label'); wrap.style.display='grid'; wrap.style.gap='6px'; wrap.style.fontSize='12px';
    wrap.textContent=label;
    const input=type==='textarea'?document.createElement('textarea'):document.createElement('input');
    if(type!=='textarea'){ input.type=type; }
    input.name=key; input.required=!!required;
    input.style.background='#111318'; input.style.color='#e5e7eb'; input.style.border='1px solid #2b3246';
    input.style.borderRadius='10px'; input.style.padding='8px'; input.style.width='100%'; input.style.boxSizing='border-box';
    if(type==='textarea'){ input.style.minHeight='80px'; input.style.resize='vertical'; }
    if(span){ wrap.style.gridColumn='1 / -1'; }
    inputs[key]=input; wrap.appendChild(input); form.appendChild(wrap);
  }

  const actions=document.createElement('div'); actions.style.display='flex'; actions.style.gap='10px'; actions.style.justifyContent='flex-end'; actions.style.marginTop='10px';
  const cancel=document.createElement('button'); cancel.type='button'; cancel.textContent='Cancel'; styleBtn(cancel);
  const save=document.createElement('button'); save.type='submit'; save.textContent='Save'; styleBtn(save);
  actions.append(cancel,save);
  // span actions across form columns and place inside the form
  actions.style.gridColumn='1 / -1';
  form.append(actions);
  panel.append(title,form); root.appendChild(panel);

  const api={
    root,
    open(data){ api._current=data||{_kind:'vendor'}; for(const k in inputs){ inputs[k].value=data?.[k]??''; } root.style.display='flex'; setTimeout(()=>document.addEventListener('keydown', escCloser)); },
    close(){ root.style.display='none'; document.removeEventListener('keydown', escCloser); },
    onSubmit:null
  };
  function escCloser(e){ if(e.key==='Escape') api.close(); }
  root.addEventListener('click', ()=>api.close());
  cancel.addEventListener('click', ()=>api.close());
  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const model={ ...api._current };
    for(const k in inputs){ model[k]=inputs[k].value; }
    if(!model.name || !model.name.trim()) return;
    if(typeof api.onSubmit==='function'){ await api.onSubmit(model); }
  });
  return api;
}

export default mountVendors;
