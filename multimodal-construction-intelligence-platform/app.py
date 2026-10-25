"""
Multimodal Construction Intelligence Platform
Skill Wallet Capstone Project 1
Run:  streamlit run app.py
"""
import json
import re
import urllib.parse
from datetime import datetime

import streamlit as st
from PIL import Image

# ----------------------------------------------------------------------------
# Page config + CSS
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Construction Intelligence Platform",
    page_icon="🏗️",
    layout="wide",
)

st.markdown(
    """
<style>
.hero {background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
       padding: 1.6rem 2rem; border-radius: 16px; color: #fff; margin-bottom: 1.2rem;}
.hero h1 {margin:0; font-size:1.9rem;}
.hero p {margin:.3rem 0 0; opacity:.85;}
.card {background: var(--secondary-background-color); border-radius: 14px;
       padding: 1rem 1.2rem; border-left: 5px solid #f2a900; margin-bottom:.6rem;}
.card .label {font-size:.78rem; text-transform:uppercase; opacity:.7; letter-spacing:.05em;}
.card .value {font-size:1.7rem; font-weight:700;}
.pill {display:inline-block; padding:.2rem .75rem; border-radius:999px;
       font-size:.8rem; font-weight:600; color:#fff;}
.pill.green{background:#2e9e5b;} .pill.yellow{background:#d9a400;}
.pill.orange{background:#e8710a;} .pill.red{background:#d93025;}
.alert {padding:.8rem 1rem; border-radius:10px; margin:.4rem 0; border-left:5px solid;}
.alert.warn {background:rgba(232,113,10,.12); border-color:#e8710a;}
.alert.crit {background:rgba(217,48,37,.12); border-color:#d93025;}
.alert.ok {background:rgba(46,158,91,.12); border-color:#2e9e5b;}
</style>
""",
    unsafe_allow_html=True,
)

SEVERITY_COLOR = {"Low": "green", "Medium": "yellow", "High": "orange", "Critical": "red"}


def pill(text: str, color: str) -> str:
    return f'<span class="pill {color}">{text}</span>'


