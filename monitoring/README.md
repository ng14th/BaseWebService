# Onflow Monitoring Stack

Stack giám sát infrastructure và services dựa trên **Prometheus + Grafana**.

## Kiến trúc

```
Nginx /monitor ──► Grafana :3000
                      │
                 Prometheus :9090
                      │
       ┌──────────────┼──────────────┐
  Node Exporter   cAdvisor    Blackbox Exporter
   (host metrics) (docker)  (probe :8888/:50010/:50020)
```

## Services & Ports

| Service            | Container Port | Host Port | Mô tả                          |
|--------------------|---------------|-----------|-------------------------------|
| Prometheus         | 9090          | 9090      | Time-series DB + scraper      |
| Grafana            | 3000          | 3000      | Dashboard visualization       |
| Node Exporter      | 9100          | 9100      | Host CPU/RAM/disk/network     |
| cAdvisor           | 8080          | 8081      | Docker container metrics      |
| Blackbox Exporter  | 9115          | 9115      | HTTP/TCP probe                |

## Khởi động

```bash
cd monitoring
docker compose up -d

# Kiểm tra status
docker compose ps
docker compose logs -f
```

## Truy cập

| URL | Mô tả |
|-----|--------|
| http://localhost/monitor | Grafana (qua nginx) |
| http://localhost:3000 | Grafana trực tiếp |
| http://localhost:9090 | Prometheus UI |
| http://localhost:9115 | Blackbox Exporter |

**Đăng nhập Grafana**: `admin` / `onflow2024`  
Dashboard tự động load: **Onflow – Service & Infrastructure Overview**

## Metrics được giám sát

### 🖥️ Host Resources
- CPU usage (per core + overall)
- RAM usage (used / total)
- Disk usage
- Network I/O (in/out)

### 🐳 Docker Containers
- Container CPU usage
- Container memory usage

### 🌐 Services (port 8888 / 50010 / 50020)
- **probe_success** – Service up/down status
- **probe_duration_seconds** – HTTP response time
- **probe_http_duration_seconds** – HTTP phase breakdown (connect, processing, transfer)
- **TCP connect** – Port open/closed check

## Cấu hình probe endpoints

Mặc định probe các path sau:
- `:8888/health` và `:8888/`
- `:50010/health` và `:50010/`
- `:50020/health` và `:50020/`

Nếu services dùng path khác, chỉnh sửa trong `prometheus/prometheus.yml` → targets.

## Tắt / Restart

```bash
docker compose down          # tắt, giữ data volumes
docker compose down -v       # tắt + xóa toàn bộ data
docker compose restart grafana  # restart riêng một service
```
