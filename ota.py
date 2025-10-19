# ota.py — ESP 32 OTA / Dev Testing
# Dark IDE UI + Logs + Web Shell + Basic Auth
# (no f-strings / no '%' formatting / no sys.stdout reassignment)

import socket, os, time, sys, _thread, machine

__version__ = "devtesting-1.0"

PORT = 80
PROTECTED = {"boot.py", "ota.py"}  # cannot delete these

# ---------- Basic Auth ----------
# change these to your own credentials
USER = "admin"
PASSWORD = "admin"
REQUIRE_AUTH = True  # set False to disable auth

try:
    import ubinascii as _b64
except:
    _b64 = None

if REQUIRE_AUTH and _b64:
    _AUTH_TOKEN = "Basic " + _b64.b2a_base64((USER + ":" + PASSWORD).encode()).decode().strip()
else:
    _AUTH_TOKEN = None

def _auth_ok(headers):
    if not REQUIRE_AUTH or _AUTH_TOKEN is None:
        return True
    return headers.get("authorization", "") == _AUTH_TOKEN

def _unauth(conn):
    _send(conn,
          "HTTP/1.1 401 Unauthorized\r\n"
          "WWW-Authenticate: Basic realm=\"ESP32-OTA\"\r\n"
          "Connection: close\r\n"
          "Content-Type: text/plain\r\n\r\n"
          "Auth required")

# ---------- tiny log buffer ----------
LOG_BUF = ""

def _log_add(s):
    global LOG_BUF
    if not isinstance(s, str):
        try: s = str(s)
        except: s = "<bin>"
    LOG_BUF = (LOG_BUF + s)[-8192:]  # keep last ~8KB

# ---------- runner ----------
_RUN_ACTIVE = False
_RUN_NAME = None

def _runner(fname):
    # Run user code; capture prints/exceptions into LOG_BUF without touching sys.stdout
    global _RUN_ACTIVE, _RUN_NAME
    _RUN_ACTIVE, _RUN_NAME = True, fname
    try:
        code = open(fname, "r").read()

        # local print that logs
        def log_print(*args, **kwargs):
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            try:
                s = sep.join([str(a) for a in args]) + end
            except:
                s = "[unprintable]\n"
            _log_add(s)

        g = {"__name__": "__main__", "print": log_print}
        exec(compile(code, fname, "exec"), g)

    except Exception as e:
        try:
            import uio
            s = uio.StringIO()
            try:
                sys.print_exception(e, s)
                _log_add(s.getvalue())
            except:
                _log_add("Exception: " + str(e) + "\n")
        except:
            _log_add("Exception: " + str(e) + "\n")
    finally:
        _RUN_ACTIVE, _RUN_NAME = False, None

def run_async(fname):
    _thread.start_new_thread(_runner, (fname,))

# ---------- simple web shell (REPL) ----------
REPL_G = {"__name__": "__repl__"}  # persistent globals across commands

