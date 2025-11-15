# Architecture Diagrams

## 1. Current Architecture (LAN Only - Before CGNAT Fix)

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOME NETWORK (192.168.1.0/24)            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Docker Host (192.168.1.100)                     │   │
│  │                                                          │   │
│  │   ┌──────────────┐       ┌──────────────────────────┐  │   │
│  │   │    Caddy     │       │    DNS Server (Python)   │  │   │
│  │   │              │       │                          │  │   │
│  │   │  Port 80     │──────▶│  Core:                   │  │   │
│  │   │  Port 443    │       │  - DNS Listener (53)     │  │   │
│  │   │  Port 853    │       │  - DoH Handler (8080)    │  │   │
│  │   │  Port 8081   │       │  - DoT Proxy (8053)      │  │   │
│  │   │              │       │  - Blacklist Manager     │  │   │
│  │   │  Modules:    │       │  - Forwarder             │  │   │
│  │   │  - DuckDNS   │       │                          │  │   │
│  │   │  - Layer4    │       │  API:                    │  │   │
│  │   │  - TLS       │       │  - FastAPI (8000)        │  │   │
│  │   └──────┬───────┘       │  - Dashboard             │  │   │
│  │          │               └────────┬─────────────────┘  │   │
│  │          │                        │                     │   │
│  │          │     ┌──────────────────▼──────────┐        │   │
│  │          └────▶│   SQLite Database           │        │   │
│  │                │   - Query logs              │        │   │
│  │                │   - Statistics              │        │   │
│  │                └─────────────────────────────┘        │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Client 1   │  │   Client 2   │  │   Client 3   │         │
│  │  (Laptop)    │  │  (Phone)     │  │  (Desktop)   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                  │                  │
└─────────┼─────────────────┼──────────────────┼──────────────────┘
          │                 │                  │
          └─────────────────┴──────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Router        │
                    │  192.168.1.1   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  ISP (CGNAT)   │ ❌ BLOCKED
                    │  No Port Fwd   │
                    └────────────────┘
                            ❌
                        INTERNET
                    (Cannot access)
```

**Problem:** CGNAT prevents external access. No port forwarding possible.

---

## 2. Solution A: Cloudflare Tunnel Architecture

```
                        ┌─────────────────────────────────┐
                        │    CLOUDFLARE NETWORK           │
                        │    (200+ data centers)          │
                        │                                  │
┌──────────────────────▶│  Edge Servers                   │
│                       │  - TLS Termination              │
│  ┌────────────────┐  │  - DDoS Protection              │
│  │  Client 1      │  │  - WAF                          │
│  │  (Anywhere)    │  │  - Rate Limiting                │
│  │                │  │  - Analytics                    │
│  │  Uses DoH:     │  └──────────┬──────────────────────┘
│  │  nt140firewall │             │ Cloudflare Tunnel
│  │  .duckdns.org  │             │ (Encrypted)
│  └────────────────┘             │
│                                  │
│  ┌────────────────┐             │
│  │  Client 2      │             │
│  │  (4G/5G)       │─────────────┘
│  └────────────────┘             │
│                                  │ Outbound only
│  ┌────────────────┐             │ (No port forward)
│  │  Client 3      │             │
│  │  (Public WiFi) │─────────────┘
│  └────────────────┘             
│                                  
│                          ┌───────▼───────────────────────────────┐
│                          │    HOME NETWORK                        │
│                          │    (Behind CGNAT)                      │
│                          │                                         │
│                          │  ┌────────────────────────────────┐   │
│                          │  │  Docker Network                 │   │
│                          │  │                                 │   │
│                          │  │  ┌──────────────┐              │   │
│                          │  │  │ Cloudflared  │              │   │
│                          │  │  │ Container    │              │   │
│                          │  │  │              │              │   │
│                          │  │  │ - Maintains  │              │   │
│                          │  │  │   tunnel     │              │   │
│                          │  │  │ - Auto       │              │   │
│                          │  │  │   reconnect  │              │   │
└──────────────────────────┼──┼──▶              │              │   │
                           │  │  └──────┬───────┘              │   │
                           │  │         │                       │   │
                           │  │  ┌──────▼───────┐  ┌────────────┐ │
                           │  │  │   Caddy      │  │ DNS Server │ │
                           │  │  │   Proxy      │─▶│  (Python)  │ │
                           │  │  └──────────────┘  └────────────┘ │
                           │  │                                    │
                           │  └────────────────────────────────────┘
                           │                                        │
                           │  ┌────────┐  ┌────────┐  ┌────────┐  │
                           │  │ LAN    │  │ LAN    │  │ LAN    │  │
                           │  │ Client │  │ Client │  │ Client │  │
                           │  │ (opt)  │  │ (opt)  │  │ (opt)  │  │
                           │  └────────┘  └────────┘  └────────┘  │
                           │    Can still use local DNS (Port 53)  │
                           └────────────────────────────────────────┘

