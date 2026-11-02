#!/usr/bin/env python3
"""
1.py - BitcoTasks PTC Auto (bypass 5s refresh via direct fetch)
Flow: firewall auto-solve -> switch_cat -> init_transaction -> lead captcha auto-solve
-> start_view (direct fetch) -> wait -> proccessLead (direct fetch)
"""
import asyncio, json, time, os, re, sys, random
from datetime import datetime
from playwright.async_api import async_playwright

PROXY = {"server":"http://geo.floppydata.com:10080","username":"V49fuDrw0OyV5G4x","password":"OiKSUe1s5YXIykIf"}
OFFERWALL_KEY = "jug2255d9d8w7hvdisoyybsttm43l3"
SUB_ID = "6692"
OFFERWALL = f"https://bitcotasks.com/offerwall/{OFFERWALL_KEY}/{SUB_ID}/"
MAX_ADS = int(os.environ.get("MAX_ADS","105"))
PROFILE = "/tmp/bitco_auto1"
LOGFILE = "/tmp/1py.log"
SOLVER_KEY = "e08d94aa53f80994fd619b2d1dd5b493"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOGFILE,"a") as f: f.write(f"[{ts}] {msg}\n")

os.makedirs(PROFILE, exist_ok=True)
open(LOGFILE,"w").write("")

async def solver_solve_gif(gif_b64):
    import subprocess, tempfile
    for attempt in range(3):
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump({"apikey":SOLVER_KEY,"methods":"bitcogif","base64":gif_b64,"json":1}, f)
                tmpf = f.name
            r = subprocess.run(["curl","-s","--noproxy","*","-m","30","-X","POST",
                "https://api.waryono.my.id/in.php",
                "-H","Content-Type: application/json",
                "--data", f"@{tmpf}"], capture_output=True, text=True, timeout=35)
            os.unlink(tmpf)
            resp = json.loads(r.stdout.strip())
            if resp.get("status") != 1:
                log(f"    solver submit: {resp}"); await asyncio.sleep(3); continue
            rid = resp["request"]
            for _ in range(30):
                await asyncio.sleep(2)
                r2 = subprocess.run(["curl","-s","--noproxy","*","-m","15",
                    f"https://api.waryono.my.id/res.php?apikey={SOLVER_KEY}&action=get&id={rid}&json=1"],
                    capture_output=True, text=True, timeout=20)
                resp2 = json.loads(r2.stdout.strip())
                if resp2.get("status") == 1:
                    m = re.search(r'x:(\d+),y:(\d+)', resp2["request"])
                    if m: return int(m.group(1)), int(m.group(2))
                elif "UNSOLVABLE" in str(resp2): return None
        except Exception as e:
            log(f"    solver err (try {attempt+1}): {e}")
            await asyncio.sleep(4)
    return None

