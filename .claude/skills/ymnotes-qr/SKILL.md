---
name: ymnotes-qr
description: Publish a YMnotes student file (PDF, image, slides, any handout) to the youssif3863/ymnotes-files GitHub repo and hand back a YMnotes-branded QR code card with the file's title, ready to show in a video. Use this whenever the user sends or points to a file and wants students to reach it, asks for a QR code for a handout/image/PDF/sheet, says "upload this for my students", "make a QR for this", "add this to my files repo", or wants to update/replace a file that already has a QR code, even if they don't mention GitHub or the repo by name.
---

# YMnotes QR publisher

**Goal:** a student watching a YMnotes video scans the QR on screen and the file opens
on their phone, today and years from now. The QR card carries the YMnotes brand and
the file's title so students know what they are about to open.

Everything below serves two promises: **the link never breaks** and **the QR always scans**.

## What you need from the user

- **The file**: an upload, a path, or a file already in the repo.
- **Title**: what students see under the QR. If they don't give one, take it from the
  content (for example, the heading of the sheet: "Ulcerative Colitis vs Crohn's Disease").
- **Subject**: the folder, for example Gastroenterology or Cardiology. Infer it from the content.

Don't stop to ask when you can infer these sensibly. Proceed and state what you chose,
because they can be changed later before the video is recorded. Ask only when the title
or subject is truly ambiguous.

## Workflow

### 1. Get the repo
Work in a clone of `youssif3863/ymnotes-files` (usually `/home/user/ymnotes-files`).
If it isn't in the session, attach it with `add_repo` (push access) and clone it. Then
`git pull` so you build on the latest catalog. If GitHub refuses access, tell the user
which step failed. Don't fake a link.

### 2. Install dependencies (once per machine)
```bash
pip install -q segno pillow opencv-python-headless
```

### 3. Publish with the script
```bash
python3 <skill-dir>/scripts/ymnotes_qr.py add --repo /home/user/ymnotes-files \
  --file "<path>" --title "<Title>" --subject "<Subject>" [--slug short-name]
```
In one step, the script:
- copies the file to `files/<subject>/<slug>.<ext>`;
- builds the QR card at `qr/<subject>/<slug>-qr.png`. The card uses error correction H,
  a YM/notes badge, the title (auto-wrapped) and a subtitle such as "Scan to open the PDF";
- decodes the card at phone-like sizes and fails if the QR won't scan;
- updates `catalog.json`, `README.md` and `index.html` (the students' browse page);
- prints JSON with `url`, `qr`, and `warnings`. Read the warnings.

Rules it enforces, and why:
- **Existing path → error unless `--replace`.** Overwriting a file silently could change
  a handout behind a QR that's already in a published video. When the user is updating a
  handout, use `--replace`: the URL is reused, so the old QR keeps working and opens the new version.
- **Over 95 MB is refused** because GitHub has a 100 MB file limit. Offer to compress it,
  or use a GitHub Release asset.
- **Keep slugs short.** A shorter URL means a less dense QR that scans more easily from a
  screen. Pass `--slug` when the title is long (for example, `--slug uc-vs-crohns`).

### 4. Link type: Pages vs raw
`--link auto` (the default) uses GitHub Pages
(`https://youssif3863.github.io/ymnotes-files/...`) when Pages is live, and the raw link
(`raw.githubusercontent.com/...`) otherwise.
Pages is better: it serves PDFs with the right type, so a phone **opens** them, while raw
links make phones **download** PDFs and other non-image files. If Pages is off and the file
is not an image, **stop before pushing**: undo the add (`git checkout -- . && git clean -fd files qr`),
ask the user to turn Pages on, and re-run once `curl https://youssif3863.github.io/ymnotes-files/catalog.json`
returns 200. Use raw only if they say a download is fine. The reason: once the QR is in a video, its URL
is permanent and can't be upgraded later. Turning Pages on is a one-time click:
*repo Settings → Pages → Deploy from a branch → `main` / `(root)` → Save*.
Never change the URL of a file that is already published (the script keeps it on `--replace`).
A raw link that's already in a video keeps working whether or not Pages is on.

### 5. Commit, push, verify live
```bash
cd /home/user/ymnotes-files && git add -A && git commit -m "Add <Title> (<subject>)" && git push origin main
python3 <skill-dir>/scripts/ymnotes_qr.py verify --url "<url from step 3>"
```
Push straight to `main`. This repo is a file host, not a code project; files only go
live from `main`, and a pull request would leave the QR dead until someone merged it.
`verify` waits until the URL answers 200 (raw links are near-instant; Pages takes about 1 minute to rebuild).
Don't report success until verify passes.

### 6. Deliver
- Send the QR card with `SendUserFile` (display `render`) or the equivalent file-sharing tool.
- Then send a short reply covering: the title, the live link, the repo path, any warnings
  (size, raw-PDF download behaviour), and one line saying that replacing the file under
  the same name keeps this QR working.

## Other tasks
- **QR for an external link** (YouTube, Google Drive, a website):
  `ymnotes_qr.py qr --url ... --out ... --title ...`. No repo change is needed.
  Tell the user that the link must itself be permanent and public.
- **Rename the title on a card**: re-run `add --replace` with the same `--slug` and the
  new `--title`. The URL stays the same.
- **Index looks stale or was edited by hand**: run `ymnotes_qr.py render --repo ...`.
- **Delete a file**: only on explicit request. First warn that any video showing its QR
  will lead to a dead link. Then remove the file and its catalog entry, and run `render`.

## Card design (for reference)
Green `#0B5A34` (logo), orange `#EA6014`, teal `#007A87`. Layout from top to bottom:
"YMnotes" header, the QR with a YM/notes badge in the centre (22% of the width, within
the 30% that error correction H can recover), the title (up to 3 lines), the subtitle,
and an orange rule. Output is a 300 dpi PNG, about 1700 px wide. In a video, show it at
least about 300 px tall for 5–10 seconds.
