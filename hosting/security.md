# 🛡️ Security Plan — Bảo Vệ Nginx qua Cloudflare Tunnel

## Bối cảnh & Rủi ro hiện tại

### Kiến trúc hiện tại
```
Internet
    │
    ▼ HTTPS
Cloudflare Edge  ← Đang có: CDN, DDoS cơ bản, SSL
    │
    ▼ (Cloudflare Tunnel)
cloudflared container
    │
    ▼ http://host.docker.internal:80
Nginx (port 80 nội bộ)
    ├── /tms/      → FastAPI :8888
    └── /einvoice/ → FastAPI :8889
                         │
                     PostgreSQL
```

### Rủi ro hiện tại

| Rủi ro | Mức độ | Hiện trạng |
|--------|--------|------------|
| Bot scanning / brute force | 🔴 Cao | Chưa có rate limit |
| SQL Injection / XSS | 🔴 Cao | Không có WAF rules |
| DNS Spoofing / Cache Poisoning | 🟡 Trung bình | DNSSEC chưa bật |
| Lộ thông tin server (version, headers) | 🟡 Trung bình | Nginx chưa ẩn headers |
| DDoS Layer 7 (HTTP Flood) | 🟡 Trung bình | Chỉ có DDoS L3/L4 free |
| Truy cập không xác thực vào admin routes | 🔴 Cao | Chưa có auth layer |
| Dependency vulnerabilities | 🟡 Trung bình | Không có monitoring |

---

## Kiến trúc mục tiêu (sau khi bảo mật)

```
Internet
    │
    ▼ HTTPS
┌─────────────────────────────────────────────┐
│  Cloudflare Edge                            │
│                                             │
│  Tầng 1: DNSSEC                             │
│    └─ Bảo vệ DNS record khỏi bị giả mạo    │
│                                             │
│  Tầng 2: WAF (Managed + Custom Rules)       │
│    └─ Block SQLi, XSS, LFI, RCE...         │
│    └─ Block bad bots, scanners             │
│                                             │
│  Tầng 3: Rate Limiting                      │
│    └─ Giới hạn req/IP theo route           │
│                                             │
│  Tầng 4: Cloudflare Access (Zero Trust)     │
│    └─ SSO / OTP cho admin routes           │
└────────────────┬────────────────────────────┘
                 │ Cloudflare Tunnel (outbound only)
                 ▼
┌─────────────────────────────────────────────┐
│  cloudflared container                      │
│    └─ Nhận request từ Cloudflare            │
│    └─ extra_hosts: host.docker.internal     │
└────────────────┬────────────────────────────┘
                 │ http://host.docker.internal:80
                 ▼
┌─────────────────────────────────────────────┐
│  Nginx (Tầng 5)                             │
│    └─ server_tokens off                     │
│    └─ Security Headers (HSTS, CSP...)       │
│    └─ Rate limit per location               │
│    └─ Block suspicious User-Agents          │
│    └─ Validate CF-Connecting-IP header      │
└──────────┬──────────────┬───────────────────┘
           │              │
           ▼              ▼
┌──────────────┐  ┌───────────────┐
│  FastAPI     │  │  FastAPI      │
│  TMS :8888   │  │  Einvoice     │
│  (Tầng 6)    │  │  :8889        │
│  JWT Auth    │  │  JWT Auth     │
│  Pydantic    │  │  Pydantic     │
└──────┬───────┘  └───────────────┘
       │
       ▼
┌──────────────┐
│  PostgreSQL  │
│  (private)   │
└──────────────┘
```

---

## Chi tiết từng tầng bảo mật

---

### Tầng 1 — DNSSEC

**DNSSEC là gì?**
DNSSEC (DNS Security Extensions) ký số (digital signature) lên DNS record. Khi DNS resolver nhận record, nó xác minh chữ ký → Không ai có thể giả mạo DNS record để chuyển hướng traffic của bạn sang server khác (DNS Spoofing/Cache Poisoning).

**Cách bật DNSSEC trên Cloudflare:**

> Cloudflare → Domain của bạn → **DNS → Settings → DNSSEC → Enable DNSSEC**

Sau khi bật, Cloudflare sẽ cấp cho bạn một **DS Record** cần thêm vào nhà cung cấp domain:

```text
Type:       DS
Key Tag:    12345
Algorithm:  13 (ECDSAP256SHA256)
Digest Type: 2 (SHA-256)
Digest:     ABCDEF1234567890...
```

