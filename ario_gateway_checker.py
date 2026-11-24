import urllib.request
import urllib.error
import urllib.parse
import json
import re
import time
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

# Target ARNS name / subdomain to search for
TARGET_NAME = "cyberleek"
TARGET_ARNS_FULL = f"{TARGET_NAME}.ar.io"

# Known registry & gateway fallback endpoints
REGISTRY_ENDPOINTS = [
    "https://api.arns.app/v1/contract/bLAgYxAdX2Ry-nt6aH2ixgvJXbpsEYm28NgJgyqfs-U/gateways",
    "https://mainnet.ar-io.net/ar-io/gateways",
    "https://g8way.io/ar-io/gateways",
    "https://arweave.net/ar-io/peers"
]

FALLBACK_GATEWAYS = [
    "arweave.net",
    "g8way.io",
    "ar-io.dev",
    "ardrive.net",
    "permaweb.io",
    "arweave.dev",
    "ar-io.net",
    "ario.network",
    "viewblock.io",
    "arweave.live",
    "ar-gateways.io",
    "arweave.cloud",
    "perma.host",
    "arweave.io",
    "ar.io"
]

def fetch_gateways_from_registry():
    """Fetch gateway domains from AR.IO registry APIs."""
    gateways = set(FALLBACK_GATEWAYS)
    print("[*] Fetching latest gateways from AR.IO registry APIs...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for endpoint in REGISTRY_ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    # Process dictionary / list responses
                    if isinstance(data, dict):
                        # Might be keyed by gateway ID or under a 'gateways' / 'items' list
                        items = data.get('gateways', data.get('items', data))
                        if isinstance(items, dict):
                            for g_id, g_info in items.items():
                                fqdn = g_info.get('fqdn') or g_info.get('settings', {}).get('fqdn') or g_info.get('domain')
                                if fqdn:
                                    gateways.add(fqdn.strip())
                        elif isinstance(items, list):
                            for g_info in items:
                                fqdn = g_info.get('fqdn') if isinstance(g_info, dict) else str(g_info)
                                if fqdn:
                                    gateways.add(fqdn.strip())
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                fqdn = item.get('fqdn') or item.get('domain')
                                if fqdn:
                                    gateways.add(fqdn.strip())
                            elif isinstance(item, str):
                                gateways.add(item.strip())
                    print(f" [+] Fetched data from {endpoint} (Total unique gateways: {len(gateways)})")
        except Exception as e:
            # Silently fallback if endpoint fails
            pass

    return sorted(list(gateways))

# Signs of a domain that is parked or for sale. They only choose the label: a page
# without the ArNS headers is never reported as working, whether or not one matches.
PARKED_PAGE = re.compile(
    r"(domain|website|site)( name)? (is|may be) for sale"
    r"|buy this (domain|website)"
    r"|this domain is parked"
    r"|sedoparking|parkingcrew|bodis\.com|afternic\.com|hugedomains\.com|forsale\.godaddy\.com"
    r"""|location(\.href)?\s*=\s*["']/lander\b""",  # GoDaddy / Afternic stub page
    re.IGNORECASE)

PARKING_HOST = re.compile(
    r"(^|\.)(forsale\.godaddy\.com|afternic\.com|sedo\.com|sedoparking\.com"
    r"|hugedomains\.com|dan\.com|bodis\.com)$",
    re.IGNORECASE)

def is_arns_response(headers):
    """True if an AR.IO gateway resolved TARGET_NAME to produce this response."""
    name = headers.get('x-arns-name')
    if name is not None:
        return name.strip().lower() == TARGET_NAME.lower()
    # Older gateways may not send the name, only the transaction it resolved to
    return bool(headers.get('x-arns-resolved-id'))

def is_parked(resp, body):
    """True if the response is a registrar's or reseller's parking page."""
    return bool(
        (resp.headers.get('Server') or '').lower().startswith('parking')
        or PARKING_HOST.search(urllib.parse.urlsplit(resp.geturl()).hostname or '')
        or PARKED_PAGE.search(body))

def classify_response(resp, body):
    """Returns (classification, details) for a response that isn't an HTTP error."""
    verified = is_arns_response(resp.headers)
    lowered = body.lower()

    if not verified and is_parked(resp, body):
        return ("PARKED / FOR SALE", "Domain is parked or for sale, not a gateway")
    if "content policy" in lowered or "blocked id" in lowered or "censored" in lowered:
        return ("BLOCKED (Content Policy)", "Blocked message detected in page body")
    if resp.status != 200:
        return (f"FAILED (HTTP {resp.status})", f"Status code {resp.status}")
    if not verified:
        return ("FAILED (Not ArNS content)", f"HTTP 200, but no ArNS headers for '{TARGET_NAME}'")
    snippet = body[:100].replace('\n', ' ').strip()
    return ("WORKING / ACTIVE", f"HTTP 200 OK | Snippet: {snippet[:40]}...")

def test_gateway(gateway):
    """
    Tests an individual gateway for the target ARNS site.
    Returns status tuple: (gateway, status_code, classification, details, target_url)
    """
    # 1. Test subdomain routing first: https://cyberleek.<gateway>
    subdomain_url = f"https://{TARGET_NAME}.{gateway}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(subdomain_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6, context=ssl_context) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            classification, details = classify_response(resp, body)
            return (gateway, resp.status, classification, details, subdomain_url)

    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode('utf-8', errors='ignore')
        except:
            pass
            
        if e.code == 451 or "content policy" in body.lower() or "blocked" in body.lower():
            return (gateway, e.code, "BLOCKED (Content Policy)", "Gateway blocked request due to node content policy", subdomain_url)
        elif e.code == 404:
            # Let's try direct Host header or path fallback
            return test_gateway_path(gateway)
        else:
            return (gateway, e.code, f"FAILED (HTTP {e.code})", f"HTTP error {e.code}", subdomain_url)

    except (urllib.error.URLError, socket.timeout, Exception) as e:
        # Try path-based resolution before marking failed
        return test_gateway_path(gateway)

def test_gateway_path(gateway):
    """Fallback test using gateway path or direct domain resolution: https://<gateway>/<TARGET_NAME>"""
    path_url = f"https://{gateway}/{TARGET_NAME}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Host': f"{TARGET_NAME}.{gateway}"
    }
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(path_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6, context=ssl_context) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            classification, details = classify_response(resp, body)
            return (gateway, resp.status, classification, details, path_url)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode('utf-8', errors='ignore')
        except:
            pass
        if "content policy" in body.lower() or "blocked" in body.lower():
            return (gateway, e.code, "BLOCKED (Content Policy)", "Blocked by node content policy", path_url)
        return (gateway, e.code, f"FAILED (HTTP {e.code})", f"HTTP error {e.code}", path_url)
    except Exception as e:
        return (gateway, None, "FAILED / UNREACHABLE", str(e), path_url)

