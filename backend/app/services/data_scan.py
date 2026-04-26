from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


def _image_files(root: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts]


@dataclass
class DatasetScan:
    name: str
    raw_dir: str | None
    processed_dir: str | None
    raw_image_count: int
    processed_image_count: int
    processed_splits: dict


def scan_datasets(data_dir: str) -> dict:
    """
    Scan dataset folders so the Admin UI can show whether data exists when the user
    downloads manually (or via admin jobs).

    Expected layout:
      {data_dir}/raw/<dataset>/...
      {data_dir}/processed/<dataset>/{train,val,test}/<label>/...
    """
    base = Path(data_dir).resolve()
    raw = base / "raw"
    processed = base / "processed"

    exists = {"data_dir": base.exists(), "raw_dir": raw.exists(), "processed_dir": processed.exists()}

    raw_sets = {p.name for p in raw.iterdir() if p.is_dir()} if raw.exists() else set()
    processed_sets = {p.name for p in processed.iterdir() if p.is_dir()} if processed.exists() else set()
    names = sorted(raw_sets | processed_sets)

    datasets: list[DatasetScan] = []
    for name in names:
        raw_dir = raw / name
        proc_dir = processed / name

        raw_count = len(_image_files(raw_dir))

        splits = {}
        proc_total = 0
        if proc_dir.exists():
            for split in ("train", "val", "test"):
                split_dir = proc_dir / split
                c = len(_image_files(split_dir))
                splits[split] = c
                proc_total += c

        datasets.append(
            DatasetScan(
                name=name,
                raw_dir=str(raw_dir) if raw_dir.exists() else None,
                processed_dir=str(proc_dir) if proc_dir.exists() else None,
                raw_image_count=raw_count,
                processed_image_count=proc_total,
                processed_splits=splits,
            )
        )

    return {"data_dir": str(base), "exists": exists, "datasets": [asdict(d) for d in datasets]}

