# Project notes for Claude

Team demo-day project. See README.md for layout and commands. These notes hold the hardware facts and decisions agreed so far.

**Project map:** https://claude.ai/artifact/LXUP6UCqxiUcj7pKq4E9h3 (private to the owner unless shared). It is the team's task tracker: tasks live in its database collection `tasks` (fields `area` = vision|plan|planner|arm|rig|mcu|demo|setup, `title`, `detail`, `status` = doing|next|blocked|decide|later|done, `order`, optional `who`, `updatedAt` ISO date). When work here finishes or new work comes up, update those rows with the ArtifactData tool (read first, pin `if_version`) rather than republishing the page.

## Pipeline

1. **Vision:** petri dish (pebbles, dry noodles, seeds, crumbs; ~1–20 mm) photographed; objects measured by size. The "real" system would use an automated microscope, but for the demo objects the team's iQCrew microscope zooms in too far (tested 2026-10-24), so the demo uses an overhead camera (phone or USB webcam, still to be chosen) with a backlight. The microscope's camera is an AmScope MD300A: plain UVC, camera index 1 on this laptop, 2048×1536, no vendor software needed (`vision/live_view.py` shows it with a focus meter).
2. **Planner:** sizes → which of the 5 filters go into the 3 rig slots (coarse-to-fine order is a rule) → list of moves.
3. **Arm:** SO-101 follower moves filters between the rig and a side storage shelf.

