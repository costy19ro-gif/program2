import streamlit as st
import requests
import math
from datetime import datetime, timedelta

st.set_page_config(page_title="BetMachine Pro 55", page_icon="🎯", layout="wide")

# ══════════════════════════════════════════════════════════
#  CONFIGURARE API — DOAR API-FOOTBALL (meciuri active)
# ══════════════════════════════════════════════════════════

RAPID_KEY  = st.secrets.get("RAPID_KEY", "b5b1816fbcf28d2f3567bf691e18f86a")
RAPID_BASE = "https://v3.football.api-sports.io"
RAPID_HEADERS = {"x-apisports-key": RAPID_KEY}

AZI      = datetime.now()
AZI_STR  = AZI.strftime("%Y-%m-%d")
SFARSIT  = (AZI + timedelta(days=7)).strftime("%Y-%m-%d")

# Ligi ACTIVE API-FOOTBALL
RAPID_LEAGUES = [
    {"id": 128, "name": "Argentina Primera C 🇦🇷"},
    {"id": 73,  "name": "Brazilia Série B 🇧🇷"},
    {"id": 75,  "name": "Brazilia Série C 🇧🇷"},
    {"id": 244, "name": "Canada Premier League 🇨🇦"},
    {"id": 265, "name": "Copa Chile 🇨🇱"},
    {"id": 253, "name": "MLS Next Pro 🇺🇸"},
    {"id": 981, "name": "USL League Two 🇺🇸"},
    {"id": 382, "name": "Islanda Besta deild 🇮🇸"},
    {"id": 169, "name": "Letonia Virsliga 🇱🇻"},
    {"id": 172, "name": "Lituania TOPLYGA 🇱🇹"},
    {"id": 113, "name": "Finlanda Ykkonen 🇫🇮"},
    {"id": 239, "name": "Peru Copa de la Liga 🇵🇪"},
    {"id": 283, "name": "Uruguay Segunda Division 🇺🇾"},
    {"id": 288, "name": "Paraguay Division Intermedia 🇵🇾"},
    {"id": 42,  "name": "Europa U19 Championship 🇪🇺"},
    {"id": 141, "name": "Insulele Feroe Premier League 🇫ᵒ"},
]

# ══════════════════════════════════════════════════════════
#  MOTOR POISSON
# ══════════════════════════════════════════════════════════

def poisson_prob(lam, k):
    if lam <= 0: return 0.0
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def calculeaza_prob(lam_h=1.35, lam_a=1.10):
    p1 = px = p2 = p_gg = p_o25 = 0.0
    for i in range(7):
        for j in range(7):
            p = poisson_prob(lam_h, i) * poisson_prob(lam_a, j)
            if i > j:    p1  += p
            elif i == j: px  += p
            else:        p2  += p
            if i > 0 and j > 0: p_gg  += p
            if i + j > 2:       p_o25 += p
    total = p1 + px + p2
    if total > 0: p1, px, p2 = p1/total, px/total, p2/total
    return {
        "p1": round(p1,3), "px": round(px,3), "p2": round(p2,3),
        "p_gg": round(p_gg,3), "p_o25": round(p_o25,3),
        "lam_h": round(lam_h,2), "lam_a": round(lam_a,2)
    }

def prob_to_cota(prob, marja=0.07):
    if prob <= 0.01: return 50.0
    return round(1 / (prob * (1 + marja)), 2)

def lam_din_standing(gf, ga, played, acasa=True):
    if played == 0: return (1.35 if acasa else 1.10)
    gf_m = gf / played
    ga_m = ga / played
    atac = gf_m / 1.2
    aparare = ga_m / 1.2
    if acasa:
        return round(max(atac * 1.2 * 1.10, 0.3), 2)
    else:
        return round(max(atac * 1.2 * 0.90, 0.3), 2)

# ══════════════════════════════════════════════════════════
#  API-FOOTBALL — DOAR MECIURI ACTIVE
# ══════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def get_rapid_fixtures(league_id, season=2026):
    try:
        r = requests.get(
            f"{RAPID_BASE}/fixtures",
            headers=RAPID_HEADERS,
            params={
                "league": league_id,
                "season": season,
                "from": AZI_STR,
                "to": SFARSIT,
                "status": "NS"
            },
            timeout=8
        )
        if r.status_code == 200:
            return r.json().get("response", [])
        return []
    except:
        return []

