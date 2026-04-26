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

**Trạng thái hiện tại (triển khai VPS)**:

- Ưu tiên **tải dữ liệu thủ công** vào `data/raw/<dataset>/...` (vì nhiều nguồn cần token/quyền truy cập và VPS chỉ chạy production).
- Admin → **Dữ liệu** có mục **Auto-scan** để tự nhận biết dữ liệu đã có trong thư mục.
- Nếu cần tải nhanh MosquitoDL (public): Admin → **Dữ liệu** → **Download** (worker sẽ `git clone` về `data/raw/mosquitodl`).

> `ml/scripts/01_download_data.py` có thể dùng để tải MosquitoDL nhanh (offline/local). Trên VPS khuyến nghị thao tác qua Admin để theo dõi tiến trình.

### 2.3 Script tiền xử lý (`ml/scripts/02_preprocess.py`)

**Trạng thái hiện tại (triển khai VPS)**:

- Admin → **Dữ liệu** → **Preprocess** sẽ chuẩn hóa/split từ `data/raw/...` sang `data/processed/...` và có progress + events.
- Hệ thống tự quét dữ liệu qua API `GET /api/admin/data/status` để UI hiển thị “đã có dữ liệu hay chưa”.
- Code thực thi nằm ở `backend/app/worker/jobs_data.py` (và scan ở `backend/app/services/data_scan.py`).

> `ml/scripts/02_preprocess.py` có thể dùng để preprocess offline/local. Trên VPS khuyến nghị thao tác qua Admin để theo dõi tiến trình.

---

## 3. Giai đoạn 2 — Training Model

**Trạng thái hiện tại (triển khai VPS, CPU-only)**:

- Training chạy dưới dạng **job nền** trong `worker` (RQ/Redis) và theo dõi qua Admin → **Training** (progress + events + metrics).
- Training đã được nối sang **Ultralytics YOLO (classification)** và cập nhật progress/metrics vào DB để Admin UI hiển thị.
- Augmentation đã có form trong Admin → **Training** và được lưu vào `training_runs.params_json.augmentation` để dùng trực tiếp khi nối YOLO.

> `ml/scripts/03_train.py`, `ml/scripts/04_evaluate.py`, `ml/scripts/05_export.py` có thể dùng để chạy offline/local. Trên VPS nên chạy qua Admin để có progress/events.

---

## 4. Giai đoạn 3 — FastAPI Backend

- Backend chạy trong container, cấu hình qua `.env` + `docker-compose.yml`.
- API chính (hiện tại):
  - `POST /api/predict` (YOLO classification; trả về top-1 label + confidence)
  - `POST /api/feedback` (nhận payload; TODO: lưu DB để retrain)
  - `GET /api/reports/health`
- Admin API (đã có): auth cookie + quản trị data/training/config/logs.

Các file quan trọng:

- `backend/app/main.py`
- `backend/app/routers/*`
- `backend/app/services/model_service.py` (YOLO inference)

---

## 5. Giai đoạn 4 — React Frontend

- Frontend build bằng Vite và chạy trong container; khi triển khai thật thì dùng Nginx host reverse proxy.
- Trang chính: upload ảnh → gọi `POST /api/predict` và hiển thị kết quả.
- Admin:
  - `/admin/login`
  - `/admin` (Dashboard: **Tổng quan / Dữ liệu / Training / Cấu hình / Logs**)

Các file quan trọng:

- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/AdminLogin.jsx`
- `frontend/src/pages/AdminPanel.jsx`
- `frontend/src/api.js`

## 6. Giai đoạn 5 — Triển khai

> **Yêu cầu**: toàn bộ hệ thống chạy trên **VPS**; VPS có **Docker**. Phần training/retrain chạy như job nền (worker) để web có thể theo dõi tiến độ.

### 6.1 Yêu cầu trên VPS

- Docker Engine + Docker Compose plugin (`docker compose`)
- (Tuỳ chọn) GPU NVIDIA cho training: NVIDIA driver + `nvidia-container-toolkit`
- VPS đã có Nginx (host) để reverse proxy (không dùng Nginx container)

### 6.2 `docker-compose.yml` (chạy trên VPS)

> Lưu ý: chỉ publish `backend` và `frontend` ra **loopback** (`127.0.0.1`) để **host Nginx** proxy vào.

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
    image: ghcr.io/truongnt/mosquito-detection-backend:main
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
    ports:
      - "127.0.0.1:${BACKEND_PORT:-8000}:8000"
    restart: unless-stopped

  # Worker xử lý job dài (training/retrain/export) và cập nhật progress để UI quản trị theo dõi.
  # Bật bằng: `docker compose --profile train up -d`.
  worker:
    image: ghcr.io/truongnt/mosquito-detection-backend:main
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
    image: ghcr.io/truongnt/mosquito-detection-frontend:main
    depends_on:
      - backend
    ports:
      - "127.0.0.1:${FRONTEND_PORT:-3000}:80"
    restart: unless-stopped

  # Auto update containers when GHCR image :main changes
  watchtower:
    image: containrrr/watchtower:1.7.1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval ${WATCHTOWER_INTERVAL:-30} --cleanup --label-enable
    restart: unless-stopped
    profiles: ["autodeploy"]

volumes:
  db_data:
  app_logs:
```

