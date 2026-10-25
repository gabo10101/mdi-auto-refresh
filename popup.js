const $ = (id) => document.getElementById(id);
const sum = (log, type) => log.reduce((a, e) => a + (e.type === type ? e.n : 0), 0);
const LIST = '/tabs/cases/list/';
const DAYS = { '24 h': 1, '7 days': 7, '30 days': 30 };
const usd = (n) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
function show() {
  chrome.storage.local.get(['email', 'password', 'log', 'price', 'period'], ({ email, password, log = [], price = 0, period = '24 h' }) => {
    $('email').value = email || '';
    $('password').placeholder = password ? 'Password saved ✓ (type to replace)' : 'MDI password';
    $('autostate').textContent = email && password ? 'on ✓' : 'off';
    $('auto').open = !(email && password); // set up once, then it stays folded away
    $('price').value = price || '';
    $('period').innerHTML = Object.keys(DAYS).map((p) => `<button class="${p === period ? 'on' : ''}">${p}</button>`).join('');
    const recent = log.filter((e) => Date.now() - e.t < DAYS[period] * 864e5);
    const cases = sum(recent, 'new'), logins = sum(recent, 'login');
    $('stats').innerHTML = `<div class="tile"><b>${cases}</b>New cases</div>`
      + `<div class="tile money"><b>${price ? usd(cases * price) : '–'}</b>${price ? 'Est. earnings' : 'Add your pay below'}</div>`;
    $('logins').textContent = logins ? `${logins} automatic re-login${logins > 1 ? 's' : ''}` : '';
  });
}
$('save').onclick = () => {
  const v = { email: $('email').value.trim() };
  if ($('password').value) v.password = $('password').value; // empty = keep the saved one
  chrome.storage.local.set(v, () => { $('password').value = ''; $('msg').textContent = 'Saved.'; show(); });
};
$('period').onclick = (e) => e.target.tagName === 'BUTTON' && chrome.storage.local.set({ period: e.target.textContent }, show);
$('price').onchange = () => chrome.storage.local.set({ price: Math.max(0, +$('price').value || 0) }, show);
$('clear').onclick = () => chrome.storage.local.remove(['email', 'password'], () => { $('msg').textContent = 'Cleared.'; show(); });

// Status: green when every Encounters list is refreshing, red with the reason when something needs a person.
async function showStatus() {
  const tabs = await chrome.tabs.query({ url: 'https://app.mdintegrations.com/*' });
  const state = await chrome.storage.session.get(null);
  const { email, password } = await chrome.storage.local.get(['email', 'password']);
  const secs = (t) => Math.round((Date.now() - t) / 1000);
  const lines = tabs.map((tab) => {
    const s = state[tab.id] || {};
    const path = new URL(tab.url).pathname; // percent-encoded, safe in HTML
    const list = path.startsWith(LIST) && path.slice(LIST.length);
    const [text, bad] =
      !s.seen ? ['waiting for the first check (max 30 s)']
      : secs(s.seen) > 90 ? [`not checked for ${Math.round(secs(s.seen) / 60)} min. Was the Mac asleep? Reload the tab.`, 1]
      : s.locked ? ['locked by MDI, type your password in MDI', 1]
      : s.login ? [s.failed ? 'auto login failed, log in by hand' : email && password ? 'logged out, logging in automatically' : 'logged out, log in by hand', 1]
      : list ? [`refreshed ${secs(s.refreshed)} s ago`]
      : []; // an open case, home, ...: not touched, not shown
    return text && { text: `${list ? list[0].toUpperCase() + list.slice(1) : path}: ${text}`, bad };
  }).filter(Boolean);
  // Path of the other MDI tabs: if logout lands somewhere unexpected, a screenshot of this shows where.
  if (!lines.length) lines.push({ text: `No Encounters list open.${tabs.length ? ` (${tabs.map((t) => new URL(t.url).pathname).join(', ')})` : ''}`, bad: 1 });
  const bad = lines.some((l) => l.bad);
  $('head').className = bad ? 'head bad' : 'head';
  $('head').textContent = bad ? '● Needs you' : '● All good, refreshing';
  $('lines').innerHTML = lines.map((l) => `<div class="${l.bad ? 'bad' : ''}">${l.text}</div>`).join('');
}
show();
showStatus();
setInterval(showStatus, 1000);
