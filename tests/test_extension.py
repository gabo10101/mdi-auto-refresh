# Developer test (not needed by end users): loads the extension into real Chromium and serves
# fake MDI pages that mimic MDI's real DOM. Run: python3 tests/test_extension.py  (~70 s)
import os, tempfile
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
    "tabs/cases/list/waiting": "<html><body>no button here</body></html>",
    "tabs/cases/12345": "<html><body>open case</body></html>",
    "login": "<html><body>login</body></html>",
}
loads = {}

def handler(route):
    path = route.request.url[len(B):]
    loads[path] = loads.get(path, 0) + 1
    route.fulfill(content_type="text/html", body=PAGES[path])

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel="chromium", headless=True,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
    ctx.route(B + "**", handler)
    pages = {k: ctx.new_page() for k in PAGES}
    for k, pg in pages.items(): pg.goto(B + k)
    ctx.new_page().goto("about:blank")  # all MDI tabs are now in the background
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    sw.evaluate("""self.created = []; const orig = chrome.notifications.create.bind(chrome.notifications);
        chrome.notifications.create = (id, o) => { self.created.push(o.title); return orig(id, o); }; 0""")  # trailing 0: else playwright calls the fn
    pages["login"].wait_for_timeout(70_000)

    a = pages["tabs/cases/list/assigned"]
    clicks, hidden = a.evaluate("[window.clicks || 0, window.hidden || 0]")
    notes = sw.evaluate("self.created")
    discardable = sw.evaluate(f"chrome.tabs.query({{url: '{B}tabs/cases/list/assigned'}}).then(t => t[0].autoDiscardable)")
    badge_lock = sw.evaluate(f"chrome.tabs.query({{url: '{B}tabs/cases/list/flagged'}}).then(t => chrome.action.getBadgeText({{tabId: t[0].id}}))")
    print("clicks:", clicks, "hidden page clicks:", hidden, "| loads:", loads)
    print("notifications:", notes, "| autoDiscardable:", discardable, "| locked badge:", badge_lock)

    assert clicks >= 2 and hidden == 0, "must click the visible page's button only"
    assert loads["tabs/cases/list/assigned"] == 1, "button found -> no page reload"
    assert loads["tabs/cases/list/waiting"] >= 3, "no button -> fallback page reload"
    assert loads["tabs/cases/12345"] == 1, "an open case must never be touched"
    assert discardable is False, "list tab must be protected from Memory Saver"
    assert badge_lock == "LOCK"
    assert sorted(notes) == sorted(["MDI: you were logged out", "MDI is locked",
        "MDI: new assigned encounter", "MDI: new assigned encounter"]), notes  # count 1 -> 2 on both lists
    print("OK")
    ctx.close()
