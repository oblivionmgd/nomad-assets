from pathlib import Path
import json
import os
import re
import shutil
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
FLYERS = ROOT / "flyers"
TIMETABLES = ROOT / "timetables"

MAX_SIZE = 2048
DATE_RE = re.compile(r"^(\d{8})(?:_v(\d+))?\.(png|jpg|jpeg)$", re.IGNORECASE)


def clean_output():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)


def copy_if_exists(src: Path, dst: Path):
    if not src.exists():
        return

    if src.is_dir():
        shutil.copytree(
            src,
            dst,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".DS_Store")
        )
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def find_latest_flyer() -> tuple[str, Path]:
    candidates = []

    if not FLYERS.exists():
        raise FileNotFoundError("flyers/ がありません")

    for path in FLYERS.iterdir():
        if not path.is_file():
            continue

        match = DATE_RE.match(path.name)
        if not match:
            continue

        date = match.group(1)
        version = int(match.group(2) or 0)
        is_png = 1 if path.suffix.lower() == ".png" else 0

        candidates.append((date, version, is_png, path))

    if not candidates:
        raise RuntimeError("flyers/ に YYYYMMDD.png / jpg がありません")

    candidates.sort()
    date, _version, _is_png, path = candidates[-1]
    return date, path


def save_latest_png(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)

        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )

        img = img.convert("RGBA" if has_alpha else "RGB")
        img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
        img.save(dst, "PNG", optimize=True)


def get_base_url() -> str:
    # カスタムドメインを使う場合は GitHub Actions 側で PAGES_BASE_URL を指定する
    custom = os.environ.get("PAGES_BASE_URL")
    if custom:
        return custom.rstrip("/")

    repo = os.environ.get("GITHUB_REPOSITORY", "<github-user>/nomad-assets")
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}"


def main():
    clean_output()

    copy_if_exists(ROOT / "index.html", OUT / "index.html")
    copy_if_exists(ROOT / ".nojekyll", OUT / ".nojekyll")
    copy_if_exists(FLYERS, OUT / "flyers")
    copy_if_exists(TIMETABLES, OUT / "timetables")

    latest_event, latest_src = find_latest_flyer()
    save_latest_png(latest_src, OUT / "flyers" / "latest.png")

    base_url = get_base_url()

    latest_flyer_url = f"{base_url}/flyers/latest.png"
    original_flyer_url = f"{base_url}/flyers/{latest_src.name}"

    (OUT / "latest_flyer.txt").write_text(
        latest_flyer_url + "\n",
        encoding="utf-8"
    )

    manifest = {
        "latestEvent": latest_event,
        "flyerUrl": latest_flyer_url,
        "originalFlyerUrl": original_flyer_url,
        "djTimetableUrl": f"{base_url}/timetables/latest_dj.txt",
        "vjTimetableUrl": f"{base_url}/timetables/latest_vj.txt",
    }

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"Latest flyer: {latest_src.name} -> flyers/latest.png")
    print(f"URL: {latest_flyer_url}")


if __name__ == "__main__":
    main()