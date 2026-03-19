"""
Reload and resave pickle models to fix numpy compatibility
"""
import joblib
import numpy as np
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "artifacts" / "models"

def resave_models():
    """Reload and resave all joblib pickle files"""
    models_reloaded = 0
    errors = []
    
    for model_file in MODELS_DIR.rglob("*.joblib"):
        try:
            print(f"Loading: {model_file.relative_to(MODELS_DIR)}")
            # Load with protocol to handle old pickles
            model = joblib.load(model_file)
            # Resave with highest protocol available
            joblib.dump(model, model_file, protocol=4)
            print(f"✅ Resaved: {model_file.relative_to(MODELS_DIR)}")
            models_reloaded += 1
        except Exception as e:
            error_msg = f"❌ {model_file.relative_to(MODELS_DIR)}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
    
    print(f"\n✅ Successfully reloaded and resaved {models_reloaded} models")
    if errors:
        print(f"\n⚠️  {len(errors)} errors encountered:")
        for err in errors:
            print(f"  {err}")

if __name__ == "__main__":
    resave_models()