def metric_card(label: str, value: str) -> None:
    st.markdown(
        f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def inr(amount: float) -> str:
    """Format INR in Lakhs / Crores."""
    if amount >= 1e7:
        return f"₹{amount / 1e7:,.2f} Cr"
    if amount >= 1e5:
        return f"₹{amount / 1e5:,.2f} L"
    return f"₹{amount:,.0f}"


# ----------------------------------------------------------------------------
# Gemini helpers (google-genai SDK) with graceful fallback
# ----------------------------------------------------------------------------
def get_client(api_key: str):
    try:
        from google import genai

        return genai.Client(api_key=api_key)
    except Exception as e:  # noqa: BLE001
        st.sidebar.error(f"Gemini init failed: {e}")
        return None


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def call_vision(client, model: str, prompt: str, image: Image.Image) -> dict:
    from google.genai import types

    resp = client.models.generate_content(
        model=model,
        contents=[prompt, image],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return parse_json(resp.text)


# ----------------------------------------------------------------------------
# Prompts (JSON data contracts - Epic 4)
# ----------------------------------------------------------------------------
PPE_PROMPT = """You are a certified construction safety officer. Audit this site photo for
PPE compliance (helmets, high-vis vests, steel-toe boots, safety harnesses) and site hazards
under OSHA 1926 and Indian standards (IS 456, IS 3764, BOCW Act). Respond ONLY with JSON:
{
 "safety_score": <int 0-100>,
 "overall_status": "Compliant" | "Needs Attention" | "Non-Compliant",
 "workers_detected": <int>,
 "ppe_detection": {"helmet": {"detected": bool, "note": str},
                   "high_vis_vest": {"detected": bool, "note": str},
                   "steel_toe_boots": {"detected": bool, "note": str},
                   "safety_harness": {"detected": bool, "note": str}},
 "hazards": [{"hazard": str, "severity": "Low"|"Medium"|"High"|"Critical", "remedy": str}],
 "summary": str
}
If the image shows no construction site, set safety_score to 0 and explain in summary."""

CRACK_PROMPT = """You are a structural engineer. Analyse this concrete/wall surface photo.
Classify the defect as one of: Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling.
Respond ONLY with JSON:
{
 "defect_type": str,
 "severity_score": <int 0-100, higher = worse>,
 "estimated_width_mm": <float>,
 "urgency": "Monitor" | "Repair Soon" | "Immediate Action",
 "root_causes": [str],
 "recommended_repairs": [str],
 "monitoring_advice": str,
 "summary": str
}
If no defect is visible, say so and use a low severity score."""

# ----------------------------------------------------------------------------
# Demo-mode data (no API key)
# ----------------------------------------------------------------------------
DEMO_PPE = {
    "safety_score": 62,
    "overall_status": "Needs Attention",
    "workers_detected": 4,
    "ppe_detection": {
        "helmet": {"detected": True, "note": "3 of 4 workers wearing helmets"},
        "high_vis_vest": {"detected": True, "note": "Vests visible on all workers"},
        "steel_toe_boots": {"detected": False, "note": "Open footwear observed on 1 worker"},
        "safety_harness": {"detected": False, "note": "No harness at elevated edge"},
    },
    "hazards": [
        {"hazard": "Unprotected working edge at height", "severity": "Critical",
         "remedy": "Install guardrails / edge netting and mandate full-body harness with anchor points."},
        {"hazard": "Worker without helmet", "severity": "High",
         "remedy": "Stop work for that worker until IS 2925 compliant helmet is worn."},
        {"hazard": "Loose material on walkway", "severity": "Medium",
         "remedy": "Daily housekeeping; designate material stacking zones."},
    ],
    "summary": "DEMO MODE: sample output. Add a Gemini API key for real image analysis.",
}
DEMO_CRACK = {
    "defect_type": "Settlement",
    "severity_score": 58,
    "estimated_width_mm": 2.5,
    "urgency": "Repair Soon",
    "root_causes": ["Differential foundation settlement", "Poor soil compaction", "Water seepage near footing"],
    "recommended_repairs": ["Epoxy injection for cracks 0.3-5 mm", "Structural re-grouting", "Fix drainage near footing"],
    "monitoring_advice": "Fix crack gauges and record widths weekly for 8 weeks.",
    "summary": "DEMO MODE: sample output. Add a Gemini API key for real image analysis.",
}

# ----------------------------------------------------------------------------
# Valuation model (Epic 3) - rates are indicative planning figures, INR / sqft
# ----------------------------------------------------------------------------
STRUCTURES = {
    "Residential (RCC Frame)": {"cost": 1800, "steel": 4.0, "cement": 0.45},
    "Commercial (RCC Frame)": {"cost": 2400, "steel": 4.8, "cement": 0.50},
    "Industrial (PEB / Steel)": {"cost": 2100, "steel": 7.5, "cement": 0.30},
    "Villa / Premium": {"cost": 3200, "steel": 4.5, "cement": 0.50},
}
TIERS = {
    "Tier 1 (Mumbai, Delhi, Bengaluru)": {"cost_mult": 1.25, "market": 12000},
    "Tier 2 (Indore, Pune, Jaipur)": {"cost_mult": 1.0, "market": 6500},
    "Tier 3 (Smaller cities)": {"cost_mult": 0.85, "market": 3800},
}
MILESTONES = [(0, "Site prep"), (15, "Foundation"), (35, "Structure / Slab"),
              (60, "Masonry & MEP"), (80, "Finishing"), (95, "Handover")]

# Weather protocols (Epic 5)
WEATHER = {
    "High Wind": [
        ("crit", "Suspend crane and hoisting operations when wind exceeds ~36 km/h (IS 875 / OSHA guidance)."),
        ("warn", "Secure scaffolding ties, loose sheets and formwork; clear unsecured materials from heights."),
        ("warn", "Restrict work on edges, roofs and tall scaffolds. Use tag lines on suspended loads."),
    ],
    "Heavy Rain": [
        ("crit", "Isolate temporary electrical panels; use RCCB/ELCB and keep cables off wet ground."),
        ("warn", "Cover freshly cast concrete; stop pours if rain is forecast within the initial set window."),
        ("warn", "Inspect excavations for collapse risk; pump out water; check shoring."),
        ("warn", "Anti-slip walkways and mandatory insulated footwear."),
    ],
    "Extreme Heat": [
        ("crit", "Enforce hydration breaks (water + ORS) and shaded rest areas; shift heavy work to early morning."),
        ("warn", "Concrete curing: wet-cure or use curing compound; start curing within hours of finishing, minimum 7 days (IS 456)."),
        ("warn", "Watch for heat-stress symptoms; buddy system for workers at height."),
    ],
    "Normal": [
        ("ok", "Conditions normal. Proceed with the planned schedule and run the daily toolbox talk."),
        ("ok", "Routine checks: PPE, scaffold tags, lifting gear inspection, housekeeping."),
    ],
}

CHAT_SYSTEM = (
    "You are a senior site engineer assistant for Indian construction projects. Be concise and practical. "
    "Cite IS codes (IS 456, IS 800, IS 875, IS 1893) or OSHA where relevant. "
    "Prioritise safety; recommend consulting a licensed structural engineer for structural decisions."
)


def demo_chat_reply(q: str) -> str:
    q = q.lower()
    if any(k in q for k in ["curing", "concrete", "cement"]):
        return "Cure concrete for at least 7 days (10+ with blended cement) per IS 456. Keep it continuously moist, shade it in heat, and protect it from rain in the first hours. *(Demo mode)*"
    if any(k in q for k in ["crack", "settle"]):
        return "Measure crack width and fix gauges. Under 0.3 mm is usually cosmetic; 0.3-5 mm suits epoxy injection; wider or stepped cracks need a structural engineer. *(Demo mode)*"
    if any(k in q for k in ["ppe", "helmet", "safety", "harness"]):
        return "Minimum PPE: helmet, high-vis vest, safety boots, gloves; full-body harness for any work above ~1.8 m with an anchor point. *(Demo mode)*"
    if any(k in q for k in ["cost", "budget", "price"]):
        return "Use the Planning tab for a quick estimate. Add 5-10% contingency, and track steel and cement prices as they swing the budget most. *(Demo mode)*"
    return "I'm in demo mode (no API key), so I can answer basics on curing, cracks, PPE and cost. Add a Gemini key for full answers."


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🏗️ Control Panel")
    api_key = st.text_input("Google Gemini API key", type="password",
                            help="Get one free at aistudio.google.com. Leave blank for demo mode.")
    model_name = st.text_input("Gemini model", value="gemini-2.5-flash",
                               help="Any multimodal Gemini model name.")
    client = get_client(api_key) if api_key else None
    if client:
        st.success("Live mode: Gemini connected")
    else:
        st.info("Demo mode: sample outputs")

    st.markdown("### Architecture")
    st.markdown(
        """
- **UI:** Streamlit
- **Vision/LLM:** Gemini multimodal
- **Contracts:** JSON schemas per module
- **Valuation:** rule-based INR model
- **3D concept:** Pollinations image API
- **Storage:** none (session state only)
"""
    )
    st.markdown("### Features")
    st.markdown("1. PPE Audit\n2. Crack Diagnostics\n3. Planning & Valuation\n4. Weather & Assistant")
    st.caption("Skill Wallet Capstone · Project 1")

st.markdown(
    '<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>'
    "<p>Site safety audits · Crack diagnostics · INR cost & valuation · Weather-aware protocols</p></div>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🦺 Safety & PPE Audit", "🧱 Crack Diagnostics", "📐 Planning & Valuation", "🌦️ Site Assistant"]
)

# ----------------------------------------------------------------------------
# Tab 1: PPE audit
# ----------------------------------------------------------------------------
with tab1:
    st.subheader("Site Safety & PPE Audit")
    up = st.file_uploader("Upload a construction site photo", type=["jpg", "jpeg", "png"], key="ppe_up")
    if up:
        img = Image.open(up).convert("RGB")
        c1, c2 = st.columns([1, 1.3])
        c1.image(img, caption="Uploaded photo", use_container_width=True)
        if c2.button("Run PPE audit", type="primary", key="ppe_btn"):
            with st.spinner("Analysing site..."):
                try:
                    st.session_state["ppe"] = (
                        call_vision(client, model_name, PPE_PROMPT, img) if client else DEMO_PPE
                    )
                except Exception as e:  # noqa: BLE001
                    st.error(f"Analysis failed: {e}")

    r = st.session_state.get("ppe")
    if r:
        try:
            score = int(r["safety_score"])
            status = r["overall_status"]
            color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            m1, m2, m3 = st.columns(3)
            with m1:
                metric_card("Safety score", f"{score}/100")
            with m2:
                metric_card("Workers detected", str(r.get("workers_detected", "-")))
            with m3:
                st.markdown(
                    f'<div class="card"><div class="label">Overall status</div>{pill(status, color)}</div>',
                    unsafe_allow_html=True,
                )
            st.progress(max(0, min(score, 100)) / 100)

            st.markdown("#### PPE checklist")
            for item, d in r["ppe_detection"].items():
                icon = "✅" if d["detected"] else "❌"
                st.markdown(f"{icon} **{item.replace('_', ' ').title()}**: {d['note']}")

            st.markdown("#### Identified hazards")
            for h in r.get("hazards", []):
                sev = h["severity"]
                st.markdown(
                    f"{pill(sev, SEVERITY_COLOR.get(sev, 'yellow'))} **{h['hazard']}**<br>"
                    f"<small>Remedy: {h['remedy']}</small>",
                    unsafe_allow_html=True,
                )
                st.write("")
            st.info(r.get("summary", ""))
            st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2),
                               file_name=f"ppe_audit_{datetime.now():%Y%m%d_%H%M}.json",
                               mime="application/json")
        except (KeyError, TypeError, ValueError) as e:
            st.error(f"Unexpected response format: {e}")
            st.json(r)

