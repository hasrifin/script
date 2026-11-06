#!/usr/bin/env python3
"""
jadi_v3.py - BitcoTasks PTC Auto
- SOLVER: https://sctg.xyz (method=bicotasks, key=kfnwGObiMNFHkFQyOZC82yx0iGDNiZSq)
- CAPTCHA4 (slider): intersep widget JS + challenge response, kirim apa adanya ke solver
- Firewall & Lead: auto-detect slider (captcha4) atau captcha2 lama
- HUMAN SCROLL: human_scroll / human_browse / human_idle anti-bot behaviour
"""
import asyncio, base64, json, time, os, re, sys, random, shutil, atexit, platform
from datetime import datetime
from playwright.async_api import async_playwright

PROXY = {"server":"http://geo.floppydata.com:10080","username":"hwpFxGZM1T4qvE40","password":"aNFVHgrzAy5sXrgP"}
OFFERWALL_KEY = "a97qctwcbii2hestyho6if3o1vp2e"
SUB_ID = "OTIwNXxmZXl8cHRj"
OFFERWALL = f"https://bitcotasks.com/offerwall/{OFFERWALL_KEY}/{SUB_ID}/"
MAX_ADS = int(os.environ.get("MAX_ADS", "130"))

SOLVER_KEY    = "kfnwGObiMNFHkFQyOZC82yx0iGDNiZSq"
SOLVER_IN     = "https://sctg.xyz/in.php"
SOLVER_RES    = "https://sctg.xyz/res.php"
SOLVER_METHOD = "bicotasks"

HEADLESS   = os.environ.get("HEADLESS", "0") == "1"
IS_WINDOWS = platform.system() == "Windows"

# Global store untuk captcha4 responses (diisi oleh persistent listener)
CAP4_STORE = {"widget": None, "challenges": []}

def attach_cap4_listener(page):
    """Pasang persistent response listener untuk tangkap captcha4 widget + challenge."""
    async def _on_resp(resp):
        if 'captcha4' not in resp.url: return
        try:
            body = await resp.text()
        except Exception:
            return
        s = body.strip()
        if s.startswith("var ccaptchaObj") or s.startswith("var cctoken") or "ccaptchaObj" in s[:120]:
            CAP4_STORE["widget"] = body
        elif s.startswith("(function") or "var p=" in s[:80]:
            CAP4_STORE["challenges"].append(body)
            if len(CAP4_STORE["challenges"]) > 5:
                CAP4_STORE["challenges"].pop(0)
    page.on("response", _on_resp)
if IS_WINDOWS:
    TEMP_DIR = os.environ.get("TEMP") or os.environ.get("TMP") or r"C:\Temp"
    PROFILE  = os.path.join(TEMP_DIR, "bitco_auto1"); LOGFILE = os.path.join(TEMP_DIR, "1py.log")
else:
    PROFILE = "/tmp/bitco_auto1"; LOGFILE = "/tmp/1py.log"