def main():
    print("=" * 70)
    print(f"  AR.IO GATEWAY SCANNER & POLICY AUDITOR — Target: {TARGET_ARNS_FULL}")
    print("=" * 70)
    
    gateways = fetch_gateways_from_registry()
    print(f"[*] Found total {len(gateways)} unique gateways to scan.\n")
    
    results = []
    
    working_list = []
    blocked_list = []
    parked_list = []
    failed_list = []

    print(f"{'GATEWAY':<25} | {'STATUS':<25} | {'DETAILS'}")
    print("-" * 75)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_gateway, gw): gw for gw in gateways}
        for future in as_completed(futures):
            gw, status_code, classification, details, target_url = future.result()
            res_entry = {
                'gateway': gw,
                'status_code': status_code,
                'classification': classification,
                'details': details,
                'url': target_url
            }
            results.append(res_entry)
            
            if "WORKING" in classification:
                working_list.append(res_entry)
                status_str = f"\033[92m{classification}\033[0m" if socket.has_ipv6 else classification
            elif "BLOCKED" in classification:
                blocked_list.append(res_entry)
                status_str = f"\033[93m{classification}\033[0m" if socket.has_ipv6 else classification
            elif "PARKED" in classification:
                parked_list.append(res_entry)
                status_str = f"\033[93m{classification}\033[0m" if socket.has_ipv6 else classification
            else:
                failed_list.append(res_entry)
                status_str = f"\033[91m{classification}\033[0m" if socket.has_ipv6 else classification

            print(f"{gw:<25} | {classification:<25} | {details}")

    print("\n" + "=" * 70)
    print("  SCAN SUMMARY RESULTS")
    print("=" * 70)
    print(f"  [+] WORKING & UNBLOCKED GATEWAYS : {len(working_list)}")
    print(f"  [-] BLOCKED BY CONTENT POLICY    : {len(blocked_list)}")
    print(f"  [$] PARKED / FOR SALE DOMAINS    : {len(parked_list)}")
    print(f"  [x] FAILED / OFFLINE GATEWAYS    : {len(failed_list)}")
    print("=" * 70)

    if working_list:
        print("\n[+] ACTIVE / WORKING GATEWAY URLS FOR YOUR SITE:")
        for item in working_list:
            print(f"   -> {item['url']}")
    else:
        print("\n[!] No direct working gateways found in primary scan.")

    if blocked_list:
        print("\n[-] BLOCKED GATEWAYS (Node Content Policy):")
        for item in blocked_list:
            print(f"   [x] {item['gateway']} ({item['url']})")

    # Save to JSON
    with open("ario_scan_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n[+] Full results saved to 'ario_scan_results.json'")

if __name__ == "__main__":
    main()
