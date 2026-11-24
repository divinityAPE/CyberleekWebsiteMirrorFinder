# 🌐 AR.IO Gateway Inspector & Network Auditor

A lightweight, high-throughput Python utility designed to discover, health-check, and audit resolution availability for **ArNS (Arweave Name System)** websites across the decentralized **AR.IO Gateway Network**.

Cyberleek Domain search made easy.
Find gateways easy. 

502 Errors suck this tool automatically solves that

---

## 📌 Overview

On the decentralized web, content hosted on Arweave via ArNS (e.g. `cyberleek.ar.io`) is served across a distributed network of independent gateway operators. Because each gateway operator maintains its own node configuration, caching layer, and content policies, an ArNS site might be:

1. **Active & Operational** on certain community nodes.
2. **Filtered / Moderated** on nodes enforcing strict gateway content policies (returning HTTP 451 / `Blocked ID` headers).
3. **Unreachable / Offline** on nodes experiencing downtime or DNS misconfigurations.

This tool dynamically retrieves the global **Gateway Address Registry (GAR)** and audits availability and policy enforcement across all active nodes simultaneously using multi-threaded HTTP probing.

---

## ⚡ Key Features

- 🛰️ **Dynamic Node Discovery**: Automatically queries on-chain registry contracts and observer APIs (`arns.app`, `ar-io.net`, `g8way.io`) to discover live gateway FQDNs.
- ⚡ **Concurrent Multithreaded Auditing**: Uses Python's `concurrent.futures.ThreadPoolExecutor` to test hundreds of nodes in parallel within seconds.
- 🔀 **Smart Fallback Routing**: Attempts both **subdomain resolution** (`https://<domain>.<gateway>`) and **path/host-header resolution** (`https://<gateway>/<domain>`).
- 🛡️ **Content Policy Detection**: Inspects response codes (e.g., HTTP 451) and body payloads to identify gateway-level censorship or node policy blocks.
- 📊 **JSON Export**: Automatically dumps detailed raw status metrics to `ario_scan_results.json`.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.8+ (No external third-party dependencies required; uses standard library `urllib`, `ssl`, `json`, `concurrent.futures`).

### 2. Running the Audit
Execute the inspector script directly from your terminal:

```bash
python ario_gateway_checker.py
```

---

## ⚙️ Configuration

You can customize the target domain and scan parameters at the top of [`ario_gateway_checker.py`](file:///c:/Users/setha/Documents/Antigravity/gateway/ario_gateway_checker.py):

```python
# Target ArNS site to audit
TARGET_NAME = "cyberleek"
TARGET_ARNS_FULL = f"{TARGET_NAME}.ar.io"

# Concurrency thread pool limit
MAX_WORKERS = 10
```

---

## 🔍 Classification Criteria

Each audited gateway is categorized into one of these statuses:

| Status | Description | HTTP Indicators |
| :--- | :--- | :--- |
| **`WORKING / ACTIVE`** | Gateway is operational and serving site payload. | `HTTP 200 OK` + `x-arns-name` / `x-arns-resolved-id` header for the target name |
| **`BLOCKED (Content Policy)`** | Node operator policy or moderation filter activated. | `HTTP 451 Unavailable For Legal Reasons` or body contains `"Content Policy"` / `"Blocked ID"` |
| **`PARKED / FOR SALE`** | Gateway's domain lapsed and is now a parking or for-sale page. | No ArNS headers + parking page text, server or redirect |
| **`FAILED (Not ArNS content)`** | Something answered, but it isn't serving the target site. | `HTTP 200 OK` without ArNS headers for the target name |
| **`FAILED / UNREACHABLE`** | Gateway node is offline, misconfigured, or timing out. | `DNS resolution error`, `Connection refused`, `HTTP 5xx` |

---

## 📁 Output Artifacts

After execution, the script generates `ario_scan_results.json`:

```json
[
  {
    "gateway": "permaweb.io",
    "status_code": 200,
    "classification": "WORKING / ACTIVE",
    "details": "HTTP 200 OK | Snippet: <!DOCTYPE html>...",
    "url": "https://permaweb.io/cyberleek"
  },
  {
    "gateway": "ardrive.net",
    "status_code": 451,
    "classification": "BLOCKED (Content Policy)",
    "details": "Blocked by node policy",
    "url": "https://cyberleek.ardrive.net"
  }
]
```

---

## 🛠️ Architecture Flow

```
                   +-------------------------------+
                   | AR.IO Gateway Registry APIs   |
                   +---------------+---------------+
                                   |
                                   v
                   +---------------+---------------+
                   |  Gateway Address Registry     |
                   |  (300+ Node FQDNs Discovered) |
                   +---------------+---------------+
                                   |
                   +---------------+---------------+
                   | ThreadPoolExecutor Parallel   |
                   | Resolution Audits             |
                   +-------+---------------+-------+
                           |               |
           +---------------+               +---------------+
           v                                               v
+-----------------------+                       +-----------------------+
|  Subdomain Resolution |                       | Path / Host-Header    |
|  https://site.node    |                       | https://node/site     |
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                   +-------------------------------+
                   | Status Classifier Engine      |
                   +---------------+---------------+
                                   |
         +-------------------------+-------------------------+
         |                         |                         |
         v                         v                         v
+------------------+     +-------------------+     +-------------------+
| WORKING / ACTIVE |     | POLICY BLOCKED    |     | FAILED / OFFLINE  |
+------------------+     +-------------------+     +-------------------+
```

---

## 📜 Free & Open-Source Software (FOSS) License & Legal Notice

### MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

### 🛡️ Legal & Ethical Usage Notice

1. **Permissive Usage**: This tool is 100% free and open-source software (FOSS). Developers, researchers, and network operators are free to audit, modify, fork, or distribute this tool for any legitimate diagnostic or research purpose.
2. **Read-Only Network Diagnostics**: This utility performs standard, unauthenticated public HTTP/S `GET` requests strictly to query domain availability, ARNS routing, and gateway health.
3. **Decentralized Network Transparency**: Auditing gateway node availability and content policies provides public transparency into the health, uptime, and censorship resistance of the AR.IO ecosystem.