class C:
    RESET="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; GREEN="\033[92m"
    YELLOW="\033[93m"; RED="\033[91m"; CYAN="\033[96m"; MAGENTA="\033[95m"; WHITE="\033[97m"
if IS_WINDOWS: os.system("")

def log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    pfx = {"ok":(f"{C.GREEN}✔{C.RESET}",C.GREEN),"err":(f"{C.RED}✘{C.RESET}",C.RED),
           "warn":(f"{C.YELLOW}⚠{C.RESET}",C.YELLOW),"title":(f"{C.CYAN}▶{C.RESET}",C.CYAN)}.get(level,(f"{C.DIM}•{C.RESET}",C.WHITE))
    print(f"{C.DIM}[{ts}]{C.RESET} {pfx[0]} {pfx[1]}{msg}{C.RESET}", flush=True)
    try:
        with open(LOGFILE,"a",encoding="utf-8") as f: f.write(f"[{ts}] {msg}\n")
    except: pass

def banner(text):
    w=55; print(f"\n{C.CYAN}{'═'*w}{C.RESET}\n{C.BOLD}{C.CYAN}  {text}{C.RESET}\n{C.CYAN}{'═'*w}{C.RESET}\n")

def cleanup_profile():
    try:
        if os.path.exists(PROFILE): shutil.rmtree(PROFILE, ignore_errors=True); print(f"{C.DIM}[cleanup] Profil dihapus{C.RESET}")
    except Exception as e: print(f"{C.YELLOW}[cleanup] {e}{C.RESET}")
atexit.register(cleanup_profile)

def find_chrome():
    if not IS_WINDOWS:
        for p in ["/usr/bin/google-chrome","/usr/bin/chromium-browser","/usr/bin/chromium","/usr/local/bin/chromium","/usr/local/bin/chromium-browser"]:
            if os.path.exists(p): return p
        return None
    for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
              os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe")]:
        if p and os.path.exists(p): return p
    return None

# ══════════════════════════════════════════════════════════════
# SOLVER CORE — sctg.xyz / bicotasks
# ══════════════════════════════════════════════════════════════
def _solver_submit_poll(p1_b64, pmain_b64):
    """Submit (p1=base64 widget JS, pmain=base64 challenge text). Return (x,y) atau (x,None) atau None."""
    import requests
    data = {"1":p1_b64, "key":SOLVER_KEY, "method":SOLVER_METHOD, "main":pmain_b64}
    log(f"solver submit (1_len={len(p1_b64)}, main_len={len(pmain_b64)})")
    try: resp = requests.post(SOLVER_IN, data=data, timeout=45)
    except Exception as e: log(f"submit err: {e}","err"); return None
    text = resp.text.strip()
    log(f"solver resp: {text[:120]}")
    if "ZERO_BALANCE" in text: log("SOLVER SALDO HABIS!","err"); return None
    task_id=None; use_json=False
    if text.startswith("OK|"): task_id = text.split("|",1)[1]
    else:
        try:
            b=resp.json(); task_id=b.get("taskId") or b.get("request") or b.get("id") or b.get("task_id"); use_json=True
        except ValueError: pass
    if not task_id: log(f"no task_id: {text[:120]}","err"); return None
    log(f"task_id={task_id}, polling...")
    pp = {"key":SOLVER_KEY,"id":task_id,"action":"get"}
    if use_json: pp["json"]=2
    else: pp["action"]="get4"
    start=time.time()
    while time.time()-start < 120:
        time.sleep(2)
        try: pr=requests.get(SOLVER_RES, params=pp, timeout=30).text.strip()
        except Exception as e: log(f"poll err: {e}","warn"); continue
        log(f"  [{time.time()-start:.0f}s] {pr[:100]}")
        if "NOT_READY" in pr or "PROCESSING" in pr: continue
        answer=None
        if use_json:
            try:
                pj=json.loads(pr)
                if pj.get("status")==1 or pj.get("request"): answer=str(pj.get("request") or pj.get("answer") or "")
            except ValueError: answer=pr
        else:
            answer = pr.split("|")[1] if pr.startswith("OK|") and len(pr.split("|"))>1 else pr
        if not answer or "ERROR" in answer or "UNSOLVABLE" in answer:
            log(f"solver gagal: {pr[:100]}","err"); return None
        # parse koordinat fleksibel: "coordinate:x=238,y=56" / "x,y" / "[x,y]" / JSON
        m=re.search(r'x\s*[:=]\s*(\d{1,4})\s*[,;]?\s*y\s*[:=]\s*(\d{1,4})', answer)
        if not m: m=re.search(r'(\d{1,4})\s*[,;:x=]\s*(\d{1,4})', answer)
        if not m: m=re.search(r'[\[(\s](\d{1,4})\s*,\s*(\d{1,4})[\])\s]', answer)
        if m:
            x,y=int(m.group(1)),int(m.group(2)); log(f"answer → ({x},{y})","ok"); return (x,y)
        try:
            arr=json.loads(answer)
            if isinstance(arr,list) and len(arr)>=2:
                x,y=int(arr[0]),int(arr[1]); log(f"answer JSON → ({x},{y})","ok"); return (x,y)
            if isinstance(arr,(int,float)):
                log(f"answer scalar x={int(arr)}","ok"); return (int(arr),None)
        except ValueError: pass
        m2=re.search(r'(\d{1,4})', answer)
        if m2:
            log(f"answer single x={int(m2.group(1))}","ok"); return (int(m2.group(1)),None)
        log(f"cannot parse: {answer[:120]}","err"); return None
    log("solver timeout","warn"); return None

async def solver_call(p1_text, pmain_text):
    """p1_text = widget JS source; pmain_text = challenge text (sudah format (function(){var p=...}))."""
    try: p1 = base64.b64encode(p1_text.encode("utf-8","replace")).decode()
    except Exception as e: log(f"p1 encode err: {e}","err"); return None
    try: pm = base64.b64encode(pmain_text.encode("utf-8","replace")).decode()
    except Exception as e: log(f"main encode err: {e}","err"); return None
    return await asyncio.to_thread(_solver_submit_poll, p1, pm)

# ══════════════════════════════════════════════════════════════
# CAPTCHA4 SLIDER — intersep widget JS + challenge
# ══════════════════════════════════════════════════════════════
async def capture_captcha4(page, trigger_refresh=True):
    """
    Baca dari CAP4_STORE (listener persisten). Return (widget_js, challenge_text).
    Jika challenge belum ada, klik "New puzzle" untuk trigger fetch baru.
    """
    widget_js = CAP4_STORE.get("widget")
    challenge = CAP4_STORE["challenges"][-1] if CAP4_STORE["challenges"] else None

    # fallback: fetch widget manual dari script src
    if not widget_js:
        cap4_url = await page.evaluate("""() => {
            for (const s of document.querySelectorAll('script[src]'))
                if (s.src.includes('captcha4')) return s.src;
            return null;
        }""")
        if cap4_url:
            try:
                widget_js = await page.evaluate(f"""async () => {{
                    const r = await fetch('{cap4_url}', {{credentials:'include',signal:AbortSignal.timeout(30000)}});
                    return await r.text();
                }}""")
                if widget_js: CAP4_STORE["widget"] = widget_js
            except Exception as e:
                log(f"fetch widget fallback err: {e}","warn")

    if not challenge and trigger_refresh:
        n_before = len(CAP4_STORE["challenges"])
        await page.evaluate("""() => { const el=document.querySelector('ubjtyazxclb'); if(el) el.click(); }""")
        for _ in range(20):
            await asyncio.sleep(0.5)
            if len(CAP4_STORE["challenges"]) > n_before:
                challenge = CAP4_STORE["challenges"][-1]
                break
    if not widget_js:
        widget_js = CAP4_STORE.get("widget")
    return widget_js, challenge

async def detect_slider(page):
    return await page.evaluate("""() => {
        const cap = document.getElementById('captcha-active') || document.querySelector('[id*=captcha]');
        if (!cap) return null;
        const hidden = cap.querySelector('input[type=hidden]');
        const tokenName = hidden ? hidden.name : (typeof captchaTokenName !== 'undefined' ? captchaTokenName : '');
        const imgs = cap.querySelectorAll('img');
        const bg = imgs[0] ? imgs[0].src : '';
        const piece = imgs[1] ? imgs[1].src : '';
        const handle = cap.querySelector('[role=slider]') || cap.querySelector('rfrfpxixjrhc');
        const box = cap.querySelector('pfrqarrrdhg') || (imgs[0] ? imgs[0].parentElement : null);
        if (!handle || !bg) return null;
        handle.setAttribute('data-slh','1');
        return {tokenName, bg, piece, handleSel:'[data-slh="1"]', boxW: box ? box.getBoundingClientRect().width : 306};
    }""")

async def drag_slider_to(page, handle_sel, target_x_px, track_width):
    h = await page.query_selector(handle_sel)
    if not h: log("slider handle not found","err"); return False
    box = await h.bounding_box()
    if not box: log("no bbox","err"); return False
    sx, sy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
    tx = sx + min(target_x_px, track_width - box["width"] - 4)
    await page.mouse.move(sx, sy); await page.mouse.down()
    steps=20
    for i in range(1,steps+1):
        await page.mouse.move(sx+(tx-sx)*i/steps, sy+random.uniform(-2,2), steps=1)
        await asyncio.sleep(0.02+random.uniform(0,0.03))
    await page.mouse.move(tx, sy); await asyncio.sleep(0.15); await page.mouse.up()
    await asyncio.sleep(1.5)
    return True

async def solve_slider_captcha(page, tag):
    info = await detect_slider(page)
    if not info:
        log(f"[{tag}] no slider","warn"); return False,"",""
    token_field = info.get("tokenName") or "vcRAA"
    track_w = info.get("boxW") or 306
    log(f"[{tag}] SLIDER captcha4: tokenField={token_field} trackW={track_w}")

    # intersep captcha4 widget JS + challenge
    widget_js, challenge = await capture_captcha4(page, trigger_refresh=True)
    if not widget_js:
        log(f"[{tag}] gagal capture widget JS captcha4","err"); return False, token_field, ""
    if not challenge:
        log(f"[{tag}] gagal capture challenge captcha4, retry reload","warn")
        try: await page.reload(wait_until="domcontentloaded", timeout=30000)
        except: pass
        await asyncio.sleep(3)
        widget_js, challenge = await capture_captcha4(page, trigger_refresh=False)
    if not challenge:
        log(f"[{tag}] challenge tetap tidak ada","err"); return False, token_field, ""

    log(f"[{tag}] captured: widget={len(widget_js)}B challenge={len(challenge)}B")
    # ekstrak w (image width) dan s (piece width) dari challenge
    img_w = 320; piece_w = 60
    mw = re.search(r'"w"\s*:\s*(\d+)', challenge)
    if mw: img_w = int(mw.group(1))
    ms = re.search(r'"s"\s*:\s*(\d+)', challenge)
    if ms: piece_w = int(ms.group(1))
    # ukur mk = track.clientWidth - handle.offsetWidth (max travel handle) dari page
    mk_info = await page.evaluate("""() => {
        const tr = document.querySelector('dprlkwzjb') || document.querySelector('[role=slider]')?.parentElement;
        const kn = document.querySelector('[role=slider]') || document.querySelector('rfrfpxixjrhc');
        if (!tr || !kn) return null;
        return {mk: tr.clientWidth - kn.offsetWidth, trackW: tr.clientWidth, handleW: kn.offsetWidth};
    }""")
    if mk_info:
        mk = mk_info["mk"]; track_w = mk_info["trackW"]
        log(f"[{tag}] mk={mk} (track={track_w}, handle={mk_info['handleW']}) img_w={img_w} piece_w={piece_w}")
    else:
        mk = track_w - 52
        log(f"[{tag}] mk fallback={mk}")
    res = await solver_call(widget_js, challenge)
    if not res:
        log(f"[{tag}] solver gagal","err"); return False, token_field, ""
    x_ans = res[0]
    # solver return CENTER x dari gap (0..img_w). Left edge piece = x_ans - piece_w/2.
    # Validasi server pakai left-edge (0..img_w-piece_w). dx = left_edge * mk / (img_w-piece_w).
    left_edge = x_ans - piece_w / 2.0
    max_x = img_w - piece_w
    left_edge = max(0, min(left_edge, max_x))
    dx = int(round(left_edge * mk / max_x)) if max_x > 0 else x_ans
    dx = max(2, min(dx, mk - 2))
    log(f"[{tag}] solver center_x={x_ans} → left_edge={left_edge:.0f} (0..{max_x}) → drag dx={dx}px (mk={mk})")
    ok = await drag_slider_to(page, info["handleSel"], dx, track_w)
    if not ok: return False, token_field, ""
    token=""
    for _ in range(20):
        token = await page.evaluate(f"""() => {{
            const el = document.querySelector('input[name="{token_field}"]');
            if (el && el.value) return el.value;
            if (typeof cctoken !== 'undefined' && cctoken) return cctoken;
            return '';
        }}""")
        if token and len(token)>5: break
        await asyncio.sleep(0.5)
    if token and len(token)>5:
        log(f"[{tag}] SLIDER SOLVED → token={token[:24]}...","ok")
        return True, token_field, token
    msg = await page.evaluate("""() => {
        const el = document.querySelector('tbkskkjgc');
        if (el) return (el.getAttribute('data-k')||'')+':'+(el.textContent||'').substring(0,60);
        const cap = document.getElementById('captcha-active');
        if (cap && cap.getAttribute('data-x')==='1') return 'shake=wrong_position';
        return '';
    }""")
    if msg: log(f"[{tag}] slider status: {msg}","warn")
    log(f"[{tag}] token kosong (salah posisi?)","err")
    return False, token_field, ""

# ══════════════════════════════════════════════════════════════
# CAPTCHA2 (lama, click-coords) — fallback
# ══════════════════════════════════════════════════════════════
async def find_cap_js(page):
    return await page.evaluate("""() => {
        for (const s of document.querySelectorAll('script[src]'))
            if ((s.src.includes('captcha2')||s.src.includes('captcha4')) && s.src.includes('.js')) return s.src;
        const m = document.body.innerHTML.match(/(captcha[24]\\/[a-zA-Z0-9]+\\.js\\?action=captcha)/);
        return m ? 'https://bitcotasks.com/'+m[1] : null;
    }""")

async def solve_captcha2(page, cap_js_url, tag):
    log(f"[{tag}] solving captcha2/4 coords...","title")
    js_text = await page.evaluate(f"""async () => {{ const r=await fetch('{cap_js_url}',{{credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text(); }}""")
    real_field, resp_key = "atxrN", "token"
    m = re.search(r"getElementById\(['\"]([a-zA-Z0-9_]+)['\"]\)\.value\s*=\s*response\.([a-zA-Z0-9_]+)", js_text)
    if m: real_field, resp_key = m.group(1), m.group(2)
    short_id=None
    m=re.search(r"captcha[24]/([a-zA-Z0-9]{3,8})\?action=data", js_text)
    if m: short_id=m.group(1)
    cj={}; img_raw=""
    for _cr in range(3):
        t=int(time.time()*1000); rnd=random.random()
        chal = await page.evaluate(f"""async () => {{ const r=await fetch('{cap_js_url}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{t:{t},r:{rnd}}}),credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text(); }}""")
        try: cj=json.loads(chal)
        except: cj={}
        img_raw = cj.get("image") or cj.get("preload") or ""
        if img_raw and len(img_raw) > 200: break
        log(f"[{tag}] image captcha belum ready (len={len(img_raw)}), retry {_cr+1}/3...","warn")
        await asyncio.sleep(2.5)
    img_full = img_raw if img_raw.startswith("data:") else f"data:image/gif;base64,{img_raw}"
    img_b64 = img_raw.split(",",1)[1] if img_raw.startswith("data:") else img_raw
    payload_m=re.search(r"var\s+payload\s*=\s*['\"]([^'\"]+)['\"]", js_text)
    sk=ck=sk_val=""
    if payload_m:
        for p in payload_m.group(1).split("&"):
            if "=" in p:
                k,v=p.split("=",1)
                if v: sk,sk_val=k,v
                else: ck=k
    def jsvar(n):
        mm=re.search(rf"var\s+{n}\s*=\s*['\"]([^'\"]+)['\"]", js_text); return mm.group(1) if mm else ""
    if not sk: sk=cj.get("static_key") or jsvar("static_key") or jsvar("sk")
    if not ck: ck=cj.get("coords_key") or jsvar("coords_key") or jsvar("ck")
    if not sk_val: sk_val=cj.get("sk") or jsvar("ok") or "x"
    cdata=cj.get("cdata") or jsvar("cdata") or ""
    m=re.search(r"captcha[24]/([a-zA-Z0-9]{3,6})\?action=data&cdata=([a-f0-9]+)", js_text)
    if m:
        if not short_id: short_id=m.group(1)
        if not cdata: cdata=m.group(2)
    if not short_id:
        m=re.search(r"captcha[24]/([a-zA-Z0-9]{3,8})\?action=data", js_text)
        if m: short_id=m.group(1)
    log(f"payload: sk={sk}={sk_val} ck={ck} shortId={short_id} imgLen={len(img_b64)}")
    if not img_b64 or not sk or not ck:
        log(f"missing keys: {list(cj.keys())[:12]}","err"); return False, real_field, ""
    # untuk captcha2: param 1=js_text, main=construct dari image
    main_js = f'(function(){{var p={{"p":"{img_full}"}}}})'
    coords = await solver_call(js_text, main_js)
    if not coords or coords[1] is None:
        log("solver gagal","err"); return False, real_field, ""
    x,y=coords; log(f"coords=({x},{y})","ok")
    await asyncio.sleep(4)
    post_url=f"https://bitcotasks.com/captcha2/{short_id}?action=data&cdata={cdata}"
    body=f"{sk}={sk_val}&{ck}=[{x},{y}]"
    val=await page.evaluate(f"""async () => {{ const r=await fetch('{post_url}',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:'{body}',credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text(); }}""")
    log(f"validate: {val[:120]}")
    try:
        vj=json.loads(val); tok=vj.get(resp_key)
        if not tok:
            for k,v in vj.items():
                if isinstance(v,str) and len(v)>=30 and re.match(r'^[a-f0-9]+$',v): tok=v; real_field=k; break
        if tok: log(f"SOLVED → field={real_field} tok={tok[:20]}...","ok"); return True, real_field, str(tok)
    except: pass
    if "ok" in val.lower(): log("SOLVED (ok)","ok"); return True, real_field, ""
    return False, real_field, ""

async def wait_captcha_ready(page, timeout=25):
    """Tunggu sampai container captcha muncul DAN semua image di dalamnya fully loaded
    (complete && naturalWidth>0). Lalu beri buffer ekstra agar piece/background terakhir
    benar-benar ter-render sebelum di-capture solver. Mencegah gagal attempt-1 karena
    gambar captcha masih loading."""
    try:
        await page.wait_for_function("""() => {
            const cap = document.getElementById('captcha-active') || document.querySelector('[id*=captcha]');
            if (!cap) return false;
            const imgs = cap.querySelectorAll('img');
            if (imgs.length === 0) return false;
            for (const im of imgs) {
                if (!im.complete || im.naturalWidth === 0) return false;
            }
            return true;
        }""", timeout=timeout*1000)
        await asyncio.sleep(3)  # buffer ekstra: render akhir + jaringan lambat
        log("[wait] captcha image fully loaded ✓","ok")
        return True
    except Exception:
        log("[wait] timeout tunggu captcha image (lanjut apa adanya)","warn")
        try: await asyncio.sleep(3)
        except: pass
        return False

async def solve_any_captcha(page, tag):
    """Return (ok, field, token). Coba slider (captcha4) dulu, fallback captcha2."""
    sl = await detect_slider(page)
    if sl:
        return await solve_slider_captcha(page, tag)
    cap = await find_cap_js(page)
    if cap:
        return await solve_captcha2(page, cap, tag)
    log(f"[{tag}] tidak ada captcha","ok")
    return True, "", ""

async def minimize_browser(page):
    try:
        cdp=await page.context.new_cdp_session(page)
        r=await cdp.send("Browser.getWindowForTarget"); wid=r.get("windowId")
        if wid: await cdp.send("Browser.setWindowBounds",{"windowId":wid,"bounds":{"windowState":"minimized"}}); log("Chrome minimized","ok")
        await cdp.detach()
    except Exception as e: log(f"minimize gagal: {e}","warn")

# ══════════════════════════════════════════════════════════════
# HUMAN-LIKE SCROLL — anti-bot behaviour
# ══════════════════════════════════════════════════════════════
async def human_scroll(page, direction="down", total_px=None, pauses=True):
    """
    Scroll seperti manusia:
    - kecepatan tidak konstan (acceleration + deceleration)
    - jarak tiap step acak
    - kadang pause singkat di tengah
    - kadang sedikit overshoot lalu koreksi
    direction: "down" | "up" | "random"
    total_px: total jarak scroll (None = acak 180-520)
    """
    try:
        if direction == "random":
            direction = random.choice(["down", "up"])
        if total_px is None:
            total_px = random.randint(180, 520)

        sign = 1 if direction == "down" else -1
        remaining = total_px
        steps = random.randint(6, 14)

        for i in range(steps):
            # ease-in-out: step lebih kecil di awal & akhir
            progress = (i + 1) / steps
            ease = 0.5 - 0.5 * (1 - (2 * progress - 1) ** 2) if progress < 0.5 else progress
            chunk = max(12, int((total_px / steps) * (0.6 + random.uniform(0.3, 1.1))))
            chunk = min(chunk, remaining)
            if chunk <= 0:
                break

            # mouse wheel event (lebih natural daripada window.scrollBy langsung)
            await page.mouse.wheel(0, sign * chunk)
            remaining -= chunk

            # jeda antar step (manusia tidak scroll konstan)
            delay = random.uniform(0.04, 0.18)
            # kadang pause lebih lama (seperti membaca)
            if pauses and random.random() < 0.18:
                delay += random.uniform(0.25, 0.7)
            await asyncio.sleep(delay)

        # slight overshoot + koreksi (perilaku manusia)
        if pauses and random.random() < 0.35:
            overshoot = random.randint(20, 55)
            await page.mouse.wheel(0, sign * overshoot)
            await asyncio.sleep(random.uniform(0.12, 0.35))
            await page.mouse.wheel(0, -sign * overshoot)
            await asyncio.sleep(random.uniform(0.08, 0.2))

        return True
    except Exception as e:
        log(f"human_scroll err: {e}", "warn")
        return False

async def human_browse(page, rounds=None):
    """
    Simulasi browsing ringan: scroll naik-turun beberapa kali
    dengan jeda acak. Dipanggil di offerwall / lead page.
    """
    if rounds is None:
        rounds = random.randint(2, 5)
    try:
        for _ in range(rounds):
            await human_scroll(page, direction=random.choice(["down", "down", "up"]), pauses=True)
            await asyncio.sleep(random.uniform(0.4, 1.3))
        # kembali ke atas secara natural
        if random.random() < 0.6:
            await human_scroll(page, direction="up", total_px=random.randint(250, 600), pauses=False)
            await asyncio.sleep(random.uniform(0.3, 0.8))
    except Exception as e:
        log(f"human_browse err: {e}", "warn")

async def human_idle(page, seconds):
    """
    Tunggu sambil sesekali melakukan micro-scroll / mouse move
    agar terlihat aktif (bukan idle bot).
    """
    end = time.time() + max(0.5, seconds)
    try:
        while time.time() < end:
            remaining = end - time.time()
            if remaining <= 0:
                break
            # micro action
            action = random.choices(
                ["wait", "scroll", "mousemove"],
                weights=[0.55, 0.30, 0.15],
                k=1
            )[0]
            if action == "scroll":
                await human_scroll(
                    page,
                    direction=random.choice(["down", "up"]),
                    total_px=random.randint(40, 140),
                    pauses=False
                )
            elif action == "mousemove":
                try:
                    vp = page.viewport_size or {"width": 1280, "height": 900}
                    x = random.randint(80, max(100, vp["width"] - 80))
                    y = random.randint(80, max(100, vp["height"] - 80))
                    await page.mouse.move(x, y, steps=random.randint(5, 14))
                except Exception:
                    pass
            sleep_t = min(remaining, random.uniform(0.6, 2.2))
            await asyncio.sleep(sleep_t)
    except Exception as e:
        # fallback pure sleep
        left = end - time.time()
        if left > 0:
            await asyncio.sleep(left)

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
async def main():
    banner("BitcoTasks PTC Auto • sctg.xyz/bicotasks • captcha4 + human scroll")
    log(f"OS={platform.system()} MAX_ADS={MAX_ADS} HEADLESS={HEADLESS}")
    log(f"Solver key: {SOLVER_KEY[:8]}...")
    chrome_path=find_chrome()
    log(f"Chrome: {chrome_path or 'bawaan'}", "ok" if chrome_path else "warn")
    if os.path.exists(PROFILE): shutil.rmtree(PROFILE, ignore_errors=True)
    os.makedirs(PROFILE, exist_ok=True)
    open(LOGFILE,"w").write("")
    CAP4_STORE["widget"] = None; CAP4_STORE["challenges"] = []
    ctx=None
    try:
        async with async_playwright() as p:
            args=["--no-sandbox","--disable-blink-features=AutomationControlled","--disable-infobars","--mute-audio",
                  "--disable-popup-blocking","--no-first-run","--no-default-browser-check","--lang=en-US",
                  "--disable-gpu","--disable-software-rasterizer","--disable-dev-shm-usage"]
            if not HEADLESS and IS_WINDOWS: args.append("--start-minimized")
            kw={"user_data_dir":PROFILE,"headless":HEADLESS,"proxy":PROXY,"viewport":{"width":1280,"height":900},
                "args":args,"timezone_id":"Asia/Makassar","locale":"en-US"}
            if chrome_path: kw["executable_path"]=chrome_path
            ctx=await p.chromium.launch_persistent_context(**kw)
            page=ctx.pages[0] if ctx.pages else await ctx.new_page()
            attach_cap4_listener(page)
            if not HEADLESS and IS_WINDOWS: await minimize_browser(page)
            log("Navigating to offerwall...","title")
            try: await page.goto(OFFERWALL, wait_until="domcontentloaded", timeout=60000)
            except Exception as e: log(f"nav err: {e}","err")
            await asyncio.sleep(random.uniform(2.5, 4.5))
            # human-like browse di offerwall agar tidak langsung kaku
            log("human browse offerwall...", "info")
            await human_browse(page, rounds=random.randint(2, 4))
            log(f"URL: {page.url[:90]}")

            # ── FIREWALL ──
            if "firewall" in page.url:
                log("Firewall → solve slider captcha4","warn")
                for att in range(6):
                    ok, fld, tok = await solve_any_captcha(page, f"fw{att+1}")
                    redirect_url=None
                    if ok and tok and fld:
                        v=await page.evaluate(f"""async () => {{
                            const fd=new FormData(); fd.append('action','validate'); fd.append('{fld}','{tok}');
                            const r=await fetch(location.href,{{method:'POST',headers:{{'X-Requested-With':'XMLHttpRequest'}},body:fd,credentials:'include',signal:AbortSignal.timeout(30000)}});
                            return await r.text();
                        }}""")
                        log(f"validate: {v[:140]}")
                        try:
                            vj=json.loads(v)
                            if vj.get("status")=="success" and vj.get("redirect"): redirect_url=vj["redirect"]
                        except: pass
                    await asyncio.sleep(3)
                    try: await page.goto(redirect_url or OFFERWALL, wait_until="domcontentloaded", timeout=60000)
                    except: pass
                    await asyncio.sleep(4)
                    if "firewall" not in page.url: log("FIREWALL PASSED","ok"); break
                    await asyncio.sleep(2)

            log(f"URL: {page.url[:90]}")
            ajax_tok=await page.evaluate("""() => {
                let m=document.body.innerHTML.match(/var\\s+token\\s*=\\s*['"]([a-f0-9]{40,80})['"]/);
                if(m) return m[1];
                for(const s of document.querySelectorAll('script')){const mm=(s.textContent||'').match(/['"]?token['"]?\\s*[:=]\\s*['"]([a-f0-9]{40,80})['"]/); if(mm) return mm[1];}
                return null;
            }""")
            log(f"AJAX token: {str(ajax_tok)[:28]}...")
            if not ajax_tok:
                log("NO TOKEN — firewall belum lolos","err")
                log((await page.evaluate("()=>document.body.innerText.substring(0,400)"))[:400])
                await asyncio.sleep(8); return

            sc=await page.evaluate(f"""async () => {{
                const fd=new FormData(); fd.append('token','{ajax_tok}'); fd.append('action','switch_cat'); fd.append('type','ptc');
                const r=await fetch(location.href,{{method:'POST',headers:{{'X-Requested-With':'XMLHttpRequest'}},body:fd,credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text();
            }}""")
            log(f"switch_cat len={len(sc)} → {sc[:160]}")
            ads=[]
            try:
                scj=json.loads(sc)
                if isinstance(scj,dict):
                    for k in ["data","ads","ptc","offers","list","items"]:
                        if isinstance(scj.get(k),list): ads=scj[k]; break
                    if not ads:
                        for v in scj.values():
                            if isinstance(v,list) and v and isinstance(v[0],dict): ads=v; break
                elif isinstance(scj,list): ads=scj
            except:
                for u in re.findall(r'href=["\']([^"\']*lead[^"\']*)', sc):
                    hm=re.search(r'/lead/([^/]+)',u); ads.append({"href":u,"title":"ad","hash":hm.group(1) if hm else ""})
            log(f"ADS ditemukan: {len(ads)}","ok")
            for i,a in enumerate(ads[:MAX_ADS]): log(f"  [{i}] {json.dumps(a)[:140]}")
            if not ads: log("Tidak ada iklan!","err"); await asyncio.sleep(8); return

            success=0; total=min(MAX_ADS,len(ads))
            for i,ad in enumerate(ads[:MAX_ADS]):
                print(f"\n{C.MAGENTA}{'─'*50}{C.RESET}")
                log(f"AD {i+1}/{total}","title")
                ah=ad.get("hash") or ad.get("id") or ""
                if not ah and ad.get("href"):
                    hm=re.search(r'/lead/([^/]+)',ad["href"]); ah=hm.group(1) if hm else ""
                title=str(ad.get("title") or ad.get("name") or ah)[:40]
                reward=ad.get("reward") or ad.get("amount") or "?"
                dur=int(ad.get("duration") or ad.get("timer") or ad.get("seconds") or 5)
                log(f"{title} +{reward} {dur}s hash={ah}")
                initr=await page.evaluate(f"""async () => {{
                    const fd=new FormData(); fd.append('token','{ajax_tok}'); fd.append('action','init_transaction');
                    fd.append('hash','{ah}'); fd.append('sid','{SUB_ID}'); fd.append('key','{OFFERWALL_KEY}'); fd.append('type','ptc');
                    const r=await fetch(location.href,{{method:'POST',headers:{{'X-Requested-With':'XMLHttpRequest'}},body:fd,credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text();
                }}""")
                log(f"init FULL: {initr}")
                await asyncio.sleep(2)  # jeda hindari rate-limit
                lead_tok=None; offer_url=""
                try:
                    ij=json.loads(initr); offer_url=ij.get("offer") or ij.get("url") or ij.get("redirect") or ""
                    mm=re.search(r'/lead/[^/]+/[^/]+/[^/]+/([a-zA-Z0-9]+)',offer_url)
                    if mm: lead_tok=mm.group(1)
                except: pass
                if not lead_tok:
                    mm=re.search(r'/lead/[^/]+/[^/]+/[^/]+/([a-zA-Z0-9]+)',initr.replace("\\/","/"))
                    if mm: lead_tok=mm.group(1)
                if not lead_tok: log("no lead token → skip","warn"); continue
                # PAKAI offer URL LANGSUNG dari init response (jangan rekonstruksi — hindari double-slash/Forbidden)
                lead_url = offer_url if offer_url else f"https://bitcotasks.com/lead/{ah}/{OFFERWALL_KEY}/{SUB_ID}/{lead_tok}"
                log(f"lead_url: {lead_url[:90]}")
                # buka lead via window.open dari main page → referer & header alami (hindari Forbidden)
                async with ctx.expect_page() as _np:
                    await page.evaluate(f"()=>window.open('{lead_url}','_blank')")
                lead_page = await _np.value
                attach_cap4_listener(lead_page)
                lead_token_var=""; cap_field=cap_token=""
                try:
                    await lead_page.wait_for_load_state("domcontentloaded", timeout=30000)
                    # cek Forbidden — jika ya, retry init sekali untuk URL fresh
                    body_text = await lead_page.evaluate("()=>document.body.innerText.substring(0,50).trim()")
                    if body_text.lower().startswith("forbidden"):
                        log("lead page Forbidden → re-init untuk URL fresh","warn")
                        await lead_page.close()
                        initr2=await page.evaluate(f"""async () => {{
                            const fd=new FormData(); fd.append('token','{ajax_tok}'); fd.append('action','init_transaction');
                            fd.append('hash','{ah}'); fd.append('sid','{SUB_ID}'); fd.append('key','{OFFERWALL_KEY}'); fd.append('type','ptc');
                            const r=await fetch(location.href,{{method:'POST',headers:{{'X-Requested-With':'XMLHttpRequest'}},body:fd,credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text();
                        }}""")
                        try:
                            ij2=json.loads(initr2); offer_url2=ij2.get("offer") or ""
                            if offer_url2:
                                lead_url = offer_url2
                                log(f"re-init ok, lead_url baru: {lead_url[:80]}")
                        except: pass
                        async with ctx.expect_page() as _np2:
                            await page.evaluate(f"()=>window.open('{lead_url}','_blank')")
                        lead_page = await _np2.value
                        attach_cap4_listener(lead_page)
                        await lead_page.wait_for_load_state("domcontentloaded", timeout=30000)
                    # light human scroll di lead page (sebelum fokus captcha)
                    await asyncio.sleep(random.uniform(0.8, 1.6))
                    await human_scroll(lead_page, direction="down", total_px=random.randint(80, 220), pauses=True)
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    # polling: tunggu captcha render & token var muncul (max 15s)
                    for _pw in range(15):
                        await asyncio.sleep(1)
                        has_cap = await lead_page.evaluate("""() => {
                            if (document.getElementById('captcha-active')) return true;
                            for (const s of document.querySelectorAll('script[src]'))
                                if (s.src.includes('captcha4')||s.src.includes('captcha2')) return true;
                            return false;
                        }""")
                        if not lead_token_var:
                            lead_token_var=await lead_page.evaluate("""() => {
                                let m=document.body.innerHTML.match(/var\\s+token\\s*=\\s*['"]([a-f0-9]{40,80})['"]/);
                                if(m) return m[1];
                                for(const s of document.querySelectorAll('script')){const mm=(s.textContent||'').match(/var\\s+token\\s*=\\s*['"]([a-f0-9]{40,80})['"]/); if(mm) return mm[1];}
                                return '';
                            }""")
                        if has_cap and lead_token_var: break
                    log(f"lead token_var: {lead_token_var[:24] or '(KOSONG)'}...")
                    if not lead_token_var:
                        log("lead token kosong — dump page:","warn")
                        log((await lead_page.evaluate("()=>document.body.innerText.substring(0,300)"))[:300])
                    log("AUTO-SOLVING captcha (max 3x)...","title")
                    solved=False
                    for attempt in range(3):
                        await wait_captcha_ready(lead_page)  # tunggu image captcha fully loaded biar attempt-1 sukses
                        ok,fld,tok=await solve_any_captcha(lead_page, f"lead{i+1}a{attempt+1}")
                        if ok and tok: cap_field=fld; cap_token=tok; solved=True; log(f"SOLVED! field={cap_field}","ok"); break
                        if ok: solved=True; break
                        log(f"attempt {attempt+1} gagal, refresh","warn")
                        try: await lead_page.reload(wait_until="domcontentloaded", timeout=20000)
                        except: pass
                        await asyncio.sleep(3)
                    if not solved: log("gagal 3x → skip","err"); await lead_page.close(); continue
                    await asyncio.sleep(2)
                    sv=await lead_page.evaluate("""async () => {
                        const fd=new FormData(); fd.append('action','start_view');
                        const r=await fetch(location.href,{method:'POST',body:fd,credentials:'include'}); return await r.text();
                    }""")
                    log(f"start_view: '{sv.strip()[:40]}'")
                    if "ok" not in sv.lower():
                        await asyncio.sleep(2)
                        sv=await lead_page.evaluate("""async () => {
                            const fd=new FormData(); fd.append('action','start_view');
                            const r=await fetch(location.href,{method:'POST',body:fd,credentials:'include'}); return await r.text();
                        }""")
                        log(f"start_view retry: '{sv.strip()[:40]}'")
                    # human idle: scroll + mouse move selama timer agar tidak terdeteksi bot idle
                    wait_sec = dur + random.uniform(1.5, 3.2)
                    log(f"human idle {wait_sec:.1f}s (scroll/mousemove)...")
                    await human_idle(lead_page, wait_sec)
                    ajax_url="https://bitcotasks.com/system/ajax.php"
                    pl=await lead_page.evaluate(f"""async () => {{
                        const fd=new FormData(); fd.append('hash','{ah}'); fd.append('sub_id','{SUB_ID}');
                        fd.append('key','{OFFERWALL_KEY}'); fd.append('token','{lead_token_var}');
                        fd.append('action','proccessLead'); if('{cap_field}') fd.append('{cap_field}','{cap_token}');
                        const r=await fetch('{ajax_url}',{{method:'POST',body:fd,credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text();
                    }}""")
                    log(f"proccessLead: {pl[:240]}")
                    ok_flag=('"status":200' in pl or '"status":"success"' in pl or
                             ('success' in pl.lower() and 'error' not in pl.lower()) or
                             ('credited' in pl.lower() and 'error' not in pl.lower()))
                    if ok_flag: log(f"SUCCESS! +{reward}","ok"); success+=1
                    else:
                        await asyncio.sleep(3)
                        pl2=await lead_page.evaluate(f"""async () => {{
                            const fd=new FormData(); fd.append('hash','{ah}'); fd.append('sub_id','{SUB_ID}');
                            fd.append('key','{OFFERWALL_KEY}'); fd.append('token','{lead_token_var}');
                            fd.append('action','proccessLead'); if('{cap_field}') fd.append('{cap_field}','{cap_token}');
                            const r=await fetch('{ajax_url}',{{method:'POST',body:fd,credentials:'include',signal:AbortSignal.timeout(30000)}}); return await r.text();
                        }}""")
                        log(f"retry: {pl2[:180]}")
                        if '"status":200' in pl2 or '"status":"success"' in pl2 or ('success' in pl2.lower() and 'error' not in pl2.lower()):
                            log(f"SUCCESS retry! +{reward}","ok"); success+=1
                    await lead_page.close()
                except Exception as e:
                    log(f"lead err: {e}","err")
                    try: await lead_page.close()
                    except: pass
                log(f"Progress: {success}/{i+1}")
                # jeda antar iklan + micro human activity di offerwall
                await human_scroll(page, direction=random.choice(["down", "up"]), total_px=random.randint(60, 180), pauses=False)
                await asyncio.sleep(random.uniform(2.2, 4.5))
            banner(f"SELESAI • {success}/{total} SUCCESS")
            await asyncio.sleep(5)
    except KeyboardInterrupt: log("Ctrl+C","warn")
    except Exception as e: log(f"Fatal: {e}","err")
    finally:
        if ctx:
            try: await ctx.close()
            except: pass

if __name__=="__main__":
    try: asyncio.run(main())
    finally: cleanup_profile()
