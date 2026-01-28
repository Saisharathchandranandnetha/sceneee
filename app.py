# app.py — SceneSense AI (UI/UX “wow” version)
# ------------------------------------------------------------
# What you get:
# ✅ Premium, eye-catching Streamlit UI (cards, tabs, palette swatches, timeline feel)
# ✅ Director / Writer modes (role-based outputs)
# ✅ Single scene + Batch mode (.txt) with scene splitter
# ✅ Robust JSON parsing + graceful fallbacks (won’t crash if fields missing)
# ✅ Export: JSON + Shotlist CSV + Batch CSV
#
# Run:
#   python -m pip install -r requirements.txt
#   python -m streamlit run app.py --server.port 8503
#
# Env:
#   Create .env in same folder:
#     GROQ_API_KEY=your_key_here
# ------------------------------------------------------------

import os
import re
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ---- Optional Groq client (you likely already have this pattern in your repo) ----
try:
    from groq import Groq
except Exception:
    Groq = None  # We'll handle gracefully


# =========================
# Page config + CSS
# =========================
st.set_page_config(
    page_title="SceneSense AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* ---------- Global ---------- */
html, body, [class*="css"] {
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
}
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.08); }

/* ---------- Hero ---------- */
.hero {
  padding: 18px 18px 14px 18px;
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  background: radial-gradient(1200px 300px at 10% 0%, rgba(124,58,237,0.25), transparent 60%),
              radial-gradient(900px 250px at 90% 20%, rgba(59,130,246,0.18), transparent 55%),
              linear-gradient(180deg, rgba(17,24,39,0.78), rgba(17,24,39,0.55));
  box-shadow: 0 12px 35px rgba(0,0,0,0.35);
}
.hero h1 { margin: 0; font-size: 34px; line-height: 1.1; }
.hero p { margin: 6px 0 0 0; opacity: 0.88; }
.hero .chips { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.05);
  font-size: 12px;
  opacity: 0.95;
}

/* ---------- Cards ---------- */
.card {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(31,41,55,0.65), rgba(17,24,39,0.55));
  padding: 14px 14px 12px 14px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.30);
}
.card h3 { margin: 0 0 6px 0; font-size: 14px; opacity: 0.92; }
.card .big { font-size: 22px; font-weight: 750; letter-spacing: 0.2px; }
.card .sub { font-size: 12px; opacity: 0.78; margin-top: 4px; }
.hr {
  height: 1px;
  background: rgba(255,255,255,0.08);
  margin: 12px 0;
}

/* ---------- Palette ---------- */
.palette {
  display: flex; gap: 10px; flex-wrap: wrap;
}
.swatch {
  width: 160px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.10);
  overflow: hidden;
  background: rgba(255,255,255,0.03);
}
.swatch .top { height: 44px; }
.swatch .bottom { padding: 10px 10px 9px 10px; }
.swatch .name { font-weight: 700; font-size: 13px; margin: 0; }
.swatch .meta { font-size: 12px; opacity: 0.80; margin: 2px 0 0 0; }

/* ---------- Shot items ---------- */
.shotrow {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  background: rgba(255,255,255,0.03);
  padding: 10px 12px;
  margin: 8px 0;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  font-size: 12px;
  margin-right: 6px;
  opacity: 0.92;
}

