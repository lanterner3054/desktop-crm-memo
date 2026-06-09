"""Scan QtWebEngine leveldb files for localStorage memo blobs and recover them."""
import os, re, json, glob

LDB_DIR = os.path.expandvars(r"%APPDATA%\DesktopMemo\桌面备忘录\web\Local Storage\leveldb")

def candidate_blobs(raw_bytes):
    """Find {"memos": ... } JSON substrings in a byte blob, trying utf-16 & utf-8."""
    results = []
    for enc in ("utf-16-le", "latin-1", "utf-8"):
        try:
            text = raw_bytes.decode(enc, errors="ignore")
        except Exception:
            continue
        # find every '{"memos"' and try to bracket-match a JSON object
        for m in re.finditer(r'\{"memos"', text):
            start = m.start()
            depth = 0
            for i in range(start, min(len(text), start + 200000)):
                c = text[i]
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        chunk = text[start:i+1]
                        try:
                            obj = json.loads(chunk)
                            if isinstance(obj, dict) and isinstance(obj.get("memos"), list):
                                results.append((enc, chunk, obj))
                        except Exception:
                            pass
                        break
    return results

def main():
    files = []
    for pat in ("*.log", "*.ldb"):
        files += glob.glob(os.path.join(LDB_DIR, pat))
    print(f"scanning {len(files)} leveldb files in:\n  {LDB_DIR}\n")

    found = []
    for f in files:
        with open(f, "rb") as fp:
            raw = fp.read()
        for enc, chunk, obj in candidate_blobs(raw):
            found.append((os.path.basename(f), enc, obj, chunk))

    # de-dup by serialized content, keep the one with most memos
    best = {}
    for fname, enc, obj, chunk in found:
        key = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        if key not in best:
            best[key] = (fname, enc, obj, chunk)

    print(f"recovered {len(best)} distinct memo snapshot(s)")
    snaps = sorted(best.values(), key=lambda t: len(t[2]["memos"]), reverse=True)
    summary = []
    for i, (fname, enc, obj, chunk) in enumerate(snaps):
        memos = obj["memos"]
        out = os.path.join(os.path.dirname(__file__), f"recovered_{i}.json")
        with open(out, "w", encoding="utf-8") as wf:
            json.dump(obj, wf, ensure_ascii=False)
        # write a human-readable txt listing too (utf-8, avoids console codec)
        listing = os.path.join(os.path.dirname(__file__), f"recovered_{i}.txt")
        with open(listing, "w", encoding="utf-8") as lf:
            lf.write(f"snapshot #{i} from {fname} ({enc}) - {len(memos)} memos\n\n")
            for mm in memos:
                txt = (mm.get("text") or "").replace("\n", " ")
                done = "done" if mm.get("done") else "open"
                lf.write(f"[{done}] {txt}\n")
        summary.append(f"snapshot #{i}: {len(memos)} memos -> recovered_{i}.json / recovered_{i}.txt")
    print("\n".join(summary))

if __name__ == "__main__":
    main()
