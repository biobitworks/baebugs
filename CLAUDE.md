# Project notes for Claude

Team demo-day project. See README.md for layout and commands. These notes hold the hardware facts and decisions agreed so far.

## Pipeline

1. **Vision:** petri dish (pebbles, dry noodles, seeds, crumbs; ~1–20 mm) photographed; objects measured by size. Objects are too big for a microscope's field of view, so the demo uses an overhead camera. The "real" system would use an automated microscope.
2. **Planner:** sizes → which of the 5 filters go into the 3 rig slots (coarse-to-fine order is a rule) → list of moves.
3. **Arm:** SO-101 follower moves filters between the rig and a side storage shelf.

## Hardware (laptop: Windows 11, AMD Ryzen AI 9 / Radeon 880M, no NVIDIA GPU)

- SO-101 leader = **COM5** (CH343 serial 5AB0183348), LeRobot id `my_leader`, **5 V supply**. Mixed 7.4 V-class motors; motor 2's max voltage limit is 8.0 V. It was once fed 12 V and all motors flagged over-voltage (status bit 0).
- SO-101 follower = **COM6** (CH343 serial 5B14030659), id `my_follower`, 12 V "Pro" motors (max limit 14.0 V).
- Both on a USB hub. Feetech STS3215, protocol 0, 1 Mbaud, IDs 1–6 (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper).
- LeRobot 0.6.1 in `C:\Users\lowoj\lerobot-env` (Python 3.13). Call `Scripts\*.exe` / `python.exe` directly.
- Calibration lives in `~\.cache\huggingface\lerobot\calibration\`; backups in `arm/calibration/`. Follower gripper range was hand-set to 1060–2214 after calibration recorded a bogus 0–4087 (measured with `arm/watch_arm.py`).
- `mirror` command: `C:\Users\lowoj\.local\bin\mirror.cmd` (copy in `arm/mirror.cmd`).
- Training must happen off-laptop (Colab / HF Jobs); small policies like ACT can run on the CPU.

## Gotchas

- Only one program can open a COM port; stop teleoperation before probing.
- Stopping teleoperation disables follower torque: it drops if unsupported.
- Paths under the Claude temp/scratchpad folder exceed Windows MAX_PATH; Python and PowerShell 5.1 fail on them. Run scripts from short paths.
- Ruler-tick detection for scale is unreliable (glare, scratches); prefer a fixed camera height or a printed square of known size.

## Arm design decisions

- Movement mostly scripted: tight fixtures (rails, back stop, chamfered slot openings, self-centring handle on each filter) + teach-and-repeat poses recorded with the leader. A learned policy (ACT) is a stretch goal, not the critical path.
- Free checks from motors: gripper closes fully = missed grab; load spike on insert = jam → back off and retry.
- Wrist camera (USB webcam) with ArUco markers: final-approach alignment, filter identity / seated check, startup inventory sweep.
- Each filter has a fixed home slot in storage (5 spots). Worst case 6 pick-and-place moves per reconfiguration.
- A hand-typed plan is the demo-day fallback if vision fails.
- Microcontroller (user wants one): optional and off the critical path, USB serial text protocol, system must run with it unplugged. Ideas: status screen (user's first pick, deferred), per-slot status LEDs, slot-seated sensors, start button, backlight box for the dish. Real e-stop = inline power switch on the follower's 12 V supply.

## Build order (shelves are still being built)

- Now: reach/clearance check of the planned shelf dimensions with the leader (urgent); **vision sizing** (current focus); teach-and-repeat tool tested with free-air poses; planner logic.
- When shelves arrive: record poses per slot → pick/place primitives with checks → full demo from a hand-typed plan → plug in the vision plan → wrist camera checks.

## Vision status

`vision/dish_sizer.py` v0: Hough-circle dish mask, local-background colour difference in CIELAB with lightness down-weighted (shadows), min-area-rect length × width in mm. On `vision/samples/dish_phone_01.webp` (720×960 phone photo, 9.18 px/mm, 63 mm dish): finds 7/8 objects; rice grain splits (low contrast), shadows inflate the pasta tube and red seed, 3 false blobs from the dish wall. Next: better photo setup (backlight or plain coloured background, fixed overhead camera, full resolution), then size groups from the 5 filters' hole sizes (not yet known) → filter plan JSON.