```

**Benefits:**
- ✅ Free, unlimited bandwidth
- ✅ Global CDN (low latency)
- ✅ DDoS protection
- ✅ Automatic TLS
- ✅ Zero maintenance

---

## 3. Solution B: Tailscale Architecture

```
                    ┌────────────────────────────────────┐
                    │   Tailscale Control Plane          │
                    │   (Coordination only)              │
                    │   - Key exchange                   │
                    │   - NAT traversal help             │
                    └────────┬──────────────┬────────────┘
                             │              │
                             │              │
        ┌────────────────────▼──┐       ┌──▼───────────────────┐
        │  Client 1              │       │  Client 2            │
        │  (Phone - 4G/5G)       │       │  (Laptop - Coffee    │
        │                        │       │   Shop WiFi)         │
        │  Tailscale IP:         │       │                      │
        │  100.x.x.3             │       │  Tailscale IP:       │
        │                        │       │  100.x.x.4           │
        │  ┌──────────────────┐  │       │                      │
        │  │ Tailscale Client │  │       │  ┌────────────────┐  │
        │  │ (App/Daemon)     │  │       │  │ Tailscale      │  │
        │  └────────┬──────────┘  │       │  │ Client         │  │
        │           │             │       │  └────────┬───────┘  │
        └───────────┼─────────────┘       └───────────┼──────────┘
                    │                                 │
                    │  Encrypted WireGuard tunnel     │
                    │  (Direct P2P if possible)       │
                    │                                 │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼─────────────────────────────┐
                    │  HOME NETWORK (Behind CGNAT)             │
                    │                                           │
                    │  ┌────────────────────────────────────┐  │
                    │  │  Server (192.168.1.100)            │  │
                    │  │                                     │  │
                    │  │  Tailscale IP: 100.x.x.2           │  │
                    │  │                                     │  │
                    │  │  ┌──────────────────┐              │  │
                    │  │  │ Tailscale Daemon │              │  │
                    │  │  │                  │              │  │
                    │  │  │ - Subnet routing │              │  │
                    │  │  │   (192.168.1.0/  │              │  │
                    │  │  │    24)           │              │  │
                    │  │  │ - DNS forwarding │              │  │
                    │  │  └────────┬─────────┘              │  │
                    │  │           │                         │  │
                    │  │  ┌────────▼──────────────────────┐ │  │
                    │  │  │  Docker (DNS Firewall)        │ │  │
                    │  │  │  - Caddy                      │ │  │
                    │  │  │  - DNS Server                 │ │  │
                    │  │  └───────────────────────────────┘ │  │
                    │  │                                     │  │
                    │  └─────────────────────────────────────┘  │
                    │                                           │
                    └───────────────────────────────────────────┘
```

**Benefits:**
- ✅ Zero-trust security
- ✅ P2P when possible (low latency)
- ✅ No public exposure
- ✅ MagicDNS

---

## 4. Solution C: FRP with VPS Architecture

```
┌────────────────┐       ┌─────────────────────────────────────┐
│  Client 1      │       │         VPS (Public IP)              │
│  (Anywhere)    │       │         (e.g., Vultr/AWS)            │
│                │       │                                      │
│  Uses:         │──────▶│  ┌────────────────────────────────┐ │
│  nt140firewall │       │  │  FRP Server (frps)             │ │
│  .duckdns.org  │       │  │                                 │ │
└────────────────┘       │  │  Port mappings:                │ │
                         │  │  - 443 → tunnel                │ │
┌────────────────┐       │  │  - 853 → tunnel                │ │
│  Client 2      │──────▶│  │  - 7000 (control)              │ │
│  (4G/5G)       │       │  └──────────┬─────────────────────┘ │
└────────────────┘       │             │ FRP Tunnel            │
                         │             │ (Encrypted)           │