### 6.3 Triển khai trên VPS (gợi ý)

```bash
# 1) Clone code + cấu hình biến môi trường
cp .env.example .env

# 2) Chạy services (host Nginx proxy vào các port loopback)
docker compose pull
docker compose up -d

# 3) (Tuỳ chọn) bật worker training/retrain
docker compose --profile train up -d
```

### 6.3.1 Auto deploy (GHCR + Watchtower)

> Luồng: `git push` → GitHub Actions build & push image lên GHCR → Watchtower trên VPS tự pull image mới và restart container.

1) Trên GitHub repo, chờ workflow `Build & Push Images (GHCR)` chạy xong.
2) Trên VPS, enable Watchtower:

```bash
docker compose --profile autodeploy up -d
```

Nếu image/package ở GHCR là private, cần login trên VPS một lần (PAT có `read:packages`):

```bash
docker login ghcr.io
```

### 6.4 Nginx trên host (gợi ý)

Ví dụ server block (proxy `/api` vào backend và `/` vào frontend) đã có sẵn tại `infra/nginx/host/mosquito-detection.conf`.

Copy vào `sites-available` và enable:

```bash
sudo cp infra/nginx/host/mosquito-detection.conf /etc/nginx/sites-available/ai.ci-pilot.asia
sudo ln -sf /etc/nginx/sites-available/ai.ci-pilot.asia /etc/nginx/sites-enabled/ai.ci-pilot.asia
sudo nginx -t && sudo systemctl reload nginx
```

Nội dung mẫu:

```nginx
server {
  listen 80;
  server_name _;

  client_max_body_size 25m;

  location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
  }
}
```

### 6.4 Giới hạn tài nguyên (khuyến nghị nếu VPS chạy nhiều dịch vụ)

- Chỉnh trong `.env` các biến như `BACKEND_CPUS`, `BACKEND_MEM`, `WORKER_CPUS`, `WORKER_MEM`, `DB_MEM`...
- Log container đã bật rotate qua `LOG_MAX_SIZE` / `LOG_MAX_FILE` để tránh đầy ổ đĩa.
- Đặt `CONTAINER_PREFIX` để tất cả container có cùng prefix và tránh trùng tên với service khác trên VPS.

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

### 7.6 Augmentation (khuyến nghị)

- Augmentation là các biến đổi ảnh **trong lúc train** để tăng khả năng tổng quát hóa (không “làm bẩn” dữ liệu gốc).
- Với mục tiêu nhận diện muỗi (ảnh chụp/đặt bẫy), nên bắt đầu từ cấu hình “vừa phải”:
  - `fliplr`: `0.5` (lật ngang thường an toàn)
  - `flipud`: `0.0` (lật dọc dễ làm ảnh “phi tự nhiên”, chỉ bật khi dữ liệu có đủ góc chụp)
  - `degrees`: `10`, `translate`: `0.1`, `scale`: `0.5`, `shear`: `2`
  - `hsv_h`: `0.015`, `hsv_s`: `0.7`, `hsv_v`: `0.4`
  - `mosaic`: `0.8`, `mixup`: `0.0` (bật `mixup` sau khi pipeline ổn định)
- Các tham số trên đã được đưa vào form **Admin → Training → Augmentation** và sẽ được dùng trực tiếp khi nối sang training YOLO thật.

---

## 9. Multi-model inference (so sánh nhiều model)

Hệ thống hỗ trợ chọn **1 hoặc nhiều model** để chạy dự đoán và hiển thị kết quả theo từng model.

- Public API:
  - `GET /api/models` danh sách model đang bật (enabled)
  - `POST /api/predict_multi` upload nhiều ảnh + chọn nhiều model (FormData: `images` + `models`)
- Frontend (trang `/`) hỗ trợ:
  - Upload **nhiều ảnh** (multi-select)
  - Chọn **nhiều model** để so sánh

### 9.1 Bật thêm model qua Admin Config

Trong Admin → **Cấu hình** bạn có thể set key `models` với cấu trúc:

```json
{
  "enabled": ["yolo"],
  "registry": {
    "vectech_xception": {
      "name": "VecTech Xception (paper)",
      "type": "vectech_xception",
      "noncommercial_only": true,
      "license": "CC BY-NC 4.0",
      "weights_path": "/app/models/external/vectech/<path_to_weights>.pth",
      "imsize": 299,
      "labels": ["class0", "class1"]
    }
  }
}
```

> Lưu ý: model `vectech_xception` là adapter tối thiểu để chạy `.pth` Xception. Bạn phải cung cấp đúng `weights_path` và `labels` khớp với weights.

### 9.2 Tải weights VecTech (tuỳ chọn)

Repo tham khảo: `vectech-dev/novel-species-detection` (license **NonCommercial**).

Có thể chạy script:

```bash
python scripts/download_vectech_model.py
```

Script sẽ tải `CNN_model_files.zip` (nếu truy cập được) và liệt kê các file `.pth` để bạn chọn `weights_path`.

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


