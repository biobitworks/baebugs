# filtration-robot

Demo-day system: a camera looks at a petri dish of mixed objects (pebbles, dry noodles, seeds...), measures their sizes, picks which filters to use, and an SO-101 robot arm swaps those filters into a 3-slot vertical filtration rig.

```
[1] vision        →   [2] planner              →   [3] arm
dish photo → sizes →   current layout + target  →   pick(slot) / place(slot)
→ filter plan          → list of moves              with checks
```

## Layout

| Path | What |
|---|---|
| `arm/` | SO-101 tools: motor probe, position watcher, leader→follower mirroring, calibration backups |
| `vision/` | Object sizing from dish photos (`dish_sizer.py`), sample images |
| `CLAUDE.md` | Project notes: hardware facts, design decisions, build order |

## Setup (Windows)

```powershell
python -m venv $env:USERPROFILE\lerobot-env
& $env:USERPROFILE\lerobot-env\Scripts\python.exe -m pip install -r requirements.txt
```

Commands below use that environment's `python.exe` directly; no activation needed.

## Arm

- **Power:** leader arm on the **5 V** supply, follower on **12 V**. 12 V on the leader triggers over-voltage errors on its motors.
- **Ports:** leader = COM5, follower = COM6 (check with `arm/probe_arms.py COM5 COM6`; the leader's motors read ~5 V).
- **Mirror the leader:** `arm\mirror.cmd` (or `mirror` if it's copied into a folder on your PATH). Hold the follower before pressing Ctrl+C: it goes limp when mirroring stops.
- **Calibration backups:** `arm/calibration/` mirrors `%USERPROFILE%\.cache\huggingface\lerobot\calibration\` (`robots\so_follower\`, `teleoperators\so_leader\`). Copy them back if that cache is lost.

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\probe_arms.py COM5 COM6   # voltage, errors, positions (read-only)
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\watch_arm.py COM6 15       # record min/max positions while you move joints
```

## Vision

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\dish_sizer.py vision\samples\dish_phone_01.webp --px-per-mm 9.18 --out vision\output\annotated.png --json vision\output\objects.json
```

Outputs each object's length and width in mm (width decides whether it passes a filter) plus an annotated image. `--px-per-mm` must be measured for each camera setup.

Then turn the measurements into a filter plan for the rig (filters stacked coarse on top to fine at the bottom):

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\filter_plan.py vision\output\objects.json --json vision\output\plan.json --image vision\samples\dish_phone_01.webp --out vision\output\plan.png
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\filter_plan.py vision\output\objects.json --target 3 6   # catch 3-6 mm objects on one shelf
```

- **split** (default): picks the 3 filters that sort the objects into the most separate groups, with hole sizes as far from any object as possible.
- **target**: picks filters so one shelf catches objects whose width is in the given range (later selectable with a microcontroller button).
- Hole sizes live in `vision/filters.json` and are **placeholders** until the real filters are measured.
- Tests: `cd vision; python -m unittest test_filter_plan`.

Photo tips that matter more than code: light from underneath (backlight) or a plain matte coloured background, camera straight overhead at a fixed height, full-resolution images, objects not touching.