┌────────────────┐       └─────────────┼───────────────────────┘
│  Client 3      │                     │
│  (Public WiFi) │─────────────────────┘
└────────────────┘                     │
                                       │ Outbound only
                                       │ (No port forward needed)
                                       │
                          ┌────────────▼────────────────────────┐
                          │   HOME NETWORK (Behind CGNAT)       │
                          │                                      │
                          │  ┌──────────────────────────────┐   │
                          │  │  Docker Network               │   │
                          │  │                               │   │
                          │  │  ┌─────────────────┐         │   │
                          │  │  │ FRP Client      │         │   │
                          │  │  │ (frpc)          │         │   │
                          │  │  │                 │         │   │
                          │  │  │ - Connects to   │         │   │
                          │  │  │   VPS           │         │   │
                          │  │  │ - Maintains     │         │   │
                          │  │  │   tunnel        │         │   │
                          │  │  │ - Forwards to   │         │   │
                          │  │  │   Caddy         │         │   │
                          │  │  └────────┬────────┘         │   │
                          │  │           │                   │   │
                          │  │  ┌────────▼───────┐  ┌─────────┐│
                          │  │  │   Caddy        │  │  DNS    ││
                          │  │  │   Proxy        │─▶│ Server  ││
                          │  │  └────────────────┘  └─────────┘│
                          │  │                                  │
                          │  └──────────────────────────────────┘
                          │                                      │
                          └──────────────────────────────────────┘
```

**Benefits:**
- ✅ Full control
- ✅ Can host multiple services
- ✅ No third-party dependency

**Costs:**
- ⚠️ VPS: $3-5/month

---

## 5. Hybrid Solution Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    PUBLIC ACCESS PATH                         │
│                    (For DoH queries)                          │
│                                                               │
│  ┌────────────┐         ┌───────────────────────────┐       │
│  │ Public     │         │  Cloudflare Network        │       │
│  │ Clients    │────────▶│  - DoH Endpoint only       │       │
│  │ (Anywhere) │         │  - DDoS Protection         │       │
│  └────────────┘         │  - Global CDN              │       │
│                         └────────────┬───────────────┘       │
└──────────────────────────────────────┼───────────────────────┘
                                       │ Cloudflare Tunnel
                                       │ (HTTPS only)
                                       │
┌──────────────────────────────────────┼───────────────────────┐
│                    ADMIN ACCESS PATH  │                       │
│                    (For Dashboard)    │                       │
│                                       │                       │
│  ┌────────────┐         ┌─────────────▼──────────┐          │
│  │ Admin      │         │  Tailscale Network      │          │
│  │ Devices    │────────▶│  - Private VPN          │          │
│  │            │         │  - Zero-trust           │          │
│  └────────────┘         └────────────┬────────────┘          │
└──────────────────────────────────────┼───────────────────────┘
                                       │ Encrypted VPN
                                       │
                          ┌────────────▼─────────────────────┐
                          │    HOME NETWORK                   │
                          │    (Behind CGNAT)                 │
                          │                                   │
                          │  ┌───────────────────────────┐   │
                          │  │  Docker Network            │   │
                          │  │                            │   │
                          │  │  ┌──────────────────────┐ │   │
                          │  │  │ Cloudflared          │ │   │
                          │  │  │ (Public DoH only)    │ │   │
                          │  │  └──────────┬───────────┘ │   │
                          │  │             │              │   │
                          │  │  ┌──────────▼───────────┐ │   │
                          │  │  │ Caddy                │ │   │
                          │  │  │                      │ │   │
                          │  │  │ Rules:               │ │   │
                          │  │  │ /dns-query → public  │ │   │
                          │  │  │ /         → deny     │ │   │
                          │  │  │ :8443     → Tailscale│ │   │
                          │  │  │             only     │ │   │
                          │  │  └──────────┬───────────┘ │   │
                          │  │             │              │   │
                          │  │  ┌──────────▼───────────┐ │   │
                          │  │  │ DNS Server (Python)  │ │   │
                          │  │  │ - DoH Handler        │ │   │
                          │  │  │ - DNS Filter         │ │   │
                          │  │  │ - API                │ │   │
                          │  │  └──────────────────────┘ │   │
                          │  │                            │   │
                          │  └────────────────────────────┘   │
                          │                                   │
                          │  ┌──────────────────────┐        │
                          │  │ Tailscale Daemon     │        │
                          │  │ (Admin access)       │        │
                          │  └──────────────────────┘        │
                          │                                   │
                          └───────────────────────────────────┘
```

**Benefits:**
- ✅ Public DoH endpoint (Cloudflare)
- ✅ Private dashboard (Tailscale)
- ✅ Best security model
- ✅ Zero cost

---

## 6. Data Flow Diagrams

### DoH Query Flow (with Cloudflare Tunnel)

