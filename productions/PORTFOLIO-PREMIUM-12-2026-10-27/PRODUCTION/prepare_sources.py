import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def download(item):
    folder = ROOT / "PRODUCTION" / "SOURCE_REVIEW"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{item['id']}.jpg"
    url = f"https://images.pexels.com/photos/{item['id']}/pexels-photo-{item['id']}.jpeg?auto=compress&cs=tinysrgb&w=2400"
    if not target.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "SiteQuiVend-Portfolio/1.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            content = response.read(25_000_001)
        if len(content) > 25_000_000:
            raise ValueError("Photo trop volumineuse")
        target.write_bytes(content)
    with Image.open(target) as im:
        im.verify()
    with Image.open(target) as im:
        dimensions = im.size
    return {**item, "download": url, "path": str(target.relative_to(ROOT)),
            "dimensions": dimensions, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def main():
    items = json.loads((ROOT / "PRODUCTION" / "asset_candidates.json").read_text(encoding="utf-8"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(download, items))
    (ROOT / "PRODUCTION" / "source_review.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    for category in sorted({r["category"] for r in records}):
        selected = [r for r in records if r["category"] == category]
        sheet = Image.new("RGB", (4 * 320, ((len(selected) + 3) // 4) * 440), "#202020")
        draw = ImageDraw.Draw(sheet)
        for i, record in enumerate(selected):
            with Image.open(ROOT / record["path"]) as image:
                tile = ImageOps.contain(ImageOps.exif_transpose(image).convert("RGB"), (316, 396))
            x, y = (i % 4) * 320, (i // 4) * 440
            sheet.paste(tile, (x + (320 - tile.width) // 2, y))
            draw.text((x + 8, y + 402), str(record["id"]), fill="white")
        sheet.save(ROOT / "PRODUCTION" / "SOURCE_REVIEW" / f"{category}-contact.jpg", quality=90)
    print(f"{len(records)} photos Pexels réelles téléchargées et décodées, aucun GPU")


if __name__ == "__main__":
    main()
