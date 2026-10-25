# Breaks recorded, not hidden: a contestable, hash-addressed virtual lab for insect sample preparation

**Draft preprint, v0.1 (2026-10-25).** Bonus submission for BioKEA Track A, Physical AI for Science Hack (Oct 24–25, 2026).

**Authors:** Byron [surname, affiliation, ORCID to fill] (biobitworks)
**Code, data and graph:** https://github.com/biobitworks/baebugs (branch `mvp-kg`) · MVP graph: https://biobitworks.github.io/baebugs/site/mvp/
**Licence of this text:** CC BY 4.0 [confirm]. Code MIT; trained weights AGPL-3.0 (see §6).

> Every number below is taken from a committed file in the repository and cites its path. Results are
> **exploratory** (silver labels, no human-reviewed ground truth) unless stated otherwise. Slots marked
> `[V4: …]` are filled when DAISY-BB-004 attempt v4 is ingested.

---

## Abstract

Insect bulk samples are sorted by hand before anything can be imaged, picked or barcoded. BioKEA's Track A asks for robust sample preparation, "bags in, barcodes out". We built baebugs, the vision and planning lane for step 1 (sieving): a camera measures every body in a sample before sieving, a planner chooses a sieve stack and flow, a digital twin of the bench rejects physically invalid plans before hardware moves, and each fraction is handed to BioKEA BugPicker in its own file format. Around that lane we built the thing we think matters more for open science: a single knowledge graph in which every file, model, dataset, printed part and result is an "atom of knowledge" with a claim, a licence in context and a content hash, rolled up by Merkle roots from leaf to repository and appended to Merkle Mountain Range (MMR) ledgers. The same graph pack is served to a web page, a CLI, an MCP server, `npx` and a Claude plugin, so a person or any bring-your-own (BYO) agent can reproduce the root and contest any atom.

Three findings. (1) Training a segmentation model on real California museum photos beats synthetic-only training on out-of-state holdouts by +0.696 (Arizona, n=72) and +0.521 (Oregon, n=132) mask mAP50-95, while synthetic training sizes printed toy insects better (median length error 0.094 vs 0.227). (2) A small per-taxon "preprocessor" that routes a specimen crop to its insect order reached a test macro-F1 of 0.70 against a 0.14 majority baseline on out-of-state photos, passing its preregistered usefulness margin, but it scores 0 F1 on Hemiptera (2 test crops) and the planned Diptera family router has no test split at all. (3) Our custody rule (any hash the graph references must resolve to stored bytes) turned two lost-weights defects into eight recorded breaks rather than eight silently trusted results. We report these breaks as results.

---

## 1. Introduction

Physical AI for science fails quietly in two places: the bench, where a robot acts on a measurement nobody checked, and the record, where a reported number cannot be traced back to the bytes that produced it. Hackathon projects are the extreme case: dozens of commits in a day, models trained on borrowed GPUs, outputs written by people and by AI agents together.

We treat the record as part of the instrument. Our contributions are:

1. **A vision-to-sieve lane for BioKEA step 1** with two independent sizers in consensus, a sieve planner, a VERID-style digital-twin preflight [5] and a BugPicker bridge [3] (§2).
2. **Atoms of knowledge (AoK)**: 749 atoms, each with claim, licence in context, status and leaf hash, rolled into one root (`bb85c673…`) and one graph pack shared by every access surface (§3).
3. **Deterministic custody**: Merkle break points, MMR ledgers, LOMO checks and FCO/FCG context objects, with a resolvability invariant that records a BREAK instead of trusting an unresolvable hash (§4).
4. **Preregistered experiments (DAISY-BB-001b, 002a, 004)** reported with their failures (§5).
5. **A Claude-vs-BYO comparison** showing how a second agent's graph differs from ours, top-down from the root to the leaf (§3.3).

## 2. System: the step-1 lane and the modular virtual lab

**Observe.** A USB/AmScope image is sized by YOLO segmentation and by classical morphometrics; sizes are kept only where both agree, and disagreements are flagged instead of sieved blind (`baebugs/measure.py`). Scale comes from a printed ArUco marker. Optionally BugPicker's own detector is a third source.

**Hypothesize.** Narrow-axis width classes map to the kit's real frames, with gentler flow for finer meshes (`baebugs/sieve.py`). Mesh apertures are estimates from bench photos until calibrated from a backlit image (`baebugs/sieve_calibrate.py`).

**Preflight.** A digital twin of the bench checks that each sieve exists and is free, the order, the slots and the water reserve before the arm or ESP32 sieve moves (`baebugs/twin.py`, `baebugs/tower_twin.py`). A 3D bench twin replays runs over time (`dashboard/twin/bench_twin.html`, `site/twin/`).

