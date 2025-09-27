import os, socket, time, uuid, random, threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

START_TS = time.time()
INSTANCE_ID = str(uuid.uuid4())[:8]
EMOJIS = ["🚀","🦄","🐙","🦾","🧠","🐳","🛰️","🦖","🛸","⚡"]
COLOR = os.getenv("APP_COLOR") or f"hsl({random.randint(0,360)}, 75%, 55%)"
LABEL = os.getenv("APP_LABEL", "k8s-demo")

app = FastAPI(title="k8s-demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

REQ_COUNT = 0

def hostname():
    return os.getenv("HOSTNAME") or socket.gethostname()

@app.get("/whoami")
def whoami(request: Request):
    global REQ_COUNT
    REQ_COUNT += 1
    client_ip = request.client.host if request.client else "unknown"
    return {
        "label": LABEL,
        "instance_id": INSTANCE_ID,
        "emoji": random.choice(EMOJIS),
        "pod_name": hostname(),
        "pod_ip": os.getenv("POD_IP"),
        "client_ip": client_ip,
        "started": START_TS,
        "uptime_s": round(time.time() - START_TS, 1),
        "request_count": REQ_COUNT,
        "color": COLOR,
    }

@app.get("/", response_class=HTMLResponse)
def index():
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>k8s load-balancer visualizer</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    html,body {{ margin:0; font-family:ui-sans-serif,system-ui; background:#0b1020; color:#e6e8f1; }}
    .wrap {{ display:grid; place-items:center; height:100vh; gap:18px; }}
    .card {{
      width:min(92vw,720px); padding:24px 28px; border-radius:16px;
      background:#151b34; box-shadow:0 10px 30px rgba(0,0,0,.35);
    }}
    .pill {{ display:inline-block; padding:6px 10px; border-radius:999px; background:#232b52; font-size:12px; letter-spacing:.4px }}
    h1 {{ margin:6px 0 16px; font-size:28px }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px }}
    .kv {{ background:#0f1630; border-radius:12px; padding:12px 14px; }}
    .tag {{ color:#9fb0ff; font-size:12px; letter-spacing:.3px }}
    .v  {{ font-size:15px; margin-top:2px }}
    .badge {{ margin-top:14px; border-radius:14px; padding:10px 14px; font-weight:700; display:inline-flex; align-items:center; gap:10px }}
    .foot {{ opacity:.75; font-size:12px; margin-top:10px }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }}
    a {{ color:#9fb0ff; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <span class="pill">Kubernetes load-balancing demo</span>
      <h1>Which pod handled this request?</h1>
      <div id="badge" class="badge">loading…</div>
      <div class="grid" id="grid"></div>
      <div class="foot">
        Auto-refreshes every second. Try scaling replicas or hitting <span class="mono">/stress?seconds=30&threads=2</span> to trigger HPA.
      </div>
    </div>
  </div>
<script>
async function refresh() {{
  try {{
    const r = await fetch('/whoami', {{ cache: 'no-store' }});
    const j = await r.json();
    const grid = document.getElementById('grid');
    const badge = document.getElementById('badge');
    badge.style.background = j.color;
    badge.innerHTML = `${{j.emoji}}&nbsp; <span class="mono">${{j.pod_name}}</span>`;

    const rows = [
      ["Label", j.label],
      ["Instance ID", j.instance_id],
      ["Pod IP", j.pod_ip || "—"],
      ["Client IP", j.client_ip],
      ["Uptime (s)", j.uptime_s],
      ["Requests (this pod)", j.request_count],
      ["Color", j.color]
    ];
    grid.innerHTML = rows.map(([k,v]) => `
      <div class="kv">
        <div class="tag">${{k}}</div>
        <div class="v mono">${{v}}</div>
      </div>`).join('');
  }} catch(e) {{
    console.error(e);
  }}
}}
setInterval(refresh, 1000);
refresh();
</script>
</body>
</html>
    """

@app.get("/ready", response_class=PlainTextResponse)
def ready():  # readiness probe
    return "ok"

@app.get("/live", response_class=PlainTextResponse)
def live():   # liveness probe
    return "ok"

@app.get("/stress", response_class=PlainTextResponse)
def stress(seconds: int = 20, threads: int = 1):
    """Burn CPU to help HPA scale: /stress?seconds=30&threads=2"""
    stop_at = time.time() + max(1, min(seconds, 600))
    def burn():
        x = 0.0
        while time.time() < stop_at:
            x = x * 1.000001 + 3.14159  # tight loop
        return x
    for _ in range(max(1, min(threads, 16))):
        threading.Thread(target=burn, daemon=True).start()
    return f"stressing CPU for {seconds}s using {threads} thread(s)"
