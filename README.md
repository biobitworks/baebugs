# baebugs

**Vision lane for BioKEA Track A, step 1 (BugSorter).** A USB camera looks at a preserved sample *before* it is sieved, measures every body in millimetres, and decides which sieves to stack and how hard to run the water. It then checks that plan against a digital twin of the bench and hands each sieve fraction to BugPicker in BugPicker's own file format. Every step is logged to a hash-chained provenance record.

Built at the Physical AI for Science Hack (Oct 24–25, 2026). The challenge is to make sample prep robust: "bags in, barcodes out".

```
 bag of specimens
      │
      ▼
 ① OBSERVE   AmScope/USB image ─► YOLO ┐
                                       ├─► consensus sizes (mm) ─► flag disagreements
             classical morphometrics ──┤        (+ optional Claude QA)
             BugPicker detector ───────┘
      │
      ▼
 ② HYPOTHESIZE  size classes ─► sieve stack (coarse→fine) + flow per sieve + water budget
      │
      ▼
 ③ PREFLIGHT   digital twin: sieve exists & free, order, slots, water above reserve
      │          (nothing reaches the arm / ESP32 sieve unless this is clean)
      ▼
 ④ RUN         partabot arm / BugSorter places sieves, water jets rinse
      │
      ▼
 ⑤ VERIFY      image each fraction ─► predicted vs observed ─► update retention margin
      │
      ▼
 ⑥ HAND OFF    manifest.jsonl / objects.jsonl with tray_size_class + sorting_tray_slot
               ─► BugDisperser ─► BugPicker ─► 96-well plate
      │
      ▼
   provenance.jsonl (hash-chained, verifiable per sample)
```

## Why each piece

| Piece | What it does | Why it matters for Track A |
|---|---|---|
| `measure.py` | Two independent sizers, YOLO and classical contours, paired by consensus | Their failure modes differ, so the arm only acts on sizes both agree on. Disagreements get flagged rather than sieved blind |
| `sieve.py` | Width classes mapped to the kit's actual frames, plus flow per mesh | The narrow axis decides what passes a mesh. Finer meshes get gentler flow so soft bodies aren't forced through |
| `sieve_calibrate.py` | Measures a mesh's real aperture from one backlit photo | Printed and woven meshes drift from their nominal size and warp. Measuring beats assuming |
| `twin.py` | Preflight in the style of Google's VERID (a digital twin of the lab) | Rejects plans that are physically invalid, such as a sieve already in use or too little water, before hardware moves |
| `method.py` | Predicted vs observed counts per fraction, then a retention-margin update | The sorter gets better each run instead of repeating the same error |
| `bugpicker_bridge.py` | Reads and writes [BugPicker](https://github.com/biokea/BugPicker)'s `manifest.jsonl` / `objects.jsonl` | Fills `tray_size_class` and `sorting_tray_slot`, so step 1 plugs into step 3 with no new protocol. It can also use BugPicker's detector as a measurement source |
| `calbug.py` | Pulls family composition for a locality from the Essig Museum / Calbug collection on GBIF (~550k records) and turns it into an expected size-class mix | Flags a bag that doesn't look like where it came from (wrong bag, broken specimens, debris) before sieving. Links provenance to `EMEC` catalog numbers |
| `provenance.py` | One hash-chained record per step | Covers what was done, to which sample, with which parameters, images and version, so the record is FAIR without a write-up afterwards |
| `mcp_server.py` | MCP tools: `measure_sample`, `plan_sieves`, `calibrate_sieve`, `sieve_inventory`, `trace_sample` | Gives the instrument an API, so an agent can run the protocol while people supervise |

## Kit (from the bench, `docs/bench/`)

| id | mesh | est. aperture | photo evidence |
|---|---|---|---|
| PERF-5 | perforated metal, round holes | ~5 mm | kept pasta, passed rice |
| GRID-4 | coarse printed plastic grid | ~4 mm | kept pasta and lasagna pieces |
| HEX-2 | hex wire | ~2.2 mm | most rice passed |
| SCREEN-1 | fine window screen | ~1.2 mm | kept rice, chia mostly passed |
| TRAY | solid catch tray | — | catches everything; hands off to BugDisperser |

These apertures are **estimates** read from the photos. Run calibration on a backlit top-down image of each mesh to replace them. Each frame has 6 cells, for replicates or separate samples.

## Quick start

```bash
pip install -e ".[notebook,dev]"          # add [yolo] and [claude] as needed
pytest -q
jupyter lab notebooks/baebugs_pipeline.ipynb   # swap data in the first cell
baebugs analyze --image tray.jpg --px-per-mm 40          # or --camera 0 --aruco-mm 10
python -m baebugs.mcp_server                             # instrument as MCP server
```

**Scale.** Put a printed ArUco marker (4x4_50) of known size in the field of view and pass `--aruco-mm`. Otherwise measure px/mm once per zoom setting on the AmScope.

## Integration options for step 1 (pick one or stack them)

1. **Vision-first stack selection** (built). Image the sample, choose which frames go in the stack, run.
2. **Fixed stack + vision verification**. Always run all frames, then image each fraction. This gives QA and the retention-margin update, with the lowest risk on the day.
3. **Closed loop with the ESP32 BugSorter**. Implement `RobotAdapter.place_sieve` / `rinse` against the sieve's web UI (or a partabot arm), so `LabTwin.execute(..., dry_run=False)` drives the hardware.
4. **Feed BugPicker directly**. `write_scan()` produces a scan directory BugPicker already understands, with fractions labelled by measured size class.

## Still needed from the team

- Family body-width ranges → `baebugs/config/family_sizes.yaml` (placeholders; drives the Essig prior)
- Real insect / analog size parameters → `baebugs/config/insects.yaml` (current values are placeholders)
- Measured apertures → `baebugs/config/sieves.yaml`
- YOLO weights trained on the nine bug analogs (BugPicker crops in `objects/` make a ready labelled set)
- ESP32 sieve endpoints / partabot SDK for `RobotAdapter`

## Licence

MIT

## Data sources

- [Essig Museum of Entomology](https://essigdb.berkeley.edu/query_specimens.html) / [Calbug](https://calbug.berkeley.edu/), via GBIF dataset `5d283bb6-64dd-4626-8b3b-a4e8db5415c3`
- [BioKEA BugPicker](https://github.com/biokea/BugPicker) file protocol
- Google Research, [VERID](https://research.google/blog/grounding-ai-agents-in-biological-reality-building-blocks-for-autonomous-wet-labs/) (digital-twin preflight pattern)
