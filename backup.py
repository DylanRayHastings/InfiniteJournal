import os
import zipfile
import time
from pathlib import Path

# ---- CONFIGURATION ----
REPO_ROOT = Path(__file__).resolve().parent  # Automatically gets directory of this file
BACKUP_DIR = REPO_ROOT / "backups"
MAX_BACKUPS = 5

BACKUP_DIR.mkdir(exist_ok=True)

timestamp = time.strftime("%Y%m%d_%H%M%S")
zip_filename = BACKUP_DIR / f"repo_{timestamp}.zip"

# ---- CREATE ZIP OF ENTIRE REPOSITORY ----
zf = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk(REPO_ROOT):
    if BACKUP_DIR.samefile(root):
        continue  # Don't include the backup folder itself
    for file in files:
        abs_file = Path(root) / file
        rel_path = abs_file.relative_to(REPO_ROOT.parent)
        zf.write(abs_file, rel_path)
zf.close()

# ---- CLEANUP OLD BACKUPS ----
zips = list(BACKUP_DIR.glob("repo_*.zip"))
zips.sort(key=os.path.getmtime, reverse=True)
i = MAX_BACKUPS
while i < len(zips):
    old_zip = zips[i]
    try:
        old_zip.unlink()
    except Exception as e:
        print(f"Could not delete old backup: {old_zip} ({e})")
    i += 1
