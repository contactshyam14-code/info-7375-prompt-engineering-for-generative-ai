"""Build data/corpus.jsonl from the raw responses my Job-Search Agent 2 saved.

Source: ../js2-loop-tools-diff/jobs/runs/2026-11-10T213906-after-patch/raw/ (a real run,
2026-11-10 21:39 ET). Parsing follows js2/providers.py (Greenhouse jobs[], Lever list).
HTML is stripped here so every later step sees the same posting text.
Usage: python build_corpus.py <raw_dir>
"""
import html, json, pathlib, re, sys

def plain(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()

def main(raw_dir: str) -> None:
    raw = pathlib.Path(raw_dir)
    index = json.loads((raw / "index.json").read_text(encoding="utf-8"))
    out = []
    for url, meta in index.items():
        if meta.get("status") != "ok":
            continue
        body = json.loads((raw / meta["file"]).read_text(encoding="utf-8"))
        if meta["ats"] == "greenhouse":
            for j in body["jobs"]:
                out.append({"id": str(j["id"]), "board": meta["board"], "ats": "greenhouse",
                            "title": (j.get("title") or "").strip(),
                            "location": ((j.get("location") or {}).get("name") or "").strip(),
                            "content": plain(j.get("content") or ""),
                            "url": j.get("absolute_url")})
        else:
            for p in body:
                cats = p.get("categories") or {}
                parts = [p.get("descriptionPlain") or ""]
                for lst in p.get("lists") or []:
                    parts.append((lst.get("text") or "") + "\n" + plain(lst.get("content") or ""))
                parts.append(p.get("additionalPlain") or "")
                out.append({"id": str(p["id"]), "board": meta["board"], "ats": "lever",
                            "title": (p.get("text") or "").strip(),
                            "location": (cats.get("location") or "").strip(),
                            "workplace": p.get("workplaceType") or "",
                            "content": plain("\n".join(parts)),
                            "url": p.get("hostedUrl")})
    dest = pathlib.Path(__file__).parent / "data" / "corpus.jsonl"
    with dest.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} postings to {dest}")

if __name__ == "__main__":
    main(sys.argv[1])
