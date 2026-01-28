
import os
import json
import sys
from dotenv import load_dotenv

# Add parent dir to sys.path to import app
sys.path.append(os.path.abspath("scene-intent-engine"))

from app import call_groq

load_dotenv()

SCENE = """INT. ABANDONED WAREHOUSE - NIGHT

The metal door creaks open. Riya steps inside, holding her phone like a torch.
Water drips from the ceiling. Somewhere deep in the dark — a faint CLICK.

She freezes.
"""

def test_model(model_name):
    print(f"\n--- Testing {model_name} ---")
    try:
        data = call_groq(SCENE, "director", model_name, temperature=0.1, max_tokens=1000)
        print("KEYS:", list(data.keys()))
        
        if "shot_list" in data:
            print(f"SHOTS: {len(data['shot_list'])} found.")
            if len(data['shot_list']) > 0:
                print("SAMPLE SHOT:", data['shot_list'][0])
        else:
            print("❌ MISSING shot_list")

        if "color_palette" in data:
             print(f"PALETTE: {len(data['color_palette'])} colors.")
        else:
             print("❌ MISSING color_palette")
             
        return data
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

if __name__ == "__main__":
    print("Starting verification...")
    
    # 1. Test Groq 8B
    res_8b = test_model("llama-3.1-8b-instant")
    
    # 2. Test Qubrid 70B
    res_70b = test_model("llama-3.3-70b-versatile")
    
    
    # Save outputs for inspection
    if res_8b:
        with open("output_8b.json", "w", encoding="utf-8") as f:
            json.dump(res_8b, f, indent=2)
            print("Saved output_8b.json")
            
    if res_70b:
        with open("output_70b.json", "w", encoding="utf-8") as f:
            json.dump(res_70b, f, indent=2)
            print("Saved output_70b.json")

    # Compare
    if res_8b and res_70b:
        print("\n--- COMPARISON ---")
        keys_8b = set(res_8b.keys())
        keys_70b = set(res_70b.keys())
        
        missing_in_70b = keys_8b - keys_70b
        if missing_in_70b:
            print(f"WARN Keys in 8B but MISSING in 70B: {missing_in_70b}")
        else:
            print("OK. 70B has all keys that 8B has.")
            
        # Check specific structures
        if isinstance(res_70b.get('shot_list'), list):
             print("OK. 70B shot_list is a List")
        else:
             print(f"WARN 70B shot_list is {type(res_70b.get('shot_list'))}")
