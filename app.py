import os
import re
import json
from json import JSONDecodeError

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from groq import Groq


# -------------------------
# Config / Setup
# -------------------------
st.set_page_config(page_title="SceneSense AI", layout="centered")

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found. Add it to your .env file and restart Streamlit.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)


# -------------------------
# Prompt Builder
# -------------------------
def build_prompt(scene_text: str, mode: str = "director") -> str:
    return f"""
You are SceneSense AI — an assistant for film directors and screenwriters.

TASK:
Analyze the screenplay scene and produce structured cinematic planning outputs.
Do NOT copy keywords. Reason using context: dialogue + action + atmosphere.

MODE:
{mode}

OUTPUT RULES:
- Return ONLY valid JSON.
- Do not add extra text.
- Keep it production-oriented and usable.
- All HEX codes must be valid #RRGGBB.
- shot_list should be 5 to 8 shots.

JSON FORMAT (strict):
{{
  "mode": "{mode}",
  "emotion": "<primary emotional tone>",
  "genre": "<thriller|romance|horror|action|drama|comedy|mystery|sci-fi|other>",
  "tone": "<1-3 words: eerie, hopeful, tense, intimate, chaotic...>",
  "intensity": <integer 1-10>,
  "narrative_purpose": "<why this scene exists in the story>",
  "visual_mood": "<lighting + atmosphere in one sentence>",
  "camera_style": "<suggested camera movement/framing in one sentence>",
  "color_palette": [
    {{"name": "<color name>", "hex": "<#RRGGBB>", "usage": "<where to use>"}},
    {{"name": "<color name>", "hex": "<#RRGGBB>", "usage": "<where to use>"}},
    {{"name": "<color name>", "hex": "<#RRGGBB>", "usage": "<where to use>"}}
  ],
  "shot_list": [
    {{
      "shot_number": 1,
      "shot_type": "<Wide|Medium|Close-up|Over-shoulder|POV|Tracking|Insert>",
      "camera_movement": "<Static|Handheld|Dolly|Crane|Pan|Tilt|Push-in|Pull-out>",
      "framing": "<framing composition>",
      "lighting": "<lighting setup>",
      "purpose": "<what this shot communicates>"
    }}
  ],
  "storyboard_prompts": [
    "<prompt 1 for image generation (cinematic style)>",
    "<prompt 2 for image generation (cinematic style)>",
    "<prompt 3 for image generation (cinematic style)>"
  ],
  "writer_notes": {{
    "emotional_beat": "<only if mode is writer, else short>",
    "subtext": "<only if mode is writer, else short>",
    "dialogue_suggestions": ["<optional rewrite idea 1>", "<optional rewrite idea 2>"]
  }},
  "confidence": <number between 0 and 1>
}}

Scene:
\"\"\"{scene_text}\"\"\"
"""


# -------------------------
# JSON Extraction (robust)
# -------------------------
def extract_json(text: str) -> dict:
    """
    Tries direct json.loads. If fails, tries to extract the first {...} block.
    """
    try:
        return json.loads(text)
    except JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            return json.loads(candidate)
        raise


# -------------------------
# Script Scene Splitter
# -------------------------
def split_scenes(script_text: str, max_scenes: int = 20):
    """
    Splits script into scenes using INT./EXT. headings.
    Keeps it simple and robust for hackathon demo.
    """
    script_text = script_text.replace("\r\n", "\n")

    # Find scene headings lines like: INT. SOMETHING - DAY / EXT. ...
    # We'll split before each heading.
    pattern = r"(?m)^(INT\.|EXT\.)\s.*$"
    matches = list(re.finditer(pattern, script_text))

    if not matches:
        # fallback: treat entire script as one scene
        return [script_text.strip()] if script_text.strip() else []

    scenes = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(script_text)
        chunk = script_text[start:end].strip()
        if chunk:
            scenes.append(chunk)

    return scenes[:max_scenes]


# -------------------------
# Model Call
# -------------------------
def analyze_scene(scene_text: str, mode: str = "director") -> dict:
    prompt = build_prompt(scene_text, mode)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a professional film analysis assistant. Output ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    raw = response.choices[0].message.content
    data = extract_json(raw)

    # Lightweight normalization / guards
    data["mode"] = data.get("mode", mode)
    if "intensity" in data:
        try:
            data["intensity"] = int(data["intensity"])
        except Exception:
            data["intensity"] = 5

    return data


# -------------------------
# UI
# -------------------------
st.title("🎬 SceneSense AI")
st.caption("AI-powered Scene Intent & Visual Planning Engine")

st.markdown("---")

mode = st.radio("Select Mode", ["director", "writer"], horizontal=True)

# Example scenes
samples = {
    "None": "",
    "Tension Scene": """INT. ABANDONED WAREHOUSE - NIGHT

John pauses before answering. His jaw tightens.
Rain echoes on the metal roof. The silence feels heavy.""",
    "Romantic Scene": """EXT. PARK - SUNSET

She smiles softly and steps closer.
The fading light wraps them in warmth as the city noise fades away.""",
    "Action Scene": """EXT. ALLEYWAY - NIGHT

A motorbike skids into frame. Glass shatters.
Two figures sprint between shadows as sirens grow louder.""",
}

selected = st.selectbox("Load example scene (optional)", list(samples.keys()))
scene_text = st.text_area("Scene Text", value=samples[selected], height=160)