**Run, verify, hand off.** Each fraction is imaged, predicted vs observed counts update a retention margin (`baebugs/method.py`), and fractions are written as BugPicker `manifest.jsonl` / `objects.jsonl` with `tray_size_class` and `sorting_tray_slot` (`baebugs/bugpicker_bridge.py`).

**Printable, modular parts.** The graph links 91 parametric toy insects (67 California families at size levels, 12 novel outside-CA, 12 fill-in 1–3 mm), 25 lab parts across seven modules (trommel, vortex sieve kit, centrifuge strainer, Opentrons Flex adapters, hand-off carrier) and 4 Opentrons labware definitions (`site/mvp/mvp.json`). These are **concepts**: geometry is watertight and simulated, not tested on specimens (`print/parts/README.md`). Toys are parametric shapes, not replicas.

**Cost (estimates, not quotes).** A separate bench twin built from 16 bench photos (`baebugs-twin/`, v0.1; not yet merged into the repo) adds 8 printable remixes on the SBS footprint (127.76 × 85.48 mm): 96, 24, 15 and 6-position tube racks with Opentrons labware definitions, a cryo grid insert, a lipped frame, a screened grid frame and a honeycomb insert. Each part has its own Merkle tree, and the part roots roll up into one lab root.

| item | ≈ USD |
|---|---|
| all 8 remixes, ~330 g filament at 75% fill | 8 |
| 1 kg PETG spool | 22 |
| digital calipers (to replace photo-estimated dimensions) | 25 |
| **parts kit total** | **≈ 55** |

This is well under the US$200 target, assuming a printer is already available. Prices are 2026 retail estimates, and every dimension not set by a standard is a photo estimate until it is checked with calipers. [TO FILL: price the step-1 sieving parts (trommel, bearings, rod, mesh) to show the full combination stays under US$200.] The racks are tube racks, not tip racks; printed parts are not used at −80 °C or for anything that spins.

## 3. Atoms of knowledge and one graph for every surface

### 3.1 Atoms

Every file is an atom with a claim (`OWN`, `OWN+TERMS`, `THIRD`), the licence that applies *in its context*, a status and a leaf hash (`kg/aok.json`, summarised in `docs/CLAIMS.md`). The current root is `bb85c6734d9e5552…` over 749 atoms: OWN 687, OWN+TERMS 42, THIRD 20. Atoms roll up file → module → repository, so a reviewer can stop at any module root (for example `lab-parts` `a974e369…`) and check only what is under it.

### 3.2 One graph pack, many readers

A single pack, `site/mvp/mvp.json` (root `548b4d8f…`), is read by the MVP page, the `baebugs-graph` CLI, the MCP server (`python -m baebugs.graph_mcp`), `npx github:biobitworks/baebugs` and a Claude plugin/skill. Because every surface reads the same bytes, they all return the same root; a disagreement between surfaces is itself a detectable break. Any atom can be contested through a GitHub issue template that carries the atom address, and a contester can submit their own FCO/FCG JSON for verification (`.github/ISSUE_TEMPLATE/contest.yml`).

### 3.3 Claude vs bring-your-own

`baebugs/compare.py` compares two graphs top-down: roots, then module break points, then leaves (MATCH / DIFFERS / ONLY). In the worked example (`docs/byo_compare_example.json`) a BYO party scales one part by 5% and adds its own tray. The comparison finds the two repository roots differ, isolates the difference to one module (`lab-parts`; the other 14 module roots are SAME), and within it reports 105 leaves MATCH, 1 DIFFERS (`arm_grip_handle.stl`) and 1 ONLY_byo (`byo_flat_tray.stl`). The point is not that the two agree; it is that a disagreement is located in O(depth) steps without either party trusting the other.

## 4. Deterministic custody

- **Merkle break points.** Each milestone and each experimental step ends at a root; the root at every step is a break point that later work can be checked against (`baebugs/explore.py`).
- **MMR ledgers.** Events are appended to Merkle Mountain Ranges, so any past leaf has an inclusion proof against any later root (`baebugs/mmr.py`; e.g. `daisy/impact_mmr.jsonl`, 104 events).
- **LOMO.** Leave-one-level-out (and leave-one-model-out over the toy-insect KG) asks how much each factor or model actually contributes (`baebugs/explore.py`, `baebugs/insect_lomo.py`).
- **FCO/FCG.** One content-addressed custody object per source (web page, GBIF record, camera, model, human); sources hybridize at a break point into a new FCO whose parents are the input roots, so the context a model used can be untangled later. Missing fields stay explicit as `unknown` (`baebugs/fco.py`).
- **Variance is allowed; unhashed steps are not.** Training is `deterministic=false`; the canonical tensor hash of the weights is the identity of each realization.
- **Resolvability invariant.** Every hash the graph references must resolve to stored bytes; otherwise a `custody_break` event is recorded. The graph currently carries **8 breaks** (§5.1).

