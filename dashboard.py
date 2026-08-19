# -*- coding: utf-8 -*-
"""
SinolifeSalesAdmin — РОП дашбоардлари генератори.

deal_state.json'дан ўқиб, ҳар РОП учун алоҳида HTML саҳифа яратади
(жами сана бўйича филтр, статус бўйича филтр, қидирув билан).
Cron орқали ҳар N дақиқада ишга туширилади ва GitHub'га push қилинади.

Ишлатиш:  python3 dashboard.py
Натижа:   docs/index.html  ва  docs/<rop-slug>-<hash>.html
"""
import json
import hashlib
import html
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=5))  # Тошкент

STATE_DIR = Path(os.environ.get("SA_STATE_DIR", "/root/sinolifesalesadmin_v2/state"))
OUT_DIR = Path(os.environ.get("SA_DASHBOARD_DIR", "/root/sales_dashboard/docs"))
# Ҳавола тахмин қилинмаслиги учун — ҳар РОП файл номига қўшиладиган махфий сўз.
# start.sh'да SA_DASHBOARD_SALT="uzun-tasodifiy-sirli-soz" қилиб қўйинг.
SALT = os.environ.get("SA_DASHBOARD_SALT", "sinolife-default-salt")

STATUS_ORDER = ["confirm_new", "no_answer", "confirmed", "rejected"]
STATUS_LABELS = {
    "confirm_new": ("🕔", "Тасдиқлаш"),
    "no_answer":   ("🟡", "Кутармади (нд)"),
    "confirmed":   ("✅", "Тасдиқланди"),
    "rejected":    ("❌", "Тасдиқланмади"),
}


def slugify(name):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (name or "nomalum")).strip("-").lower()
    return s or "nomalum"


def rop_filename(rop_name):
    """Тахмин қилиб бўлмайдиган файл номи: nom-<12 belgili hash>.html"""
    digest = hashlib.sha256((SALT + "|" + (rop_name or "")).encode()).hexdigest()[:12]
    return f"{slugify(rop_name)}-{digest}.html"


