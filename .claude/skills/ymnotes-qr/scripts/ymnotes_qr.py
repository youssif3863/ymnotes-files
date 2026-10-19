#!/usr/bin/env python3
"""YMnotes student-file publisher: file -> repo folder -> branded QR -> index.

Subcommands
  add     Copy a file into the ymnotes-files repo, make its branded QR card,
          check the QR decodes, and update catalog.json / README.md / index.html.
  verify  After pushing, poll the public URL until it answers 200.
  render  Rebuild README.md and index.html from catalog.json.
  qr      Make a QR card for any URL (no repo changes).

Requires: pip install segno pillow opencv-python-headless
"""
import argparse
import datetime as dt
import html
import io
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import segno
from PIL import Image, ImageDraw, ImageFont

OWNER, REPO = "youssif3863", "ymnotes-files"
RAW_BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main"
PAGES_BASE = f"https://{OWNER}.github.io/{REPO}"

GREEN = (11, 90, 52)      # YMnotes logo green
TEAL = (0, 122, 135)
ORANGE = (234, 96, 20)
GREY = (70, 70, 70)

GITHUB_LIMIT_MB = 95      # GitHub rejects files over 100 MB
MOBILE_WARN_MB = 25       # big files are slow for students on mobile data

KIND = {
    ".pdf": "PDF", ".png": "Image", ".jpg": "Image", ".jpeg": "Image",
    ".webp": "Image", ".gif": "Image", ".svg": "Image", ".mp4": "Video",
    ".mp3": "Audio", ".m4a": "Audio", ".docx": "Word file",
    ".pptx": "Slides", ".xlsx": "Spreadsheet", ".zip": "ZIP file",
    ".html": "Web page", ".txt": "Text",
}
# Raw links serve these with a type phones can display inline; anything else
# (notably PDF) arrives as application/octet-stream and only downloads.
RAW_INLINE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".txt"}


# ---------------------------------------------------------------- helpers
def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text) or "file"