colA, colB = st.columns([1, 1])

with colA:
    run_single = st.button("Analyze Scene", use_container_width=True)

with colB:
    st.write("")  # spacing
    st.write("")  # spacing

# Batch upload
st.markdown("### 📂 Batch Mode (Upload a Script)")
uploaded = st.file_uploader("Upload a script (.txt)", type=["txt"])

batch_results = None
df = None

if uploaded:
    script_text = uploaded.read().decode("utf-8", errors="ignore")
    scenes = split_scenes(script_text, max_scenes=20)

    if not scenes:
        st.warning("No scenes detected.")
    else:
        st.info(f"Detected {len(scenes)} scene(s). Click below to run batch analysis.")
        run_batch = st.button("Run Batch Analysis (Max 20 scenes)", use_container_width=True)

        if run_batch:
            batch_results = []
            with st.spinner("Analyzing scenes..."):
                for i, sc in enumerate(scenes, 1):
                    data = analyze_scene(sc, mode="director")
                    data["scene_number"] = i
                    data["scene_heading"] = sc.split("\n")[0][:80]  # first line
                    batch_results.append(data)

            st.success("✅ Batch analysis complete")

            # Build table
            rows = []
            for d in batch_results:
                rows.append(
                    {
                        "scene_number": d.get("scene_number"),
                        "scene_heading": d.get("scene_heading", ""),
                        "emotion": d.get("emotion", ""),
                        "genre": d.get("genre", ""),
                        "tone": d.get("tone", ""),
                        "intensity": d.get("intensity", 0),
                        "confidence": d.get("confidence", 0),
                    }
                )
            df = pd.DataFrame(rows)

            st.markdown("### 📊 Batch Summary Table")
            st.dataframe(df, use_container_width=True)

            st.markdown("### 📈 Scene Intensity Timeline")
            try:
                st.line_chart(df.set_index("scene_number")["intensity"])
            except Exception:
                st.info("Timeline not available (intensity missing).")

            # Downloads
            st.markdown("### ⬇️ Export")
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                data=csv_bytes,
                file_name="scenesense_batch.csv",
                mime="text/csv",
                use_container_width=True,
            )

            json_bytes = json.dumps(batch_results, indent=2).encode("utf-8")
            st.download_button(
                "Download JSON",
                data=json_bytes,
                file_name="scenesense_batch.json",
                mime="application/json",
                use_container_width=True,
            )

st.markdown("---")

# Single Scene Output
if run_single:
    if not scene_text.strip() or len(scene_text.strip()) < 30:
        st.warning("Please enter a longer scene (at least ~30 characters) for meaningful analysis.")
    else:
        with st.spinner("Analyzing scene intent..."):
            data = analyze_scene(scene_text, mode=mode)

        st.success("Analysis Complete ✅")

        col1, col2, col3 = st.columns(3)
        col1.metric("Emotion", data.get("emotion", "—"))
        col2.metric("Genre", data.get("genre", "—"))
        col3.metric("Intensity", str(data.get("intensity", "—")))

        st.subheader("🎥 Cinematic Summary")
        st.write("**Narrative Purpose:**", data.get("narrative_purpose", "—"))
        st.write("**Visual Mood:**", data.get("visual_mood", "—"))
        st.write("**Camera Style:**", data.get("camera_style", "—"))
        st.write("**Confidence:**", data.get("confidence", "—"))

        st.subheader("🎨 Color Palette")
        palette = data.get("color_palette", [])
        if palette:
            for c in palette:
                name = c.get("name", "")
                hx = c.get("hex", "")
                usage = c.get("usage", "")
                st.write(f"- **{name}** ({hx}): {usage}")
        else:
            st.write("—")

        st.subheader("🎬 Shot List (Production Ready)")
        shots = data.get("shot_list", [])
        if shots:
            for shot in shots:
                st.markdown(
                    f"""
**Shot {shot.get('shot_number', '')} — {shot.get('shot_type', '')}**  
- Movement: {shot.get('camera_movement', '')}  
- Framing: {shot.get('framing', '')}  
- Lighting: {shot.get('lighting', '')}  
- Purpose: {shot.get('purpose', '')}  
"""
                )
        else:
            st.write("—")

        st.subheader("🧠 Storyboard Prompts")
        prompts = data.get("storyboard_prompts", [])
        if prompts:
            for p in prompts:
                st.write("•", p)
        else:
            st.write("—")

        if mode == "writer":
            st.subheader("✍️ Writer Notes")
            wn = data.get("writer_notes", {})
            st.write("**Emotional Beat:**", wn.get("emotional_beat", "—"))
            st.write("**Subtext:**", wn.get("subtext", "—"))
            st.write("**Dialogue Suggestions:**")
            ds = wn.get("dialogue_suggestions", [])
            if ds:
                for s in ds:
                    st.write("•", s)
            else:
                st.write("—")

        st.subheader("📦 Raw JSON Output")
        st.json(data)

        # Downloads for single scene
        st.markdown("### ⬇️ Export")
        single_json = json.dumps(data, indent=2).encode("utf-8")
        st.download_button(
            "Download Scene JSON",
            data=single_json,
            file_name="scenesense_scene.json",
            mime="application/json",
            use_container_width=True,
        )

st.markdown("---")
st.caption("SceneSense AI — Hackathon Prototype. Future roadmap: batch script upload + PDF export + integrations with storyboard/previz tools.")