Frozen protocols, preregistrations and amendments are never edited; corrections are new amendment files (e.g. DAISY-BB-004 amendment 4 corrects amendment 3).

## 5. Experiments

All three experiments were preregistered before data were seen (`daisy/*-prereg*.md`). Labels on real photos come from a YOLOE teacher [7] or from GBIF identifications, so results measure agreement with those silver labels, not accuracy against human review. Status of every run: `OBSERVED_EXPLORATORY`.

### 5.1 Custody breaks as results

| run | what was lost | how it was caught | record |
|---|---|---|---|
| DAISY-BB-001b v6 (6 runs) | trained weights (sha256 recorded, no bytes anywhere) | resolvability invariant | 6 `custody_break` events, `daisy/impact_mmr.jsonl` |
| DAISY-BB-002a v2 (2 runs) | trained weights for CA_only and Synth_only | resolvability invariant | 2 `custody_break` events, idx 96–97 |

Cause, the same in both: the Kaggle kernel's FINISH step exported weights only for runs with status EXECUTED, but EVAL had already relabelled them OBSERVED_EXPLORATORY, so the working directory was deleted with the weights in it (`daisy/results/DAISY-BB-002a/v2/DECISION.md`). The fix (weights hashed every epoch, best.pt copied and re-verified right after training, fail-closed custody check before `results.json`) is in every later kernel. 001b v6 numbers (synth_seg 0.92, real pseudo-labelled specimens 0.25–0.26 mask mAP50-95) are recorded but **cannot be used as evidence**. 002a numbers below are reported with this break attached.

DAISY-BB-004 also failed twice before it ran: a per-epoch values gate could not read the training loss (Ultralytics 8.4.188 stores it as a dict) and, as designed, stopped training after one epoch. Attempts v2 and v3 are kept as evidence of the defect and not interpreted (amendments 3 and 4). A gate that cannot read its input failed closed, which is what it should do.

### 5.2 DAISY-BB-002a: do real California photos help out of state?

Two YOLO segmentation runs, CA_only (real Essig/Calbug photos via GBIF [4]) and Synth_only (synthetic renders), evaluated on held-out states; primary measure mask mAP50-95, tolerance 0.03 (`daisy/results/DAISY-BB-002a/v2/DECISION.md`; 14/14 data custody members OK).

| holdout | photos | CA_only | Synth_only | CA − Synth | verdict |
|---|---|---|---|---|---|
| Arizona | 72 | 0.845 | 0.149 | **+0.696** | SUPPORTED |
| Oregon | 132 | 0.713 | 0.192 | **+0.521** | SUPPORTED |
| Nevada | 8 | 0.537 | 0.039 | +0.498 | not interpreted (n<20) |

Transfer from the CA validation score (0.852) is near zero for Arizona (−0.007) and −0.139 for Oregon. The secondary result runs the other way: on printed-toy renders with exact parametric truth, Synth_only sizes better (median length error 0.094 vs 0.227 at 20 px/mm). For the physical demo, which uses printed toys, that matters. One eval set (`teacher_check`) scores ≈0 for both runs and is flagged, not interpreted.

### 5.3 DAISY-BB-004: per-taxon preprocessors

**Question.** Can small crop classifiers route a specimen to its order, and within an order to its family, so lower or local models only see the taxa they specialise in?

**Data.** 2,627 crops cut from teacher segmentations (train 2,015 CA; val 381 CA; test 231 out-of-state), labelled with GBIF order/family, split by source photo (media-id leakage 0), data root `4d5f2831…`; 2,613 crops CC0, 14 CC BY 4.0 (`daisy/taxon_crops_report.json`). Model yolo11n-cls [6], 224 px, 15 epochs, run locally on Apple MPS after Kaggle's GPU quota ran out (amendments 1–2). Decision rule: USEFUL if test macro-F1 beats the majority-class baseline by more than 0.10.

| run | classes | test crops | test macro-F1 | baseline | verdict |
|---|---|---|---|---|---|
| ORDER | 5 orders + other | 231 | **0.70** [V4: confirm from results.json] | 0.14 | USEFUL |
| FAMILY_Hymenoptera | 6 families + other | 86 | [V4] | [V4] | [V4] |
| FAMILY_Diptera | 3 families + other | **0** | none | none | **no test split** |

Weaknesses we report rather than average away:

- **Hemiptera test F1 is 0.** There are only 2 Hemiptera crops in the out-of-state test set (133 in train), so the score is both zero and nearly uninformative.
- **No Diptera in test at all.** The test set has 0 Diptera crops, so the ORDER router was never tested on flies, and the FAMILY_Diptera router has no test split. It can be reported on CA validation only, which is not out-of-state.
- **The test set is skewed**: Lepidoptera 118 and Hymenoptera 87 of 231. The baseline (always Lepidoptera) has macro-F1 ≈ 0.14 over the five labels present.
- Labels are GBIF identifications (silver), so this measures routing to what the collections say, not verified taxonomy.