def font(bold, size):
    names = (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]
             if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf", "arial.ttf"])
    dirs = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
            "/Library/Fonts", "/System/Library/Fonts/Supplemental", "C:/Windows/Fonts", ""]
    for d in dirs:
        for n in names:
            try:
                return ImageFont.truetype(str(Path(d) / n) if d else n, size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def fit_lines(draw, text, bold, start, max_w, max_lines):
    """Largest font size at which text wraps into <= max_lines lines."""
    size = start
    while size > 18:
        f = font(bold, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, lines
        size -= 4
    f = font(bold, size)
    return f, wrap(draw, text, f, max_w)[:max_lines]


def curl(url):
    """Return (status, content_type) using curl, which honours the proxy setup."""
    out = subprocess.run(
        ["curl", "-sS", "-L", "-o", "/dev/null", "-r", "0-0", "-w", "%{http_code} %{content_type}", url],
        capture_output=True, text=True, timeout=60)
    parts = (out.stdout or "0 ").split(" ", 1)
    return int(parts[0] or 0), parts[1].strip() if len(parts) > 1 else ""


def pages_live():
    try:
        return curl(f"{PAGES_BASE}/catalog.json")[0] in (200, 206)
    except Exception:
        return False


# ---------------------------------------------------------------- QR card
def make_card(url, out, title, subtitle="Scan to open"):
    qr = segno.make(url, error="h", micro=False)   # H = 30% damage tolerance, room for the badge
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=24, border=4, dark=GREEN, light="white")
    code = Image.open(buf).convert("RGB")
    size = code.width
    d = ImageDraw.Draw(code)

    badge = int(size * 0.22)                       # keep the badge well under the 30% budget
    bx = by = (size - badge) // 2
    d.rounded_rectangle([bx, by, bx + badge, by + badge], radius=badge // 6,
                        fill="white", outline=GREEN, width=max(6, badge // 30))
    ym, nt = font(True, int(badge * 0.42)), font(True, int(badge * 0.20))
    d.text((bx + (badge - d.textlength("YM", font=ym)) / 2, by + badge * 0.14), "YM", font=ym, fill=GREEN)
    d.text((bx + (badge - d.textlength("notes", font=nt)) / 2, by + badge * 0.62), "notes", font=nt, fill=ORANGE)

    pad, head = size // 14, size // 5
    W = size + 2 * pad
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tfont, tlines = fit_lines(probe, title, True, int(size * 0.052), W - 2 * pad, 3)
    sfont, slines = fit_lines(probe, subtitle, False, int(size * 0.036), W - 2 * pad, 2)
    tl_h, sl_h = int(tfont.size * 1.22), int(sfont.size * 1.3)
    foot = int(size * 0.05) + tl_h * len(tlines) + int(size * 0.025) + sl_h * len(slines) + int(size * 0.09)
    H = size + head + foot

    card = Image.new("RGB", (W, H), "white")
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([8, 8, W - 9, H - 9], radius=W // 18, outline=GREEN, width=14)
    brand = font(True, int(head * 0.42))
    cd.text(((W - cd.textlength("YMnotes", font=brand)) / 2, head * 0.22), "YMnotes", font=brand, fill=GREEN)
    card.paste(code, (pad, head))
    y = head + size + int(size * 0.02)
    for line in tlines:
        cd.text(((W - cd.textlength(line, font=tfont)) / 2, y), line, font=tfont, fill=TEAL)
        y += tl_h
    y += int(size * 0.025)
    for line in slines:
        cd.text(((W - cd.textlength(line, font=sfont)) / 2, y), line, font=sfont, fill=GREY)
        y += sl_h
    cd.rectangle([W * 0.3, y + size * 0.02, W * 0.7, y + size * 0.03], fill=ORANGE)
    out.parent.mkdir(parents=True, exist_ok=True)
    card.save(out, dpi=(300, 300))
    return out


def check_decodes(png, url):
    """Decode at several on-screen sizes, as a phone would see it in a video."""
    import cv2
    img = cv2.imread(str(png))
    ok = []
    for width in (300, 450, 700):
        s = width / img.shape[1]
        small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        ok.append(cv2.QRCodeDetector().detectAndDecode(small)[0] == url)
    return sum(ok) >= 2, ok


# ---------------------------------------------------------------- catalog
def load_catalog(repo):
    p = repo / "catalog.json"
    return json.loads(p.read_text()) if p.exists() else {"files": []}


def save_catalog(repo, cat):
    cat["files"].sort(key=lambda e: (e["subject"].lower(), e["title"].lower()))
    (repo / "catalog.json").write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")


README_HEAD = """# YMnotes Files

Images and handouts for YMnotes students, shared through QR codes in the videos.
Browse everything at **{pages}/**

| Folder | Contents |
|---|---|
| `files/<subject>/` | The files students open (PDFs, images, ...) |
| `qr/<subject>/` | The branded QR card for each file |
| `catalog.json` | Source of truth for the index below |
| `.claude/skills/ymnotes-qr/` | The Claude skill + script that publishes files |

## Rules that keep the QR codes working
- Keep this repository **public**.
- Never rename, move or delete a file once its QR code is in a video.
- To update a handout, replace the file with one of the **same name**: the QR keeps working.

## Index
| Subject | Title | Type | QR |
|---|---|---|---|
"""


def render(repo):
    cat = load_catalog(repo)
    rows = [f"| {e['subject']} | [{e['title']}]({e['path']}) | {e['kind']} | [QR]({e['qr']}) |"
            for e in cat["files"]]
    (repo / "README.md").write_text(README_HEAD.format(pages=PAGES_BASE) + "\n".join(rows) + "\n")

    groups = {}
    for e in cat["files"]:
        groups.setdefault(e["subject"], []).append(e)
    sections = "".join(
        f"<h2>{html.escape(s)}</h2><ul>" + "".join(
            f'<li><a href="{html.escape(e["path"])}">{html.escape(e["title"])}</a>'
            f' <span>{html.escape(e["kind"])}</span></li>' for e in items) + "</ul>"
        for s, items in groups.items())
    (repo / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YMnotes Files</title>
<style>
:root{{--g:#0b5a34;--o:#ea6014;--bg:#fff;--fg:#222;--mut:#666;--line:#e3e8e5}}
@media (prefers-color-scheme:dark){{:root{{--g:#5fc28f;--bg:#111;--fg:#eee;--mut:#aaa;--line:#2a2f2c}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:720px;margin:0 auto;padding:24px 16px}}
h1{{color:var(--g);margin:0}} h1 b{{color:var(--o)}}
h2{{color:var(--g);border-bottom:2px solid var(--line);padding-bottom:4px;margin-top:28px}}
ul{{list-style:none;padding:0}} li{{padding:10px 0;border-bottom:1px solid var(--line)}}
a{{color:inherit;font-weight:600}} span{{color:var(--mut);font-size:.85em;margin-left:6px}}
</style></head><body><main>
<h1>YM<b>notes</b> Files</h1><p>Handouts and images from the YMnotes videos.</p>
{sections or "<p>No files yet.</p>"}
</main></body></html>
""")


# ---------------------------------------------------------------- commands
def cmd_add(a):
    repo = Path(a.repo).resolve()
    src = Path(a.file).expanduser().resolve()
    if not src.is_file():
        sys.exit(f"error: file not found: {src}")
    mb = src.stat().st_size / 1e6
    if mb > GITHUB_LIMIT_MB:
        sys.exit(f"error: {mb:.0f} MB is over GitHub's 100 MB file limit; compress it or use a GitHub Release asset")

    ext = src.suffix.lower()
    subject_slug = slugify(a.subject)
    slug = slugify(a.slug or a.title)
    rel = f"files/{subject_slug}/{slug}{ext}"
    qr_rel = f"qr/{subject_slug}/{slug}-qr.png"
    dest = repo / rel

    cat = load_catalog(repo)
    existing = next((e for e in cat["files"] if e["path"] == rel), None)
    if dest.exists() and not a.replace:
        sys.exit(f"error: {rel} already exists. Re-run with --replace to update it in place "
                 f"(its QR keeps working), or pass a different --slug for a new file.")

    if existing and a.replace:
        url = existing["url"]                      # never change a URL that may be in a video
    else:
        mode = a.link
        if mode == "auto":
            mode = "pages" if pages_live() else "raw"
        url = f"{PAGES_BASE if mode == 'pages' else RAW_BASE}/{rel}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)

    kind = KIND.get(ext, ext.lstrip(".").upper() + " file")
    noun = kind if kind.isupper() or kind.split()[0].isupper() else kind.lower()
    subtitle = a.subtitle or f"Scan to open the {noun}"
    make_card(url, repo / qr_rel, a.title, subtitle)
    ok, detail = check_decodes(repo / qr_rel, url)
    if not ok:
        sys.exit(f"error: QR did not decode reliably {detail}; shorten --slug or --subject and retry")

    entry = {"title": a.title, "subject": a.subject, "kind": kind, "path": rel, "qr": qr_rel,
             "url": url, "bytes": dest.stat().st_size,
             "added": existing["added"] if existing else dt.date.today().isoformat(),
             "updated": dt.date.today().isoformat()}
    cat["files"] = [e for e in cat["files"] if e["path"] != rel] + [entry]
    save_catalog(repo, cat)
    render(repo)

    warnings = []
    if mb > MOBILE_WARN_MB:
        warnings.append(f"{mb:.0f} MB is heavy on mobile data; consider compressing")
    if url.startswith(RAW_BASE) and ext not in RAW_INLINE:
        warnings.append(f"raw GitHub links make phones download {ext} files instead of opening them; "
                        f"enable GitHub Pages (Settings > Pages > Deploy from branch: main, / root) "
                        f"before publishing (an already-published URL is kept on --replace)")
    print(json.dumps({"url": url, "file": rel, "qr": str(repo / qr_rel),
                      "replaced": bool(existing), "decode_checks": detail,
                      "warnings": warnings}, indent=2))


def cmd_verify(a):
    deadline = time.time() + a.timeout
    while True:
        code, ctype = curl(a.url)
        if code in (200, 206):
            print(json.dumps({"url": a.url, "status": code, "content_type": ctype, "live": True}))
            return
        if time.time() > deadline:
            sys.exit(json.dumps({"url": a.url, "status": code, "live": False}))
        time.sleep(10)


def cmd_qr(a):
    out = make_card(a.url, Path(a.out), a.title, a.subtitle or "Scan to open")
    ok, detail = check_decodes(out, a.url)
    print(json.dumps({"qr": str(out), "decodes": ok, "decode_checks": detail}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--repo", required=True, help="path to the ymnotes-files clone")
    s.add_argument("--file", required=True)
    s.add_argument("--title", required=True, help="what students see under the QR")
    s.add_argument("--subject", required=True, help="e.g. Gastroenterology")
    s.add_argument("--slug", help="short file name (default: from title)")
    s.add_argument("--subtitle", help="default: 'Scan to open the <type>'")
    s.add_argument("--link", choices=["auto", "pages", "raw"], default="auto")
    s.add_argument("--replace", action="store_true", help="update an existing file in place")
    s.set_defaults(fn=cmd_add)
    s = sub.add_parser("verify")
    s.add_argument("--url", required=True)
    s.add_argument("--timeout", type=int, default=180)
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("render")
    s.add_argument("--repo", required=True)
    s.set_defaults(fn=lambda a: render(Path(a.repo)))
    s = sub.add_parser("qr")
    s.add_argument("--url", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--subtitle")
    s.set_defaults(fn=cmd_qr)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
