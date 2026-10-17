const $ = (id) => document.getElementById(id);
const sum = (log, type) => log.reduce((a, e) => a + (e.type === type ? e.n : 0), 0);
function show() {
  chrome.storage.local.get(['email', 'password', 'log'], ({ email, password, log = [] }) => {
    $('email').value = email || '';
    $('password').placeholder = password ? 'Password saved ✓ (type to replace)' : 'MDI password';
    const rows = [['Refreshes', 'refresh'], ['New assigned encounters', 'new'], ['Automatic re-logins', 'login']];
    $('stats').innerHTML = rows.map(([label, type]) => `<tr><td>${label}</td><td>${sum(log.filter((e) => Date.now() - e.t < 864e5), type)}</td></tr>`).join('');
  });
}
$('save').onclick = () => {
  const v = { email: $('email').value.trim() };
  if ($('password').value) v.password = $('password').value; // empty = keep the saved one
  chrome.storage.local.set(v, () => { $('password').value = ''; $('msg').textContent = 'Saved.'; show(); });
};
$('clear').onclick = () => chrome.storage.local.remove(['email', 'password'], () => { $('msg').textContent = 'Cleared.'; show(); });
show();
