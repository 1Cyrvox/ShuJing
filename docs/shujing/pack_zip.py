import zipfile, os
from pathlib import Path

site = Path(__file__).resolve().parents[1] / "site"
out = Path(__file__).resolve().parent / "shujing-site.zip"
count = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for p in site.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            arcname = str(p.relative_to(site)).replace(os.sep, "/")
            zf.write(p, arcname)
            count += 1
            if count % 200 == 0:
                print(f"  {count} files...", flush=True)
print(f"Done: {count} files -> {out}")
print(f"Size: {out.stat().st_size / 1024 / 1024:.1f} MB")