def parse_last_text(text):
    """Бот юборган хабар матнидан майдонларни ажратади (формат ўзимизники,
    шунинг учун ишончли)."""
    out = {"order_num": "", "deal_id": "", "products": [], "summa": "",
           "region": "", "address": "", "client": "", "phones": [],
           "operator": "", "source": ""}
    if not text:
        return out
    lines = text.split("\n")
    in_products = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("№"):
            out["order_num"] = stripped[1:].strip()
            in_products = False
        elif "Id сделки:" in stripped:
            out["deal_id"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif stripped.startswith("📦"):
            out["products"].append(stripped.split(":", 1)[1].strip())
            in_products = True
        elif stripped.startswith("💵"):
            out["summa"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif stripped.startswith("📍"):
            out["region"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif stripped.startswith("🚚"):
            out["address"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif stripped.startswith("👤"):
            out["client"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif stripped.startswith("📞"):
            out["phones"].append(stripped.split(":", 1)[1].strip())
            in_products = False
        elif stripped.startswith("Оператор:"):
            out["operator"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif stripped.startswith("🌐"):
            out["source"] = stripped.split(":", 1)[1].strip()
            in_products = False
        elif in_products and stripped:
            out["products"].append(stripped)
    return out


def load_orders():
    """deal_state.json'дан барча буюртмаларни ўқиб, РОП бўйича гуруҳлайди."""
    path = STATE_DIR / "deal_state.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    by_rop = {}
    for deal_id, entry in data.items():
        rop = entry.get("rop_name") or "Номаълум"
        parsed = parse_last_text(entry.get("last_text", ""))
        created = entry.get("created_at") or entry.get("sent_at") or ""
        try:
            dt = datetime.fromisoformat(created).astimezone(TZ)
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            date_str, time_str = "", ""

        by_rop.setdefault(rop, []).append({
            "deal_id": deal_id,
            "order_num": parsed["order_num"],
            "date": date_str,
            "time": time_str,
            "products": parsed["products"],
            "summa": parsed["summa"],
            "region": parsed["region"],
            "address": parsed["address"],
            "client": parsed["client"],
            "phones": parsed["phones"],
            "operator": parsed["operator"],
            "source": parsed["source"],
            "status": entry.get("status_key", "confirm_new"),
        })

    for rop in by_rop:
        by_rop[rop].sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    return by_rop


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f5f7fb;--panel:#ffffff;--panel2:#eef2f8;--border:#dde4ee;
  --text:#1c2533;--muted:#6b7a90;--accent:#2f6fed;--accent2:#7c4dff;
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:linear-gradient(165deg,#f5f7fb 0%,#eaf0f9 100%);color:var(--text);
padding:18px;font-size:14px;min-height:100vh}
h1{font-size:22px;margin-bottom:4px;font-weight:800;
background:linear-gradient(90deg,#7c4dff,#2f6fed);-webkit-background-clip:text;
background-clip:text;-webkit-text-fill-color:transparent;display:inline-block}
.sub{color:var(--muted);font-size:13px;margin-bottom:18px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:12px;
padding:12px 16px;min-width:112px;transition:transform .15s,box-shadow .15s;
box-shadow:0 1px 3px rgba(28,37,51,.06)}
.stat:hover{transform:translateY(-2px);box-shadow:0 6px 16px rgba(47,111,237,.14)}
.stat .n{font-size:24px;font-weight:800;color:var(--text)}
.stat .l{font-size:11px;color:var(--muted);margin-top:3px;text-transform:uppercase;
letter-spacing:.03em}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
input,select,button{padding:9px 12px;border:1px solid var(--border);border-radius:8px;
font-size:14px;background:var(--panel);color:var(--text);font-family:inherit}
input::placeholder{color:#9aa8bd}
input[type=text]{min-width:220px;flex:1}
.btn{cursor:pointer;font-weight:600;transition:background .15s,border-color .15s,box-shadow .15s}
.btn:hover{border-color:var(--accent);box-shadow:0 2px 8px rgba(47,111,237,.15)}
.btn-primary{background:linear-gradient(90deg,var(--accent2),var(--accent));border:none;
color:#fff}
.btn-primary:hover{filter:brightness(1.06)}
.btn-alt{background:linear-gradient(90deg,#0ea36b,#12b981);border:none;color:#fff}
.btn-alt:hover{filter:brightness(1.06)}
.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border);
background:var(--panel);box-shadow:0 1px 3px rgba(28,37,51,.06)}
table{width:100%;border-collapse:collapse;min-width:1180px}
th{background:var(--panel2);padding:11px 12px;text-align:left;font-size:11px;font-weight:700;
color:var(--muted);white-space:nowrap;text-transform:uppercase;letter-spacing:.04em;
border-bottom:1px solid var(--border);position:sticky;top:0;z-index:2}
td{padding:10px 12px;border-top:1px solid var(--border);vertical-align:top;white-space:nowrap}
tr{transition:background .1s}
tr:hover td{background:#f3f7ff}
.badge{display:inline-block;padding:4px 10px;border-radius:20px;font-size:12px;
white-space:nowrap;font-weight:600;border:1px solid transparent}
.s-confirm_new{background:#fff6dd;color:#8a6100;border-color:#f0dfae}
.s-no_answer{background:#fff0d8;color:#8a5300;border-color:#f0d7ab}
.s-confirmed{background:#dcf7e6;color:#0d6b33;border-color:#a9e6c1}
.s-rejected{background:#ffe3e5;color:#a41722;border-color:#f5b9be}
.prod{font-size:13px;line-height:1.5;white-space:normal;max-width:260px}
.muted{color:var(--muted);font-size:12px}
.nowrap{white-space:nowrap}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.ph{display:inline-flex;align-items:center;gap:6px}
.eye{border:1px solid var(--border);background:var(--panel2);border-radius:6px;cursor:pointer;
padding:3px 7px;font-size:12px;line-height:1.4;color:var(--muted)}
.eye:hover{color:var(--text);border-color:var(--accent)}
.addr{max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
display:inline-block;vertical-align:bottom;cursor:pointer}
.addr.open{white-space:normal;max-width:320px;overflow:visible}
/* ── Статистика модали ── */
.modal{display:none;position:fixed;inset:0;background:rgba(20,28,42,.45);z-index:50;
padding:24px;overflow-y:auto}
.modal.show{display:block}
.modal-box{background:var(--panel);border-radius:14px;max-width:1000px;margin:0 auto;
padding:22px;box-shadow:0 20px 60px rgba(20,28,42,.25)}
.modal-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.modal-head h2{font-size:19px;font-weight:800}
.close-x{cursor:pointer;border:1px solid var(--border);background:var(--panel2);
border-radius:8px;padding:6px 12px;font-size:15px;font-weight:700;color:var(--muted)}
.close-x:hover{color:var(--text);border-color:var(--accent)}
.stat-table{width:100%;border-collapse:collapse;min-width:auto}
.stat-table th{position:static}
.stat-table td{white-space:nowrap}
.bar{height:7px;border-radius:4px;background:var(--panel2);overflow:hidden;min-width:90px;
margin-top:5px}
.bar span{display:block;height:100%;background:linear-gradient(90deg,#12b981,#0ea36b)}
.pct{font-weight:700}
@media(max-width:700px){
 body{padding:10px}
 .stat{min-width:92px;padding:10px 12px}
 .stat .n{font-size:20px}
 input[type=text]{min-width:150px}
 .modal{padding:10px}
 .modal-box{padding:14px}
}
"""

def build_js(today_str):
    return f"""
var TODAY = "{today_str}";
var STATUS_KEYS = ["confirm_new","no_answer","confirmed","rejected"];

function togglePhone(btn){{
  var wrap=btn.closest('.ph');
  var span=wrap.querySelector('.pm');
  var full=wrap.dataset.full;
  if(btn.dataset.shown==='1'){{
    span.textContent=full.slice(0,6)+'***'+full.slice(-4);
    btn.dataset.shown='0'; btn.textContent='👁'; btn.title='Кўрсатиш';
  }}else{{
    span.textContent=full;
    btn.dataset.shown='1'; btn.textContent='🙈'; btn.title='Яшириш';
  }}
}}

function toggleAddr(el){{ el.classList.toggle('open'); }}

function applyFilters(){{
  var q=document.getElementById('q').value.toLowerCase();
  var st=document.getElementById('st').value;
  var d1=document.getElementById('d1').value;
  var d2=document.getElementById('d2').value;
  var ropEl=document.getElementById('rop');
  var rop=ropEl?ropEl.value:'';
  var rows=document.querySelectorAll('tbody tr');
  var shown=0;
  var counts={{confirm_new:0,no_answer:0,confirmed:0,rejected:0}};

  rows.forEach(function(r){{
    var ok=true;
    if(st && r.dataset.status!==st) ok=false;
    if(ok && rop && r.dataset.rop!==rop) ok=false;
    if(ok && d1 && r.dataset.date < d1) ok=false;
    if(ok && d2 && r.dataset.date > d2) ok=false;
    if(ok && q){{
      var hay=(r.innerText+' '+(r.dataset.phones||'')).toLowerCase();
      if(hay.indexOf(q)===-1) ok=false;
    }}
    r.style.display = ok ? '' : 'none';
    if(ok){{
      shown++;
      if(counts[r.dataset.status]!==undefined) counts[r.dataset.status]++;
    }}
  }});

  document.getElementById('shown').textContent=shown;
  var totEl=document.getElementById('c-total');
  if(totEl) totEl.textContent=shown;
  STATUS_KEYS.forEach(function(k){{
    var el=document.getElementById('c-'+k);
    if(el) el.textContent=counts[k];
  }});
}}

function filterToday(){{
  document.getElementById('d1').value=TODAY;
  document.getElementById('d2').value=TODAY;
  applyFilters();
}}

function resetF(){{
  document.getElementById('q').value='';
  document.getElementById('st').value='';
  document.getElementById('d1').value='';
  document.getElementById('d2').value='';
  var ropEl=document.getElementById('rop');
  if(ropEl) ropEl.value='';
  applyFilters();
}}

function openStats(){{
  var rows=document.querySelectorAll('tbody tr');
  var byRop={{}};
  rows.forEach(function(r){{
    if(r.style.display==='none') return;
    var rop=r.dataset.rop||'—';
    if(!byRop[rop]) byRop[rop]={{total:0,confirm_new:0,no_answer:0,confirmed:0,rejected:0,summa:0}};
    byRop[rop].total++;
    if(byRop[rop][r.dataset.status]!==undefined) byRop[rop][r.dataset.status]++;
    var sm=parseFloat((r.dataset.summa||'0').replace(/[^0-9]/g,''))||0;
    byRop[rop].summa+=sm;
  }});

  var names=Object.keys(byRop).sort(function(a,b){{return byRop[b].total-byRop[a].total}});
  var g={{total:0,confirm_new:0,no_answer:0,confirmed:0,rejected:0,summa:0}};
  var html='<table class="stat-table"><thead><tr>'+
    '<th>РОП</th><th>Жами</th><th>✅ Тасдиқланди</th><th>🟡 нд</th>'+
    '<th>❌ Рад</th><th>🕔 Кутилмоқда</th><th>Конверсия</th><th>Сумма</th>'+
    '</tr></thead><tbody>';

  names.forEach(function(n){{
    var d=byRop[n];
    ['total','confirm_new','no_answer','confirmed','rejected','summa'].forEach(function(k){{g[k]+=d[k]}});
    var pct=d.total?Math.round(d.confirmed/d.total*100):0;
    html+='<tr><td><b>'+n+'</b></td><td>'+d.total+'</td><td>'+d.confirmed+'</td>'+
      '<td>'+d.no_answer+'</td><td>'+d.rejected+'</td><td>'+d.confirm_new+'</td>'+
      '<td><span class="pct">'+pct+'%</span><div class="bar"><span style="width:'+pct+'%"></span></div></td>'+
      '<td>'+d.summa.toLocaleString('ru-RU')+'</td></tr>';
  }});

  var gp=g.total?Math.round(g.confirmed/g.total*100):0;
  html+='</tbody><tfoot><tr style="border-top:2px solid var(--border);font-weight:800">'+
    '<td>ЖАМИ</td><td>'+g.total+'</td><td>'+g.confirmed+'</td><td>'+g.no_answer+'</td>'+
    '<td>'+g.rejected+'</td><td>'+g.confirm_new+'</td>'+
    '<td><span class="pct">'+gp+'%</span></td><td>'+g.summa.toLocaleString('ru-RU')+'</td>'+
    '</tr></tfoot></table>';

  document.getElementById('stats-body').innerHTML=html;
  document.getElementById('stats-modal').classList.add('show');
}}

function closeStats(){{ document.getElementById('stats-modal').classList.remove('show'); }}

document.addEventListener('DOMContentLoaded',function(){{
  ['q','st','d1','d2','rop'].forEach(function(id){{
    var el=document.getElementById(id);
    if(!el) return;
    el.addEventListener('input',applyFilters);
    el.addEventListener('change',applyFilters);
  }});
  var m=document.getElementById('stats-modal');
  if(m) m.addEventListener('click',function(e){{ if(e.target===m) closeStats(); }});
  document.addEventListener('keydown',function(e){{ if(e.key==='Escape') closeStats(); }});
  applyFilters();
  setTimeout(function(){{location.reload()}}, 120000);
}});
"""


def esc(s):
    return html.escape(str(s or ""))


def mask_phone(phone):
    """+998977927504 -> +99897***7504 (ўртаси яширилади)."""
    p = str(phone or "").strip()
    if len(p) <= 10:
        return p
    return p[:6] + "***" + p[-4:]


def build_row(o, show_rop=False):
    """Битта буюртма қатори (устунлар тартиби фойдаланувчи белгилаган)."""
    emoji, label = STATUS_LABELS.get(o["status"], ("", o["status"]))
    prods = "<br>".join(esc(p) for p in o["products"]) or "—"
    if o["phones"]:
        phones = "<br>".join(
            f'<span class="ph" data-full="{esc(p)}">'
            f'<span class="pm">{esc(mask_phone(p))}</span>'
            f'<button class="eye" onclick="togglePhone(this)" title="Кўрсатиш">👁</button>'
            f'</span>' for p in o["phones"])
    else:
        phones = "—"
    all_phones = " ".join(o["phones"])
    addr = esc(o["address"]) or "—"
    rop_cell = (f'<td data-l="РОП" class="nowrap"><b>{esc(o.get("rop", ""))}</b></td>'
                if show_rop else "")

    return f"""<tr data-status="{esc(o['status'])}" data-date="{esc(o['date'])}" \
data-phones="{esc(all_phones)}" data-rop="{esc(o.get('rop',''))}" data-summa="{esc(o['summa'])}">
{rop_cell}
<td data-l="№" class="nowrap">{esc(o['order_num'])}</td>
<td data-l="Сана" class="nowrap">{esc(o['date'])}<div class="muted">{esc(o['time'])}</div></td>
<td data-l="Id сделки" class="nowrap">{esc(o['deal_id'])}</td>
<td data-l="Мижоз">{esc(o['client']) or '—'}</td>
<td data-l="Телефон" class="nowrap">{phones}</td>
<td data-l="Оператор">{esc(o['operator']) or '—'}</td>
<td data-l="Продукт" class="prod">{prods}</td>
<td data-l="Сумма" class="nowrap">{esc(o['summa'])}</td>
<td data-l="Регион">{esc(o['region']) or '—'}</td>
<td data-l="Адрес"><span class="addr" onclick="toggleAddr(this)" title="{addr}">{addr}</span></td>
<td data-l="Статус"><span class="badge s-{esc(o['status'])}">{emoji} {label}</span></td>
<td data-l="Источник">{esc(o['source']) or '—'}</td>
</tr>"""


def build_stats(orders):
    """Тепадаги рақамлар. id'лар билан — филтрда JS уларни янгилайди."""
    counts = {k: 0 for k in STATUS_ORDER}
    for o in orders:
        if o["status"] in counts:
            counts[o["status"]] += 1
    out = (f'<div class="stat"><div class="n" id="c-total">{len(orders)}</div>'
           f'<div class="l">Жами</div></div>')
    for key in STATUS_ORDER:
        emoji, label = STATUS_LABELS[key]
        out += (f'<div class="stat"><div class="n" id="c-{key}">{counts[key]}</div>'
                f'<div class="l">{emoji} {label}</div></div>')
    return out


def build_page(title, orders, updated_at, rop_options_html=""):
    """Умумий саҳифа қурувчи — ҳам битта РОП, ҳам барчаси учун."""
    show_rop = bool(rop_options_html)

    opts = '<option value="">Барча статус</option>'
    for key in STATUS_ORDER:
        emoji, label = STATUS_LABELS[key]
        opts += f'<option value="{key}">{emoji} {label}</option>'

    rop_select = (f'<select id="rop">{rop_options_html}</select>' if show_rop else "")
    rop_th = "<th>РОП</th>" if show_rop else ""
    rows = "".join(build_row(o, show_rop=show_rop) for o in orders)

    return f"""<!DOCTYPE html>
<html lang="uz"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head><body>
<h1>{esc(title)}</h1>
<div class="sub">Янгиланди: {updated_at} (ҳар 2 дақиқада автомат янгиланади) ·
Кўрсатилмоқда: <b id="shown">0</b> та</div>
<div class="stats">{build_stats(orders)}</div>
<div class="controls">
<input type="text" id="q" placeholder="Қидирув (исм, телефон, маҳсулот, ID...)">
<button class="btn btn-primary" onclick="filterToday()">📅 Бугун</button>
{rop_select}
<select id="st">{opts}</select>
<input type="date" id="d1" title="Дан">
<input type="date" id="d2" title="Гача">
<button class="btn" onclick="resetF()">Тозалаш</button>
<button class="btn btn-alt" onclick="openStats()">📊 Статистика</button>
</div>
<div class="table-wrap">
<table><thead><tr>
{rop_th}<th>№</th><th>Сана</th><th>Id сделки</th><th>Мижоз</th><th>Телефон</th>
<th>Оператор</th><th>Продукт</th><th>Сумма</th><th>Регион</th><th>Адрес</th>
<th>Статус</th><th>Источник</th>
</tr></thead><tbody>
{rows}
</tbody></table>
</div>

<div class="modal" id="stats-modal">
  <div class="modal-box">
    <div class="modal-head">
      <h2>📊 Статистика (жорий филтр бўйича)</h2>
      <button class="close-x" onclick="closeStats()">✕</button>
    </div>
    <div id="stats-body"></div>
  </div>
</div>

<script>{build_js(datetime.now(TZ).strftime('%Y-%m-%d'))}</script>
</body></html>"""


def build_rop_page(rop_name, orders, updated_at):
    orders = [dict(o, rop=rop_name) for o in orders]
    return build_page(f"{rop_name} — буюртмалар", orders, updated_at)


def build_index(by_rop, updated_at):
    """Умумий саҳифа — БАРЧА буюртмалар, РОП филтри билан."""
    all_orders = []
    for rop, orders in by_rop.items():
        for o in orders:
            o = dict(o)
            o["rop"] = rop
            all_orders.append(o)
    all_orders.sort(key=lambda x: (x["date"], x["time"]), reverse=True)

    rop_opts = '<option value="">Барча РОП</option>'
    for rop in sorted(by_rop.keys()):
        rop_opts += f'<option value="{esc(rop)}">{esc(rop)} ({len(by_rop[rop])})</option>'

    return build_page("Барча буюртмалар", all_orders, updated_at, rop_options_html=rop_opts)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_rop = load_orders()
    updated_at = datetime.now(TZ).strftime("%d.%m.%Y %H:%M")

    for rop, orders in by_rop.items():
        fn = rop_filename(rop)
        (OUT_DIR / fn).write_text(build_rop_page(rop, orders, updated_at), encoding="utf-8")
        print(f"{rop}: {len(orders)} ta buyurtma -> {fn}")

    (OUT_DIR / "index.html").write_text(build_index(by_rop, updated_at), encoding="utf-8")
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"\nJami {len(by_rop)} ta ROP dashboard yaratildi: {OUT_DIR}")


if __name__ == "__main__":
    main()