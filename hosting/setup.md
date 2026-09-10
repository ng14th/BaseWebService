# 🌐 Hướng Dẫn Trỏ Domain Vào Server — Từ DNS đến Production

> Tài liệu này giải thích toàn bộ quá trình đưa một domain trỏ đến server của bạn,
> bao gồm cấu hình DNS, hai phương pháp triển khai (Cloudflare Tunnel và Public IP),
> các lớp bảo vệ bổ sung, và checklist debug hoàn chỉnh.

---

## 📋 Mục lục

1. [Tổng quan flow](#1-tổng-quan-flow)
2. [Cấu hình DNS — Nameserver và Record](#2-cấu-hình-dns--nameserver-và-record)
3. [Hướng 1 — Cloudflare Tunnel (Không cần IP tĩnh)](#3-hướng-1--cloudflare-tunnel-không-cần-ip-tĩnh)
4. [Hướng 2 — Public IP trực tiếp](#4-hướng-2--public-ip-trực-tiếp)
5. [Bảo vệ nhiều lớp](#5-bảo-vệ-nhiều-lớp)
6. [✅ Checklist Debug Hoàn Chỉnh](#6--checklist-debug-hoàn-chỉnh)

---

## 1. Tổng quan flow

```
                         ┌─────────────────┐
                         │   Người dùng    │
                         │  truy cập       │
                         │ lab14.io.vn     │
                         └────────┬────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   DNS Resolver       │
                       │  (Nhà mạng / 8.8.8.8)│
                       │                      │
                       │  Hỏi: lab14.io.vn    │
                       │  trỏ về đâu?         │
                       └──────────┬───────────┘
                                  │
                      ┌───────────┴───────────┐
                      │   Nameserver của bạn  │
                      │   (VD: Cloudflare NS) │
                      │   ns1.cloudflare.com  │
                      └──────────┬────────────┘
                                 │ Trả về DNS Record
                    ┌────────────┴──────────────────┐
                    │                               │
          ┌─────────▼──────────┐         ┌──────────▼──────────┐
          │  Hướng 1           │         │  Hướng 2            │
          │  CNAME →           │         │  A Record →         │
          │  Cloudflare Tunnel │         │  Public IP Server   │
          └─────────┬──────────┘         └──────────┬──────────┘
                    │                               │
          ┌─────────▼──────────┐         ┌──────────▼──────────┐
          │  Cloudflare Edge   │         │  Cloudflare Edge /  │
          │  (Lo SSL, DDoS)    │         │  Router / Firewall  │
          │  → cloudflared     │         │  (Mở Port 80/443)   │
          │    container       │         └──────────┬──────────┘
          └─────────┬──────────┘                    │
                    │                    ┌──────────▼──────────┐
                    │                    │  Nginx / Load       │
                    │                    │  Balancer (SSL)     │
                    │                    └──────────┬──────────┘
                    └──────────────┬────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   App Backend       │
                        │   FastAPI / Node /  │
                        │   bất kỳ service    │
                        └─────────────────────┘
```

---

## 2. Cấu hình DNS — Nameserver và Record

### 2.1. Nameserver (NS)

Nameserver là "sổ địa chỉ" của domain. Khi bạn mua domain tại Namecheap, GoDaddy, Inet.vn, v.v., nhà cung cấp đó sẽ mặc định dùng NS của họ. Để dùng Cloudflare làm DNS, bạn cần **chuyển NS về Cloudflare**:

**Các bước:**

1. Đăng ký domain tại nhà cung cấp (VD: Inet.vn).
2. Thêm domain vào Cloudflare Dashboard → Cloudflare cấp cho bạn 2 nameserver:

   ```text
   e.g., adam.ns.cloudflare.com
         mia.ns.cloudflare.com
   ```

3. Vào trang quản lý của nhà cung cấp domain → **Đổi NS** thành 2 địa chỉ trên.
4. Chờ DNS propagate (~5 phút đến 48 giờ tùy nhà cung cấp).

> **Lưu ý:** Nếu bạn KHÔNG muốn dùng Cloudflare NS mà vẫn muốn dùng Cloudflare Tunnel,
> bạn cần dùng **Cloudflare for SaaS** hoặc chuyển sang phương án Public IP.

---

### 2.2. Các loại DNS Record

| Type | Mục đích | Ví dụ giá trị | Ghi chú |
| -------- | ---------- | --------------- | --------- |
| **A** | Trỏ domain về **IPv4** của server | `103.56.207.100` | Phổ biến nhất cho server VPS |
| **AAAA** | Trỏ domain về **IPv6** của server | `2001:db8::1` | Khi server hỗ trợ IPv6 |
| **CNAME** | Tạo bí danh (alias) trỏ về một **hostname** khác | `lab14.io.vn → xxxx.cfargotunnel.com` | Không dùng cho root domain, dùng `www`, subdomain |
| **MX** | Trỏ về mail server | `mail.lab14.io.vn` | Dùng cho email |
| **TXT** | Lưu metadata (verify domain, SPF, DKIM...) | `v=spf1 include:...` | Không ảnh hưởng traffic |
| **NS** | Xác định nameserver của domain | `adam.ns.cloudflare.com` | Chỉ cấu hình tại nhà cung cấp domain |

#### Khi nào dùng A vs CNAME?

```text
A Record:    lab14.io.vn  →  103.56.207.100   ✅ Dùng cho root domain và subdomain
AAAA Record: lab14.io.vn  →  2001:db8::1      ✅ IPv6

CNAME:       www          →  lab14.io.vn      ✅ Subdomain trỏ về hostname khác
CNAME:       lab14.io.vn  →  (hostname)       ❌ KHÔNG dùng CNAME cho root domain
                                                   (vì root domain cần A/AAAA)
```

> **Ngoại lệ:** Cloudflare hỗ trợ **CNAME Flattening** (còn gọi là ALIAS record)
> cho phép CNAME trên root domain. Đây là cách Cloudflare Tunnel hoạt động.

---

## 3. Hướng 1 — Cloudflare Tunnel (Không cần IP tĩnh)

### 3.1. Mô hình

```
Internet
  │  HTTPS://lab14.io.vn
  ▼
Cloudflare Edge (SSL, DDoS Protection, IP ẩn)
  │  Forward request qua Cloudflare network
  ▼
cloudflared container (chạy trên máy bạn)
  │  Kết nối outbound tới Cloudflare qua port 443/7844
  ▼
Nginx (http://host.docker.internal:80)
  │
  ├── /tms/      → localhost:8888 (FastAPI TMS)
  └── /einvoice/ → localhost:8889 (FastAPI Einvoice)
```

### 3.2. Ưu điểm

| Ưu điểm | Giải thích |
| --------- | ----------- |
| **Không cần IP tĩnh** | Máy home server, mạng NAT, 4G đều chạy được |
| **Không cần mở port** | Không cần cấu hình router, firewall port 80/443 |
| **SSL tự động** | Cloudflare lo toàn bộ chứng chỉ |
| **Ẩn IP gốc** | Không ai biết IP thật của máy bạn |
| **DDoS Protection miễn phí** | Cloudflare filter ở tầng Edge |

### 3.3. Cấu hình DNS (CNAME record)

```text
Type:    CNAME
Name:    lab14.io.vn  (hoặc @ )
Target:  <tunnel-id>.cfargotunnel.com
Proxy:   ✅ Proxied (cam Cloudflare)
TTL:     Auto
```

> Cloudflare tự động tạo CNAME record khi bạn cấu hình route trong Zero Trust Dashboard.

### 3.4. Các bước setup Cloudflare Tunnel

**Bước 1: Tạo Tunnel**

1. Vào Cloudflare Zero Trust → **Networks → Tunnels → Create a tunnel**.
2. Chọn **Cloudflared** → Đặt tên tunnel (VD: `lab14-tunnel`) → **Save tunnel**.
3. Cloudflare cấp cho bạn một **tunnel token**.

**Bước 2: Chạy container cloudflared**

```yaml
# hosting/cloudflare/docker-compose.yml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared-staging
    restart: always
    env_file:
      - .env
    environment:
      - TUNNEL_TOKEN=${TOKEN_CF_TUNNEL}
    command: tunnel --no-autoupdate run --token ${TOKEN_CF_TUNNEL}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

```bash
# hosting/cloudflare/.env
TOKEN_CF_TUNNEL=eyJhIjoiNWI1MD...    # Token từ Cloudflare
```

**Bước 3: Cấu hình Route trong Cloudflare**

| Field | Giá trị |
|-------|---------|
| Hostname | `lab14.io.vn` |
| Service URL | `http://host.docker.internal:80` — KHÔNG phải `localhost` |

**Bước 4: Kiểm tra**

```bash
# Container cloudflared phải thấy log CONNECTED (không phải ERR)
docker logs cloudflared-staging --tail 5

# Kiểm tra từ máy bạn trước
curl http://localhost:80/tms/

# Sau đó test từ ngoài
curl https://lab14.io.vn/tms/
```

### 3.5. Lỗi thường gặp với Cloudflare Tunnel

| Lỗi | Nguyên nhân | Cách sửa |
| ----- | ------------- | --------- |
| `502 Bad Gateway` | Service URL dùng `localhost` | Đổi thành `http://host.docker.internal:80` |
| `ERR connection refused` | Container thiếu `extra_hosts` | Thêm `extra_hosts: - "host.docker.internal:host-gateway"` |
| `ERR timeout` | App backend chưa chạy | Kiểm tra app đang lắng nghe đúng port |
| `ERR certificate` | Tunnel token sai/hết hạn | Tạo lại token trên Cloudflare Dashboard |

---

## 4. Hướng 2 — Public IP trực tiếp

### 4.1. Mô hình

```
Internet
  │  HTTPS://lab14.io.vn
  ▼
DNS Lookup:  A Record  →  103.56.207.100  (IP server thật)
  │
  ▼
Cloudflare Edge (nếu dùng Proxy ✅)  HOẶC  Trực tiếp server (nếu DNS Only)
  │  Port 80/443 được forward từ Router/Firewall
  ▼
Nginx (chạy trên server)
  │  Có chứng chỉ SSL (Let's Encrypt hoặc Cloudflare Origin Cert)
  ├── /tms/      → localhost:8888
  └── /einvoice/ → localhost:8889
```

### 4.2. Cấu hình DNS (A record)

```text
Type:    A
Name:    lab14.io.vn  (hoặc @ )
IPv4:    103.56.207.100   (IP tĩnh của server)
Proxy:   ✅ Proxied (nếu muốn dùng Cloudflare CDN/DDoS)
         hoặc
         ☁️ DNS Only (nếu muốn traffic đi thẳng vào server)
TTL:     Auto (nếu Proxied) hoặc 300s (nếu DNS Only)
```

```text
# Nếu server hỗ trợ IPv6, thêm thêm AAAA record
Type:    AAAA
Name:    lab14.io.vn
IPv6:    2001:db8::1
Proxy:   ✅ Proxied
```

### 4.3. Proxy ✅ vs DNS Only ☁️

| | Proxy ✅ (Cam Cloudflare) | DNS Only ☁️ |
| -- | -------------------------- | ------------- |
| **IP hiển thị** | IP của Cloudflare Edge | IP thật của server bạn |
| **SSL** | Cloudflare lo / Flexible/Full | Bạn phải tự cấu hình (Let's Encrypt) |
| **DDoS Protection** | ✅ Có | ❌ Không |
| **CDN/Cache** | ✅ Có | ❌ Không |
| **WebSocket** | Cần cấu hình thêm | ✅ Tự nhiên |
| **Port** | Chỉ 80, 443 (mặc định) | Bất kỳ port |

### 4.4. Cấu hình Nginx với SSL (Let's Encrypt)

```nginx
server {
    listen 80;
    server_name lab14.io.vn;

    # Dùng cho ACME challenge (certbot verify domain)
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect toàn bộ HTTP → HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name lab14.io.vn;

    ssl_certificate     /etc/letsencrypt/live/lab14.io.vn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lab14.io.vn/privkey.pem;

    location /tms/ {
        proxy_pass http://localhost:8888/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Cấp chứng chỉ SSL bằng certbot
certbot --nginx -d lab14.io.vn --email admin@lab14.io.vn --agree-tos --no-eff-email
```

### 4.5. Cấu hình với Cloudflare Origin Certificate

Khi bạn bật Proxy ✅, Cloudflare cung cấp **Origin Certificate** miễn phí (15 năm):

1. Cloudflare Dashboard → **SSL/TLS → Origin Server → Create Certificate**.
2. Download `cert.pem` và `key.pem` về server.
3. Cấu hình Nginx dùng cert đó.
4. Đặt SSL Mode về **Full (Strict)** trong Cloudflare.

> Lưu ý: Cloudflare Origin Certificate chỉ hoạt động khi traffic đi qua Cloudflare Proxy.
> Browser trực tiếp gọi IP server sẽ không tin cert này.

---

## 5. Bảo vệ nhiều lớp

### 5.1. Kiến trúc nhiều lớp bảo vệ

```
Tầng 1: Cloudflare Edge
├── DDoS Protection (băng thông lên đến 327 Tbps)
├── WAF (Web Application Firewall) — block SQL injection, XSS...
├── Rate Limiting — giới hạn request theo IP
├── Bot Management — lọc bot xấu
└── Geo-blocking — chặn quốc gia cụ thể

Tầng 2: Cloudflare Tunnel / Firewall Server
├── Tunnel: Không mở port ra internet — kẻ tấn công không tìm được IP
└── Public IP: Chỉ cho phép traffic từ IP Cloudflare đến server
               (Cloudflare công bố IP ranges: https://www.cloudflare.com/ips/)

Tầng 3: Nginx (Reverse Proxy)
├── Chỉ expose port 80 (Tunnel mode) hoặc 80+443 (Public IP mode)
├── Header security (HSTS, X-Frame-Options, CSP...)
├── Rate limit tại Nginx (limit_req_zone)
└── Block user-agent xấu

Tầng 4: Application (FastAPI)
├── JWT Authentication
├── Permission-based Authorization
├── Input Validation (Pydantic)
└── Audit Logging
```

### 5.2. Cấu hình Security Headers trong Nginx

```nginx
server {
    # Ẩn phiên bản Nginx
    server_tokens off;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'self';" always;

    # Rate limiting — 100 req/phút mỗi IP
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;

    location /tms/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://host.docker.internal:8888/;
    }
}
```

### 5.3. Chỉ cho phép IP Cloudflare vào server (khi dùng Public IP)

```bash
# Whitelist IP Cloudflare vào UFW (cập nhật tự động)
for ip in $(curl -s https://www.cloudflare.com/ips-v4); do
    ufw allow from $ip to any port 80,443 proto tcp
done
ufw default deny incoming
```

### 5.4. Cloudflare Access (Zero Trust Authentication)

Dùng khi bạn muốn chỉ cho phép người dùng đã xác thực (Google SSO, GitHub, OTP...) truy cập vào route cụ thể:

1. Zero Trust → **Access → Applications → Add an Application**.
2. Chọn loại ứng dụng và domain.
3. Thêm **Policy** (VD: email phải thuộc `@yourcompany.com`).
4. Cloudflare sẽ yêu cầu login trước khi cho phép vào app.

---

## 6. ✅ Checklist Debug Hoàn Chỉnh

Khi setup domain bị lỗi, đi theo thứ tự từ trên xuống dưới để khoanh vùng vấn đề:

### Bước 1: Kiểm tra DNS đã propagate chưa

```bash
# Xem domain đang trỏ về đâu
dig lab14.io.vn A
nslookup lab14.io.vn

# Tool online: https://dnschecker.org hoặc https://whatsmydns.net
```

| Kết quả | Ý nghĩa |
| --------- | --------- |
| IP Cloudflare (104.21.x.x / 172.67.x.x) | Đang dùng Cloudflare Proxy — DNS OK |
| IP server thật | DNS Only — DNS OK |
| NXDOMAIN | Domain không tồn tại hoặc NS chưa cập nhật |
| Timeout | NS chưa propagate, chờ thêm |

---

### Bước 2: Kiểm tra NS đã đúng chưa

```bash
dig NS lab14.io.vn
whois lab14.io.vn | grep -i nameserver
```

- ✅ Kết quả phải là `*.ns.cloudflare.com` nếu bạn dùng Cloudflare NS.
- ❌ Nếu vẫn là NS của nhà cung cấp → Chưa đổi NS hoặc chưa propagate.

---

### Bước 3: Kiểm tra SSL/TLS

```bash
# Kiểm tra chứng chỉ SSL
curl -vk https://lab14.io.vn 2>&1 | grep -E "SSL|certificate|issuer"

# Kiểm tra SSL expiry
echo | openssl s_client -connect lab14.io.vn:443 2>/dev/null | \
  openssl x509 -noout -dates
```

| Kết quả | Ý nghĩa |
| --------- | --------- |
| `issuer: Let's Encrypt` | Cert từ Certbot — OK |
| `issuer: Cloudflare` | Cert từ Cloudflare — OK |
| `certificate verify failed` | Cert hết hạn, sai domain, hoặc self-signed |
| `SSL_ERROR_RX_RECORD_TOO_LONG` | Port 443 đang trả HTML thay vì SSL |

---

### Bước 4: Kiểm tra Cloudflare Tunnel (nếu dùng Tunnel)

```bash
# Xem container đang chạy không
docker ps | grep cloudflared

# Xem log — phải thấy "Connected" không phải "ERR"
docker logs cloudflared-staging --tail 20

# Dấu hiệu hoạt động đúng:
# INF Connection ... registered connIndex=0
# INF Registered tunnel connection ...
```

**Kiểm tra Service URL trong Cloudflare Zero Trust:**

| Service URL | Kết quả |
|-------------|---------|
| `http://host.docker.internal:80` | ✅ Đúng — kết nối được vào Nginx |
| `http://localhost:80` | ❌ Sai — localhost trong container là chính nó |
| `http://127.0.0.1:80` | ❌ Sai — tương tự localhost |

---

### Bước 5: Kiểm tra Nginx

```bash
# Kiểm tra Nginx đang chạy
docker ps | grep nginx

# Test cú pháp config
docker compose exec nginx nginx -t

# Xem log error của Nginx
docker compose logs nginx | tail -20

# Test trực tiếp từ máy (bypass Cloudflare)
curl -i http://localhost:80/
curl -i http://localhost:80/tms/

# Test với header Host giả lập domain
curl -i -H "Host: lab14.io.vn" http://localhost:80/tms/
```

---

### Bước 6: Kiểm tra App Backend

```bash
# Test app trực tiếp không qua Nginx
curl -i http://localhost:8888/
curl -i http://localhost:8889/

# Xem log app
docker logs onflow-tms-api --tail 20
```

---

### Bước 7: Kiểm tra network nội bộ Docker

```bash
# Kiểm tra extra_hosts đã cấu hình
docker inspect cloudflared-staging --format '{{.HostConfig.ExtraHosts}}'
# Phải thấy: [host.docker.internal:host-gateway]

# Từ container cloudflared, test kết nối đến Nginx
docker exec cloudflared-staging wget -qO- http://host.docker.internal:80/ 2>&1
```

---

### Bước 8: Test end-to-end qua Cloudflare

```bash
# Test từ ngoài internet (qua Cloudflare proxy)
curl -vk https://lab14.io.vn/

# Bypass Cloudflare cache
curl -vk -H "Cache-Control: no-cache" https://lab14.io.vn/tms/

# Xem header Cloudflare để xác nhận đi qua proxy
curl -sI https://lab14.io.vn/ | grep -i "cf-ray\|server\|cf-cache"
```

---

### Bảng tra cứu lỗi nhanh

| Triệu chứng | Nguyên nhân có thể | Kiểm tra |
| ------------- | ------------------- | --------- |
| `502 Bad Gateway` | Service URL sai, Nginx không chạy | Bước 4, 5 |
| `521 Web server is down` | Server không nhận kết nối từ Cloudflare IP | Bước 5, mở port |
| `522 Connection timed out` | Server nhận TCP nhưng không phản hồi | App bị treo — Bước 6 |
| `523 Origin is unreachable` | DNS sai, server down | Bước 1, 2 |
| `524 A timeout occurred` | App chạy quá chậm (>100s) | Tối ưu app hoặc tăng timeout Nginx |
| `404 Not Found` | Route không match trong Nginx | Kiểm tra `location` trong nginx.conf, dấu `/` cuối |
| `SSL_ERROR` | Cert hết hạn hoặc sai SSL Mode Cloudflare | Bước 3 |
| `ERR_TOO_MANY_REDIRECTS` | Nginx redirect HTTP→HTTPS + Cloudflare cũng redirect | Đặt SSL Mode = Full (Strict) |
| `Connection refused` | App chưa chạy hoặc sai port | Bước 6 |

---

## Tóm tắt so sánh 2 hướng

| Tiêu chí | Cloudflare Tunnel | Public IP |
| ---------- | ------------------ | ----------- |
| **IP tĩnh** | Không cần | Bắt buộc |
| **Mở port router** | Không cần | Cần mở 80, 443 |
| **SSL** | Cloudflare tự lo | Cần cấu hình (Certbot hoặc Cloudflare Origin Cert) |
| **Ẩn IP server** | Hoàn toàn | Chỉ khi bật Proxy ✅ |
| **Phù hợp** | Home server, mạng NAT, laptop | VPS/Cloud server có IP tĩnh |
| **Độ phức tạp** | Thấp | Trung bình |
| **WebSocket** | Hỗ trợ | Hỗ trợ |
| **Chi phí** | Miễn phí (gói Free) | Phụ thuộc nhà cung cấp VPS |

---

*Tài liệu được tạo vào 2026-09-10 — Project: webapp_FastAPI/hosting*