/* ---------- Footnotes ---------- */
.smallnote { font-size: 12px; opacity: 0.75; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================
# Helpers
# =========================
def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_get(d: Dict[str, Any], key: str, default=None):
    v = d.get(key, default)
    return default if v is None else v


def clamp_intensity(x: Any, default: int = 5) -> int:
    try:
        v = int(x)
        return max(1, min(10, v))
    except Exception:
        return default


def clamp_confidence(x: Any, default: float = 0.75) -> float:
    try:
        v = float(x)
        return max(0.0, min(1.0, v))
    except Exception:
        return default


def normalize_hex(h: str) -> str:
    if not h:
        return "#111111"
    h = h.strip()
    if not h.startswith("#"):
        h = "#" + h
    # keep #RRGGBB if possible
    if len(h) == 4:  # #RGB -> expand
        h = "#" + "".join([c * 2 for c in h[1:]])
    if len(h) != 7:
        return "#111111"
    return h


def extract_json_loose(text: str) -> Optional[Dict[str, Any]]:
    """
    Tries to recover JSON from LLM responses that include extra text or code fences.
    """
    if not text:
        return None
    # strip code fences
    text2 = re.sub(r"```(json)?", "", text, flags=re.IGNORECASE).strip("` \n\t")
    # try direct
    try:
        return json.loads(text2)
    except Exception:
        pass

    # try find first { ... } block (greedy)
    m = re.search(r"\{.*\}", text2, flags=re.DOTALL)
    if not m:
        return None
    blob = m.group(0)
    try:
        return json.loads(blob)
    except Exception:
        # common fixes: trailing commas
        blob2 = re.sub(r",(\s*[}\]])", r"\1", blob)
        try:
            return json.loads(blob2)
        except Exception:
            return None


def scene_splitter(script_text: str) -> List[str]:
    """
    Basic screenplay splitter using INT./EXT. headings.
    If no headings found, returns [whole_text].
    """
    if not script_text or len(script_text.strip()) < 30:
        return []

    # Normalize line endings
    t = script_text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on scene headings like: INT. / EXT. / INT/EXT.
    pattern = r"(?=^(?:INT\.|EXT\.|INT/EXT\.|I/E\.).*$)"
    parts = re.split(pattern, t, flags=re.MULTILINE)

    scenes = []
    for p in parts:
        p = p.strip()
        if len(p) >= 60:
            scenes.append(p)

    return scenes if scenes else [t.strip()]


# =========================
# Groq call (LLM)
# =========================
def build_prompt(scene_text: str, mode: str) -> str:
    """
    Strict schema prompt so output is consistently structured.
    Keep it short enough for speed but strict enough for JSON.
    """
    schema = {
        "mode": "director|writer",
        "emotion": "string",
        "genre": "string",
        "tone": "string",
        "intensity": "integer 1-10",
        "narrative_purpose": "string",
        "visual_mood": "string",
        "camera_style": "string",
        "color_palette": [
            {"name": "string", "hex": "#RRGGBB", "usage": "string"}
        ],
        "shot_list": [
            {
                "shot_number": "int",
                "shot_type": "string (Wide/Medium/Close-up/OTS/POV etc.)",
                "camera_movement": "string",
                "framing": "string",
                "lighting": "string",
                "purpose": "string"
            }
        ],
        "storyboard_prompts": ["string", "string", "string"],
        "writer_notes": {
            "emotional_beat": "string",
            "subtext": "string",
            "dialogue_suggestions": ["string"]
        },
        "confidence": "float 0-1"
    }

    # writer_notes should still exist but can be minimal in director mode; or present only in writer mode
    mode_value = "writer" if mode == "writer" else "director"
    req_writer = "Include writer_notes with rich content." if mode_value == "writer" else "Include writer_notes but keep it brief."
    req_shots = "Provide 5 to 8 shots in shot_list." if mode_value == "director" else "Provide 3 to 5 shots in shot_list."

    return f"""
You are SceneSense AI. Analyze the screenplay scene and return ONLY valid JSON.
No markdown, no code fences, no extra commentary.

Mode: {mode_value}

Required behavior:
- emotion: concise (e.g., tense, intimate, hopeful, eerie)
- narrative_purpose: one strong sentence
- visual_mood: lighting + atmosphere in one sentence
- camera_style: movement/framing guidance in one sentence
- genre, tone, intensity(1-10) must be present
- color_palette: exactly 3 items with valid HEX
- storyboard_prompts: exactly 3 cinematic prompts
- {req_shots}
- confidence: 0-1
- {req_writer}

JSON schema (types guidance):
{json.dumps(schema, indent=2)}

Scene:
{scene_text}
""".strip()


def call_groq(scene_text: str, mode: str, model: str, temperature: float = 0.4, max_tokens: int = 1200) -> Dict[str, Any]:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found. Add it to .env (same folder as app.py).")

    if Groq is None:
        raise RuntimeError("groq package not found. Install it or adjust your client code.")

    client = Groq(api_key=api_key)

    prompt = build_prompt(scene_text, mode)

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": "You return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
    )

    text = resp.choices[0].message.content if resp and resp.choices else ""
    data = extract_json_loose(text)
    if not isinstance(data, dict):
        raise RuntimeError("Model returned non-JSON or invalid JSON. Try again or reduce temperature.")
    return data


