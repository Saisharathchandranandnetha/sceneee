# 🎬 SceneSense AI — Scene Intent & Visual Planning Engine

SceneSense AI is a lightweight AI tool that converts **raw screenplay scenes (text)** into **structured cinematic intent** such as:

✅ Emotion  
✅ Narrative Purpose  
✅ Visual Mood  
✅ Camera Style  
✅ Confidence Score  

This helps film teams align faster during **pre-production** (planning shots, lighting, mood, and storytelling intent).

---

## 🚀 Demo Preview (What it does)

### ✅ Input
Paste any screenplay scene like:

> INT. ABANDONED WAREHOUSE - NIGHT  
> John pauses before answering. His jaw tightens.  
> Rain echoes on the metal roof. The silence feels heavy.

### ✅ Output (Strict JSON)
```json
{
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
```

📌 Problem We Solve

In filmmaking, screenplay scenes are unstructured text.
Teams spend time repeatedly discussing:

What is the emotional tone of this scene?

What is the purpose of this scene in the story?

What should the lighting and mood look like?

What type of camera movement fits this moment?

This manual process is:
❌ slow
❌ inconsistent
❌ dependent on interpretation
❌ creates miscommunication between director, DoP, storyboard team

✅ SceneSense AI gives a fast, structured baseline in seconds.

✅ Solution Overview

SceneSense AI provides a structured cinematic breakdown using an LLM:

Scene Text → AI Analysis → JSON Output + Confidence Score

This helps directors and teams quickly align on:

mood

narrative goal

visual tone

framing ideas

🏗️ Architecture (High Level)
User (Browser)
   ↓
Streamlit UI (app.py)
   ↓
Prompt Builder (strict JSON format)
   ↓
Groq API (LLaMA 3.1 8B Instant)
   ↓
JSON Parser + Confidence Badge
   ↓
Final Output in UI

⚙️ Tech Stack

Python

Streamlit (UI)

Groq API (LLM inference)

LLaMA 3.1 8B Instant

python-dotenv (API key management)

JSON parsing for structured output

📂 Project Structure
scene-intent-engine/
│── app.py
│── test_groq.py
│── requirements.txt
│── .env.example
│── .gitignore
│── README.md

✅ Setup & Run Locally (VS Code)
✅ 1. Clone the Repository
git clone <your-repo-link>
cd scene-intent-engine

✅ 2. Create Virtual Environment
Windows (PowerShell)
python -m venv venv
.\venv\Scripts\activate

Mac/Linux
python3 -m venv venv
source venv/bin/activate

✅ 3. Install Dependencies
pip install -r requirements.txt

✅ 4. Add Groq API Key (Important)
Create a .env file inside project folder:

✅ DO NOT upload .env to GitHub

GROQ_API_KEY=your_api_key_here

Example .env.example file already provided:
GROQ_API_KEY=your_api_key_here

✅ 5. Run the App

✅ Recommended command (works always):

python -m streamlit run app.py


App runs here:
📍 http://localhost:8501

✅ Testing Groq Connection (Optional)

Use this before running UI:

python test_groq.py


Expected output:

{"status":"ok"}

✅ Common Errors & Fixes
❌ streamlit not recognized

✅ Fix:

python -m pip install streamlit
python -m streamlit run app.py

❌ GROQ_API_KEY not found

✅ Fix:
Create .env file in same folder as app.py

GROQ_API_KEY=your_api_key_here

❌ JSON output parsing error

✅ Why it happens:
Sometimes model output might not return strict JSON.

✅ Fix:
Try again OR reduce temperature OR use longer scene input.

(Future Enhancements)

✅ Multi-scene analysis (entire script)
✅ Batch processing + caching
✅ Shot-list generation from JSON output
✅ Export to PDF / CSV
✅ Director Mode vs Writer Mode
✅ Integration with storyboard & previz tools
