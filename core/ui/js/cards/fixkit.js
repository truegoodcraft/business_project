export async function mountFixKit(root){
  root.innerHTML = `
    <h2>FixKit</h2>
    <ul>
      <li><a href="#/fixkit/vendors">Vendors</a></li>
      <li><a href="#/fixkit/items">Items</a></li>
      <li><a href="#/fixkit/tasks">Tasks</a></li>
    </ul>
  `;
}