def _repl_exec(src):
    g = REPL_G
    out_parts = []

    def log_print(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        try:
            s = sep.join([str(a) for a in args]) + end
        except:
            s = "[unprintable]\n"
        out_parts.append(s)
        _log_add(s)

    g["print"] = log_print

    if src.strip() in (":reset", "%reset"):
        REPL_G.clear(); REPL_G["__name__"] = "__repl__"; REPL_G["print"] = log_print
        txt = "REPL state cleared.\n"
        out_parts.append(txt); _log_add(txt)
        return "OK\n" + "".join(out_parts)

    try:
        try:
            result = eval(src, g)
            if result is not None:
                s = repr(result) + "\n"
                out_parts.append(s); _log_add(s)
        except SyntaxError:
            exec(src, g)
        return "OK\n" + "".join(out_parts)
    except Exception as e:
        try:
            import uio
            s = uio.StringIO()
            try:
                sys.print_exception(e, s)
                tb = s.getvalue()
            except:
                tb = "Exception: " + str(e) + "\n"
        except:
            tb = "Exception: " + str(e) + "\n"
        _log_add(tb)
        return "ERR\n" + "".join(out_parts) + tb

# ---------- HTTP helpers ----------
def _send(conn, s):
    if isinstance(s, str): s = s.encode()
    conn.sendall(s)

def _ok(conn, ctype="text/html"):
    _send(conn, "HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Type: " + ctype + "\r\nCache-Control: no-store\r\n\r\n")

def _bad(conn, msg="Bad Request"):
    _send(conn, "HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n"); _send(conn, msg)

def _read_head(conn, maxlen=65536):
    data = b""
    while b"\r\n\r\n" not in data and len(data) < maxlen:
        c = conn.recv(1024)
        if not c: break
        data += c
    if b"\r\n\r\n" not in data: return None, None, None, None
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.decode().split("\r\n")
    if not lines: return None, None, None, None
    req = lines[0].split(" ", 2)
    if len(req) < 3: return None, None, None, None
    method, path, _ = req
    hdrs = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            hdrs[k.strip().lower()] = v.strip()
    if hdrs.get("expect","").lower() == "100-continue":
        try: _send(conn, "HTTP/1.1 100 Continue\r\n\r\n")
        except: pass
    return method, path, hdrs, body

def _parse_qs(path):
    if "?" not in path: return path, {}
    r, qs = path.split("?", 1)
    out = {}
    for p in qs.split("&"):
        if "=" in p: k, v = p.split("=", 1)
        else: k, v = p, ""
        out.setdefault(k, []).append(v)
    return r, out

def _sanitize(name):
    # allow only [A-Za-z0-9._-]
    out = []
    for ch in name:
        o = ord(ch)
        if (48 <= o <= 57) or (65 <= o <= 90) or (97 <= o <= 122) or ch in "._-":
            out.append(ch)
    s = "".join(out)
    return s or "app.py"

# ---------- urlencoded body -> dict ----------
def _urldecode(b):
    s = b.decode().replace("+", " ")
    res = ""
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "%" and i+2 < n:
            try:
                res += chr(int(s[i+1:i+3], 16)); i += 3; continue
            except: pass
        res += ch; i += 1
    out = {}
    for pair in res.split("&"):
        if "=" in pair: k, v = pair.split("=", 1)
        else: k, v = pair, ""
        out.setdefault(k, []).append(v)
    return out

# ---------- HTML UI ----------
def _html(ip, mode, msg):
    import os
    files = sorted(os.listdir())
    listing = ""
    for f in files:
        if f in PROTECTED:
            listing += '<div class="file item"><span class="name">'+f+'</span></div>'
        else:
            listing += (
                '<div class="file item"><span class="name">'+f+'</span> '
                '<a class="danger" href="/del?f='+f+'" '
                'onclick="return confirm(\'Delete '+f+'?\')">delete</a></div>'
            )

    run_info = "IDLE" if not _RUN_ACTIVE else "ACTIVE · " + (_RUN_NAME or "")
    if msg is None:
        msg = ""

    h  = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    h += '<title>ESP 32 OTA / Dev Testing</title>'

    # =========================
    # Styles (with box-sizing fix and unified inner boxes)
    # =========================
    h += "<style>"
    h += ":root{--bg:#0b0f14;--panel:#0f1520;--muted:#9fb1c7;--text:#e6edf3;--line:#243041;--accent:#6ea8fe;--accent2:#1f6feb;--ok:#3fb950;--err:#f85149;--btn:#0d1117}"
    h += "*,*::before,*::after{box-sizing:border-box}"
    h += "html,body{height:100%}"
    h += "body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,Monaco,monospace}"
    h += ".wrap{max-width:1100px;margin:24px auto;padding:0 16px}"
    h += ".headline{font-size:20px;font-weight:700;margin:0 0 14px}"
    h += ".meta{color:var(--muted);margin:6px 0 18px}"
    h += ".card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin:18px 0;box-shadow:0 6px 20px rgba(0,0,0,.25)}"
    h += "label,input,button{font:inherit}"
    h += "input[type=text]{width:260px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:.5rem .6rem;outline:none}"
    h += "input[type=text]:focus{border-color:var(--accent)}"
    h += "button{background:var(--btn);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:.55rem .9rem;cursor:pointer}"
    h += "button:hover{border-color:var(--accent)}"
    h += ".accent{border-color:var(--accent);background:linear-gradient(180deg,#0f1a2a,#0b1322)}"
    h += "a{color:var(--accent)}a:hover{color:var(--accent2)}"
    h += ".row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:.4rem 0}"
    # Unified inner editor boxes
    h += "textarea{display:block;width:100%;min-height:320px;resize:vertical;background:#0a1018;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:12px 14px;outline:none;line-height:1.45}"
    h += "textarea:focus{border-color:var(--accent)}"
    h += "#repl_in{display:block;width:100%;min-height:240px;line-height:1.45;background:#0a1018;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:12px 14px;outline:none;resize:vertical}"
    h += "pre#log,pre#repl_out{display:block;width:100%;max-height:260px;overflow:auto;white-space:pre-wrap;background:#0a1018;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:0}"
    h += ".status{position:sticky;top:0;z-index:5;margin:0 0 12px;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:#0a111a88;backdrop-filter:blur(6px)}"
    h += ".status.ok{border-color:var(--ok);color:var(--ok)}.status.err{border-color:var(--err);color:var(--err)}"
    h += ".files{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px}"
    h += ".file.item{padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:#0a1018}"
    h += ".file .name{color:#dbe7ff}"
    h += ".file .danger{color:var(--err);text-decoration:none;margin-left:8px}.file .danger:hover{text-decoration:underline}"
    h += ".bar{display:flex;justify-content:space-between;align-items:center;margin:6px 0}"
    h += ".hint{color:var(--muted);font-size:12px}.count{color:var(--muted);font-size:12px}"
    h += "</style>"

    # =========================
    # Body
    # =========================
    h += '<div class="wrap"><h1 class="headline">ESP 32 OTA / Dev Testing</h1>'
    h += '<div class="meta">Mode <b>'+mode+'</b> · IP <b>'+ip+'</b> · Runner <b>'+run_info+'</b></div>'

    status_class = "status"
    if msg.startswith("OK:"):
        status_class += " ok"
    elif msg.startswith("ERR:") or msg.startswith("Exception"):
        status_class += " err"
    h += '<div class="'+status_class+'">'+(msg.replace("<","&lt;") if msg else "Ready.")+'</div>'

    # 1) Files
    h += '<div class="card"><h3 style="margin:0 0 10px">Files</h3><div class="files">'+listing+'</div></div>'

    # 2) Run existing
    h += (
        '<div class="card"><h3 style="margin:0 0 10px">Run existing</h3>'
        '<form method="GET" action="/run" class="row">'
        '<input name="f" value="app.py" placeholder="filename.py">'
        '<button type="submit">Run</button>'
        '</form></div>'
    )

    # 3) Paste code, save & run
    h += (
        '<div class="card"><h3 style="margin:0 0 10px">Paste code, save & run</h3>'
        '<form method="POST" action="/save" id="saveform">'
        '<div class="row">'
        '<label>Save as:</label><input name="name" id="name" type="text" value="app.py" required>'
        '<label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="run" value="1" checked> Run immediately (background)</label>'
        '<button class="accent" type="submit" id="saveBtn">Save & Run</button>'
        '<button type="submit" id="saveOnly">Save only</button>'
        '</div>'
        '<textarea name="code" id="code" placeholder="# paste your MicroPython here"></textarea>'
        '<div class="bar"><span class="hint">Tip: ⌘/Ctrl + S to Save & Run</span><span class="count" id="count">0 lines, 0 chars</span></div>'
        '</form></div>'
    )

    # 4) Logs
    h += (
        '<div class="card"><h3 style="margin:0 0 10px">Logs</h3>'
        '<pre id="log"></pre>'
        '</div>'
    )

    # 5) Shell
    h += (
        '<div class="card"><h3 style="margin:0 0 10px">Shell</h3>'
        '<div class="row"><span class="hint">Type Python here. Enter or ⌘/Ctrl+Enter to run. Use <code>:reset</code> to clear state.</span></div>'
        '<textarea id="repl_in" placeholder="print(\'hello\')\\n2+2"></textarea>'
        '<div class="bar"><div class="hint">&nbsp;</div><button id="repl_btn" type="button">Run</button></div>'
        '<pre id="repl_out"></pre>'
        '</div>'
    )

    # 6) Hard reset (last)
    h += '<div class="card"><a href="/reset">Hard reset</a></div>'

    # =========================
    # Scripts
    # =========================
    h += '<script>(function(){'
    # live char counter
    h += 'var code=document.getElementById("code");var count=document.getElementById("count");function upd(){var t=code.value;var lines=(t.match(/\\n/g)||[]).length+(t.length?1:0);count.textContent=lines+" lines, "+t.length+" chars";}code.addEventListener("input",upd);upd();'
    # cmd/ctrl+s to submit
    h += 'document.addEventListener("keydown",function(e){if((e.ctrlKey||e.metaKey)&&e.key==="s"){e.preventDefault();document.getElementById("saveform").submit();}});'
    # localStorage persistence
    h += 'var nameEl=document.getElementById("name");try{nameEl.value=localStorage.getItem("mpy_name")||nameEl.value;code.value=localStorage.getItem("mpy_code")||code.value;upd();nameEl.addEventListener("input",function(){localStorage.setItem("mpy_name",nameEl.value)});code.addEventListener("input",function(){localStorage.setItem("mpy_code",code.value)});}catch(e){}'
    # Save only toggler
    h += 'var saveOnly=document.getElementById("saveOnly");var runBox=document.querySelector(\'input[name="run"]\');if(saveOnly){saveOnly.addEventListener("click",function(){if(runBox)runBox.checked=false;});}'
    # Log poller
    h += 'var logEl=document.getElementById("log");function pollLog(){try{var x=new XMLHttpRequest();x.open("GET","/log",true);x.onreadystatechange=function(){if(x.readyState===4&&x.status===200){logEl.textContent=x.responseText||"";logEl.scrollTop=logEl.scrollHeight;}};x.send();}catch(e){}}setInterval(pollLog,700);pollLog();'
    # Shell
    h += 'var rin=document.getElementById("repl_in");var rout=document.getElementById("repl_out");var rbtn=document.getElementById("repl_btn");function appendOut(s){rout.textContent+=s;rout.scrollTop=rout.scrollHeight;}function runShell(){var codeTxt=rin.value;if(!codeTxt.trim())return;appendOut(">>> "+codeTxt.replace(/\\n/g,"\\n... ")+"\\n");var x=new XMLHttpRequest();x.open("POST","/exec",true);x.setRequestHeader("Content-Type","application/x-www-form-urlencoded");x.onreadystatechange=function(){if(x.readyState===4){if(x.status===200){var t=x.responseText.replace(/^OK\\n/,"").replace(/^ERR\\n/,"");appendOut(t);}else{appendOut("HTTP "+x.status+"\\n");}}};x.send("code="+encodeURIComponent(codeTxt));}if(rbtn){rbtn.addEventListener("click",runShell);}if(rin){rin.addEventListener("keydown",function(e){if((e.key==="Enter"&&(e.ctrlKey||e.metaKey))||(e.key==="Enter"&&e.shiftKey)){e.preventDefault();runShell();}});}'
    h += '})();</script>'

    h += "</div>"
    return h


# ---------- handlers ----------
def _handle_root(conn):
    _ok(conn); _send(conn, _html(ip, mode, ""))

def _handle_save(conn, headers, body_start):
    total = int(headers.get("content-length", "0"))
    body = body_start
    while len(body) < total:
        c = conn.recv(min(2048, total - len(body)))
        if not c: break
        body += c
    form = _urldecode(body)
    name = _sanitize((form.get("name", ["app.py"])[0]).strip() or "app.py")
    code = form.get("code", [""])[0]
    run_now = ("run" in form)

    try:
        with open(name, "w") as f:
            f.write(code)
    except Exception as e:
        _ok(conn); _send(conn, _html(ip, mode, "ERR: Write failed: " + str(e))); return

    if run_now:
        try:
            run_async(name)
            _ok(conn); _send(conn, _html(ip, mode, "OK: Saved " + name + ". Running…")); return
        except Exception as e:
            _ok(conn); _send(conn, _html(ip, mode, "ERR: Saved but failed to run: " + str(e))); return

    _ok(conn); _send(conn, _html(ip, mode, "OK: Saved " + name + "."))

def _handle_run(conn, path):
    route, q = _parse_qs(path)
    name = _sanitize((q.get("f", ["app.py"])[0]).strip() or "app.py")
    if name not in os.listdir():
        _ok(conn); _send(conn, _html(ip, mode, "ERR: " + name + " not found")); return
    run_async(name)
    _ok(conn); _send(conn, _html(ip, mode, "OK: Running " + name + "…"))

def _handle_del(conn, path):
    route, q = _parse_qs(path)
    name = _sanitize((q.get("f", [""])[0]).strip())
    if not name:
        _ok(conn); _send(conn, _html(ip, mode, "ERR: No filename")); return
    if name in PROTECTED:
        _ok(conn); _send(conn, _html(ip, mode, "ERR: Refusing to delete " + name)); return
    if name not in os.listdir():
        _ok(conn); _send(conn, _html(ip, mode, "ERR: " + name + " not found")); return
    try:
        os.remove(name)
        _ok(conn); _send(conn, _html(ip, mode, "OK: Deleted " + name))
    except Exception as e:
        _ok(conn); _send(conn, _html(ip, mode, "ERR: Delete failed: " + str(e)))

def _handle_log(conn):
    _ok(conn, "text/plain"); _send(conn, LOG_BUF)

def _handle_exec(conn, headers, body_start):
    total = int(headers.get("content-length", "0"))
    body = body_start
    while len(body) < total:
        c = conn.recv(min(2048, total - len(body)))
        if not c: break
        body += c
    form = _urldecode(body)
    code = form.get("code", [""])[0]
    res = _repl_exec(code)
    _ok(conn, "text/plain"); _send(conn, res)

# ---------- server ----------
def start(ip="0.0.0.0", mode="STA"):
    globals()["ip"] = ip
    globals()["mode"] = mode
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT)); s.listen(2)
    print("HTTP server on", ip, "port", PORT)

    while True:
        conn, _ = s.accept()
        try:
            method, path, headers, body_start = _read_head(conn)
            if method is None:
                _bad(conn, "Bad headers"); conn.close(); continue

            # --- auth gate ---
            if not _auth_ok(headers):
                _unauth(conn); conn.close(); continue

            if method == "GET":
                route, _ = _parse_qs(path)
                if route == "/": _handle_root(conn)
                elif route == "/run": _handle_run(conn, path)
                elif route == "/del": _handle_del(conn, path)
                elif route == "/reset":
                    _ok(conn, "text/plain"); _send(conn, "Reset…")
                    def _r(): time.sleep(0.4); machine.reset()
                    _thread.start_new_thread(_r, ())
                elif route == "/log":
                    _handle_log(conn)
                else:
                    _bad(conn)
            elif method == "POST":
                route, _ = _parse_qs(path)
                if route == "/save":
                    _handle_save(conn, headers, body_start)
                elif route == "/exec":
                    _handle_exec(conn, headers, body_start)
                else:
                    _bad(conn, "Unknown POST")
            else:
                _bad(conn)
        except Exception as e:
            try: _bad(conn, "Exception: " + str(e))
            except: pass
        finally:
            try: conn.close()
            except: pass
