import streamlit as st
from groq import Groq
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

st.set_page_config(page_title="Scene Intent Engine", layout="centered")

st.title("🎬 Scene Intent & Visual Planning Engine")
st.write("Paste a film script scene to extract emotion, mood, and visual intent.")

# Sample scenes for demo
samples = {
    "Tension Scene": """INT. ABANDONED WAREHOUSE – NIGHT

John pauses before answering. His jaw tightens.
Rain echoes on the metal roof. The silence feels heavy.""",

    "Romantic Scene": """EXT. PARK – SUNSET

She smiles softly and steps closer.
The fading light wraps them in warmth.""",

    "Action Scene": """EXT. CITY STREET – DAY

Cars screech as he sprints across traffic.
Sirens howl behind him."""
}

choice = st.selectbox("Load example scene (optional)", ["None"] + list(samples.keys()))

scene_text = samples.get(choice, "")

scene = st.text_area("Scene Text", value=scene_text, height=200)

if st.button("Analyze Scene"):
    if len(scene.strip()) < 30:
        st.warning("Please enter a longer scene for meaningful analysis.")
    else:
        with st.spinner("Analyzing scene intent..."):
            prompt = f"""
You are an AI assistant for film directors.

Analyze the following script scene and infer its creative intent.
Reason over dialogue, actions, and atmosphere — not keywords.

Return ONLY valid JSON in the following format:

{{
  "emotion": "<primary emotional tone>",
  "narrative_purpose": "<purpose of the scene in the story>",
  "visual_mood": "<lighting and atmosphere>",
  "camera_style": "<suggested camera movement or framing>",
  "confidence": <number between 0 and 1>
}}

Scene:
\"\"\"{scene}\"\"\"
"""

            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a professional film analysis assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )

                result = json.loads(response.choices[0].message.content)
                result["confidence"] = max(0.0, min(1.0, result["confidence"]))

                st.success("Analysis Complete")
                st.json(result)

                if result["confidence"] >= 0.8:
                    st.write("🟢 Confidence: High")
                elif result["confidence"] >= 0.6:
                    st.write("🟡 Confidence: Medium")
                else:
                    st.write("🔴 Confidence: Low")

            except Exception as e:
                st.error("Failed to analyze scene.")
                st.write(e)

            st.markdown("---")
st.markdown("## ✅ Final Recommendations & Next Steps")

st.markdown("""
**SceneSense AI** is designed as a pre-production assistant.  
Based on this demo, we recommend the following next steps for real-world use:
""")

st.markdown("""
### 🎬 Creative Recommendations
- Use extracted **emotion & visual mood** to guide lighting and color palette decisions
- Apply **camera style suggestions** directly during storyboarding and shot planning
- Use confidence score to identify scenes needing human creative review
""")

st.markdown("""
### 🚀 Product Roadmap (Post-Hackathon)
- Multi-scene screenplay upload and batch analysis  
- Automatic **shot list generation** per scene  
- Integration with **storyboarding / previz tools** (Unreal, Blender, Runway)  
- Director Mode vs Writer Mode outputs  
""")

st.markdown("""
### 🏆 Hackathon Takeaway
This project demonstrates how **LLM-based reasoning** can convert unstructured script text
into **actionable cinematic intent**, saving time during early film production.
""")

