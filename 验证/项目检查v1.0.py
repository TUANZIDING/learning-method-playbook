#!/usr/bin/env python3
"""项目检查 v1.0：本地链接、锚点、必需文件、文件命名与 SVG 可解析。不联网。
Project check v1.0: local links, anchors, required files, file naming and SVG well-formedness. Offline.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r'(?:\]\(([^)\s]+)\)|(?:href|src)="([^"]+)")')
EXEMPT = {"README.md", "LICENSE", "CHANGELOG.md", ".gitignore"}
errors = []


def anchors(text: str) -> set:
    return set(re.findall(r'<a id="([^"]+)"', text))


for md in ROOT.rglob("*.md"):
    if ".git" in md.parts:
        continue
    text = md.read_text(encoding="utf-8")
    # 跳过代码块里的示例链接
    text_wo_code = re.sub(r"```.*?```", "", text, flags=re.S)
    for m in LINK.finditer(text_wo_code):
        target = m.group(1) or m.group(2)
        if re.match(r"^(https?:|mailto:)", target):
            continue
        path, _, frag = target.partition("#")
        dest = (md.parent / unquote(path)).resolve() if path else md
        if not dest.exists():
            errors.append(f"{md.relative_to(ROOT)}: 链接目标不存在 {target}")
            continue
        if frag and dest.suffix == ".md" and frag not in anchors(dest.read_text(encoding="utf-8")):
            errors.append(f"{md.relative_to(ROOT)}: 缺少锚点 #{frag}（{path or md.name}）")

for f in ROOT.rglob("*"):
    if ".git" in f.parts or ".github" in f.parts or f.is_dir() or "__pycache__" in f.parts:
        continue
    if f.name in EXEMPT:
        continue
    if "_" in f.name:
        errors.append(f"{f.relative_to(ROOT)}: 文件名不应含下划线")
    if not re.search(r"v\d+\.\d+", f.stem):
        errors.append(f"{f.relative_to(ROOT)}: 文件名缺少版本号（如 v1.0）")

for svg in ROOT.rglob("*.svg"):
    try:
        ET.parse(svg)
    except ET.ParseError as exc:
        errors.append(f"{svg.relative_to(ROOT)}: {exc}")

for name in ["README.md", "LICENSE", "CHANGELOG.md", "文档/英文说明v1.0.md", "文档/方法总表v1.0.md",
             "文档/参考文献v1.0.md", "验证/参考文献v1.0.json"]:
    if not (ROOT / name).exists():
        errors.append(f"缺少必需文件 {name}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("项目检查通过 / project check passed")
