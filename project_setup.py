from pathlib import Path

dirs = ["data/raw", "data/processed", "notebooks", "src", "app", "claude_project"]
files = ["src/__init__.py", "src/feature_engineering.py", "src/recommender.py",
         "src/product_catalog.py", "app/main.py", "claude_project/system_prompt.md",
         "requirements.txt", "README.md"]

for d in dirs:
    Path(d).mkdir(parents=True, exist_ok=True)
for f in files:
    Path(f).touch(exist_ok=True)
print("Repo structure ready")