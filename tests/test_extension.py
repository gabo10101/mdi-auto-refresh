# Developer test (not needed by end users): loads the extension into real Chromium and serves
# fake MDI pages that mimic MDI's real DOM. Run: python3 tests/test_extension.py  (~105 s)
# --demo: opens a visible Chromium with the extension and the fake pages to click around in; no asserts.
import os, sys, tempfile
from playwright.sync_api import sync_playwright

EXT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = "https://app.mdintegrations.com/"
# Hidden (cached) Ionic page first, then the visible one. Each click "brings in" one new assigned case.
LIST = """<html><body>
<a tour="assigned-encounters"> Assigned <span class="c-sidemenu__extra" id="n">0</span></a>
<app-cases-page class="ion-page ion-page-hidden"><ion-button onclick="window.hidden=1"><ion-icon name="reload-outline"></ion-icon></ion-button></app-cases-page>
<app-cases-page class="ion-page"><ion-button onclick="window.clicks=(window.clicks||0)+1;n.textContent=window.clicks">
<ion-icon name="reload-outline"></ion-icon></ion-button></app-cases-page>%s</body></html>"""
PAGES = {
    "tabs/cases/list/assigned": LIST % "",
    "tabs/cases/list/flagged": LIST % "<app-inactivity-lock-modal></app-inactivity-lock-modal>",
    # After unlocking, the lock modal can stay in the DOM hidden (Ionic: ion-modal.overlay-hidden = display:none).
    "tabs/cases/list/unlocked": LIST % '<ion-modal style="display:none"><app-inactivity-lock-modal></app-inactivity-lock-modal></ion-modal>',
    "tabs/cases/list/waiting": "<html><body>no button here</body></html>",
    "tabs/cases/12345": "<html><body>open case</body></html>",
    "tabs/cases/list/expired": LIST % "",
    "tabs/home": "<html><body>home</body></html>",
    "login": """<html><body><form onsubmit="if (email.value == 'a@b.c' && pw.value == 'secret') location = '/tabs/home'; return false">
<input id="email" type="email"><input id="pw" type="password"><button type="submit">Log in</button></form></body></html>""",
}
loads = {}

def handler(route):
    path = route.request.url[len(B):]
    loads[path] = loads.get(path, 0) + 1
    route.fulfill(content_type="text/html", body=PAGES[path])

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel="chromium", headless="--demo" not in sys.argv,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
    ctx.route(B + "**", handler)
    pages = {k: ctx.new_page() for k in PAGES}
    for k, pg in pages.items(): pg.goto(B + k)
    ctx.new_page().goto("about:blank")  # all MDI tabs are now in the background
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    sw.evaluate("""self.created = []; const orig = chrome.notifications.create.bind(chrome.notifications);
        chrome.notifications.create = (id, o) => { self.created.push(o.title); return orig(id, o); }; 0""")  # trailing 0: else playwright calls the fn
    sw.evaluate("chrome.storage.local.set({email: 'a@b.c', password: 'secret'}).then(() => 0)")
    if "--demo" in sys.argv:
        print("Demo: puzzle icon (top right) -> pin MDI Auto Refresh, then click it. Badges appear within 30 s. Close the window to quit.")
        try:
            while ctx.pages: ctx.pages[0].wait_for_timeout(1000)  # until every tab/window is closed
        except Exception: pass  # window closed mid-wait
        sys.exit()
    pages["tabs/cases/list/expired"].wait_for_timeout(35_000)
    pages["tabs/cases/list/expired"].evaluate(f"location.href = '{B}login'")  # session expires after the 1st tick saw the list
    pages["login"].wait_for_timeout(70_000)
    expired_url = pages["tabs/cases/list/expired"].url

    a = pages["tabs/cases/list/assigned"]
    clicks, hidden = a.evaluate("[window.clicks || 0, window.hidden || 0]")
    notes = sw.evaluate("self.created")
    discardable = sw.evaluate(f"chrome.tabs.query({{url: '{B}tabs/cases/list/assigned'}}).then(t => t[0].autoDiscardable)")
    badge_lock = sw.evaluate(f"chrome.tabs.query({{url: '{B}tabs/cases/list/flagged'}}).then(t => chrome.action.getBadgeText({{tabId: t[0].id}}))")
    badge_unlocked = sw.evaluate(f"chrome.tabs.query({{url: '{B}tabs/cases/list/unlocked'}}).then(t => chrome.action.getBadgeText({{tabId: t[0].id}}))")
    print("clicks:", clicks, "hidden page clicks:", hidden, "| loads:", loads)
    print("notifications:", notes, "| autoDiscardable:", discardable, "| locked badge:", badge_lock)

    assert clicks >= 2 and hidden == 0, "must click the visible page's button only"
    assert loads["tabs/cases/list/assigned"] == 1, "button found -> no page reload"
    assert loads["tabs/cases/list/waiting"] >= 3, "no button -> fallback page reload"
    assert loads["tabs/cases/12345"] == 1, "an open case must never be touched"
    assert discardable is False, "list tab must be protected from Memory Saver"
    assert badge_lock == "LOCK"
    assert badge_unlocked == "ON", f"hidden lock modal is not a lock, got {badge_unlocked}"
    assert expired_url == B + "tabs/cases/list/expired", f"after auto login back to the list, got {expired_url}"
    assert notes.count("MDI: you were logged out") == 2 and "MDI is locked" in notes and "MDI: new assigned encounter" in notes, notes
    assert "MDI: auto login failed" not in notes
    log = sw.evaluate("chrome.storage.local.get('log').then(v => v.log)")
    kinds = {k: sum(e["n"] for e in log if e["type"] == k) for k in ("refresh", "new", "login")}
    print("24h log:", kinds)
    assert kinds["refresh"] >= 4 and kinds["new"] >= 2 and kinds["login"] >= 2, kinds
    assert sw.evaluate("chrome.storage.local.get('password').then(v => v.password)") == "secret"
    popup = ctx.new_page()
    popup.goto(f"chrome-extension://{sw.url.split('/')[2]}/popup.html")
    popup.wait_for_timeout(1500)
    status = popup.inner_text("#head") + " | " + popup.inner_text("#lines")
    print("popup status:", status)
    assert "Needs you" in status and "Flagged: locked by MDI" in status and "Assigned: refreshed" in status, status
    assert "12345" not in status, "an open case is not listed"
    print("OK")
    ctx.close()