```
Client Device
    │
    │ 1. HTTPS POST /dns-query
    │    (DNS query in body)
    ▼
Cloudflare Edge
    │
    │ 2. Route through tunnel
    │    (Encrypted)
    ▼
Home: Cloudflared Container
    │
    │ 3. Forward to Caddy
    ▼
Home: Caddy Container
    │
    │ 4. Reverse proxy to DNS Server
    ▼
Home: DNS Server (Python)
    │
    │ 5. Parse DNS query
    │ 6. Check blacklist
    ▼
Is domain blocked?
    │
    ├─ YES ──→ Return sinkhole IP (192.168.1.100)
    │          Log to DB (status: blocked)
    │
    └─ NO ───→ Forward to upstream DNS (1.1.1.1)
               Get response
               Log to DB (status: allowed)
               Return response
    │
    │ 7. DNS response
    ▼
Client Device
    │
    │ 8. Use IP address
    ▼
Connect to website (or sinkhole if blocked)
```

### DNS Query Flow (LAN - Direct)

```
LAN Client (e.g., 192.168.1.50)
    │
    │ 1. UDP DNS query (Port 53)
    │    e.g., "google.com A?"
    ▼
Home Server (192.168.1.100:53)
    │
    │ 2. Received by DNS Server container
    ▼
DNS Server (Python)
    │
    │ 3. Parse query
    │ 4. Check blacklist
    ▼
Is domain blocked?
    │
    ├─ YES ──→ Return sinkhole IP
    │          (192.168.1.100)
    │
    └─ NO ───→ Forward to router (192.168.1.1)
               Router forwards to ISP DNS
               or upstream (1.1.1.1)
    │
    │ 5. DNS response
    ▼
LAN Client
    │
    │ 6. Connect to resolved IP
    ▼
Internet or Sinkhole
```

---

## 7. Security Architecture

### Before (No CGNAT fix)

```
                   ┌─────────────┐
                   │  Internet   │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │  ISP (CGNAT)│
                   └──────┬──────┘
                          │ ❌ No direct access
                   ┌──────▼──────┐
                   │  Home Router│
                   └──────┬──────┘
                          │
        ┌─────────────────┼─────────────────┐
        │        LAN      │                  │
        │  ┌──────────────▼──────────────┐  │
        │  │  Server (192.168.1.100)     │  │
        │  │  - DNS Firewall              │  │
        │  │  - Dashboard                 │  │
        │  │  - No external auth needed   │  │
        │  └─────────────────────────────┘  │
        │                                    │
        └────────────────────────────────────┘

Security: Physical access only (good)
Problem: No WAN access (bad for mobile)
```

### After (Cloudflare Tunnel)

```
                   ┌─────────────────────────┐
                   │  Internet (Attackers)   │
                   └────────────┬────────────┘
                                │
                   ┌────────────▼──────────────┐
                   │  Cloudflare Network       │
                   │  ─────────────────────    │
                   │  Layer 7 DDoS Protection  │
                   │  WAF (Web App Firewall)   │
                   │  Rate Limiting            │
                   │  TLS 1.3 Encryption       │
                   │  Bot Detection            │
                   └────────────┬──────────────┘
                                │ Only valid traffic
                                │ passes
                   ┌────────────▼──────────────┐
                   │  Cloudflared Tunnel       │
                   │  (Encrypted channel)      │
                   └────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────┐
        │       Home Network    │                    │
        │  ┌────────────────────▼────────────────┐  │
        │  │  Server (192.168.1.100)             │  │
        │  │  ───────────────────────────        │  │
        │  │  Caddy:                              │  │
        │  │  - Basic Auth on Dashboard          │  │
        │  │  - TLS termination                  │  │
        │  │                                      │  │
        │  │  DNS Server:                        │  │
        │  │  - Query validation                 │  │
        │  │  - Rate limiting (future)           │  │
        │  │  - Logging                          │  │
        │  └─────────────────────────────────────┘  │
        │                                            │
        └────────────────────────────────────────────┘

Security: Multi-layer protection
Access: Global via Cloudflare
```

---