# =========================
# UI building blocks
# =========================
def render_hero():
    st.markdown(
        """
<div class="hero">
  <h1>🎬 SceneSense AI</h1>
  <p>Turn screenplay text into <b>director-ready planning</b> — shot lists, palettes, storyboard prompts, and writer insights.</p>
  <div class="chips">
    <span class="chip">⚡ Fast scene intent</span>
    <span class="chip">🎥 Director Mode</span>
    <span class="chip">✍️ Writer Mode</span>
    <span class="chip">📁 Batch script analysis</span>
    <span class="chip">⬇️ Export JSON / CSV</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


def render_insight_cards(data: Dict[str, Any]):
    emotion = str(safe_get(data, "emotion", "—")).title()
    genre = str(safe_get(data, "genre", "—")).title()
    tone = str(safe_get(data, "tone", "—")).title()
    intensity = clamp_intensity(safe_get(data, "intensity", 5))
    conf = clamp_confidence(safe_get(data, "confidence", 0.75))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
<div class="card">
  <h3>🎭 Emotion</h3>
  <div class="big">{emotion}</div>
  <div class="sub">Scene feeling</div>
</div>
""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
<div class="card">
  <h3>🎬 Genre</h3>
  <div class="big">{genre}</div>
  <div class="sub">Story category</div>
</div>
""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
<div class="card">
  <h3>🔥 Intensity</h3>
  <div class="big">{intensity}/10</div>
  <div class="sub">Pace & tension</div>
</div>
""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
<div class="card">
  <h3>✅ Confidence</h3>
  <div class="big">{int(conf*100)}%</div>
  <div class="sub">Output reliability</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("")


def render_summary_cards(data: Dict[str, Any]):
    purpose = str(safe_get(data, "narrative_purpose", "—"))
    mood = str(safe_get(data, "visual_mood", "—"))
    camera = str(safe_get(data, "camera_style", "—"))

    a, b, c = st.columns(3)
    with a:
        st.markdown(f"""
<div class="card">
  <h3>🎯 Narrative Purpose</h3>
  <div class="sub">{purpose}</div>
</div>
""", unsafe_allow_html=True)
    with b:
        st.markdown(f"""
<div class="card">
  <h3>🎨 Visual Mood</h3>
  <div class="sub">{mood}</div>
</div>
""", unsafe_allow_html=True)
    with c:
        st.markdown(f"""
<div class="card">
  <h3>🎥 Camera Style</h3>
  <div class="sub">{camera}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("")


def render_palette(data: Dict[str, Any]):
    palette = safe_get(data, "color_palette", []) or []
    


    if not isinstance(palette, list) or len(palette) == 0:
        st.info("🎨 No color palette generated for this scene.")
        return

    # Limit to 3 colors for clarity
    palette = palette[:3]

    st.markdown("## 🎨 Cinematic Color Palette")
    st.caption("Guides lighting, mood, costume, and color grading decisions")

    cols = st.columns(len(palette))

    for col, p in zip(cols, palette):
        name = str(safe_get(p, "name", "Color"))
        hx = normalize_hex(str(safe_get(p, "hex", "#111111")))
        usage = str(safe_get(p, "usage", ""))

        with col:
            st.markdown(
                f"""
                <div style="
                    background:{hx};
                    height:110px;
                    border-radius:16px;
                    box-shadow:0 8px 24px rgba(0,0,0,0.45);
                    margin-bottom:12px;
                "></div>

                <div style="padding-left:4px">
                    <strong style="font-size:16px">{name}</strong><br>
                    <span style="opacity:0.7; font-size:13px">{hx}</span><br>
                    <span style="font-size:13px; opacity:0.9">
                        <b>Use:</b> {usage}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )



def render_shot_list(data: Dict[str, Any]):
    shots = safe_get(data, "shot_list", []) or []
    if not isinstance(shots, list) or len(shots) == 0:
        st.info("No shot list returned.")
        return

    st.markdown("### 🎬 Shot List (Production Ready)")

    for s in shots:
        num = safe_get(s, "shot_number", None)
        stype = str(safe_get(s, "shot_type", "Shot"))
        move = str(safe_get(s, "camera_movement", "—"))
        frame = str(safe_get(s, "framing", "—"))
        light = str(safe_get(s, "lighting", "—"))
        purpose = str(safe_get(s, "purpose", "—"))

        title = f"Shot {num} — {stype}" if num is not None else f"{stype}"
        with st.expander(title, expanded=False):
            st.markdown(
                f"""
<div class="shotrow">
  <span class="badge">🎥 Movement: {move}</span>
  <span class="badge">🖼️ Framing: {frame}</span>
  <span class="badge">💡 Lighting: {light}</span>
  <div style="margin-top:8px; opacity:0.90;"><b>Purpose:</b> {purpose}</div>
</div>
""",
                unsafe_allow_html=True,
            )


def render_storyboard_prompts(data: Dict[str, Any]):
    prompts = safe_get(data, "storyboard_prompts", []) or []
    if not isinstance(prompts, list) or len(prompts) == 0:
        st.info("No storyboard prompts returned.")
        return

    st.markdown("### 🧩 Storyboard Prompts")
    for i, p in enumerate(prompts[:3], start=1):
        st.markdown(f"**Prompt {i}:** {p}")


def render_writer_notes(data: Dict[str, Any]):
    wn = safe_get(data, "writer_notes", {}) or {}
    if not isinstance(wn, dict) or len(wn) == 0:
        st.info("No writer notes returned.")
        return

    beat = str(safe_get(wn, "emotional_beat", "—"))
    sub = str(safe_get(wn, "subtext", "—"))
    sugg = safe_get(wn, "dialogue_suggestions", []) or []

    st.markdown("### ✍️ Writer Notes")
    st.success(f"**Emotional Beat**\n\n{beat}")
    st.warning(f"**Subtext**\n\n{sub}")

    if isinstance(sugg, list) and sugg:
        st.markdown("**💬 Dialogue Suggestions**")
        for s in sugg[:8]:
            st.write(f"• {s}")


def export_json_button(data: Dict[str, Any], filename_prefix: str = "scenesense_scene"):
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    st.download_button(
        "⬇️ Download Scene JSON",
        data=payload,
        file_name=f"{filename_prefix}_{now_stamp()}.json",
        mime="application/json",
        use_container_width=True,
    )


def export_shotlist_csv(data: Dict[str, Any], filename_prefix: str = "scenesense_shotlist"):
    shots = safe_get(data, "shot_list", []) or []
    if not isinstance(shots, list) or len(shots) == 0:
        st.info("No shot list available for CSV export.")
        return
    df = pd.DataFrame(shots)
    st.download_button(
        "⬇️ Download Shot List CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{filename_prefix}_{now_stamp()}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# =========================
# Sidebar controls
# =========================
def sidebar_controls() -> Dict[str, Any]:
    st.sidebar.markdown("## 🎛️ Controls")
    role = st.sidebar.radio("Role Mode", ["🎥 Director Mode", "✍️ Writer Mode"], index=0)
    mode = "director" if "Director" in role else "writer"

    st.sidebar.markdown("### ⚙️ Model Settings")
    model = st.sidebar.selectbox(
    "Groq model",
    options=[
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ],
    index=0,
)

    temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.0, 0.35, 0.05)
    max_tokens = st.sidebar.slider("Max tokens", 400, 2500, 1200, 50)

    st.sidebar.markdown("### 🧪 Output Display")
    show_raw = st.sidebar.toggle("Show raw JSON (advanced)", value=False)
    show_debug = st.sidebar.toggle("Show debug info", value=False)

    st.sidebar.markdown("### 🛡️ Stability")
    force_port_tip = st.sidebar.checkbox("Show port tips", value=False)
    if force_port_tip:
        st.sidebar.info("If Windows errors happen, run with a different port: `--server.port 8503`")

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<div class="smallnote">Tip: During demo, start with the <b>Insight Cards</b>, then show <b>Shot List</b>, then <b>Export</b>.</div>',
        unsafe_allow_html=True,
    )

    return {
        "mode": mode,
        "model": model,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "show_raw": bool(show_raw),
        "show_debug": bool(show_debug),
    }


# =========================
# Main App
# =========================
def main():
    render_hero()
    controls = sidebar_controls()

    tab1, tab2 = st.tabs(["🎬 Single Scene", "📁 Batch Mode"])

    # ---------- Single Scene ----------
    with tab1:
        st.markdown("## 🎛️ Scene Input")

        left, right = st.columns([1, 2], gap="large")

        examples = {
            "None": "",
            "Action Chase (High Intensity)": """EXT. MARKET STREET - NIGHT

A motorbike roars through crowded stalls. People scream and jump aside.
Ravi grips the handlebar, dodging carts and neon signs.

Behind him, a black SUV crashes through a fruit stand— mangos explode across the road.

RAVI (yelling): They're still on me!

A shot rings out. Glass shatters above him.
Ravi swerves into a narrow alley. Sparks fly as the bike scrapes the wall.
""",
            "Tension Thriller (Warehouse)": """INT. ABANDONED WAREHOUSE - NIGHT

The metal door creaks open. Riya steps inside, holding her phone like a torch.
Water drips from the ceiling. Somewhere deep in the dark — a faint CLICK.

She freezes.

Her breath turns shallow as the light flickers. A shadow moves behind a pillar.

RIYA: Hello...?

Silence. Then— a slow FOOTSTEP, closer this time.
""",
            "Romance (Sunset Bench)": """EXT. PARK - SUNSET

Golden light spills through the trees. Aarav and Meera sit on a bench, shoulders almost touching.

MEERA: You never told me why you left.
AARAV: I thought it was easier... than saying goodbye.

Meera turns. Her eyes shine. She reaches for his hand. He lets her.
The city noise fades, leaving only the wind and their breathing.
""",
            "Horror (Mirror)": """INT. APARTMENT BATHROOM - 2:13 AM

Only the mirror light hums. Ananya washes her face, trying to calm down.
She looks up.

Her reflection smiles— but she doesn’t.

ANANYA: ...What?

The light flickers. The reflection slowly raises its hand.
Ananya’s real hand doesn’t move.

The bathroom door behind her clicks shut by itself.
""",
        }

        with left:
            st.markdown("**Role**")
            role_label = "🎥 Director Mode" if controls["mode"] == "director" else "✍️ Writer Mode"
            st.info(f"Selected: **{role_label}**")

            ex = st.selectbox("Load example (optional)", list(examples.keys()), index=0)
            if st.button("✨ Load Example", use_container_width=True):
                st.session_state["scene_text"] = examples[ex]

            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
            st.caption("Pro tip: In demo, use “Warehouse” or “Mirror” scenes for the most cinematic output.")

        with right:
            scene_text = st.text_area(
                "Scene Text",
                value=st.session_state.get("scene_text", ""),
                height=220,
                placeholder="Paste your screenplay scene here…",
            )

            analyze = st.button("🎬 Analyze Scene", type="primary", use_container_width=True)

        if analyze:
            if not scene_text or len(scene_text.strip()) < 30:
                st.warning("Please paste a longer scene (at least ~30 characters).")
                return

            with st.spinner("Analyzing scene… generating cinematic plan ✨"):
                t0 = time.time()
                try:
                    data = call_groq(
                        scene_text=scene_text.strip(),
                        mode=controls["mode"],
                        model=controls["model"],
                        temperature=controls["temperature"],
                        max_tokens=controls["max_tokens"],
                    )
                except Exception as e:
                    st.error(f"LLM call failed: {e}")
                    return
                dt = time.time() - t0

            st.success(f"✅ Analysis complete in {dt:.2f}s")
            st.markdown("## 🔍 Scene Insight")
            render_insight_cards(data)

            st.markdown("## 🎞️ Cinematic Summary")
            render_summary_cards(data)

            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

            # Role-specific output
            if controls["mode"] == "director":
                left2, right2 = st.columns([1.1, 1], gap="large")
                with left2:
                    render_shot_list(data)
                with right2:
                    render_palette(data)
                    st.markdown("")
                    render_storyboard_prompts(data)
            else:
                left2, right2 = st.columns([1, 1], gap="large")
                with left2:
                    render_writer_notes(data)
                with right2:
                    render_palette(data)
                    st.markdown("")
                    render_storyboard_prompts(data)
                    st.markdown("")
                    render_shot_list(data)  # still useful for writers too

            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

            st.markdown("## ⬇️ Export")
            e1, e2 = st.columns([1, 1])
            with e1:
                export_json_button(data)
            with e2:
                export_shotlist_csv(data)

            if controls["show_raw"]:
                with st.expander("📦 Raw JSON (Advanced)", expanded=False):
                    st.json(data)

            if controls["show_debug"]:
                st.caption("Debug: Parsed keys")
                st.code(", ".join(sorted(list(data.keys()))))

    # ---------- Batch Mode ----------
    with tab2:
        st.markdown("## 📁 Batch Mode — Script Analysis")
        st.write("Upload a `.txt` script. The app will split it into scenes and analyze each scene (lightweight batch).")

        up = st.file_uploader("Upload script (.txt)", type=["txt"])
        batch_run = st.button("🚀 Run Batch Analysis", type="primary", use_container_width=True)

        if batch_run:
            if up is None:
                st.warning("Please upload a .txt file first.")
                return

            script_text = up.read().decode("utf-8", errors="ignore")
            scenes = scene_splitter(script_text)

            if not scenes:
                st.warning("No scenes detected. Ensure the script has content.")
                return

            st.success(f"✅ Detected {len(scenes)} scene(s). Starting batch analysis…")
            max_scenes = 12  # keep demo-safe
            scenes = scenes[:max_scenes]

            results = []
            progress = st.progress(0)
            for i, sc in enumerate(scenes, start=1):
                try:
                    data = call_groq(
                        scene_text=sc,
                        mode=controls["mode"],
                        model=controls["model"],
                        temperature=controls["temperature"],
                        max_tokens=controls["max_tokens"],
                    )
                    results.append({
                        "scene_index": i,
                        "emotion": safe_get(data, "emotion", ""),
                        "genre": safe_get(data, "genre", ""),
                        "tone": safe_get(data, "tone", ""),
                        "intensity": clamp_intensity(safe_get(data, "intensity", 5)),
                        "confidence": clamp_confidence(safe_get(data, "confidence", 0.75)),
                    })
                except Exception as e:
                    results.append({
                        "scene_index": i,
                        "emotion": "",
                        "genre": "",
                        "tone": "",
                        "intensity": "",
                        "confidence": "",
                        "error": str(e),
                    })

                progress.progress(int(i / len(scenes) * 100))

            df = pd.DataFrame(results)
            st.markdown("## 📊 Batch Summary")
            st.dataframe(df, use_container_width=True)

            st.markdown("## ⬇️ Export Batch Summary")
            st.download_button(
                "⬇️ Download Batch Summary CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"scenesense_batch_summary_{now_stamp()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            if controls["show_raw"]:
                with st.expander("📦 Raw Batch JSON (Advanced)", expanded=False):
                    st.json(results)

    st.markdown("---")
    st.markdown(
        '<div class="smallnote">Built for offline hackathon demo: Start with <b>Single Scene → Insight Cards → Shot List → Export</b>.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
