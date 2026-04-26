# Hệ thống Nhận dạng Muỗi — Tài liệu Kỹ thuật Chi tiết

> **Mục tiêu**: Website cho cán bộ y tế upload ảnh muỗi (1 hoặc nhiều góc) để nhận dạng đến mức loài (*Ae. aegypti*, *Ae. albopictus*, *Anopheles dirus*, *Culex quinquefasciatus*...) phục vụ giám sát dịch tễ.

---

## Mục lục

1. [Cấu trúc dự án](#1-cấu-trúc-dự-án)
2. [Giai đoạn 1 — Thu thập & Chuẩn bị dữ liệu](#2-giai-đoạn-1--thu-thập--chuẩn-bị-dữ-liệu)
3. [Giai đoạn 2 — Training Model](#3-giai-đoạn-2--training-model)
4. [Giai đoạn 3 — FastAPI Backend](#4-giai-đoạn-3--fastapi-backend)
5. [Giai đoạn 4 — React Frontend](#5-giai-đoạn-4--react-frontend)
6. [Giai đoạn 5 — Triển khai](#6-giai-đoạn-5--triển-khai)
7. [Giao diện quản trị (Admin) — Log & Training](#7-giao-diện-quản-trị-admin--log--training)
8. [Feedback Loop & Cải thiện Model](#8-feedback-loop--cải-thiện-model)

---

## 1. Cấu trúc dự án

```
mosquito-id/
├── data/                          # Dữ liệu thô + đã xử lý
│   ├── raw/                       # Dataset gốc download về
│   │   ├── mosquitodl/
│   │   ├── kaggle_aedes/
│   │   ├── mosqvision/
│   │   └── mosquitoalert/
│   ├── processed/                 # Sau khi chuẩn hóa
│   │   ├── train/
│   │   │   ├── ae_aegypti/
│   │   │   ├── ae_albopictus/
│   │   │   ├── an_dirus/
│   │   │   ├── an_minimus/
│   │   │   ├── cx_quinquefasciatus/
│   │   │   └── other/
│   │   ├── val/
│   │   └── test/
│   └── uploads/                   # Ảnh người dùng upload (production)
│
├── ml/                            # Toàn bộ phần Machine Learning
│   ├── scripts/
│   │   ├── 01_download_data.py    # Script tải dataset
│   │   ├── 02_preprocess.py       # Chuẩn hóa, split dataset
│   │   ├── 03_train.py            # Training chính
│   │   ├── 04_evaluate.py         # Đánh giá model
│   │   └── 05_export.py           # Export model ra ONNX/TorchScript
│   ├── models/
│   │   └── saved/                 # Lưu model weights (.pth, .onnx)
│   ├── notebooks/                 # Jupyter notebooks thử nghiệm
│   └── requirements.txt
│
├── backend/                       # FastAPI
│   ├── app/
│   │   ├── main.py                # Entry point FastAPI
│   │   ├── routers/
│   │   │   ├── predict.py         # /api/predict
│   │   │   ├── reports.py         # /api/reports
│   │   │   └── feedback.py        # /api/feedback
│   │   │   ├── training.py        # /api/admin/training (tạo/giám sát training)
│   │   │   └── admin_logs.py      # /api/admin/logs (xem log)
│   │   ├── services/
│   │   │   ├── model_service.py   # Load & inference model
│   │   │   └── image_service.py   # Xử lý ảnh đầu vào
│   │   ├── models/
│   │   │   └── schemas.py         # Pydantic schemas
│   │   └── database.py            # SQLAlchemy setup
│   │   └── worker/                # Job queue: training/retrain + progress update
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      # React
│   ├── src/
│   │   ├── components/
│   │   │   ├── ImageUploader.jsx  # Upload nhiều ảnh
│   │   │   ├── ResultCard.jsx     # Hiển thị kết quả
│   │   │   ├── ConfidenceBar.jsx  # Thanh confidence
│   │   │   └── FeedbackForm.jsx   # Form xác nhận của chuyên gia
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   └── History.jsx        # Lịch sử nhận dạng
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── infra/                         # Cấu hình chạy trên VPS (compose/nginx/ssl)
│   └── nginx/
│       ├── conf.d/
│       └── certs/
└── README.md
```

---

## 2. Giai đoạn 1 — Thu thập & Chuẩn bị dữ liệu

### 2.1 Danh sách dataset cần tải

| # | Dataset | Số ảnh | Loài | Link | Cách tải |
|---|---------|--------|------|------|----------|
| 1 | MosquitoDL | ~6.000 | 8 loài Aedes/Anopheles/Culex | https://github.com/jypark1994/MosquitoDL | Git clone |
| 2 | Kaggle Aedes Thái Lan | 4.120 | Ae. aegypti + Ae. albopictus | https://kaggle.com/pradeepisawasan/aedes-mosquitos | Kaggle API |
| 3 | MosqVision-3K | 3.000 | 3 chi cân bằng | https://zenodo.org/records/14238701 | wget |
| 4 | Mosquito Alert | 10.000+ | Ae. albopictus, Ae. aegypti... | https://www.mosquitoalert.com/en/mosquito-images-dataset/ | wget EBI |
| 5 | Mendeley Mosquito on Skin | ~2.600 | Aedes + Culex | https://data.mendeley.com/datasets/zw4p9kj6nt/2 | Web download |
| 6 | IEEE Dataport Aedes+Culex | 1.400 | Aedes + Culex (Thái Lan) | https://ieee-dataport.org/open-access/image-dataset-aedes-and-culex-mosquito-species | Web download |

**Tổng ước tính sau gộp & loại trùng: ~18.000–22.000 ảnh**

### 2.2 Script tải dữ liệu (`ml/scripts/01_download_data.py`)

```python
#!/usr/bin/env python3
"""
Script tải tất cả dataset muỗi về thư mục data/raw/
Chạy: python 01_download_data.py
"""

import os
import subprocess
from pathlib import Path

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def download_mosquitodl():
    """
    Dataset từ Hàn Quốc — 8 loài, ~6000 ảnh
    Loài: Ae.albopictus, Ae.vexans, Ae.dorsalis, Ae.koreicus,
          Anopheles spp., Cx.pipiens, Cx.tritaeniorhynchus, Cx.inatomii
    """
    target = RAW_DIR / "mosquitodl"
    if target.exists():
        print("MosquitoDL đã tồn tại, bỏ qua.")
        return
    print("Đang clone MosquitoDL...")
    subprocess.run([
        "git", "clone",
        "https://github.com/jypark1994/MosquitoDL.git",
        str(target)
    ], check=True)
    print("✓ MosquitoDL xong")


def download_kaggle_aedes():
    """
    Dataset Aedes Thái Lan — 4120 ảnh Ae.aegypti + Ae.albopictus
    Yêu cầu: cài kaggle CLI và cấu hình ~/.kaggle/kaggle.json
    Xem: https://www.kaggle.com/docs/api
    """
    target = RAW_DIR / "kaggle_aedes"
    if target.exists():
        print("Kaggle Aedes đã tồn tại, bỏ qua.")
        return
    target.mkdir(parents=True)
    print("Đang tải Kaggle Aedes (cần kaggle CLI)...")
    subprocess.run([
        "kaggle", "datasets", "download",
        "-d", "pradeepisawasan/aedes-mosquitos",
        "-p", str(target),
        "--unzip"
    ], check=True)
    print("✓ Kaggle Aedes xong")


def download_mosqvision():
    """
    MosqVision-3K từ Zenodo — 3000 ảnh, 3 chi cân bằng
    """
    import urllib.request
    import zipfile

    target = RAW_DIR / "mosqvision"
    if target.exists():
        print("MosqVision đã tồn tại, bỏ qua.")
        return
    target.mkdir(parents=True)

    # Zenodo DOI: 10.5281/zenodo.14238701
    url = "https://zenodo.org/records/14238701/files/Mosquito_Dataset.zip"
    zip_path = target / "dataset.zip"

    print(f"Đang tải MosqVision-3K từ Zenodo...")
    urllib.request.urlretrieve(url, zip_path)

    print("Đang giải nén...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(target)
    zip_path.unlink()
    print("✓ MosqVision-3K xong")


def download_mosquito_alert():
    """
    Mosquito Alert — ảnh được chuyên gia validate, nhiều loài Aedes
    Tải từ EBI BioStudies: https://www.ebi.ac.uk/biostudies/studies/S-BIAD249
    Chỉ tải Ae.aegypti và Ae.albopictus để tiết kiệm bandwidth
    """
    import urllib.request

    species_urls = {
        "Aedes_albopictus": "https://www.ebi.ac.uk/biostudies/files/S-BIAD249/Aedes_albopictus",
        "Aedes_aegypti": "https://www.ebi.ac.uk/biostudies/files/S-BIAD249/Aedes_aegypti",
    }

    target = RAW_DIR / "mosquitoalert"
    target.mkdir(parents=True, exist_ok=True)

    for species, url in species_urls.items():
        species_dir = target / species
        if species_dir.exists():
            print(f"MosquitoAlert/{species} đã tồn tại, bỏ qua.")
            continue
        print(f"Đang tải MosquitoAlert/{species}...")
        # Tải từng năm (2015-2022)
        for year in range(2015, 2023):
            year_url = f"{url}/{year}/{year}.zip"
            year_dir = species_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            try:
                zip_path = year_dir / f"{year}.zip"
                urllib.request.urlretrieve(year_url, zip_path)
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(year_dir)
                zip_path.unlink()
                print(f"  ✓ {species}/{year}")
            except Exception as e:
                print(f"  ✗ {species}/{year}: {e}")

    print("✓ Mosquito Alert xong")


if __name__ == "__main__":
    print("=" * 50)
    print("Bắt đầu tải dataset muỗi")
    print("=" * 50)

    download_mosquitodl()
    download_mosqvision()
    download_mosquito_alert()

    # Kaggle cần setup riêng — chạy thủ công nếu cần
    print("\nLưu ý: Kaggle dataset cần setup kaggle CLI trước.")
    print("Xem hướng dẫn: https://www.kaggle.com/docs/api")
    print("Sau đó chạy: python 01_download_data.py --kaggle")

    print("\n✓ Hoàn tất tải dữ liệu!")
    print(f"Kiểm tra thư mục: {RAW_DIR.absolute()}")
```

### 2.3 Script tiền xử lý (`ml/scripts/02_preprocess.py`)

```python
#!/usr/bin/env python3
"""
Chuẩn hóa tất cả dataset về cùng cấu trúc thư mục,
sau đó split train/val/test (70/15/15).

Mapping loài về nhãn chuẩn:
  ae_aegypti       ← Aedes aegypti
  ae_albopictus    ← Aedes albopictus
  an_dirus         ← Anopheles dirus (+ Anopheles spp. từ MosquitoDL)
  cx_quinquefasciatus ← Culex quinquefasciatus + Cx.pipiens
  other            ← Các loài khác, không phải véc-tơ chính

Chạy: python 02_preprocess.py
"""

import os
import shutil
import random
from pathlib import Path
from PIL import Image

# --- Cấu hình ---
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
IMG_SIZE = (224, 224)   # EfficientNet chuẩn
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15
RANDOM_SEED = 42

# Nhãn chuẩn của hệ thống
STANDARD_LABELS = [
    "ae_aegypti",
    "ae_albopictus",
    "an_dirus",
    "an_minimus",
    "cx_quinquefasciatus",
    "other"
]

# Mapping tên thư mục/file gốc → nhãn chuẩn
SPECIES_MAPPING = {
    # MosquitoDL (Hàn Quốc)
    "Aedes albopictus":        "ae_albopictus",
    "Aedes aegypti":           "ae_aegypti",
    "Aedes vexans":            "other",
    "Aedes dorsalis":          "other",
    "Aedes koreicus":          "other",
    "Anopheles spp":           "an_dirus",    # Treat as proxy cho Anopheles ĐNA
    "Culex pipiens":           "cx_quinquefasciatus",
    "Culex tritaeniorhynchus": "other",
    "Culex inatomii":          "other",

    # Kaggle Aedes Thái Lan
    "Ae_aegypti":              "ae_aegypti",
    "Ae_albopictus":           "ae_albopictus",

    # MosqVision-3K
    "Aedes":                   "ae_albopictus",  # MosqVision không phân loài Aedes
    "Anopheles":               "an_dirus",
    "Culex":                   "cx_quinquefasciatus",

    # Mosquito Alert
    "Aedes_albopictus":        "ae_albopictus",
    "Aedes_aegypti":           "ae_aegypti",
}


def resize_and_save(src_path: Path, dst_path: Path, size=IMG_SIZE):
    """Resize ảnh về kích thước chuẩn và lưu."""
    try:
        with Image.open(src_path) as img:
            # Chuyển về RGB (bỏ alpha channel nếu PNG)
            img = img.convert("RGB")
            img = img.resize(size, Image.LANCZOS)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(dst_path, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"  Lỗi xử lý {src_path.name}: {e}")
        return False


def collect_all_images() -> dict[str, list[Path]]:
    """
    Duyệt qua tất cả dataset thô, map về nhãn chuẩn.
    Trả về dict: {label: [list of image paths]}
    """
    collection = {label: [] for label in STANDARD_LABELS}
    VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    def add_image(img_path: Path, label: str):
        if img_path.suffix.lower() in VALID_EXTS and label in STANDARD_LABELS:
            collection[label].append(img_path)

    # --- Dataset 1: MosquitoDL ---
    mosq_dl = RAW_DIR / "mosquitodl" / "Datasets"
    if mosq_dl.exists():
        print("Xử lý MosquitoDL...")
        for species_dir in mosq_dl.iterdir():
            if not species_dir.is_dir():
                continue
            label = SPECIES_MAPPING.get(species_dir.name)
            if label:
                for img in species_dir.rglob("*"):
                    if img.suffix.lower() in VALID_EXTS:
                        add_image(img, label)

    # --- Dataset 2: Kaggle Aedes ---
    kaggle_aedes = RAW_DIR / "kaggle_aedes"
    if kaggle_aedes.exists():
        print("Xử lý Kaggle Aedes...")
        for species_dir in kaggle_aedes.iterdir():
            if not species_dir.is_dir():
                continue
            label = SPECIES_MAPPING.get(species_dir.name)
            if label:
                for img in species_dir.rglob("*"):
                    if img.suffix.lower() in VALID_EXTS:
                        add_image(img, label)

    # --- Dataset 3: MosqVision-3K ---
    mosqvision = RAW_DIR / "mosqvision"
    if mosqvision.exists():
        print("Xử lý MosqVision-3K...")
        for species_dir in mosqvision.rglob("*"):
            if not species_dir.is_dir():
                continue
            label = SPECIES_MAPPING.get(species_dir.name)
            if label:
                for img in species_dir.iterdir():
                    if img.suffix.lower() in VALID_EXTS:
                        add_image(img, label)

    # --- Dataset 4: Mosquito Alert ---
    mosq_alert = RAW_DIR / "mosquitoalert"
    if mosq_alert.exists():
        print("Xử lý Mosquito Alert...")
        for species_dir in mosq_alert.iterdir():
            if not species_dir.is_dir():
                continue
            label = SPECIES_MAPPING.get(species_dir.name)
            if label:
                for img in species_dir.rglob("*"):
                    if img.suffix.lower() in VALID_EXTS:
                        add_image(img, label)

    return collection


def split_and_copy(collection: dict[str, list[Path]]):
    """Split train/val/test và copy ảnh vào thư mục đã xử lý."""
    random.seed(RANDOM_SEED)

    for split in ["train", "val", "test"]:
        for label in STANDARD_LABELS:
            (PROCESSED_DIR / split / label).mkdir(parents=True, exist_ok=True)

    total_stats = {}

    for label, images in collection.items():
        random.shuffle(images)
        n = len(images)
        n_train = int(n * TRAIN_RATIO)
        n_val   = int(n * VAL_RATIO)

        splits = {
            "train": images[:n_train],
            "val":   images[n_train:n_train + n_val],
            "test":  images[n_train + n_val:]
        }

        total_stats[label] = {split: len(imgs) for split, imgs in splits.items()}

        for split, imgs in splits.items():
            for i, src in enumerate(imgs):
                # Đặt tên file mới để tránh trùng
                dst = PROCESSED_DIR / split / label / f"{label}_{split}_{i:05d}.jpg"
                resize_and_save(src, dst)

        print(f"  {label}: train={splits['train'].__len__()} | "
              f"val={splits['val'].__len__()} | test={splits['test'].__len__()}")

    return total_stats


def print_summary(stats: dict):
    print("\n" + "=" * 50)
    print("TỔNG KẾT DATASET")
    print("=" * 50)
    total = 0
    for label, counts in stats.items():
        n = sum(counts.values())
        total += n
        print(f"  {label:25s}: {n:5d} ảnh  "
              f"(train={counts['train']}, val={counts['val']}, test={counts['test']})")
    print(f"\n  {'TỔNG':25s}: {total:5d} ảnh")
    print("=" * 50)


if __name__ == "__main__":
    print("Bắt đầu tiền xử lý dataset...")

    # Xóa processed cũ nếu có
    if PROCESSED_DIR.exists():
        confirm = input(f"\nThư mục {PROCESSED_DIR} đã tồn tại. Xóa và làm lại? (y/N): ")
        if confirm.lower() == 'y':
            shutil.rmtree(PROCESSED_DIR)
        else:
            print("Hủy.")
            exit(0)

    print("\nBước 1: Thu thập ảnh từ tất cả dataset...")
    collection = collect_all_images()

    print("\nBước 2: Split train/val/test và resize ảnh...")
    stats = split_and_copy(collection)

    print_summary(stats)
    print(f"\n✓ Dataset đã sẵn sàng tại: {PROCESSED_DIR.absolute()}")
```

---

## 3. Giai đoạn 2 — Training Model

### 3.1 Cài đặt môi trường training

```bash
# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Cài thư viện ML
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install timm scikit-learn pillow matplotlib seaborn tqdm wandb
```

### 3.2 Script training chính (`ml/scripts/03_train.py`)

```python
#!/usr/bin/env python3
"""
Training EfficientNetB3 pretrained (ImageNet) cho nhận dạng loài muỗi.

Chiến lược:
  - Giai đoạn 1 (5 epoch): Chỉ train classifier head (lớp cuối)
                            Backbone bị đóng băng (frozen)
  - Giai đoạn 2 (20 epoch): Fine-tune toàn bộ mạng với learning rate nhỏ hơn
                              Có early stopping

Chạy:
  python 03_train.py
  python 03_train.py --resume models/saved/best_model.pth   # Tiếp tục từ checkpoint
"""

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import timm
from tqdm import tqdm

# --- Cấu hình ---
CONFIG = {
    "data_dir":       "data/processed",
    "model_name":     "efficientnet_b3",    # Từ thư viện timm
    "num_classes":    6,                     # Số loài muỗi
    "img_size":       224,
    "batch_size":     32,
    "num_workers":    4,

    # Giai đoạn 1 — chỉ train head
    "phase1_epochs":  5,
    "phase1_lr":      1e-3,

    # Giai đoạn 2 — fine-tune toàn bộ
    "phase2_epochs":  25,
    "phase2_lr":      1e-4,

    "weight_decay":   1e-4,
    "early_stop_patience": 7,   # Dừng nếu val_loss không giảm sau 7 epoch
    "save_dir":       "models/saved",
    "device":         "cuda" if torch.cuda.is_available() else "cpu",
}

CLASS_NAMES = [
    "ae_aegypti",
    "ae_albopictus",
    "an_dirus",
    "an_minimus",
    "cx_quinquefasciatus",
    "other"
]


def get_transforms(phase: str, img_size: int):
    """Data augmentation khác nhau cho train/val/test."""

    if phase == "train":
        return transforms.Compose([
            transforms.RandomResizedCrop(img_size, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(30),
            transforms.ColorJitter(
                brightness=0.3, contrast=0.3,
                saturation=0.2, hue=0.05
            ),
            transforms.RandomGrayscale(p=0.05),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet mean
                std=[0.229, 0.224, 0.225]    # ImageNet std
            ),
        ])
    else:
        # Val và Test: chỉ resize + normalize, không augment
        return transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])


def get_dataloaders(config: dict):
    """Load dataset từ thư mục đã xử lý."""
    data_dir = Path(config["data_dir"])

    datasets_dict = {
        phase: datasets.ImageFolder(
            root=str(data_dir / phase),
            transform=get_transforms(phase, config["img_size"])
        )
        for phase in ["train", "val", "test"]
    }

    dataloaders = {
        phase: DataLoader(
            ds,
            batch_size=config["batch_size"],
            shuffle=(phase == "train"),
            num_workers=config["num_workers"],
            pin_memory=True if config["device"] == "cuda" else False
        )
        for phase, ds in datasets_dict.items()
    }

    print("\nDataset info:")
    for phase, ds in datasets_dict.items():
        print(f"  {phase:6s}: {len(ds):6d} ảnh | classes: {ds.classes}")

    return dataloaders


def build_model(config: dict) -> nn.Module:
    """
    Load EfficientNetB3 pretrained từ timm,
    thay lớp classifier cuối cho phù hợp số class.
    """
    model = timm.create_model(
        config["model_name"],
        pretrained=True,           # Tải weight ImageNet pretrained
        num_classes=config["num_classes"]
    )
    return model.to(config["device"])


def freeze_backbone(model: nn.Module):
    """Đóng băng backbone, chỉ để classifier head trainable."""
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"  Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")


def unfreeze_all(model: nn.Module):
    """Mở băng toàn bộ model cho phase 2."""
    for param in model.parameters():
        param.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable params: {trainable:,} (toàn bộ)")


def train_one_epoch(model, loader, criterion, optimizer, device, phase="train"):
    """Chạy 1 epoch training hoặc validation."""
    is_training = (phase == "train")
    model.train() if is_training else model.eval()

    running_loss    = 0.0
    running_correct = 0
    total           = 0

    with torch.set_grad_enabled(is_training):
        for images, labels in tqdm(loader, desc=f"  {phase}", leave=False):
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss    = criterion(outputs, labels)

            if is_training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            _, preds      = outputs.max(1)
            running_loss    += loss.item() * images.size(0)
            running_correct += preds.eq(labels).sum().item()
            total           += images.size(0)

    epoch_loss = running_loss / total
    epoch_acc  = running_correct / total
    return epoch_loss, epoch_acc


def train(config: dict, resume_path: str = None):
    device = config["device"]
    print(f"\nDevice: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Load data
    dataloaders = get_dataloaders(config)

    # Build model
    print("\nKhởi tạo model EfficientNetB3...")
    model = build_model(config)

    # Loss function — dùng label smoothing để tránh overconfident
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    # Lưu lịch sử training
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    save_dir = Path(config["save_dir"])
    save_dir.mkdir(parents=True, exist_ok=True)

    best_val_acc = 0.0
    patience_counter = 0

    # =========================================================
    # PHASE 1: Chỉ train classifier head (backbone frozen)
    # =========================================================
    print("\n" + "=" * 50)
    print("PHASE 1: Training classifier head (backbone frozen)")
    print("=" * 50)
    freeze_backbone(model)

    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config["phase1_lr"],
        weight_decay=config["weight_decay"]
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config["phase1_epochs"]
    )

    for epoch in range(1, config["phase1_epochs"] + 1):
        print(f"\nEpoch {epoch}/{config['phase1_epochs']}")
        t0 = time.time()

        train_loss, train_acc = train_one_epoch(
            model, dataloaders["train"], criterion, optimizer, device, "train"
        )
        val_loss, val_acc = train_one_epoch(
            model, dataloaders["val"], criterion, optimizer, device, "val"
        )
        scheduler.step()

        elapsed = time.time() - t0
        print(f"  train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
              f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} | {elapsed:.0f}s")

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

    # =========================================================
    # PHASE 2: Fine-tune toàn bộ model
    # =========================================================
    print("\n" + "=" * 50)
    print("PHASE 2: Fine-tuning toàn bộ model")
    print("=" * 50)
    unfreeze_all(model)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=config["phase2_lr"],
        weight_decay=config["weight_decay"]
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config["phase2_epochs"]
    )

    for epoch in range(1, config["phase2_epochs"] + 1):
        print(f"\nEpoch {epoch}/{config['phase2_epochs']}")
        t0 = time.time()

        train_loss, train_acc = train_one_epoch(
            model, dataloaders["train"], criterion, optimizer, device, "train"
        )
        val_loss, val_acc = train_one_epoch(
            model, dataloaders["val"], criterion, optimizer, device, "val"
        )
        scheduler.step()

        elapsed = time.time() - t0
        print(f"  train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
              f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} | {elapsed:.0f}s")

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        # Lưu model tốt nhất
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": val_acc,
                "config": config,
                "class_names": CLASS_NAMES,
            }, save_dir / "best_model.pth")
            print(f"  ✓ Lưu best model (val_acc={val_acc:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= config["early_stop_patience"]:
                print(f"\n  Early stopping sau {epoch} epoch (patience={config['early_stop_patience']})")
                break

    # Lưu model cuối cùng
    torch.save(model.state_dict(), save_dir / "last_model.pth")

    # Lưu history
    with open(save_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n✓ Training xong! Best val_acc = {best_val_acc:.4f}")
    print(f"  Model lưu tại: {save_dir.absolute()}")
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", type=str, default=None,
                        help="Path đến checkpoint để tiếp tục training")
    args = parser.parse_args()

    train(CONFIG, resume_path=args.resume)
```

### 3.3 Script đánh giá (`ml/scripts/04_evaluate.py`)

```python
#!/usr/bin/env python3
"""
Đánh giá model trên test set, in classification report và confusion matrix.
Chạy: python 04_evaluate.py --model models/saved/best_model.pth
"""

import argparse
import torch
import timm
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from sklearn.metrics import classification_report, confusion_matrix

CLASS_NAMES = [
    "ae_aegypti", "ae_albopictus", "an_dirus",
    "an_minimus", "cx_quinquefasciatus", "other"
]


def evaluate(model_path: str, data_dir: str = "data/processed"):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)
    config = checkpoint.get("config", {})

    # Load model
    model = timm.create_model(
        config.get("model_name", "efficientnet_b3"),
        pretrained=False,
        num_classes=config.get("num_classes", 6)
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    # Test transform
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])

    test_dataset = datasets.ImageFolder(
        root=f"{data_dir}/test", transform=transform
    )
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    all_preds  = []
    all_labels = []
    all_probs  = []

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            probs   = torch.softmax(outputs, dim=1)
            _, preds = outputs.max(1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    # In kết quả
    print("\nClassification Report:")
    print(classification_report(all_labels, all_preds, target_names=CLASS_NAMES))

    # Vẽ confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.title("Confusion Matrix — Test Set")
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.tight_layout()
    plt.savefig("models/saved/confusion_matrix.png", dpi=150)
    print("✓ Confusion matrix lưu tại: models/saved/confusion_matrix.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/saved/best_model.pth")
    parser.add_argument("--data_dir", default="data/processed")
    args = parser.parse_args()
    evaluate(args.model, args.data_dir)
```

### 3.4 Script export ONNX (`ml/scripts/05_export.py`)

```python
#!/usr/bin/env python3
"""
Export model PyTorch sang ONNX để deploy trên server không cần GPU.
Chạy: python 05_export.py --model models/saved/best_model.pth
"""

import torch
import timm
import argparse


def export_onnx(model_path: str, output_path: str = "models/saved/model.onnx"):
    device = "cpu"

    checkpoint = torch.load(model_path, map_location=device)
    config = checkpoint.get("config", {})

    model = timm.create_model(
        config.get("model_name", "efficientnet_b3"),
        pretrained=False,
        num_classes=config.get("num_classes", 6)
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dummy_input = torch.randn(1, 3, 224, 224)

    torch.onnx.export(
        model, dummy_input, output_path,
        export_params=True,
        opset_version=13,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input":  {0: "batch_size"},
            "output": {0: "batch_size"}
        }
    )
    print(f"✓ ONNX model lưu tại: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/saved/best_model.pth")
    parser.add_argument("--output", default="models/saved/model.onnx")
    args = parser.parse_args()
    export_onnx(args.model, args.output)
```

---

## 4. Giai đoạn 3 — FastAPI Backend

### 4.1 Cài đặt

```bash
cd backend
pip install fastapi uvicorn python-multipart pillow torch timm onnxruntime sqlalchemy aiosqlite
```

### 4.2 Model Service (`backend/app/services/model_service.py`)

```python
"""
Load model và thực hiện inference.
Hỗ trợ tổng hợp kết quả từ nhiều ảnh (multi-image voting).
"""

import torch
import timm
import numpy as np
from PIL import Image
from pathlib import Path
from torchvision import transforms

CLASS_NAMES = [
    "ae_aegypti",
    "ae_albopictus",
    "an_dirus",
    "an_minimus",
    "cx_quinquefasciatus",
    "other"
]

# Tên hiển thị thân thiện
DISPLAY_NAMES = {
    "ae_aegypti":           "Aedes aegypti (Muỗi vằn — Sốt xuất huyết chính)",
    "ae_albopictus":        "Aedes albopictus (Muỗi hổ — Sốt xuất huyết phụ)",
    "an_dirus":             "Anopheles dirus (Muỗi sốt rét rừng)",
    "an_minimus":           "Anopheles minimus (Muỗi sốt rét đồng bằng)",
    "cx_quinquefasciatus":  "Culex quinquefasciatus (Muỗi nhà — Viêm não Nhật Bản)",
    "other":                "Loài khác / Không xác định được"
}

# Ngưỡng confidence để báo "cần chuyên gia xem lại"
CONFIDENCE_THRESHOLD = 0.70


class MosquitoClassifier:
    def __init__(self, model_path: str):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model  = self._load_model(model_path)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])

    def _load_model(self, model_path: str):
        checkpoint = torch.load(model_path, map_location=self.device)
        config = checkpoint.get("config", {})
        model = timm.create_model(
            config.get("model_name", "efficientnet_b3"),
            pretrained=False,
            num_classes=config.get("num_classes", 6)
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model = model.to(self.device)
        model.eval()
        return model

    def predict_single(self, image: Image.Image) -> dict:
        """Dự đoán 1 ảnh, trả về dict kết quả."""
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor)
            probs   = torch.softmax(outputs, dim=1)[0]

        probs_np    = probs.cpu().numpy()
        pred_idx    = int(probs_np.argmax())
        pred_label  = CLASS_NAMES[pred_idx]
        confidence  = float(probs_np[pred_idx])

        return {
            "label":      pred_label,
            "confidence": confidence,
            "probs":      {CLASS_NAMES[i]: float(probs_np[i]) for i in range(len(CLASS_NAMES))}
        }

    def predict_multi(self, images: list[Image.Image]) -> dict:
        """
        Dự đoán nhiều ảnh cùng 1 con muỗi.
        Tổng hợp bằng weighted average của probabilities.
        """
        if not images:
            raise ValueError("Cần ít nhất 1 ảnh")

        # Dự đoán từng ảnh
        all_probs   = []
        per_image   = []

        for img in images:
            result = self.predict_single(img)
            all_probs.append(list(result["probs"].values()))
            per_image.append(result)

        # Weighted average: ảnh có confidence cao được tính trọng số cao hơn
        confidences = np.array([r["confidence"] for r in per_image])
        weights     = confidences / confidences.sum()

        avg_probs   = np.average(all_probs, axis=0, weights=weights)
        pred_idx    = int(avg_probs.argmax())
        pred_label  = CLASS_NAMES[pred_idx]
        confidence  = float(avg_probs[pred_idx])

        needs_expert = confidence < CONFIDENCE_THRESHOLD

        return {
            "label":         pred_label,
            "display_name":  DISPLAY_NAMES[pred_label],
            "confidence":    confidence,
            "needs_expert":  needs_expert,
            "message":       (
                "Độ tin cậy thấp — khuyến nghị chuyên gia xác nhận."
                if needs_expert else
                f"Nhận dạng thành công với độ tin cậy {confidence:.0%}"
            ),
            "probs":         {CLASS_NAMES[i]: float(avg_probs[i]) for i in range(len(CLASS_NAMES))},
            "per_image":     per_image,
            "num_images":    len(images),
        }


# Singleton — load model 1 lần khi server khởi động
_classifier: MosquitoClassifier | None = None

def get_classifier() -> MosquitoClassifier:
    global _classifier
    if _classifier is None:
        model_path = "models/saved/best_model.pth"
        _classifier = MosquitoClassifier(model_path)
    return _classifier
```

### 4.3 Main FastAPI (`backend/app/main.py`)

```python
"""
FastAPI entry point.
Chạy: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import io
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.services.model_service import get_classifier

app = FastAPI(
    title="Mosquito ID API",
    description="Nhận dạng loài muỗi từ ảnh — Hệ thống giám sát dịch tễ",
    version="1.0.0"
)

# CORS — cho phép React frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FeedbackRequest(BaseModel):
    prediction_id: str
    confirmed_label: str
    expert_note: Optional[str] = None


@app.get("/")
def root():
    return {"message": "Mosquito ID API đang chạy", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/predict")
async def predict(
    files: list[UploadFile] = File(..., description="1 đến 5 ảnh của cùng 1 con muỗi"),
    location: Optional[str] = None,
    reporter: Optional[str] = None,
):
    """
    Nhận 1-5 ảnh của cùng 1 con muỗi, trả về kết quả nhận dạng.
    """
    # Validate
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 ảnh")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Tối đa 5 ảnh mỗi lần")

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
    images = []

    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename}: Chỉ hỗ trợ JPEG, PNG, WebP, BMP"
            )
        contents = await file.read()
        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            images.append(img)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Không thể đọc file ảnh: {file.filename}"
            )

    # Inference
    try:
        classifier = get_classifier()
        result = classifier.predict_multi(images)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi model: {str(e)}")

    # Tạo ID cho prediction này (để feedback sau)
    prediction_id = str(uuid.uuid4())

    return {
        "prediction_id":  prediction_id,
        "timestamp":      datetime.now().isoformat(),
        "location":       location,
        "reporter":       reporter,
        "num_images":     result["num_images"],
        "result": {
            "label":        result["label"],
            "display_name": result["display_name"],
            "confidence":   result["confidence"],
            "needs_expert": result["needs_expert"],
            "message":      result["message"],
            "probabilities": result["probs"],
        }
    }


@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Cán bộ y tế xác nhận hoặc sửa kết quả — dữ liệu này dùng để retrain sau.
    """
    # Trong production: lưu vào database
    print(f"Feedback: {feedback.prediction_id} → {feedback.confirmed_label}")
    return {
        "status": "ok",
        "message": "Cảm ơn! Phản hồi của bạn giúp cải thiện hệ thống.",
        "prediction_id": feedback.prediction_id
    }
```

---

## 5. Giai đoạn 4 — React Frontend

### 5.1 Cài đặt

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install axios react-dropzone lucide-react
```

### 5.2 Component chính (`frontend/src/App.jsx`)

```jsx
import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import axios from "axios"

const API_URL = "http://localhost:8000"

// Label → màu hiển thị
const SPECIES_COLORS = {
  ae_aegypti:          "bg-red-100 border-red-400 text-red-800",
  ae_albopictus:       "bg-orange-100 border-orange-400 text-orange-800",
  an_dirus:            "bg-purple-100 border-purple-400 text-purple-800",
  an_minimus:          "bg-purple-100 border-purple-400 text-purple-800",
  cx_quinquefasciatus: "bg-blue-100 border-blue-400 text-blue-800",
  other:               "bg-gray-100 border-gray-400 text-gray-800",
}

export default function App() {
  const [files, setFiles]         = useState([])
  const [previews, setPreviews]   = useState([])
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [reporter, setReporter]   = useState("")
  const [location, setLocation]   = useState("")

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length + files.length > 5) {
      setError("Tối đa 5 ảnh mỗi lần")
      return
    }
    setFiles(prev => [...prev, ...acceptedFiles])
    setPreviews(prev => [
      ...prev,
      ...acceptedFiles.map(f => URL.createObjectURL(f))
    ])
    setError(null)
    setResult(null)
  }, [files])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".webp"] },
    maxFiles: 5
  })

  const removeImage = (idx) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
    setPreviews(prev => prev.filter((_, i) => i !== idx))
  }

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError("Vui lòng chọn ít nhất 1 ảnh")
      return
    }
    setLoading(true)
    setError(null)

    const formData = new FormData()
    files.forEach(f => formData.append("files", f))
    if (location) formData.append("location", location)
    if (reporter) formData.append("reporter", reporter)

    try {
      const res = await axios.post(`${API_URL}/api/predict`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      })
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || "Lỗi kết nối server")
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (confirmedLabel) => {
    if (!result?.prediction_id) return
    await axios.post(`${API_URL}/api/feedback`, {
      prediction_id: result.prediction_id,
      confirmed_label: confirmedLabel
    })
    alert("Cảm ơn! Phản hồi đã được ghi nhận.")
  }

  const reset = () => {
    setFiles([])
    setPreviews([])
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">🦟 Nhận dạng Muỗi</h1>
          <p className="text-gray-500 mt-2">
            Hệ thống nhận dạng loài muỗi véc-tơ — Hỗ trợ giám sát dịch tễ
          </p>
        </div>

        {/* Form thông tin */}
        <div className="bg-white rounded-xl shadow p-6 mb-6 grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700">Cán bộ báo cáo</label>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Tên cán bộ..."
              value={reporter}
              onChange={e => setReporter(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Địa điểm thu thập</label>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Tỉnh/Huyện/Xã..."
              value={location}
              onChange={e => setLocation(e.target.value)}
            />
          </div>
        </div>

        {/* Upload zone */}
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition
              ${isDragActive ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-blue-300"}`}
          >
            <input {...getInputProps()} />
            <p className="text-4xl mb-3">📷</p>
            <p className="font-medium text-gray-700">
              {isDragActive ? "Thả ảnh vào đây..." : "Kéo thả ảnh hoặc click để chọn"}
            </p>
            <p className="text-sm text-gray-400 mt-1">
              Chụp nhiều góc khác nhau của cùng 1 con muỗi (tối đa 5 ảnh)
            </p>
          </div>

          {/* Preview ảnh */}
          {previews.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-3">
              {previews.map((src, idx) => (
                <div key={idx} className="relative">
                  <img
                    src={src} alt={`Ảnh ${idx+1}`}
                    className="w-24 h-24 object-cover rounded-lg border"
                  />
                  <button
                    onClick={() => removeImage(idx)}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center"
                  >×</button>
                  <span className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-1 rounded">
                    {idx+1}
                  </span>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
              ⚠️ {error}
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading || files.length === 0}
            className="mt-4 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300
                       text-white font-medium py-3 rounded-xl transition"
          >
            {loading ? "Đang nhận dạng..." : `Nhận dạng (${files.length} ảnh)`}
          </button>
        </div>

        {/* Kết quả */}
        {result && (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-bold text-lg text-gray-800 mb-4">Kết quả nhận dạng</h2>

            <div className={`border-2 rounded-xl p-4 mb-4 ${SPECIES_COLORS[result.result.label]}`}>
              <p className="font-bold text-xl">{result.result.display_name}</p>
              <p className="text-sm mt-1">Độ tin cậy: {(result.result.confidence * 100).toFixed(1)}%</p>
              {result.result.needs_expert && (
                <p className="text-sm mt-2 font-medium">
                  ⚠️ {result.result.message}
                </p>
              )}
            </div>

            {/* Thanh xác suất các loài */}
            <div className="space-y-2 mb-6">
              {Object.entries(result.result.probabilities)
                .sort(([,a],[,b]) => b - a)
                .map(([label, prob]) => (
                  <div key={label}>
                    <div className="flex justify-between text-xs text-gray-600 mb-1">
                      <span>{label}</span>
                      <span>{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${prob * 100}%` }}
                      />
                    </div>
                  </div>
                ))
              }
            </div>

            {/* Xác nhận của cán bộ */}
            <div className="border-t pt-4">
              <p className="text-sm font-medium text-gray-700 mb-2">
                Xác nhận kết quả (tùy chọn):
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleFeedback(result.result.label)}
                  className="bg-green-100 text-green-800 border border-green-300 px-3 py-1 rounded-lg text-sm hover:bg-green-200"
                >
                  ✓ Kết quả đúng
                </button>
                <button
                  onClick={() => handleFeedback("other")}
                  className="bg-orange-100 text-orange-800 border border-orange-300 px-3 py-1 rounded-lg text-sm hover:bg-orange-200"
                >
                  ✗ Cần xem lại
                </button>
              </div>
            </div>

            <button
              onClick={reset}
              className="mt-4 w-full border border-gray-300 text-gray-700 py-2 rounded-xl hover:bg-gray-50 text-sm"
            >
              Nhận dạng ảnh khác
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

---

## 6. Giai đoạn 5 — Triển khai

> **Yêu cầu**: toàn bộ hệ thống chạy trên **VPS**; VPS có **Docker**. Phần training/retrain chạy như job nền (worker) để web có thể theo dõi tiến độ.

### 6.1 Yêu cầu trên VPS

- Docker Engine + Docker Compose plugin (`docker compose`)
- (Tuỳ chọn) GPU NVIDIA cho training: NVIDIA driver + `nvidia-container-toolkit`

### 6.2 `docker-compose.yml` (chạy trên VPS)

> Lưu ý: nguyên tắc production là **chỉ mở public Nginx** (80/443). Backend/DB/Redis chạy nội bộ trong network Docker.

```yaml
version: "3.9"
name: mosquito-id

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: mosquito
      POSTGRES_USER: mosquito
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg2://mosquito:${POSTGRES_PASSWORD}@db:5432/mosquito
      REDIS_URL: redis://redis:6379/0
      MODEL_PATH: /app/models/saved/best_model.pth
      UPLOAD_DIR: /app/data/uploads
      LOG_DIR: /app/logs
    volumes:
      - ./ml/models/saved:/app/models/saved:ro
      - ./data/uploads:/app/data/uploads
      - app_logs:/app/logs
    depends_on:
      - db
      - redis
    expose:
      - "8000"
    restart: unless-stopped

  # Worker xử lý job dài (training/retrain/export) và cập nhật progress để UI quản trị theo dõi.
  # Bật bằng: `docker compose --profile train up -d`.
  worker:
    build: ./backend
    command: python -m app.worker
    environment:
      DATABASE_URL: postgresql+psycopg2://mosquito:${POSTGRES_PASSWORD}@db:5432/mosquito
      REDIS_URL: redis://redis:6379/0
      MODEL_DIR: /app/models/saved
      DATA_DIR: /app/data
      LOG_DIR: /app/logs
    volumes:
      - ./ml:/app/ml
      - ./ml/models/saved:/app/models/saved
      - ./data:/app/data
      - app_logs:/app/logs
    depends_on:
      - db
      - redis
    restart: unless-stopped
    profiles: ["train"]

  # Frontend build ra static và serve bằng Nginx (khuyến nghị cho production).
  frontend:
    build: ./frontend
    depends_on:
      - backend
    expose:
      - "80"
    restart: unless-stopped

  # Reverse proxy duy nhất public ra Internet (HTTPS, routing /api -> backend).
  nginx:
    image: nginx:1.27
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/nginx/conf.d:/etc/nginx/conf.d:ro
      - ./infra/nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  db_data:
  app_logs:
```

### 6.3 Triển khai trên VPS (gợi ý)

```bash
# 1) Clone code + cấu hình biến môi trường
cp .env.example .env

# 2) Build + chạy (nginx là service duy nhất mở port 80/443 ra ngoài)
docker compose up -d --build

# 3) (Tuỳ chọn) bật worker training/retrain
docker compose --profile train up -d --build
```

---

## 7. Giao diện quản trị (Admin) — Log & Training

> **Mục tiêu**: thêm giao diện quản trị trên web để **theo dõi log**, **theo dõi tiến độ training**, và quản lý vòng đời model trên VPS.

### 7.1 Chức năng tối thiểu nên có

- **Training runs**: tạo job training/retrain, xem trạng thái (queued/running/succeeded/failed), phần trăm tiến độ, ETA
- **Artifacts**: xem danh sách model phiên bản, metrics, ngày train, người tạo, link tải/đánh dấu “đang dùng”
- **Logs**: xem log theo service (`backend`, `worker`) và theo `run_id`/`request_id` (tail/grep cơ bản)
- **Audit**: ghi lại ai bấm retrain/deploy và thay đổi cấu hình nào

### 7.2 Dữ liệu cần lưu để theo dõi tiến độ training

Gợi ý tạo bảng (hoặc collection) tối thiểu:

- `training_runs`: `id`, `created_at`, `created_by`, `status`, `progress` (0..100), `current_epoch`, `total_epochs`, `metrics_json`, `artifact_path`, `error_message`
- `training_events`: `run_id`, `ts`, `level`, `message`, `payload_json` (tuỳ chọn)

### 7.3 API gợi ý (FastAPI)

- `POST /api/admin/training/runs` tạo run mới (cấu hình epochs, dataset, lr, ...)
- `GET /api/admin/training/runs` danh sách runs + trạng thái
- `GET /api/admin/training/runs/{id}` chi tiết run + metrics
- `GET /api/admin/training/runs/{id}/events` stream sự kiện (SSE/WebSocket) để UI realtime
- `GET /api/admin/logs?service=worker&tail=200&run_id=...` xem log theo bộ lọc

### 7.4 UI gợi ý (React)

- Route `/admin` (yêu cầu đăng nhập/role `admin`)
- Trang “Training”: bảng runs, nút “Start retrain”, biểu đồ tiến độ/metrics
- Trang “Logs”: chọn service + filter theo `run_id`, xem realtime (polling hoặc stream)

### 7.5 Quy ước log/progress để UI hiển thị đúng

- Worker nên **ghi progress định kỳ** (mỗi epoch hoặc mỗi N batches) vào `training_runs.progress`
- Mọi log liên quan training gắn `run_id` để truy vết (structured log JSON càng tốt)

---

## 8. Feedback Loop & Cải thiện Model

### Quy trình liên tục

```
Người dùng upload ảnh
       ↓
Model dự đoán
       ↓
Cán bộ y tế xác nhận / sửa kết quả  ← bước này quan trọng nhất
       ↓
Ảnh + nhãn mới được lưu vào data/uploads/confirmed/
       ↓
Mỗi 3-6 tháng: gộp dữ liệu mới vào training set
       ↓
Retrain model với toàn bộ dữ liệu (cũ + mới)
       ↓
Đánh giá: nếu val_acc tăng → deploy phiên bản mới
```

### Điều cần theo dõi (metrics)

- `val_accuracy` > 90% trước khi deploy
- Confidence trung bình của các dự đoán đúng > 0.80
- Tỉ lệ `needs_expert` < 20% (nếu > 20% tức model không đủ tốt)
- Confusion matrix: kiểm tra đặc biệt Ae. aegypti vs Ae. albopictus (hay nhầm nhất)

---

## Ghi chú quan trọng

### Giới hạn kỹ thuật cần truyền đạt cho người dùng

1. **Chất lượng ảnh quyết định kết quả** — muỗi cần chiếm >30% diện tích ảnh, nền đơn màu, đủ sáng
2. **Không phân biệt được nếu mẫu bị hỏng** — cánh gãy, thân bẹp sẽ làm giảm accuracy
3. **Confidence < 70% = cần chuyên gia** — hệ thống tự báo, đừng bỏ qua cảnh báo này
4. **Anopheles khó hơn Aedes** — ít data hơn, cần bổ sung ảnh thực địa VN

### Phần cần làm thêm (ngoài scope tài liệu này)

- Authentication / phân quyền cán bộ y tế
- Dashboard thống kê phân bố loài theo địa bàn
- Export báo cáo PDF/Excel
- Tích hợp geolocation từ ảnh EXIF metadata

