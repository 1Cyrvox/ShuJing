import re
import os
from pathlib import Path

CONTENT_DIR = Path("content")
SITE_DIR = Path("site")
OFFICIAL_DIR = Path("D:/asd/dfghj/manimgx-main/manimgx-main/docs/content")

def slugify(text):
    s = re.sub(r'[^a-z0-9 -]', '', text.lower()).strip()
    s = re.sub(r'[-\s]+', '-', s)
    return s.strip('-')

def extract_headings(md_path):
    headings = []
    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if not in_code:
                m = re.match(r'^(#{1,6})\s+(.+)', line)
                if m:
                    headings.append(m.group(2).strip())
    except Exception:
        pass
    return headings

def extract_html_ids(html_path):
    ids = []
    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'<h[1-6] id="([^"]+)"', text):
            ids.append(m.group(1))
    except Exception:
        pass
    return ids

def get_target_page(link_target, current_md_rel):
    if "#" in link_target:
        file_part = link_target.split("#")[0]
    else:
        file_part = link_target

    if not file_part:
        if current_md_rel == "index.md":
            return ""
        return current_md_rel[:-3]

    current_dir = os.path.dirname(current_md_rel)

    if file_part.startswith("../"):
        parts = file_part.split("/")
        while parts and parts[0] == "..":
            current_dir = os.path.dirname(current_dir)
            parts = parts[1:]
        file_part = "/".join(parts)

    if current_dir:
        full_path = current_dir + "/" + file_part
    else:
        full_path = file_part

    full_path = full_path.replace("\\", "/")

    if full_path.endswith(".md"):
        full_path = full_path[:-3]

    return full_path

def build_anchor_map():
    anchor_map = {}

    for md_file in CONTENT_DIR.rglob("*.md"):
        rel = md_file.relative_to(CONTENT_DIR)
        rel_str = str(rel).replace(os.sep, "/")

        if rel_str == "index.md":
            page_key = ""
        else:
            page_key = rel_str[:-3]

        official_file = OFFICIAL_DIR / rel_str
        if not official_file.exists():
            continue

        off_headings = extract_headings(official_file)

        if page_key:
            html_path = SITE_DIR / page_key / "index.html"
        else:
            html_path = SITE_DIR / "index.html"
        html_ids = extract_html_ids(html_path)

        if len(off_headings) != len(html_ids):
            continue

        for off_h, html_id in zip(off_headings, html_ids):
            off_anchor = slugify(off_h)
            if off_anchor and off_anchor != html_id:
                key = (page_key, off_anchor)
                anchor_map[key] = html_id

    return anchor_map

def fix_anchors():
    anchor_map = build_anchor_map()
    print(f"建立了 {len(anchor_map)} 个锚点映射")

    total_fixed = 0
    files_fixed = 0

    for md_file in CONTENT_DIR.rglob("*.md"):
        rel = md_file.relative_to(CONTENT_DIR)
        rel_str = str(rel).replace(os.sep, "/")

        text = md_file.read_text(encoding="utf-8")
        original = text

        def replacer(m):
            nonlocal total_fixed
            full = m.group(0)
            link_text = m.group(1)
            target = m.group(2)

            if target.startswith("http") or target.startswith("mailto:") or "#" not in target:
                return full

            file_part, anchor = target.split("#", 1)
            target_page = get_target_page(target, rel_str)
            if target_page is None:
                return full

            key = (target_page, anchor)
            if key in anchor_map:
                new_anchor = anchor_map[key]
                new_target = file_part + "#" + new_anchor
                total_fixed += 1
                return f"]({new_target})"

            return full

        text = re.sub(r'\[([^\]]*)\]\(([^)]+)\)', replacer, text)

        if text != original:
            md_file.write_text(text, encoding="utf-8")
            files_fixed += 1
            print(f"  修复: {rel_str}")

    print(f"\n总计: 修复 {total_fixed} 个链接，涉及 {files_fixed} 个文件")

fix_anchors()