"""Vercel static site security and publication policy tests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_versioned_security_headers():
    c = json.loads((ROOT / "vercel.json").read_text())
    headers = {h["key"].lower(): h["value"] for rule in c["headers"] for h in rule["headers"]}
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "SAMEORIGIN"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'self'" in headers["content-security-policy"]
    assert "object-src 'none'" in headers["content-security-policy"]
    assert "raw.githubusercontent.com" in headers["content-security-policy"]
    assert "https://api.gbif.org" in headers["content-security-policy"]
    assert "frame-src 'self' https://www.youtube-nocookie.com" in headers["content-security-policy"]

    assert "youtube-nocookie.com" in headers["content-security-policy"]
    assert "camera=()" in headers["permissions-policy"]


def test_team_photo_publication_assertion_is_scoped():
    r = json.loads((ROOT / "docs/slideshow/TEAM_PHOTO_PUBLICATION_APPROVAL_20261028.json").read_text())
    assert r["user_assertion"] == "The team pic is approved"
    assert r["signing"] == "NOT_SIGNED"
    assert r["independent_release_from_every_person"] == "NOT_VERIFIED"


def test_audit_never_promotes_untested_robot_results():
    r = json.loads((ROOT / "docs/submission/VERCEL_AUDIT_RELEASE_FCO_20261028.json").read_text())
    assert r["physical_robot"] == "NOT_TESTED"
    assert r["mmr_commit"] == "NOT_COMPUTED"
    assert r["security_headers_effective"] == "NOT_TESTED_UNTIL_VERCEL_STAGING"