@st.cache_data(ttl=3600)
def get_rapid_standings(league_id, season=2026):
    try:
        r = requests.get(
            f"{RAPID_BASE}/standings",
            headers=RAPID_HEADERS,
            params={"league": league_id, "season": season},
            timeout=8
        )
        if r.status_code == 200:
            standings = r.json().get("response", [])
            if standings:
                return standings[0].get("league", {}).get("standings", [[]])[0]
        return []
    except:
        return []

def proceseaza_rapid(fixtures, standings, comp_name):
    team_map = {}
    for row in standings:
        tid = row.get("team", {}).get("id")
        played = max(row.get("all", {}).get("played", 0), 1)
        gf = row.get("all", {}).get("goals", {}).get("for", 0)
        ga = row.get("all", {}).get("goals", {}).get("against", 0)
        if tid:
            team_map[tid] = {"played": played, "gf": gf, "ga": ga}

    result = []
    for fix in fixtures:
        try:
            f   = fix["fixture"]
            h   = fix["teams"]["home"]
            a   = fix["teams"]["away"]
            dt  = datetime.strptime(f["date"][:16], "%Y-%m-%dT%H:%M")

            sh  = team_map.get(h["id"], {})
            sa  = team_map.get(a["id"], {})

            lam_h = lam_din_standing(sh.get("gf",0), sh.get("ga",0), sh.get("played",1), acasa=True) if sh else 1.35
            lam_a = lam_din_standing(sa.get("gf",0), sa.get("ga",0), sa.get("played",1), acasa=False) if sa else 1.10

            prob = calculeaza_prob(lam_h, lam_a)

            result.append({
                "sursa": "API",
                "comp": comp_name,
                "data": dt.strftime("%d.%m"),
                "ora": dt.strftime("%H:%M"),
                "home": h["name"],
                "away": a["name"],
                "prob": prob
            })
        except:
            continue

    return result

# ══════════════════════════════════════════════════════════
#  ASAMBLARE BILETE
# ══════════════════════════════════════════════════════════

def asambleaza_bilete(selectii):
    bilet_sigur = []
    bilet_combo = []
    bilet_bomba = []
    cota_s = cota_c = cota_b = 1.0

    sortate = sorted(selectii, key=lambda x: max(x["prob"]["p1"], x["prob"]["p2"]), reverse=True)

    for s in sortate:
        p    = s["prob"]
        c1   = prob_to_cota(p["p1"])
        cx   = prob_to_cota(p["px"])
        c2   = prob_to_cota(p["p2"])
        c1x  = prob_to_cota(p["p1"] + p["px"])
        cx2  = prob_to_cota(p["px"] + p["p2"])
        cgg  = prob_to_cota(p["p_gg"])
        co25 = prob_to_cota(p["p_o25"])
        pfx  = f"({s['data']} {s['ora']}) {s['home']} vs {s['away']}"

        # BILET SIGUR
        if cota_s < 20.0:
            if p["p1"] + p["px"] >= 0.62 and 1.18 <= c1x <= 1.65:
                bilet_sigur.append({"text": f"{pfx} ➜ 1X", "cota": c1x, "comp": s["comp"]})
                cota_s *= c1x
            elif p["px"] + p["p2"] >= 0.62 and 1.18 <= cx2 <= 1.65:
                bilet_sigur.append({"text": f"{pfx} ➜ X2", "cota": cx2, "comp": s["comp"]})
                cota_s *= cx2
            elif p["p_o25"] >= 0.60 and 1.22 <= co25 <= 1.70:
                bilet_sigur.append({"text": f"{pfx} ➜ Peste 2.5 goluri", "cota": co25, "comp": s["comp"]})
                cota_s *= co25
            elif p["p1"] >= 0.55 and 1.20 <= c1 <= 1.75:
                bilet_sigur.append({"text": f"{pfx} ➜ 1", "cota": c1, "comp": s["comp"]})
                cota_s *= c1

        # BILET COMBO
        if len(bilet_combo) < 5 and cota_c < 20.0:
            if p["p1"] >= 0.46 and 1.60 <= c1 <= 3.00:
                bilet_combo.append({"text": f"{pfx} ➜ 1", "cota": c1, "comp": s["comp"]})
                cota_c *= c1
            elif p["p2"] >= 0.46 and 1.60 <= c2 <= 3.00:
                bilet_combo.append({"text": f"{pfx} ➜ 2", "cota": c2, "comp": s["comp"]})
                cota_c *= c2
            elif p["p_gg"] >= 0.52 and 1.60 <= cgg <= 2.80:
                bilet_combo.append({"text": f"{pfx} ➜ GG", "cota": cgg, "comp": s["comp"]})
                cota_c *= cgg

        # BILET BOMBĂ
        if len(bilet_bomba) < 4:
            if c2 >= 3.00 and p["p2"] >= 0.28:
                bilet_bomba.append({"text": f"{pfx} ➜ 2 (surpriză)", "cota": c2, "comp": s["comp"]})
                cota_b *= c2
            elif c1 >= 3.00 and p["p1"] >= 0.28:
                bilet_bomba.append({"text": f"{pfx} ➜ 1 (surpriză)", "cota": c1, "comp": s["comp"]})
                cota_b *= c1
            elif cgg >= 3.00 and p["p_gg"] >= 0.38:
                bilet_bomba.append({"text": f"{pfx} ➜ GG cotă mare", "cota": cgg, "comp": s["comp"]})
                cota_b *= cgg
            elif co25 >= 3.00 and p["p_o25"] >= 0.35:
                bilet_bomba.append({"text": f"{pfx} ➜ O2.5 cotă mare", "cota": co25, "comp": s["comp"]})
                cota_b *= co25

    return {
        "sigur": {"sel": bilet_sigur, "cota": round(cota_s, 2)},
        "combo": {"sel": bilet_combo, "cota": round(cota_c, 2)},
        "bomba": {"sel": bilet_bomba, "cota": round(cota_b, 2)},
    }