**Closed loop (user's design, 2026-10-24):** the demo sample will likely be about two layers with pile-up, so per-object measuring of the first photo won't work. Instead:
- First photo of the pile → rough estimate of which of the 9 types are present and how much (patch classifier on colour/texture, trained from single-type photos, plus a per-type reference size table) → first 3 filters chosen **coarse-first**, targeting the largest common objects.
- Each time the robot changes a filter it photographs that filter's catch (recommended: a fixed inspection spot under the overhead camera, so the calibration holds) → identify the catch → update the sample estimate → re-plan the next filter change.
- Every capture is logged (run, step, filter, and the size band it implies: caught by hole h_i, passed h_{i-1}). The filters act as free size labels for training, and the band is a consistency check on the classifier (e.g. "rice" on a 5–8 mm filter is impossible), so retraining on new captures doesn't reinforce its own mistakes.
- Limits: the camera sees only the top layer, and shaking makes small items sink. Piles need front lighting (colour); a backlight would turn a pile into one shadow.
- Open questions: what happens to a catch after it's photographed (re-poured? by whom?); what the filter mesh looks like as a photo background.

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

Demo objects: 9 types (big curved pasta, pasta tube, black wild-rice grain, red seed, white rice, oat/beige grain, small crumb, small grey seed, tiny black seed); the real demo dish will hold several of each.

Dish: 63 mm across; flat floor out to ~24 mm radius, side wall 24–27 mm, rim to ~31.5 mm (consistent across all 3 samples once scale is right).

`vision/ruler_scale.py`: px/mm from ruler mm ticks (autocorrelation spacing, shortest strong peak to avoid the 2x long/short-tick harmonic, then line fit; strips with fit rms > 1 px ignored). Samples: 01 = 9.12, 02 = 12.89, 03 = 11.84 px/mm (02 vs 03 differ 9%: phone height changed).

Webcam (XWF-1080P, 1920×1080) is mounted over the dish on white printer paper. Calibrated 2026-10-24 from `vision/samples/webcam_calibration_ruler.webp` (metal ruler mm ticks): **13.9 px/mm**, stored in `vision/calibration.json` and used by dish_sizer when `--px-per-mm` is omitted; the dish measures ~62 mm, matching the phone photos. The ruler's right end reads ~3% lower, so a slight tilt remains. A ruler under the dish ruins segmentation (metal stripes behind objects, background model skewed); keep it beside the dish, or out of the photo once calibrated. A ruler at the top of the frame read 14.6 px/mm, so expect up to ~5% scale error across the frame until the camera is levelled or calibrated with the ruler where the dish sits.

calibration.json also holds the webcam setup's segmentation settings, applied only when `--px-per-mm` is omitted (explicit flags win): `threshold` 10 (pale yellow on white paper differs by only ~11 colour units; red seed ~53, empty floor ~2) and `floor_mm` 52. Dish finding: Hough was dropped. `fit_rim` brute-forces dish-sized circles (28–34 mm radius) with at least 80% of the rim in frame (the dish often runs off the bottom edge), scoring the **median** gradient across the circle (radial) on a 1/4-size image, then refines at full size. Median, not mean, so circles borrowing part of the ruler's strong straight edge lose. Correct on all 21 samples; ~3 s per photo.

`vision/pile_types.py` (rough per-type estimate for piles): 2.5 mm squares on the dish floor, 13 colour/texture features, OpenCV random forest. Training list in `vision/training.json` (single-type photos; `packed` photos label every floor square, others use segmentation with a per-photo `label_threshold`: 10 for pale types, 20 for dark). `set2_yellow_grain` is excluded (partly packed: the background model takes the grain colour as floor). Leave-one-photo-out check with 12 photos: red seed 93%, white rice 83%, pasta tube 66%, dark seed 54%, oat 38%, background 67% (empty floor most often misread as dark seed/oat/tube). Mixed piles: plausible rough map; dark seed over-counted, rice/oat under-counted, untrained curved/flat pasta fall into "pasta tube". Model files in `vision/models/` are git-ignored; retrain in ~1 min. A marked fixed spot plus `dish_center_px` in calibration.json is still the most robust option for the demo; `--dish-center X Y` overrides.

First full webcam set (`samples/webcam_set1_*.webp`, red light, white paper): spread-out objects measure well; packed or piled dishes (couscous, white rice, mixed) fail because the background model needs visible empty floor, and touching objects merge. Rough sizes (median length × width, mm): red seed 6.3 × 3.8, oat grain 7.0 × 3.5, small dark seed 2.0 × 1.4, pasta tube 6.7 × 5.3. Open question for the user: how dense the real demo sample will be (spread in one layer vs a pile); a pile needs touching-object splitting or a trained instance-segmentation model. On `samples/webcam_white_01.webp` with `--dish-center 893 610`: 8 of 9 objects found (rice only partly), 2 false blobs from a light streak on the wall. Earlier webcam captures used a triangular scale ruler (not cm; likely an engineer's inch scale) and were unreliable for scale.

`vision/dish_sizer.py`: Hough circle gives only the dish centre (it locks onto different rings); the search uses dish-sized radii in mm, relaxes edge thresholds for faint rims on white paper, ignores circles that don't fit in the photo (rulers create border-centred ones) and takes the median of the top candidates. Analysed area is `--floor-mm` (default 48) around it. Background = quadratic surface per CIELAB channel refit 4x without outliers. Darkening is down-weighted (`--shadow-weight` 0.5), lightening is not (pale objects). Status on the phone photos (tan desk, ceiling lights): rice, red seed, small seeds, black grain OK; big pale curved pasta fragments; oat grain partly missed; ceiling-light reflection on the dish wall becomes a false object; touching objects merge (tube + black grain). Further tuning on these photos has hit its limit — next step is the photo setup (backlight best, else matte coloured background + diffuse light, fixed overhead camera, full resolution), then touching-object splitting (watershed) since the real dish has several of each type.

`vision/filter_plan.py` reads dish_sizer's objects JSON and writes the plan JSON the arm planner will consume (`rig: {top, middle, bottom} -> filter id`). An object is caught by the first filter (top→bottom) whose hole <= its width. Modes: `split` (default; maximise non-empty fractions, then the log-ratio gap between any width and any hole) and `target MIN MAX` (coarsest hole <= MIN catches, finest hole > MAX guards above; filters in between are excluded). User wants target mode selectable by a microcontroller button later. Hole sizes in `vision/filters.json` are placeholders (1.5/3/5/8/12 mm). 2D width ignores thickness, so flat objects may pass a filter their measured width says they wouldn't.
