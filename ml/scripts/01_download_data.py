import argparse
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def _has_images(root: Path) -> bool:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            return True
    return False


def download_mosquitodl(raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / "mosquitodl"
    repo_url = "https://github.com/jypark1994/MosquitoDL.git"

    if dest.exists() and (dest / ".git").exists():
        _run(["git", "-C", str(dest), "fetch", "--all", "--prune"])
        _run(["git", "-C", str(dest), "reset", "--hard", "origin/master"])
        return dest

    if dest.exists():
        shutil.rmtree(dest)
    _run(["git", "clone", "--depth", "1", repo_url, str(dest)])
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download mosquito datasets into data/raw/")
    parser.add_argument("--raw-dir", default="data/raw", help="Target raw directory")
    parser.add_argument("--mosquitodl", action="store_true", help="Download MosquitoDL (public GitHub)")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir).resolve()
    if not args.mosquitodl:
        args.mosquitodl = True

    if args.mosquitodl:
        dest = download_mosquitodl(raw_dir)
        if _has_images(dest):
            print(f"✓ MosquitoDL ready: {dest}")
        else:
            print(f"⚠ MosquitoDL cloned but no images were found under: {dest}")
            print("  The upstream repo may not include the full dataset (or it requires extra download/LFS).")
            print("  If you already have images, place them under:")
            print("    data/raw/mosquitodl/<label>/*.jpg")
            print("  Then run preprocess:")
            print("    python ml/scripts/02_preprocess.py --raw-dir data/raw/mosquitodl --out-dir data/processed/mosquitodl")


if __name__ == "__main__":
    main()