[V4: per-class F1 table, val vs test, weights tensor sha and resolvability result for each run, DECISION.md path `daisy/results/DAISY-BB-004/v4/DECISION.md`.]

### 5.4 Sizing methods on museum photos

Against the teacher, a distilled student and FastSAM have median relative size deviations of 0.022 and 0.023 (n≈2,550–2,580), while classical `skimage` thresholding deviates 0.31 (`kg/lomo_methods.json`). Odonata is the hardest order for every learned method (≈0.10). This supports keeping a learned sizer in consensus and using classical morphometrics as a cross-check on clean backgrounds rather than as a primary sizer.

## 6. Licensing in three lines

1. Code, prints, labware, pages, protocols and ledgers written here are ours (MIT).
2. Trained weights are AGPL-3.0 because they come from Ultralytics YOLO [6].
3. Specimen photos belong to the museums (CC0 needs nothing; CC BY needs the rights holder credited). BioKEA and zlite repositories are pinned by commit and sha256, never copied; those with no licence need the owner's permission before reuse (`docs/CLAIMS.md`).

## 7. Use case: an independent open lab

[TO CONFIRM with Byron: describe the Heterodox Labs-style platform and its workflow.] The intended use is a small independent lab or community group that wants to (a) print a sorting kit from the graph, (b) swap in its own models, agents or licence terms, (c) run a sample and (d) publish a result that an outside reviewer can verify without trusting the lab. In baebugs terms: the lab forks the graph, its changes show up as module break points in a BYO comparison (§3.3), its runs append to its own MMR, and a reviewer contests any atom by address. A planned extension alerts the entomologist when a run reaches step *n* through an open-source ticketing tool (not yet built).

## 8. Limitations

- No hardware run on real specimens yet; apertures, tower geometry and damage parameters are placeholders or photo estimates.
- Every real-photo label is silver (YOLOE teacher or GBIF identification). No human-reviewed test set.
- Eight result realizations are custody-broken; 001b needs a v7 rerun with the fixed kernel before it can count as evidence.
- Small, skewed out-of-state test sets (Nevada n=8; 004 test has no Diptera, 2 Hemiptera).
- 004 ran on Apple MPS rather than the preregistered Kaggle GPU (amendments 1–2); weights are numerically different from a GPU run, and their tensor hash is their identity.
- Parts are concepts. Cost figures are retail estimates for printed parts only; the sieving hardware is not yet priced.
- Much of the code and text was written by an AI agent (Claude) under the author's direction; see the statement below.

## 9. Future work

Per-species preprocessors beyond order and family where data allow, tracked on both weights and values and distilled into local models; a Hugging Face release toward a BioKEA novel-bug finder; a dashboard covering every bug, print and part at every level of abstraction; and the step-*n* alert integration.

## Data and code availability

Everything is in https://github.com/biobitworks/baebugs: graph pack `site/mvp/mvp.json`, atoms `kg/aok.json`, protocols and amendments `daisy/`, results `daisy/results/`, ledgers `ledger/` and `daisy/*_mmr.jsonl`, notebooks `notebooks/` (each replayable with swappable data), demo video `docs/demo/baebugs_mvp_demo.mp4`. DAISY-BB-004 weights live on the author's drive and are referenced by hash; per the AGPL they are released with source.

## AI use statement

Claude (Anthropic) wrote much of the code, kernels and text, including this draft, under the author's direction. The author chose the questions, the preregistered rules and what was kept. Copyright in purely AI-generated text is unsettled; the claim rests on human direction and selection (`docs/CLAIMS.md`).

## References

1. Merkle, R. C. (1987). A digital signature based on a conventional encryption function. *CRYPTO '87*, LNCS 293. doi:10.1007/3-540-48184-2_32
2. Merkle Mountain Ranges: append-only accumulator with inclusion proofs. [TO FILL: cite preferred source.]
3. BioKEA. BugPicker. https://github.com/biokea/BugPicker (pinned by commit + sha256).
4. Essig Museum of Entomology / Calbug, via GBIF dataset `5d283bb6-64dd-4626-8b3b-a4e8db5415c3`.
5. Google Research. Grounding AI agents in biological reality: building blocks for autonomous wet labs (VERID). https://research.google/blog/grounding-ai-agents-in-biological-reality-building-blocks-for-autonomous-wet-labs/
6. Jocher, G., Qiu, J. Ultralytics YOLO11. https://github.com/ultralytics/ultralytics (AGPL-3.0).
7. Wang, A. et al. (2025). YOLOE: Real-Time Seeing Anything. *ICCV 2025*. doi:10.1109/iccv51701.2025.02280
