#!/usr/bin/env python3
"""引用核对 v1.0 · Citation check v1.0

1. 离线：文档中每个 `参考文献v1.0.md#key` 链接都能在 验证/参考文献v1.0.json 找到；
   JSON 中每条文献都在 文档/参考文献v1.0.md 有锚点。
2. 联网（加 --online）：DOI 走 Crossref、PMID 走 PubMed E-utilities、ISBN 走 Open Library、
   网页走 HTTP 状态码，逐条比对题名与年份。只用 Python 3 标准库。

用法 / Usage:
    python3 验证/引用核对v1.0.py            # 离线一致性检查
    python3 验证/引用核对v1.0.py --online   # 再逐条联网核对
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "验证/参考文献v1.0.json").read_text(encoding="utf-8"))
REFS = {r["key"]: r for r in DATA["references"]}
UA = {"User-Agent": "learning-method-playbook citation check (mailto:haixiangding001@gmail.com)"}
errors, warnings = [], []


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"<[^>]+>", "", s or "").lower())


def similar(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def offline() -> None:
    cited = set()
    for md in ROOT.rglob("*.md"):
        if ".git" in md.parts:
            continue
        for key in re.findall(r"参考文献v1\.0\.md#([a-z0-9]+)", md.read_text(encoding="utf-8")):
            cited.add(key)
            if key not in REFS:
                errors.append(f"{md.relative_to(ROOT)}: 引用了不存在的文献 #{key}")
    reflist = (ROOT / "文档/参考文献v1.0.md").read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a id="([a-z0-9]+)"', reflist))
    for key in REFS:
        if key not in anchors:
            errors.append(f"参考文献v1.0.md 缺少锚点 #{key}")
        if key not in cited:
            warnings.append(f"文献 {key} 未在正文中被引用")


def online() -> None:
    for key, r in REFS.items():
        kind = r.get("check")
        try:
            if kind == "doi":
                m = get_json("https://api.crossref.org/works/" + urllib.parse.quote(r["doi"]))["message"]
                title = (m.get("title") or [""])[0]
                year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
                score = similar(r["title"], title)
                ok = score > 0.8 and (r.get("year") is None or abs(int(year) - int(r["year"])) <= 1)
                print(("OK " if ok else "?? ") + f"{key:18} DOI  {score:.2f} {year} {title[:70]}")
                if not ok:
                    errors.append(f"{key}: Crossref 题名/年份不符 → {title} ({year})")
            elif kind == "pmid":
                m = get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=" + r["pmid"])
                title = m["result"][r["pmid"]]["title"]
                score = similar(r["title"], title)
                print(("OK " if score > 0.8 else "?? ") + f"{key:18} PMID {score:.2f} {title[:70]}")
                if score <= 0.8:
                    errors.append(f"{key}: PubMed 题名不符 → {title}")
            elif kind == "isbn":
                m = get_json(f"https://openlibrary.org/api/books?bibkeys=ISBN:{r['isbn']}&format=json&jscmd=data")
                title = next(iter(m.values()))["title"] if m else ""
                score = similar(r["title"].split(":")[0], title)
                print(("OK " if score > 0.6 else "?? ") + f"{key:18} ISBN {score:.2f} {title[:70]}")
                if score <= 0.6:
                    errors.append(f"{key}: Open Library 未找到或题名不符 → {title!r}")
            elif kind == "url":
                req = urllib.request.Request(r["url"], headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    code = resp.status
                print(("OK " if code < 400 else "?? ") + f"{key:18} URL  {code}")
                if code >= 400:
                    errors.append(f"{key}: 网页返回 {code}")
            else:
                print(f"-- {key:18} 无可核对标识（{r.get('note', '')}）")
        except Exception as exc:  # 网络问题记为警告，人工复核
            warnings.append(f"{key}: 联网核对失败 {exc}")
            print(f"!! {key:18} {exc}")
        time.sleep(0.35)


offline()
if "--online" in sys.argv:
    online()
for w in warnings:
    print("提示:", w)
if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"引用核对通过 / citation check passed（{len(REFS)} 条）")