# ----------------------------------------------------------------------------
# Tab 2: Crack diagnostics
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    up2 = st.file_uploader("Upload concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack_up")
    if up2:
        img2 = Image.open(up2).convert("RGB")
        c1, c2 = st.columns([1, 1.3])
        c1.image(img2, caption="Uploaded surface", use_container_width=True)
        if c2.button("Diagnose defect", type="primary", key="crack_btn"):
            with st.spinner("Analysing structure..."):
                try:
                    st.session_state["crack"] = (
                        call_vision(client, model_name, CRACK_PROMPT, img2) if client else DEMO_CRACK
                    )
                except Exception as e:  # noqa: BLE001
                    st.error(f"Analysis failed: {e}")

    r = st.session_state.get("crack")
    if r:
        try:
            sev = int(r["severity_score"])
            ucolor = {"Monitor": "green", "Repair Soon": "orange", "Immediate Action": "red"}.get(r["urgency"], "yellow")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                metric_card("Defect type", r["defect_type"])
            with m2:
                metric_card("Severity", f"{sev}/100")
            with m3:
                metric_card("Est. width", f"{r['estimated_width_mm']} mm")
            with m4:
                st.markdown(
                    f'<div class="card"><div class="label">Urgency</div>{pill(r["urgency"], ucolor)}</div>',
                    unsafe_allow_html=True,
                )
            a, b = st.columns(2)
            a.markdown("#### Root causes")
            for x in r["root_causes"]:
                a.markdown(f"- {x}")
            b.markdown("#### Recommended repairs")
            for x in r["recommended_repairs"]:
                b.markdown(f"- {x}")
            st.markdown(f"**Monitoring:** {r.get('monitoring_advice', '-')}")
            st.info(r.get("summary", ""))
            st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2),
                               file_name=f"crack_report_{datetime.now():%Y%m%d_%H%M}.json",
                               mime="application/json")
        except (KeyError, TypeError, ValueError) as e:
            st.error(f"Unexpected response format: {e}")
            st.json(r)

