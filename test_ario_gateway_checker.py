"""Run with: python -m unittest -v

The bodies and headers are cut down from responses captured on 2026-11-24.
"""
import unittest
from email.message import Message
from unittest import mock
from urllib.error import URLError

import ario_gateway_checker as checker

SEDO = (
    "<title>koniq.xyz&nbsp;-&nbsp;This website is for sale!</title>"
    '<img src="https://img.sedoparking.com/images/js_preloader.gif">'
)
LANDER = (
    "<!DOCTYPE html><html><head><script>window.onload=function()"
    '{window.location.href="/lander"}</script></head></html>'
)
OWNER_SALE = "<h1>This domain is for sale</h1><h3>Contact the Owner</h3>"
JS_REDIRECT = (
    "<html><head><title>Loading...</title></head><body><script>"
    "window.location.replace('https://cyberleek.mutu.pro/?ch=1')</script></body></html>"
)
NGINX = "<title>Welcome to nginx!</title>"
SITE = "<!DOCTYPE html><html><head><title>CYBERLEEK</title></head></html>"
ARNS = {"x-arns-name": "cyberleek", "x-arns-resolved-id": "T2_D0Jh99jdntz"}


class FakeResponse:
    def __init__(self, url, body, headers=None, status=200):
        self.url, self.body, self.status = url, body, status
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body.encode()

    def geturl(self):
        return self.url


def scan(body, headers=None, final_url=None, subdomain_fails=False):
    """Classify a gateway that answers every request with this response."""
    def urlopen(req, **kwargs):
        if subdomain_fails and req.full_url.startswith("https://cyberleek."):
            raise URLError("Name or service not known")
        return FakeResponse(final_url or req.full_url, body, headers)

    with mock.patch("urllib.request.urlopen", urlopen):
        return checker.test_gateway("example.xyz")[2]


class ClassificationTest(unittest.TestCase):
    def test_parked_domains_are_not_working(self):
        cases = {
            "sedo": (SEDO, {"Server": "Parking/1.0"}, None),
            "godaddy lander": (LANDER, None, None),
            "owner sale page": (OWNER_SALE, None, None),
            "redirect to marketplace": ("", None, "https://forsale.godaddy.com/forsale/x.xyz"),
        }
        for name, (body, headers, final_url) in cases.items():
            for subdomain_fails in (False, True):
                with self.subTest(name, path_fallback=subdomain_fails):
                    self.assertEqual(
                        scan(body, headers, final_url, subdomain_fails), "PARKED / FOR SALE")

    def test_parked_page_mentioning_a_content_policy_is_parked(self):
        self.assertEqual(scan(SEDO + "Read our content policy"), "PARKED / FOR SALE")

    def test_other_pages_without_arns_headers_are_not_working(self):
        for body in (JS_REDIRECT, NGINX, "", '{"wallet":"CkEU4i91"}'):
            with self.subTest(body):
                self.assertEqual(scan(body), "FAILED (Not ArNS content)")

    def test_another_arns_name_is_not_working(self):
        self.assertEqual(scan(SITE, {"x-arns-name": "ardrive"}), "FAILED (Not ArNS content)")

    def test_real_mirror_is_working(self):
        self.assertEqual(scan(SITE, ARNS), "WORKING / ACTIVE")
        self.assertEqual(scan(SITE, ARNS, subdomain_fails=True), "WORKING / ACTIVE")

    def test_gateway_without_the_name_header_is_working(self):
        self.assertEqual(scan(SITE, {"X-ArNS-Resolved-Id": "T2_D0Jh99jdntz"}), "WORKING / ACTIVE")

    def test_real_mirror_that_says_for_sale_is_working(self):
        self.assertEqual(scan(SITE + "this domain is for sale", ARNS), "WORKING / ACTIVE")

    def test_policy_block_is_still_blocked(self):
        self.assertEqual(scan("Blocked by content policy"), "BLOCKED (Content Policy)")


if __name__ == "__main__":
    unittest.main()