## 8. Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                       DOCKER COMPOSE                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Caddy Container                                          │  │
│  │  ───────────────                                          │  │
│  │  Ports: 80, 443, 853, 8081                               │  │
│  │  Volumes:                                                 │  │
│  │    - Caddyfile (config)                                   │  │
│  │    - caddy_data (TLS certs)                              │  │
│  │    - dashboard (static files)                            │  │
│  │    - clients (download files)                            │  │
│  │                                                           │  │
│  │  Functions:                                               │  │
│  │    1. TLS termination (DuckDNS)                          │  │
│  │    2. Reverse proxy (DoH → :8080, API → :8000)          │  │
│  │    3. Layer 4 proxy (DoT → :8053)                       │  │
│  │    4. Serve dashboard & client files                     │  │
│  │    5. Basic authentication                               │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│                          │ HTTP/HTTPS                           │
│                          │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │  DNS Server Container (Python)                           │  │
│  │  ─────────────────────────────                           │  │
│  │  Ports: 53/UDP, 53/TCP, 8000, 8053, 8080                │  │
│  │  Volumes:                                                 │  │
│  │    - ./server (code)                                     │  │
│  │    - data/ (persistent)                                  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ main.py (FastAPI + Uvicorn)                        │ │  │
│  │  │                                                     │ │  │
│  │  │  ┌───────────────┐    ┌────────────────────────┐  │ │  │
│  │  │  │ API Router    │    │ Core Modules           │  │ │  │
│  │  │  │ (FastAPI)     │    │                        │  │ │  │
│  │  │  │               │    │ ┌────────────────────┐ │  │ │  │
│  │  │  │ Endpoints:    │    │ │ dns_server.py      │ │  │ │  │
│  │  │  │ - /dns-query  │◄───┼─│ UDP/TCP listeners  │ │  │ │  │
│  │  │  │ - /api/stats  │    │ └────────────────────┘ │  │ │  │
│  │  │  │ - /api/logs   │    │                        │  │ │  │
│  │  │  │ - /api/config │    │ ┌────────────────────┐ │  │ │  │
│  │  │  └───────┬───────┘    │ │ filtering.py       │ │  │ │  │
│  │  │          │            │ │ BlacklistManager   │ │  │ │  │
│  │  │          │            │ │ - is_blocked()     │ │  │ │  │
│  │  │          │            │ │ - reload()         │ │  │ │  │
│  │  │          │            │ └─────────┬──────────┘ │  │ │  │
│  │  │          │            │           │            │  │ │  │
│  │  │          │            │ ┌─────────▼──────────┐ │  │ │  │
│  │  │          │            │ │ blacklist_updater  │ │  │ │  │
│  │  │          │            │ │ - Fetch sources    │ │  │ │  │
│  │  │          │            │ │ - Parse & merge    │ │  │ │  │
│  │  │          │            │ │ - Update every 24h │ │  │ │  │
│  │  │          │            │ └────────────────────┘ │  │ │  │
│  │  │          │            │                        │  │ │  │
│  │  │          │            │ ┌────────────────────┐ │  │ │  │
│  │  │          │            │ │ forwarder.py       │ │  │ │  │
│  │  │          │            │ │ - Forward to       │ │  │ │  │
│  │  │          │            │ │   upstream DNS     │ │  │ │  │
│  │  │          │            │ └────────────────────┘ │  │ │  │
│  │  │          │            └────────────────────────┘  │ │  │
│  │  │          │                                        │ │  │
│  │  │          ▼                                        │ │  │
│  │  │  ┌────────────────┐                              │ │  │
│  │  │  │ database.py    │                              │ │  │
│  │  │  │ (SQLAlchemy)   │                              │ │  │
│  │  │  │                │                              │ │  │
│  │  │  │ ┌────────────┐ │                              │ │  │
│  │  │  │ │ SQLite DB  │ │                              │ │  │
│  │  │  │ │ queries.db │ │                              │ │  │
│  │  │  │ │            │ │                              │ │  │
│  │  │  │ │ Tables:    │ │                              │ │  │
│  │  │  │ │ - dns_logs │ │                              │ │  │
│  │  │  │ └────────────┘ │                              │ │  │
│  │  │  └────────────────┘                              │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Cloudflared Container (Optional - CGNAT fix)        │  │
│  │  ────────────────────────────────────                │  │
│  │  - Connects to Cloudflare Edge                       │  │
│  │  - Tunnels traffic to Caddy                          │  │
│  │  - Auto-reconnect                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Summary

**Current Issues:**
- ❌ CGNAT blocks external access
- ⚠️ No monitoring/alerting
- ⚠️ Performance could be optimized

**Solutions (pick one):**
1. **Cloudflare Tunnel** ← Recommended (free, easy, stable)
2. **Tailscale** ← For privacy/VPN approach
3. **FRP + VPS** ← For full control
4. **Hybrid** ← Best security model

**Next Steps:**
1. Choose solution (recommend Cloudflare Tunnel)
2. Follow quick start guide
3. Test thoroughly
4. Update clients
5. Monitor & optimize
