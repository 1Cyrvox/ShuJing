import zipfile, os
from pathlib import Path

site = Path(r"D:\asd\dfghj\manimgx-src\docs\site")
out = Path(r"D:\asd\dfghj\manimgx-src\docs\shujing\shujing-site.zip")
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