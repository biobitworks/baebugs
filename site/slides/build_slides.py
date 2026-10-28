"""Publish source-verifiable slideshow decks and the user-approved team image.

The single image derivative uses exact embedded JPEG bytes from source PPTX;
the signed/consent status remains explicitly distinct from content identity.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
LINK_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
FILES = (
    ("baebugs_final_setup_autoplay", 32),
    ("baebugs_bench_photos_autoplay", 9),
)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build_slides(repo: Path, target: Path, source_ref: str, mvp_path: Path) -> dict:
    repo, target = Path(repo).resolve(), Path(target)
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("Unpinned source reference")
    target.mkdir(parents=True, exist_ok=True)
    pack = json.loads(Path(mvp_path).read_text())
    atoms = {a["path"]: a for a in pack["leaves"]}
    approved = "docs/slideshow/TEAM_PHOTO_PUBLICATION_APPROVAL_20261028.json"
    approval = json.loads((repo / approved).read_text())
    if approval.get("user_assertion") != "The team pic is approved":
        raise ValueError("No scoped publication assertion")
    readme = (repo / "docs/slideshow/README.md").read_text()

    def atom(path):
        a = atoms.get(path)
        if not a or sha((repo / path).read_bytes()) != a["sha256"]:
            raise ValueError("Source slideshow identity mismatch: " + path)
        return {k: a[k] for k in ("path", "sha256", "leaf", "licence", "claim", "status")}

    output = {"schema": "baebugs.SlideshowPublicationProjection.v1",
              "source_ref": source_ref, "evidence_root": pack["root"],
              "approval_atom": atom(approved),
              "readme_atom": atom("docs/slideshow/README.md"),
              "publication_approval": "USER_ASSERTED_NOT_SIGNED",
              "independent_participant_releases": "NOT_VERIFIED",
              "source_rights": "SOURCE_DECLARED_AND_USER_ASSERTED; NOT_INDEPENDENTLY_ADJUDICATED",
              "scientific_results": "NOT_ESTABLISHED",
              "mmr_commit": "NOT_COMPUTED", "decks": []}
    for basename, expected_slides in FILES:
        file_ref = "docs/slideshow/" + basename + ".pptx"
        ppsx_ref = "docs/slideshow/" + basename + ".ppsx"
        a, b = atom(file_ref), atom(ppsx_ref)
        if basename not in readme or a["sha256"] not in readme or b["sha256"] not in readme:
            raise ValueError("README slideshow hashes not matched")
        archive_path = repo / file_ref
        with zipfile.ZipFile(archive_path) as z:
            names = z.namelist()
            if any(n.startswith("/") or ".." in n.split("/") for n in names):
                raise ValueError("Unsafe archive member")
            if any("vbaproject" in n.lower() or "activex/" in n.lower()
                   or "/embeddings/" in n.lower() for n in names):
                raise ValueError("Active embedded slide content")
            slides = [n for n in names if re.fullmatch(r"ppt/slides/slide[0-9]+.xml", n)]
            if len(slides) != expected_slides:
                raise ValueError("Unexpected slideshow count")
            for relation_file in (n for n in names if n.endswith(".rels")):
                doc = ET.fromstring(z.read(relation_file))
                if any(r.attrib.get("TargetMode") == "External" for r in doc):
                    raise ValueError("External slideshow dependency")
            if basename == "baebugs_final_setup_autoplay":
                xml = ET.fromstring(z.read("ppt/slides/slide32.xml"))
                keys = [node.attrib[LINK_NS] for node in xml.iter() if LINK_NS in node.attrib]
                if len(keys) != 1:
                    raise ValueError("Team photo slide image ambiguity")
                rels = ET.fromstring(z.read("ppt/slides/_rels/slide32.xml.rels"))
                relation = {r.attrib["Id"]: r.attrib.get("Target") for r in rels}
                link = relation.get(keys[0])
                if not link or not link.startswith("../media/"):
                    raise ValueError("Unexpected team photo relationship")
                original_name = "ppt/" + link.replace("../", "")
                raw = z.read(original_name)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format != "JPEG" or image.getexif():
                        raise ValueError("Team photo includes EXIF or unsupported format")
                    width, height = image.size
                    image.verify()
                (target / "team_workcell_approved.jpg").write_bytes(raw)
                source_image = {
                    "schema": "baebugs.SlideImageAtom.v1",
                    "source_deck_sha256": a["sha256"],
                    "source_slide": 32,
                    "source_member": original_name,
                    "jpeg_sha256": sha(raw),
                    "pixel_dimensions": [width, height],
                    "publication_approval": "USER_ASSERTED",
                    "scientific_observation": "PHOTO_OF_WORKCELL_NOT_PERFORMANCE_TEST"
                }
                context = {"source_deck_leaf": a["leaf"], "source_root": pack["root"],
                           "occurrence": "BAEBUGS_FINAL_PUBLIC_TEAM_PHOTO_20261028",
                           "content_sha256": sha(canonical(source_image))}
                output["team_photo"] = {
                    **source_image,
                    "content_sha256": sha(canonical(source_image)),
                    "context_sha256": sha(canonical(context)),
                    "public_path": "team_workcell_approved.jpg"
                }
        for ext in ("pptx", "ppsx"):
            shutil.copy2(repo / ("docs/slideshow/" + basename + "." + ext),
                         target / (basename + "." + ext))
        output["decks"].append({"name": basename, "slides": expected_slides,
                                "pptx": a, "ppsx": b,
                                "download_pptx": basename + ".pptx",
                                "download_ppsx": basename + ".ppsx"})
    (target / "slides.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return output