Vào nhà cung cấp domain (Inet.vn, Namecheap...) → Tìm mục **DNSSEC** → Thêm DS Record trên.

**Xác minh DNSSEC đã hoạt động:**
```bash
# Kết quả phải có "ad" flag (Authenticated Data)
dig lab14.io.vn +dnssec

# Dùng tool online
# https://dnssec-analyzer.verisignlabs.com
# https://dnsviz.net
```

---

### Tầng 2 — Cloudflare WAF (Web Application Firewall)

#### 2.1. Bật Cloudflare Managed Rules (Free tier)

> Cloudflare → **Security → WAF → Managed Rules**

Các ruleset quan trọng cần bật:

| Ruleset | Mô tả | Hành động |
|---------|-------|----------|
| **Cloudflare Managed Ruleset** | Block SQLi, XSS, LFI, Path Traversal... | Block |
| **Cloudflare OWASP Core Ruleset** | Tuân theo chuẩn OWASP Top 10 | Block |
| **Cloudflare Leaked Credentials** | Phát hiện password bị leak | Block |

> ⚠️ **Free plan** có giới hạn WAF rules. Managed Ruleset đầy đủ cần **Pro plan ($20/tháng)**.
> Free plan vẫn có **WAF cơ bản** nhưng hạn chế số lượng custom rules.

#### 2.2. Custom WAF Rules — Bảo vệ theo route

> Cloudflare → **Security → WAF → Custom Rules → Create rule**

**Rule 1: Block scanner và bad bots**
```text
Rule Name: Block Scanners & Bad Bots
Expression:
  (http.user_agent contains "sqlmap") or
  (http.user_agent contains "nikto") or
  (http.user_agent contains "nmap") or
  (http.user_agent contains "masscan") or
  (http.user_agent contains "zgrab") or
  (http.user_agent contains "python-requests") or
  (http.user_agent eq "")

Action: Block
```

**Rule 2: Giới hạn method HTTP**
```text
Rule Name: Allow only GET/POST/PUT/DELETE/PATCH
Expression:
  not (http.request.method in {"GET" "POST" "PUT" "DELETE" "PATCH" "OPTIONS"})

Action: Block
```

**Rule 3: Bảo vệ API route — chỉ nhận request có Content-Type hợp lệ**
```text
Rule Name: API Content-Type Validation
Expression:
  (http.request.uri.path contains "/tms/") and
  (http.request.method eq "POST") and
  not (http.request.headers["content-type"][*] contains "application/json")

Action: Block
```

**Rule 4: Block các path nguy hiểm**
```text
Rule Name: Block Sensitive Paths
Expression:
  (http.request.uri.path contains "/.env") or
  (http.request.uri.path contains "/.git") or
  (http.request.uri.path contains "/wp-admin") or
  (http.request.uri.path contains "/phpmyadmin") or
  (http.request.uri.path contains "/admin/config") or
  (http.request.uri.path contains "/../") or
  (http.request.uri.path contains "/.well-known/acme-challenge" and
   http.request.method ne "GET")

Action: Block
```

**Rule 5: Geo-restriction (tùy chọn — nếu chỉ phục vụ Việt Nam)**
```text
Rule Name: Geo Block
Expression:
  not (ip.geoip.country in {"VN" "SG" "US"})

Action: Managed Challenge (CAPTCHA)
```

---

### Tầng 3 — Cloudflare Rate Limiting

> Cloudflare → **Security → WAF → Rate limiting rules → Create rule**

> ⚠️ Rate Limiting cơ bản có trong Free plan (10 rules). Advanced cần Pro plan.

**Rule 1: Rate limit toàn bộ API**
```text
Rule Name: API Rate Limit — Global
Traffic matching: URI Path contains /tms/ OR /einvoice/
Rate: 100 requests per 1 minute per IP
Action: Block (duration: 10 minutes)
```

**Rule 2: Rate limit login / auth endpoint**
```text
Rule Name: Auth Rate Limit
Traffic matching: URI Path contains /auth/ OR /login
Rate: 10 requests per 1 minute per IP
Action: Block (duration: 30 minutes)
```

**Rule 3: Slow-down repeated 4xx errors**
```text
Rule Name: Error Rate Limit
Traffic matching: HTTP response code equals 401 OR 403
Rate: 20 responses per 1 minute per IP
Action: Managed Challenge
```

