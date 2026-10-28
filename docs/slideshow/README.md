# BaeBugs slideshows (self-playing)

Two auto-advancing photo shows. Open the `.ppsx` to start the show directly; the `.pptx` is the same deck for editing or importing into Google Slides (Google Slides drops the auto-advance timings, so use Present → auto-play there).

Both shows loop until Esc. All embedded images were re-encoded on build, so no EXIF, GPS or camera metadata is carried (checked: 0 of 40 embedded images have EXIF).

| File | Slides | Runtime | sha256 |
|---|---|---|---|
| `baebugs_final_setup_autoplay.ppsx` | 32 | ~2 min 19 s | `6b7fc180799d7c9d83cd56b4b8e7b83e1c8a1d2182d026ef5ecb19ac7d5a1137` |
| `baebugs_final_setup_autoplay.pptx` | 32 | ~2 min 19 s | `87ab882512739ab001888aad7987cc50bdd4bff3f9b55c03891fb3b3e2f667bb` |
| `baebugs_bench_photos_autoplay.ppsx` | 9 | ~59 s | `4e337f83706a64edc828fe3403ce6c3245a651f55efd3c48b55bb02d14255ffb` |
| `baebugs_bench_photos_autoplay.pptx` | 9 | ~59 s | `035483479df9ad2d36390986dc3927b3fd2f84fe88380bab3638771841412cc6` |

## Final setup show (pictures only, no captions)

Ladybug mark → repurposed labware photos → labware renders (`print/labware/previews.png`) → printed frames and failed FDM attempt → parts and trommel renders (`print/parts/`) → depowdering drum → PA12 toys, toy renders (`print/fuse1/preview.png`), detections (`docs/toy_photo_models/`, `docs/ladder_demo/`) → sieve, tower photo and renders (`experiments/biokea_*`) → arms, vortexer, Opentrons deck and adapter renders (`opentrons/previews.png`) → 3D lab still (`docs/demo/baebugs_mvp_demo.mp4` at 24 s) → screenshots of `site/twin`, `site/board`, `site/mvp`, `site/aok` → team photo → final bench setup (held 10 s).

Bench photos are Byron's uploads from 2026-10-25, which aren't stored elsewhere in the repo. The slideshow files are the only stored copy of those bytes here.

## Bench photos show (captioned, Arial)

Eight bench photos, cropped to remove reflections of people and prominent vendor logos, with short captions and a closing repo link.

## Photo policy note

The final setup show includes team photos with faces (a selfie and the final bench setup). Byron chose to include them. This is an exception to the repo's default of withholding bench photos that show faces or vendor logos. The bench-photos show follows the default.
