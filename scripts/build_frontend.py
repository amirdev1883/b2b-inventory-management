"""Build the React interface and package it for Django/WhiteNoise."""

import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=root / "frontend", check=True)
subprocess.run(["npm", "run", "build"], cwd=root / "frontend", check=True)
templates = root / "backend" / "templates" / "compiled"
templates.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "frontend" / "dist" / "index.html", templates / "index.html")
shutil.copytree(
    root / "frontend" / "dist" / "assets",
    root / "backend" / "static" / "assets",
    dirs_exist_ok=True,
)
print("Frontend packaged. Run python backend/manage.py collectstatic --noinput next.")
