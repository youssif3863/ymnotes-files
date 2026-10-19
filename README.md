# YMnotes Files

Images and handouts for YMnotes students, shared through QR codes in the videos.

| Folder | Contents |
|---|---|
| `files/<subject>/` | The files students open (images, PDFs) |
| `qr/<subject>/` | The branded QR code for each file |
| `tools/make_qr.py` | QR generator |

## Rules that keep the QR codes working
- Keep this repository **public**.
- Never rename, move or delete a file once its QR code is in a video.
- To update a handout, replace the file with one of the **same name** — the QR keeps working.

## Making a QR code
```
pip install segno pillow
python3 tools/make_qr.py "https://raw.githubusercontent.com/youssif3863/ymnotes-files/main/files/<subject>/<file>" qr/<subject>/<file>-qr.png "Title"
```

## Index
| Subject | File | QR |
|---|---|---|
| Gastroenterology | [UC vs Crohn's Disease](files/gastroenterology/uc-vs-crohns.png) | [QR](qr/gastroenterology/uc-vs-crohns-qr.png) |
