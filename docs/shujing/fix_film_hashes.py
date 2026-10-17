"""Fix film hash mismatch: copy films from old hash to new (translated) hash."""
import sys, os, shutil, textwrap
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from examples import Example, FILMS, blocks, PAGES, README, SOURCE, ROOT, FENCE
import re

def find_scene_films(scene_name):
    """Find all film files for a given scene name."""
    results = []
    for f in FILMS.iterdir():
        if f.name.startswith(f"{scene_name}-"):
            results.append(f)
    return results

def get_all_code_blocks():
    """Extract all Python code blocks from translated markdown and docstrings."""
    blocks_found = []
    
    for page in sorted(PAGES.rglob("*.md")):

        text = page.read_text(encoding="utf-8")
        for match in FENCE.finditer(text):
            code = textwrap.dedent(match.group("code"))
            e = Example(code, str(page.relative_to(ROOT)))
            if e.scene is not None:
                blocks_found.append((page, e))
    
    text = README.read_text(encoding="utf-8")
    for match in FENCE.finditer(text):
        code = textwrap.dedent(match.group("code"))
        e = Example(code, "README.md")
        if e.scene is not None:
            blocks_found.append((Path("README.md"), e))
    
    import ast
    for module in sorted(SOURCE.rglob("*.py")):
        try:
            tree = ast.parse(module.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if doc:
                    for match in FENCE.finditer(doc):
                        code = textwrap.dedent(match.group("code"))
                        e = Example(code, str(module.relative_to(ROOT)))
                        if e.scene is not None:
                            blocks_found.append((module, e))
    
    return blocks_found

def main():
    print("Scanning all translated code blocks...", flush=True)
    all_blocks = get_all_code_blocks()
    print(f"Found {len(all_blocks)} code blocks with scenes", flush=True)
    
    missing = []
    found = 0
    mp4_fixed = 0
    for path, example in all_blocks:
        stem = example.stem
        webp = FILMS / f"{stem}.webp"
        mp4 = FILMS / f"{stem}.mp4"
        if webp.exists() and mp4.exists():
            found += 1
            continue
        if webp.exists() and not mp4.exists():
            scene_films = find_scene_films(example.scene)
            mp4_sources = [f for f in scene_films if f.suffix == ".mp4"]
            if mp4_sources:
                src_mp4 = mp4_sources[0]
                shutil.copy2(src_mp4, FILMS / f"{stem}.mp4")
                mp4_fixed += 1
                old_stem = src_mp4.stem
                for ext in [".svg", "-light.svg"]:
                    src_ext = FILMS / f"{old_stem}{ext}"
                    if src_ext.exists() and not (FILMS / f"{stem}{ext}").exists():
                        shutil.copy2(src_ext, FILMS / f"{stem}{ext}")
            found += 1
            continue
        
        scene_films = find_scene_films(example.scene)
        if not scene_films:
            missing.append((path, example, "no films for scene"))
            continue
        
        webp_sources = [f for f in scene_films if f.suffix == ".webp"]
        if not webp_sources:
            missing.append((path, example, "no webp"))
            continue
        
        missing.append((path, example, webp_sources))
    
    print(f"\nMatched (already exist): {found}", flush=True)
    print(f"Missing: {len(missing)}", flush=True)
    
    no_film = [m for m in missing if isinstance(m[2], str)]
    has_film = [m for m in missing if not isinstance(m[2], str)]
    print(f"  - No source films: {len(no_film)}", flush=True)
    print(f"  - Can copy: {len(has_film)}", flush=True)
    
    copied = 0
    for path, example, webp_sources in has_film:
        stem = example.stem
        scene = example.scene
        
        source_webps = [f for f in webp_sources if f.suffix == ".webp"]
        source_mp4s = [f for f in FILMS.glob(f"{scene}-*.mp4")]
        source_svgs = [f for f in FILMS.glob(f"{scene}-*.svg")]
        source_light_svgs = [f for f in FILMS.glob(f"{scene}-*-light.svg")]
        
        if len(source_webps) == 1:
            src = source_webps[0]
            dst = FILMS / f"{stem}.webp"
            shutil.copy2(src, dst)
            copied += 1
            
            old_stem = src.stem
            for ext in [".mp4", ".svg", "-light.svg"]:
                src_ext = FILMS / f"{old_stem}{ext}"
                if src_ext.exists():
                    dst_ext = FILMS / f"{stem}{ext}"
                    shutil.copy2(src_ext, dst_ext)
        else:
            old_stems = set(f.stem for f in source_webps)
            for old_stem in old_stems:
                old_webp = FILMS / f"{old_stem}.webp"
                new_stem = f"{stem}"
                if not (FILMS / f"{new_stem}.webp").exists():
                    shutil.copy2(old_webp, FILMS / f"{new_stem}.webp")
                    copied += 1
                    for ext in [".mp4", ".svg", "-light.svg"]:
                        src_ext = FILMS / f"{old_stem}{ext}"
                        if src_ext.exists():
                            shutil.copy2(src_ext, FILMS / f"{new_stem}{ext}")
    
    print(f"\nCopied {copied} film files", flush=True)
    
    still_missing = 0
    for path, example, _ in has_film:
        if not (FILMS / f"{example.stem}.webp").exists():
            still_missing += 1
    print(f"Still missing after copy: {still_missing}", flush=True)
    
    if no_film:
        print(f"\nScenes with no source films at all:", flush=True)
        seen = set()
        for path, example, reason in no_film:
            if example.scene not in seen:
                print(f"  {example.scene} (from {path})", flush=True)
                seen.add(example.scene)

if __name__ == "__main__":
    main()