---

### Tầng 4 — Cloudflare Access (Zero Trust)

Dùng để bảo vệ các route nhạy cảm (Admin panel, Internal API, Docs...) bằng cách yêu cầu xác thực SSO trước khi Nginx nhận request.

> Zero Trust → **Access → Applications → Add an Application → Self-hosted**

**Ví dụ bảo vệ `/tms/docs` (FastAPI Swagger):**

```text
Application Name: TMS Swagger Docs
Subdomain: lab14.io.vn
Path: /tms/docs*

Policy:
  Name: Onflow Team Only
  Action: Allow
  Require:
    - Emails ending in: @yourcompany.com
    OR
    - Email is: trusted_user@gmail.com

Session duration: 8 hours
```

Khi truy cập `https://lab14.io.vn/tms/docs`, Cloudflare sẽ redirect sang trang login Google/OTP trước → Sau khi xác thực mới forward request về Nginx.

---

### Tầng 5 — Nginx Hardening

Cập nhật file [conf.d/default.conf](file:///Users/mac-dev05/project/onflow/webapp_FastAPI/hosting/nginx/conf.d/default.conf):

```nginx
events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    # ─── Ẩn thông tin Nginx ───────────────────────────────────────
    server_tokens off;

    # ─── Rate Limiting zones ──────────────────────────────────────
    # (Dự phòng thêm lớp sau Cloudflare)
    limit_req_zone $http_cf_connecting_ip zone=api_zone:10m rate=100r/m;
    limit_req_zone $http_cf_connecting_ip zone=auth_zone:10m rate=10r/m;

    # ─── Log format có CF-Ray và real IP ──────────────────────────
    log_format cf_log '$http_cf_connecting_ip - $remote_addr [$time_local] '
                      '"$request" $status $body_bytes_sent '
                      '"$http_referer" "$http_user_agent" '
                      'cf-ray="$http_cf_ray"';
    access_log /var/log/nginx/access.log cf_log;

    sendfile on;
    keepalive_timeout 60;

    # ─── Block request không có Host header ───────────────────────
    server {
        listen 80 default_server;
        server_name _;
        return 444;   # Nginx drop connection (không trả HTTP response)
    }

    server {
        listen 80;
        server_name lab14.io.vn nginx-lab14.cloudflared.dev localhost;

        # ─── Security Headers ─────────────────────────────────────
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        # Điều chỉnh CSP cho phù hợp với app của bạn
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

        # ─── Chỉ nhận request đến từ Cloudflare ──────────────────
        # Cloudflare sẽ gắn header CF-Connecting-IP và CF-Ray
        # Nếu header này trống → request không qua Cloudflare → chặn
        if ($http_cf_ray = "") {
            return 403;
        }

        # ─── Block bad User-Agents ────────────────────────────────
        if ($http_user_agent ~* (sqlmap|nikto|nmap|masscan|zgrab|python-requests)) {
            return 403;
        }

        # ─── Trang gốc: trả thông tin server ─────────────────────
        location = / {
            default_type application/json;
            return 200 '{\n  "service": "Onflow Gateway",\n  "status": "online"\n}\n';
        }

        # ─── /tms/ ────────────────────────────────────────────────
        location = /tms { return 301 /tms/; }

        location /tms/ {
            limit_req zone=api_zone burst=20 nodelay;

            proxy_pass http://host.docker.internal:8888/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            # Dùng IP thật của người dùng từ Cloudflare
            proxy_set_header X-Real-IP $http_cf_connecting_ip;
            proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Prefix /tms;

            # Timeout bảo vệ tránh slow-loris attack
            proxy_connect_timeout 10s;
            proxy_send_timeout    60s;
            proxy_read_timeout    60s;

            # Giới hạn kích thước request body (default: 1MB)
            client_max_body_size 10M;
        }

        # ─── /einvoice/ ───────────────────────────────────────────
        location = /einvoice { return 301 /einvoice/; }

        location /einvoice/ {
            limit_req zone=api_zone burst=20 nodelay;

            proxy_pass http://host.docker.internal:8889/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $http_cf_connecting_ip;
            proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Prefix /einvoice;

            proxy_connect_timeout 10s;
            proxy_send_timeout    60s;
            proxy_read_timeout    60s;
            client_max_body_size 10M;
        }

        # ─── Block các path nhạy cảm ─────────────────────────────
        location ~ /\. {
            deny all;  # Block .env, .git, .htaccess...
        }

        location ~* \.(sql|bak|log|conf|ini|sh|py)$ {
            deny all;
        }

        # ─── Custom error responses ───────────────────────────────
        location @custom_auth_401 {
            default_type application/json;
            return 401 '{"code":401,"message":"Unauthorized","error":true}';
        }

        location @custom_auth_403 {
            default_type application/json;
            return 403 '{"code":403,"message":"Access denied","error":true}';
        }

        error_page 401 = @custom_auth_401;
        error_page 403 = @custom_auth_403;
    }
}
```

---

### Tầng 6 — Cloudflare Security Settings

> Cloudflare → **Security → Settings**

| Setting | Giá trị khuyến nghị | Lý do |
|---------|---------------------|-------|
| **Security Level** | High | Block request từ IP có lịch sử tấn công |
| **Browser Integrity Check** | On | Phát hiện browser bất thường |
| **Challenge Passage** | 30 minutes | Sau khi pass CAPTCHA giữ 30 phút |
| **Privacy Pass Support** | On | Giảm CAPTCHA friction cho user bình thường |
| **Bot Fight Mode** | On (Free) | Block các bot cơ bản |

> Cloudflare → **SSL/TLS**

| Setting | Giá trị | Lý do |
|---------|---------|-------|
| **SSL Mode** | Full (Strict) | Tránh ERR_TOO_MANY_REDIRECTS |
| **Always Use HTTPS** | On | Auto redirect HTTP → HTTPS |
| **Min TLS Version** | TLS 1.2 | Không hỗ trợ TLS 1.0/1.1 cũ và yếu |
| **Opportunistic Encryption** | On | — |
| **TLS 1.3** | On | Protocol mới nhất, bảo mật cao nhất |
| **HSTS** | Enable (max-age=31536000) | Enforce HTTPS 1 năm |

---

## Kế hoạch triển khai

### Giai đoạn 1 — Ngay lập tức (15 phút)

- [ ] Bật **DNSSEC** trên Cloudflare + thêm DS Record vào nhà cung cấp domain
- [ ] Đặt **SSL Mode = Full (Strict)** trong Cloudflare
- [ ] Bật **Always Use HTTPS**
- [ ] Bật **Bot Fight Mode**
- [ ] Tăng **Security Level = High**

### Giai đoạn 2 — Hôm nay (1 giờ)

- [ ] Cập nhật `conf.d/default.conf` theo mẫu Tầng 5 ở trên
- [ ] Thêm WAF Custom Rules (4 rules) trong Cloudflare
- [ ] Thêm Rate Limiting Rules (3 rules) trong Cloudflare
- [ ] Test lại với `curl` và trình duyệt
- [ ] Kiểm tra Nginx log có ghi đúng IP thật không

### Giai đoạn 3 — Tuần tới (tùy ngân sách)

- [ ] Cân nhắc nâng **Cloudflare Pro ($20/tháng)** để có:
  - WAF Managed Ruleset đầy đủ (OWASP)
  - Advanced Rate Limiting
  - Analytics chi tiết hơn
- [ ] Cấu hình **Cloudflare Access** bảo vệ route `/tms/docs` và `/einvoice/docs`
- [ ] Thiết lập **Cloudflare Alerts** (email/webhook khi có spike request hoặc bị attack)

---

## Câu hỏi cần xác nhận trước khi triển khai

> [!IMPORTANT]
> **Kiểm tra nhà cung cấp domain có hỗ trợ DS Record không?**
> Một số nhà cung cấp domain Việt Nam (Inet.vn, PA Vietnam) chưa hỗ trợ nhập DS Record thủ công.
> Nếu không hỗ trợ → DNSSEC không bật được → bỏ qua tầng này.

> [!IMPORTANT]
> **Rule kiểm tra `CF-Ray` header có thể gây vấn đề khi test local không?**
> `if ($http_cf_ray = "") { return 403; }` sẽ block tất cả request không qua Cloudflare.
> Điều này có thể gây khó khi debug bằng `curl http://localhost/tms/`.
> Cân nhắc chỉ bật rule này trên môi trường production.

> [!NOTE]
> **Geo-blocking có cần thiết không?**
> Nếu app chỉ phục vụ user Việt Nam → nên bật để giảm đáng kể lượng bot scan từ nước ngoài.
