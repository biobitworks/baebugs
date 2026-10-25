# What baebugs claims, and under which licence

Every file is an *atom* with a claim, a licence in context, a status and a hash (full list for agents: [`kg/aok.json`](../kg/aok.json)). This page is the short version. It records what the licences say; it is not legal advice.

**AoK root:** `e8cc45601b3a21ab28d10fd136623e2839040af70876cd779dc19d54e275f98e` · 725 atoms · OWN 660 · OWN+TERMS 45 · THIRD 20

| claim | meaning |
|---|---|
| **OWN** | written here; claimable; MIT |
| **OWN+TERMS** | written here and claimable; the listed outside terms also apply in this context |
| **THIRD** | not ours; used under its licence; credited, pinned by hash, never claimed |

## Ours (biobitworks), by module

| module | atoms | claim | outside terms that apply here | module root |
|---|---|---|---|---|
| custody-ledgers | 33 | OWN 33 | none | `74b10e7d4a0a` |
| daisy-protocols | 13 | OWN 13 | none | `504e1182f96e` |
| daisy-results | 5 | OWN+TERMS 5 | gbif-media, ultralytics | `cc24bbbbe630` |
| dashboards | 16 | OWN 16 | none | `350619827ff6` |
| docs | 21 | OWN 21 | none | `b36b5f07dd87` |
| kaggle-kernels | 10 | OWN+TERMS 10 | gbif-media, ultralytics | `423690e09c02` |
| knowledge-graph | 5 | OWN+TERMS 5 | gbif-media | `f76004ad5e8e` |
| lab-parts | 106 | OWN 106 | none | `a974e369a4d0` |
| mvp-site | 29 | OWN 29 | none | `e07531bd1203` |
| notebooks | 16 | OWN 16 | none | `a20c483ea79c` |
| opentrons-modules | 13 | OWN+TERMS 13 | opentrons | `40b680b50dba` |
| python-package | 75 | OWN 65, OWN+TERMS 10 | opentrons, ultralytics | `c326a08368ba` |
| repo-meta | 6 | OWN 6 | none | `32548ae54105` |
| tests | 31 | OWN 29, OWN+TERMS 2 | opentrons, ultralytics | `9b86c6884ca1` |
| toy-insects | 326 | OWN 326 | none | `6f32a71b22ca` |

## Not ours (used, credited, never claimed)

| thing | licence | what it means for us |
|---|---|---|
| [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) | AGPL-3.0 | models trained or run with it are AGPL-3.0 unless an Ultralytics Enterprise licence is held |
| [GBIF specimen photos (museum collections)](https://www.gbif.org) | CC0-1.0 / CC-BY-4.0 | CC BY images need the rights holder credited in anything derived (crops, figures); see daisy/licences_gbif.json |
| [Opentrons Python API + labware schema](https://github.com/Opentrons/opentrons) | Apache-2.0 | our labware and protocols are our own; 'Opentrons' is their trademark, no endorsement implied |
| [three.js](https://github.com/mrdoob/three.js) | MIT | none beyond keeping its notice |
| [manifold3d](https://github.com/elalish/manifold) | Apache-2.0 | none on the generated meshes |
| [trimesh](https://github.com/mikedh/trimesh) | MIT | none on the generated meshes |
| [Kaggle notebooks (GPU)](https://www.kaggle.com/terms) | Kaggle Terms of Use | private datasets/kernels stay private; outputs are ours |
| [Claude (Anthropic)](https://www.anthropic.com/legal) | Anthropic Terms (outputs assigned to the user) | biobitworks directed, reviewed and chose the work; copyright in purely AI-generated text is unsettled law, so the claim rests on the human direction and selection |
| [BioKEA/BugPicker](https://github.com/BioKEA/BugPicker) | GPL-3.0 | pinned by commit + sha256 root only, never copied into baebugs |
| [BioKEA/BugPicker-arm-demo](https://github.com/BioKEA/BugPicker-arm-demo) | GPL-3.0 | pinned by commit + sha256 root only, never copied into baebugs |
| [BioKEA/BugSorter](https://github.com/BioKEA/BugSorter) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [BioKEA/PlateReader](https://github.com/BioKEA/PlateReader) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [BioKEA/prompt-to-print](https://github.com/BioKEA/prompt-to-print) | MIT | pinned by commit + sha256 root only, never copied into baebugs |
| [zlite/B601](https://github.com/zlite/B601) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [zlite/disperser](https://github.com/zlite/disperser) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [zlite/entosieve](https://github.com/zlite/entosieve) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [zlite/liquid-handler](https://github.com/zlite/liquid-handler) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [zlite/liquid-handler-marlin](https://github.com/zlite/liquid-handler-marlin) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [zlite/plate-gripper](https://github.com/zlite/plate-gripper) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |
| [zlite/railprinter](https://github.com/zlite/railprinter) | no licence (all rights reserved) | pinned by commit + sha256 root only, never copied into baebugs; ask the owner before reuse |

## The three things to remember

1. **Code, prints, labware, pages, protocols and ledgers written here are ours (MIT).** That includes the parametric toy insects, the lab parts and the Opentrons labware.
2. **Trained weights are AGPL-3.0** because they come from Ultralytics YOLO; anything shipped with them must offer its source under AGPL-3.0 (or hold an Ultralytics licence).
3. **Specimen photos belong to the museums.** CC0 needs nothing; CC BY needs the rights holder credited wherever crops or figures appear. BioKEA and zlite repos are pinned by hash, not copied; the ones with no licence need the owner's permission before any reuse.
