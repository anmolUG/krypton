import os
import sys
from pathlib import Path

# Add the project root to sys.path to allow importing from src
sys.path.append(str(Path(__file__).parent))

from src.detection import _download_models

def main():
    model_dir = Path(__file__).parent / "models" / "buffalo_l"
    print(f"Downloading models to {model_dir}...")
    _download_models(model_dir)
    print("Download complete.")

if __name__ == "__main__":
    main()
