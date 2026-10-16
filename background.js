// MDI Auto Refresh — made by Gábor Kiss, MIT License.
const BASE = 'https://app.mdintegrations.com/';
// Only the Encounters lists are touched, never an open case (no risk to a half-written reply).
const isList = (url) => url.startsWith(BASE + 'tabs/cases/list/');
const isLogin = (url) => url.startsWith(BASE + 'login');

// chrome.alarms is not throttled in background tabs (setInterval is). 30 s is its minimum.
chrome.alarms.get('tick', (a) => a || chrome.alarms.create('tick', { periodInMinutes: 0.5 }));

// Runs inside the MDI page. Element names come from MDI's own code (Angular + Ionic).
function refreshPage() {
  const page = document.querySelector('app-cases-page:not(.ion-page-hidden)');
  const btn = page?.querySelector('ion-icon[name="reload-outline"]')?.closest('ion-button');
  btn?.click(); // same as the user clicking ⟳ (MDI runs getEncounters("hard"))
  const n = document.querySelector('[tour="assigned-encounters"]')?.textContent.match(/(\d+)\s*$/);
  return { clicked: !!btn, assigned: n ? +n[1] : null, locked: !!document.querySelector('app-inactivity-lock-modal') };
}

function notify(tabId, title, message) {
  chrome.notifications.create(`${tabId}:${Date.now()}`, { type: 'basic', iconUrl: 'icon.png', title, message, priority: 2 });
}

chrome.notifications.onClicked.addListener((id) => {
  const tabId = +id.split(':')[0];
  chrome.tabs.update(tabId, { active: true }, (tab) => tab && chrome.windows.update(tab.windowId, { focused: true }));
});

chrome.alarms.onAlarm.addListener(async () => {
  const tabs = await chrome.tabs.query({ url: BASE + '*' });
  const lists = tabs.filter((t) => isList(t.url));
  // Keeps the Mac from idle-sleeping while a list is open (closing the lid still sleeps it).
  lists.length ? chrome.power.requestKeepAwake('system') : chrome.power.releaseKeepAwake();

  const state = await chrome.storage.session.get(null); // per tab: last count / lock / login seen
  for (const tab of tabs) {
    const s = state[tab.id] || {};
    if (isLogin(tab.url) && !s.login) notify(tab.id, 'MDI: you were logged out', 'Log in again so auto refresh can continue.');
    s.login = isLogin(tab.url);

    if (isList(tab.url)) {
      chrome.tabs.update(tab.id, { autoDiscardable: false }); // Chrome Memory Saver must not freeze this tab
      let r = {};
      try {
        [{ result: r }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: refreshPage });
      } catch (e) {}
      if (!r.clicked) chrome.tabs.reload(tab.id); // fallback: if the button ever changes, reload the page instead
      if (r.locked && !s.locked) notify(tab.id, 'MDI is locked', 'Inactivity lock: enter your password to continue.');
      if (r.assigned > (s.assigned ?? Infinity)) notify(tab.id, 'MDI: new assigned encounter', `Assigned: ${r.assigned}`);
      s.locked = !!r.locked;
      if (r.assigned != null) s.assigned = r.assigned;

      const how = r.clicked ? 'refresh button' : 'page reload';
      chrome.action.setBadgeText({ tabId: tab.id, text: r.locked ? 'LOCK' : r.clicked ? 'ON' : 'R' });
      chrome.action.setBadgeBackgroundColor({ tabId: tab.id, color: r.locked ? '#d93025' : '#1a7f64' });
      chrome.action.setTitle({ tabId: tab.id, title: `MDI Auto Refresh — last: ${new Date().toLocaleTimeString()} (${how})` });
    }
    state[tab.id] = s;
  }
  await chrome.storage.session.set(state);
});