async def solve_captcha(page, cap_js_url, tag):
    """Solve captcha given JS URL. Returns (ok, field, token)."""
    log(f"  [{tag}] solving...")
    # 1. GET JS for field mapping + validate pattern
    js_text = await page.evaluate(f"""async () => {{
        const r = await fetch('{cap_js_url}', {{credentials:'include'}});
        return await r.text();
    }}""")
    
    real_field, resp_key = "atxrN", "token"
    m = re.search(r"getElementById\(['\"]([a-zA-Z0-9_]+)['\"]\)\.value\s*=\s*response\.([a-zA-Z0-9_]+)", js_text)
    if m: real_field, resp_key = m.group(1), m.group(2)
    
    short_id = None
    m = re.search(r"captcha2/([a-zA-Z0-9]{3,8})\?action=data", js_text)
    if m: short_id = m.group(1)
    
    # 2. POST challenge {t, r} -> get image + keys
    t = int(time.time()*1000); rnd = random.random()
    chal = await page.evaluate(f"""async () => {{
        const r = await fetch('{cap_js_url}', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify({{t:{t}, r:{rnd}}}), credentials:'include'
        }});
        return await r.text();
    }}""")
    
    try: cj = json.loads(chal)
    except: cj = {}
    
    img = cj.get("image") or cj.get("preload") or ""
    if img.startswith("data:"): img = img.split(",",1)[1]
    # Parse payload var: 'BcFOMB=PURqVm&emaz=' -> sk=BcFOMB sk_val=PURqVm ck=emaz
    payload_m = re.search(r"var\s+payload\s*=\s*['\"]([^'\"]+)['\"]", js_text)
    sk = ck = sk_val = ""
    if payload_m:
        parts = payload_m.group(1).split("&")
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                if v:  # has value = static key
                    sk, sk_val = k, v
                else:  # empty value = coords key
                    ck = k
    def jsvar(name):
        m = re.search(rf"var\s+{name}\s*=\s*['\"]([^'\"]+)['\"]", js_text)
        return m.group(1) if m else ""
    if not sk: sk = cj.get("static_key") or jsvar("static_key") or jsvar("sk")
    if not ck: ck = cj.get("coords_key") or jsvar("coords_key") or jsvar("ck")
    if not sk_val: sk_val = cj.get("sk") or jsvar("ok") or "x"
    cdata = cj.get("cdata") or jsvar("cdata") or ""
    # Extract short_id + cdata from xhr.open URL pattern
    m = re.search(r"captcha2/([a-zA-Z0-9]{3,6})\?action=data&cdata=([a-f0-9]+)", js_text)
    if m:
        if not short_id: short_id = m.group(1)
        if not cdata: cdata = m.group(2)
    if not short_id:
        m = re.search(r"captcha2/([a-zA-Z0-9]{3,8})\?action=data", js_text)
        if m: short_id = m.group(1)
    
    log(f"    payload: sk={sk}={sk_val} ck={ck} shortId={short_id} cdata={str(cdata)[:20]} imgLen={len(img)}")
    
    if not img or not sk or not ck:
        log(f"    challenge missing keys: {list(cj.keys())[:12]}")
        return False, real_field, ""
    
    # 3. Solve
    coords = await solver_solve_gif(img)
    if not coords:
        log(f"    solver failed"); return False, real_field, ""
    x, y = coords
    log(f"    coords={x},{y}")
    await asyncio.sleep(4)  # human delay
    
    # 4. POST coords
    post_url = f"https://bitcotasks.com/captcha2/{short_id}?action=data&cdata={cdata}"
    body = f"{sk}={sk_val}&{ck}=[{x},{y}]"
    val = await page.evaluate(f"""async () => {{
        const r = await fetch('{post_url}', {{
            method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
            body:'{body}', credentials:'include'
        }});
        return await r.text();
    }}""")
    log(f"    validate: {val[:120]}")
    
    try:
        vj = json.loads(val)
        tok = vj.get(resp_key)
        if not tok:
            for k,v in vj.items():
                if isinstance(v,str) and len(v)>=30 and re.match(r'^[a-f0-9]+$',v):
                    tok=v; real_field=k; break
        if tok:
            log(f"    SOLVED field={real_field} tok={tok[:20]}...")
            return True, real_field, str(tok)
    except: pass
    if "ok" in val.lower():
        log(f"    SOLVED (ok)"); return True, real_field, ""
    return False, real_field, ""

async def find_cap_js(page):
    return await page.evaluate("""() => {
        for (const s of document.querySelectorAll('script[src]'))
            if (s.src.includes('captcha2') && s.src.includes('.js')) return s.src;
        const m = document.body.innerHTML.match(/(captcha2\\/[a-zA-Z0-9]+\\.js\\?action=captcha)/);
        return m ? 'https://bitcotasks.com/'+m[1] : null;
    }""")