# ══════════════════════════════════════════════════════════
#  INTERFAȚĂ
# ══════════════════════════════════════════════════════════

st.title("🎯 BetMachine Pro — Program 55")
st.markdown(f"📅 **{AZI.strftime('%d.%m.%Y %H:%M')}** | 🔄 Meciuri din **{AZI_STR}** până la **{SFARSIT}**")
st.markdown("⚡ Surse: **API-Football** (doar meciuri active)")

if not RAPID_KEY:
    st.sidebar.error("❌ Cheia API-Football lipsește!")
else:
    st.sidebar.success("✅ Cheie API-Football activă")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Surse active")

toate_selectiile = []
rapid_count = 0

with st.spinner("⏳ Se descarcă meciurile active (API-Football)..."):
    for liga in RAPID_LEAGUES:
        fixtures  = get_rapid_fixtures(liga["id"])
        if not fixtures:
            continue
        standings = get_rapid_standings(liga["id"])
        proc = proceseaza_rapid(fixtures, standings, liga["name"])
        if proc:
            toate_selectiile.extend(proc)
            rapid_count += len(proc)

st.sidebar.success(f"✅ API-Football: **{rapid_count}** meciuri active")

if not toate_selectiile:
    st.error("❌ Nu există meciuri active în acest moment!")
    st.stop()

st.success(f"### ✅ Total meciuri analizate: **{len(toate_selectiile)}** din {len(set(s['comp'] for s in toate_selectiile))} competiții")

# ══════════════════════════════════════════════════════════
#  BILETE
# ══════════════════════════════════════════════════════════

bilete = asambleaza_bilete(toate_selectiile)

st.markdown("---")
st.subheader("🎫 Biletele Generate de Algoritmul Poisson/Dixon-Coles")

col1, col2, col3 = st.columns(3)

# BILET SIGUR
with col1:
    cs = bilete["sigur"]["cota"]
    st.success("🟢 BILET SIGUR")
    st.metric("Cotă Totală", cs, "Obiectiv ≥ 20")
    st.caption("Strategie: 1X / X2 / O2.5")
    if bilete["sigur"]["sel"]:
        for ev in bilete["sigur"]["sel"]:
            st.markdown(f"✔️ `{ev['cota']}` {ev['text']}")
    st.markdown(f"💰 5 RON ➜ **{round(5*cs,2)} RON**")

# BILET COMBO
with col2:
    cc = bilete["combo"]["cota"]
    st.info("🔵 BILET COMBO VALUE")
    st.metric("Cotă Totală", cc, "3-5 selecții")
    if bilete["combo"]["sel"]:
        for ev in bilete["combo"]["sel"]:
            st.markdown(f"✔️ `{ev['cota']}` {ev['text']}")
    st.markdown(f"💰 5 RON ➜ **{round(5*cc,2)} RON**")

# BILET BOMBĂ
with col3:
    cb = bilete["bomba"]["cota"]
    st.warning("🔥 BILET BOMBĂ")
    st.metric("Cotă Totală", cb, "Surprize ≥ 3.00")
    if bilete["bomba"]["sel"]:
        for ev in bilete["bomba"]["sel"]:
            st.markdown(f"✔️ `{ev['cota']}` {ev['text']}")
    st.markdown(f"💰 2 RON ➜ **{round(2
