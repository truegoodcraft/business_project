import { apiGet, apiPost } from '../token.js';
export async function mountSettings(el){
  el.innerHTML = `
    <h2>Settings</h2>
    <div>
      <label>Writes:</label>
      <button class="btn" id="writesBtn">toggle</button>
      <span id="writesLabel"></span>
    </div>
  `;
  const btn = el.querySelector('#writesBtn');
  const lab = el.querySelector('#writesLabel');
  async function sync(){
    const s = await apiGet('/dev/writes');
    lab.textContent = s.enabled ? 'enabled' : 'disabled';
  }
  btn.onclick = async ()=>{
    const s = await apiGet('/dev/writes');
    await apiPost('/dev/writes', { enabled: !s.enabled });
    await sync();
  };
  sync();
}