async def main():
    log("="*55)
    log("1.py START - direct proccessLead bypass refresh")
    log("="*55)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE, executable_path="/usr/bin/google-chrome",
            headless=False, proxy=PROXY, viewport={"width":1280,"height":900},
            args=["--no-sandbox","--disable-blink-features=AutomationControlled","--start-maximized",
                  "--disable-infobars","--mute-audio","--disable-popup-blocking","--no-first-run",
                  "--no-default-browser-check","--lang=en-US"],
            timezone_id="Asia/Makassar", locale="en-US")
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        
        log("Navigating...")
        try: await page.goto(OFFERWALL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e: log(f"nav err: {e}")
        await asyncio.sleep(4)
        log(f"URL: {page.url[:100]}")
        
        # Firewall
        if "firewall" in page.url:
            log("Firewall -> auto-solve")
            for att in range(6):
                cap = await find_cap_js(page)
                if not cap:
                    log("  no captcha JS, navigating to offerwall")
                    break
                ok, fld, tok = await solve_captcha(page, cap, f"fw{att+1}")
                redirect_url = None
                if ok and tok:
                    v = await page.evaluate(f"""async () => {{
                        const fd = new FormData();
                        fd.append('action','validate');
                        fd.append('{fld}','{tok}');
                        const r = await fetch(location.href, {{method:'POST', body:fd, credentials:'include'}});
                        return await r.text();
                    }}""")
                    log(f"  validate: {v[:120]}")
                    try:
                        vj = json.loads(v)
                        if vj.get("status") == "success" and vj.get("redirect"):
                            redirect_url = vj["redirect"]
                    except: pass
                await asyncio.sleep(3)
                goto_url = redirect_url or OFFERWALL
                try: await page.goto(goto_url, wait_until="domcontentloaded", timeout=60000)
                except: pass
                await asyncio.sleep(4)
                if "firewall" not in page.url:
                    log("  FIREWALL PASSED"); break
                try: await page.reload(wait_until="domcontentloaded", timeout=30000)
                except: pass
                await asyncio.sleep(3)
        
        log(f"URL: {page.url[:100]}")
        
        # Extract ajax token
        ajax_tok = await page.evaluate("""() => {
            let m = document.body.innerHTML.match(/var\\s+token\\s*=\\s*['"]([a-f0-9]{40,80})['"]/);
            if (m) return m[1];
            for (const s of document.querySelectorAll('script')) {
                const mm = (s.textContent||'').match(/['"]?token['"]?\\s*[:=]\\s*['"]([a-f0-9]{40,80})['"]/);
                if (mm) return mm[1];
            }
            return null;
        }""")
        log(f"AJAX token: {str(ajax_tok)[:25]}...")
        if not ajax_tok:
            log("NO TOKEN! dump:")
            log((await page.evaluate("()=>document.body.innerHTML.substring(0,1000)"))[:1000])
            await asyncio.sleep(3600); return
        
        # switch_cat
        sc = await page.evaluate(f"""async () => {{
            const fd = new FormData();
            fd.append('token','{ajax_tok}'); fd.append('action','switch_cat'); fd.append('type','ptc');
            const r = await fetch(location.href, {{method:'POST', body:fd, credentials:'include'}});
            return await r.text();
        }}""")
        log(f"switch_cat len={len(sc)}: {sc[:250]}")
        
        ads = []
        try:
            scj = json.loads(sc)
            if isinstance(scj, dict):
                for k in ["data","ads","ptc","offers","list","items"]:
                    if isinstance(scj.get(k), list): ads=scj[k]; break
                if not ads:
                    for v in scj.values():
                        if isinstance(v,list) and v and isinstance(v[0],dict): ads=v; break
            elif isinstance(scj, list): ads=scj
        except:
            for u in re.findall(r'href=["\']([^"\']*lead[^"\']*)', sc):
                hm = re.search(r'/lead/([^/]+)', u)
                ads.append({"href":u, "title":"ad", "hash": hm.group(1) if hm else ""})
        
        log(f"ADS: {len(ads)}")
        for i,a in enumerate(ads[:MAX_ADS]): log(f"  [{i}] {json.dumps(a)[:180]}")
        if not ads:
            log("No ads!"); await asyncio.sleep(3600); return
        
        success = 0
        for i, ad in enumerate(ads[:MAX_ADS]):
            log(f"\n{'='*45}\nAD {i+1}/{min(MAX_ADS,len(ads))}")
            ah = ad.get("hash") or ad.get("id") or ""
            if not ah and ad.get("href"):
                hm = re.search(r'/lead/([^/]+)', ad["href"])
                if hm: ah = hm.group(1)
            title = str(ad.get("title") or ad.get("name") or ah)[:40]
            reward = ad.get("reward") or ad.get("amount") or "?"
            dur = int(ad.get("duration") or ad.get("timer") or ad.get("seconds") or 5)
            log(f"  {title} +{reward} {dur}s hash={ah}")
            
            # init_transaction
            initr = await page.evaluate(f"""async () => {{
                const fd = new FormData();
                fd.append('token','{ajax_tok}'); fd.append('action','init_transaction');
                fd.append('hash','{ah}'); fd.append('sid','{SUB_ID}');
                fd.append('key','{OFFERWALL_KEY}'); fd.append('type','ptc');
                const r = await fetch(location.href, {{method:'POST', body:fd, credentials:'include'}});
                return await r.text();
            }}""")
            log(f"  init: {initr[:150]}")
            
            lead_tok = None
            try:
                ij = json.loads(initr)
                offer_url = ij.get("offer") or ij.get("url") or ij.get("redirect") or ""
                mm = re.search(r'/lead/[^/]+/[^/]+/[^/]+/([a-zA-Z0-9]+)', offer_url)
                if mm: lead_tok = mm.group(1)
            except Exception as e:
                log(f"  init parse err: {e}")
            if not lead_tok:
                mm = re.search(r'/lead/[^/]+/[^/]+/[^/]+/([a-zA-Z0-9]+)', initr.replace("\\/","/"))
                if mm: lead_tok = mm.group(1)
            
            if not lead_tok:
                log("  no lead token, skip"); continue
            
            lead_url = f"https://bitcotasks.com//lead/{ah}/{OFFERWALL_KEY}/{SUB_ID}/{lead_tok}"
            log(f"  lead token: {lead_tok[:20]}...")
            
            # Open lead page in browser tab - USER solves captcha manually via VNC
            log(f"  >>> OPENING lead tab - solve captcha manually via VNC! <<<")
            lead_page = await ctx.new_page()
            lead_token_var = ""
            cap_field = cap_token = ""
            try:
                await lead_page.goto(lead_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                # Extract lead-specific token from page JS
                lead_token_var = await lead_page.evaluate("""() => {
                    let m = document.body.innerHTML.match(/var\\s+token\\s*=\\s*['"]([a-f0-9]{40,80})['"]/);
                    if (m) return m[1];
                    for (const s of document.querySelectorAll('script')) {
                        const mm = (s.textContent||'').match(/var\\s+token\\s*=\\s*['"]([a-f0-9]{40,80})['"]/);
                        if (mm) return mm[1];
                    }
                    return '';
                }""")
                log(f"  lead token_var: {lead_token_var[:24]}...")
                # Reposition captcha panel to left
                await lead_page.evaluate("""() => {
                    const move = () => {
                        document.querySelectorAll('div, section, form').forEach(el => {
                            const r = el.getBoundingClientRect();
                            const txt = (el.innerText||'').toLowerCase();
                            if ((r.left > window.innerWidth-80 && r.width>150 && r.width<700) ||
                                ((txt.includes('verifikasi')||txt.includes('verification')||txt.includes('klik ikon')||txt.includes('captcha')) && r.width>150 && r.width<700 && r.height>150)) {
                                el.style.setProperty('left','10px','important');
                                el.style.setProperty('right','auto','important');
                                el.style.setProperty('position','fixed','important');
                                el.style.setProperty('top','50px','important');
                                el.style.setProperty('z-index','999999','important');
                                el.style.setProperty('max-width','340px','important');
                            }
                        });
                    };
                    move(); setInterval(move, 1500);
                }""")
                log(f"  lead tab open - AUTO-SOLVING captcha (max 3 attempts)...")
                await lead_page.bring_to_front()
                # AUTO-SOLVE with BitcoGIF solver, retry up to 3x
                solved = False
                for attempt in range(3):
                    cap_url = await lead_page.evaluate("""() => {
                        for (const s of document.querySelectorAll('script[src]'))
                            if (s.src.includes('captcha2') && s.src.includes('.js')) return s.src;
                        const m = document.body.innerHTML.match(/(captcha2\\/[a-zA-Z0-9]+\\.js\\?action=captcha)/);
                        return m ? 'https://bitcotasks.com/'+m[1] : null;
                    }""")
                    if not cap_url:
                        log(f"    no captcha (already solved?)"); solved = True; break
                    ok, fld, tok = await solve_captcha(lead_page, cap_url, f"lead{i+1}a{attempt+1}")
                    if ok and tok:
                        cap_field = fld; cap_token = tok; solved = True
                        log(f"  >>> AUTO-SOLVED! field={cap_field} tok={cap_token[:24]}...")
                        break
                    elif ok:
                        solved = True; break
                    log(f"    attempt {attempt+1} failed, refreshing challenge...")
                    try: await lead_page.reload(wait_until="domcontentloaded", timeout=20000)
                    except: pass
                    await asyncio.sleep(3)
                if not solved:
                    log("  AUTO-SOLVE failed after 3 attempts, skipping ad")
                    await lead_page.close()
                    continue
                
                # KEEP lead page focused - call start_view and proccessLead from LEAD page
                await lead_page.bring_to_front()
                await asyncio.sleep(2)
                
                # start_view from lead page context (POST to lead URL)
                sv = await lead_page.evaluate("""async () => {
                    const fd = new FormData(); fd.append('action','start_view');
                    const r = await fetch(location.href, {method:'POST', body:fd, credentials:'include'});
                    return await r.text();
                }""")
                log(f"  start_view: '{sv.strip()[:40]}'")
                
                if "ok" not in sv.lower():
                    await asyncio.sleep(2)
                    sv = await lead_page.evaluate("""async () => {
                        const fd = new FormData(); fd.append('action','start_view');
                        const r = await fetch(location.href, {method:'POST', body:fd, credentials:'include'});
                        return await r.text();
                    }""")
                    log(f"  start_view retry: '{sv.strip()[:40]}'")
                
                # Wait duration - keep lead page focused
                log(f"  waiting {dur+2}s (keep lead tab focused)...")
                await asyncio.sleep(dur + 2)
                
                # proccessLead from LEAD page context to system/ajax.php with lead token
                ajax_url = "https://bitcotasks.com/system/ajax.php"
                pl = await lead_page.evaluate(f"""async () => {{
                    const fd = new FormData();
                    fd.append('hash','{ah}');
                    fd.append('sub_id','{SUB_ID}');
                    fd.append('key','{OFFERWALL_KEY}');
                    fd.append('token','{lead_token_var}');
                    fd.append('action','proccessLead');
                    fd.append('{cap_field}','{cap_token}');
                    const r = await fetch('{ajax_url}', {{method:'POST', body:fd, credentials:'include'}});
                    return await r.text();
                }}""")
                log(f"  proccessLead: {pl[:300]}")
                
                if ('"status":200' in pl or '"status":"success"' in pl or 
                    ('success' in pl.lower() and 'error' not in pl.lower()) or
                    ('credited' in pl.lower() and 'error' not in pl.lower())):
                    log(f"  >>> SUCCESS! +{reward} ✅✅✅")
                    success += 1
                else:
                    await asyncio.sleep(3)
                    pl2 = await lead_page.evaluate(f"""async () => {{
                        const fd = new FormData();
                        fd.append('hash','{ah}');
                        fd.append('sub_id','{SUB_ID}');
                        fd.append('key','{OFFERWALL_KEY}');
                        fd.append('token','{lead_token_var}');
                        fd.append('action','proccessLead');
                        fd.append('{cap_field}','{cap_token}');
                        const r = await fetch('{ajax_url}', {{method:'POST', body:fd, credentials:'include'}});
                        return await r.text();
                    }}""")
                    log(f"  proccessLead retry: {pl2[:200]}")
                    if ('"status":200' in pl2 or '"status":"success"' in pl2 or
                        ('success' in pl2.lower() and 'error' not in pl2.lower())):
                        log(f"  >>> SUCCESS on retry! +{reward} ✅")
                        success += 1
                
                await lead_page.close()
            except Exception as e:
                log(f"  lead page err: {e}")
                try: await lead_page.close()
                except: pass
            
            log(f"  RUNNING: {success}/{i+1}")
            await asyncio.sleep(3)
        
        log(f"\n{'='*45}\nDONE! {success}/{min(MAX_ADS,len(ads))} SUCCESS\n{'='*45}")
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