# ----------------------------------------------------------------------------
# Tab 3: Planning & valuation
# ----------------------------------------------------------------------------
with tab3:
    st.subheader("Project Planning & Real Estate Valuation")
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(STRUCTURES))
    tier = c2.selectbox("Location tier", list(TIERS))
    sqft = c1.number_input("Built-up area (sqft)", min_value=100, max_value=1_000_000, value=2000, step=100)
    pct = c2.slider("Completion %", 0, 100, 40)

    s, t = STRUCTURES[stype], TIERS[tier]
    budget = sqft * s["cost"] * t["cost_mult"]
    capex = budget * pct / 100
    # Asset value: market rate x area, scaled by completion (finished value realised progressively)
    full_value = sqft * t["market"] * (1.15 if "Villa" in stype else 1.0)
    asset_value = full_value * (0.25 + 0.75 * pct / 100) if pct > 0 else full_value * 0.25
    steel_t = sqft * s["steel"] / 1000
    cement_bags = sqft * s["cement"]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Total budget", inr(budget))
    with m2:
        metric_card("CapEx incurred", inr(capex))
    with m3:
        metric_card("Current asset value", inr(asset_value))
    with m4:
        metric_card("Value on completion", inr(full_value))
    m5, m6 = st.columns(2)
    with m5:
        metric_card("Steel requirement", f"{steel_t:,.1f} tonnes")
    with m6:
        metric_card("Cement requirement", f"{cement_bags:,.0f} bags (50 kg)")

    st.markdown("#### Milestone progress")
    st.progress(pct / 100)
    current = [name for p, name in MILESTONES if pct >= p][-1]
    st.caption(f"Current phase: **{current}**")
    cols = st.columns(len(MILESTONES))
    for col, (p, name) in zip(cols, MILESTONES):
        col.markdown(f"{'✅' if pct >= p else '⬜'}<br><small>{name}</small>", unsafe_allow_html=True)
    st.caption("Indicative planning estimates only (excludes land cost). Get a quantity surveyor's estimate for tendering.")

    st.markdown("#### 🎨 Conceptual 3D architectural rendering")
    style = st.selectbox("Style", ["Modern minimalist", "Contemporary Indian", "Glass facade", "Sustainable / green"])
    extra = st.text_input("Extra details (optional)", placeholder="e.g. rooftop garden, sunset lighting")
    prompt = (f"3D architectural rendering of a {stype.split(' (')[0].lower()} building, {style} style, "
              f"{int(sqft)} sqft, Indian city, photorealistic, golden hour, {extra}").strip(", ")
    st.code(prompt, language=None)
    if st.button("Generate rendering", key="render_btn"):
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
               + "?width=1024&height=640&nologo=true")
        try:
            st.image(url, caption="Concept render (Pollinations AI)", use_container_width=True)
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not load image: {e}")

# ----------------------------------------------------------------------------
# Tab 4: Weather + assistant
# ----------------------------------------------------------------------------
with tab4:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    wx = st.radio("Today's condition", list(WEATHER), horizontal=True)
    for kind, msg in WEATHER[wx]:
        st.markdown(f'<div class="alert {kind}">{msg}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 💬 Site engineering assistant")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if user_q := st.chat_input("Ask about curing, scaffolding, IS codes, cost, safety..."):
        st.session_state.chat.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    if client:
                        history = "\n".join(
                            f"{'Engineer' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                            for m in st.session_state.chat[-10:]
                        )
                        full = f"{CHAT_SYSTEM}\nToday's weather: {wx}.\n\n{history}\nAssistant:"
                        reply = client.models.generate_content(model=model_name, contents=full).text
                    else:
                        reply = demo_chat_reply(user_q)
                except Exception as e:  # noqa: BLE001
                    reply = f"Sorry, the assistant hit an error: {e}"
            st.markdown(reply)
        st.session_state.chat.append({"role": "assistant", "content": reply})
    if st.session_state.chat and st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()
