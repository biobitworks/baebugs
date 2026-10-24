"""First-pass object sizing for a petri dish photo.

Finds the dish, separates objects from the background by colour difference,
and measures each object's length and width (the short side is what decides
whether it fits through a filter's holes).

Usage: python dish_sizer.py IMAGE --px-per-mm 9.18 [--out annotated.png] [--json objects.json]
"""
import argparse
import json

import cv2
import numpy as np


def find_dish(img):
    """Return (cx, cy, r) of the dish's outer rim, or None."""
    gray = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 5)
    w = gray.shape[1]
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.5, minDist=w,
        param1=100, param2=40, minRadius=int(0.25 * w), maxRadius=int(0.6 * w),
    )
    if circles is None:
        return None
    cx, cy, r = circles[0][0]
    return int(cx), int(cy), int(r)


def local_background(lab, mask, size):
    """Estimate the background colour around each pixel with a large median filter.

    Pixels outside the dish are filled with the dish's median colour first so the rim doesn't bleed in.
    """
    filled = lab.copy()
    filled[mask == 0] = np.median(lab[mask > 0], axis=0)
    small = cv2.resize(filled, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA).astype(np.uint8)
    k = max(3, (size // 4) | 1)
    bg = np.dstack([cv2.medianBlur(small[:, :, i], k) for i in range(3)])
    return cv2.resize(bg, (lab.shape[1], lab.shape[0]), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def segment(img, mask, threshold, bg_size, lightness_weight):
    """Mark pixels whose colour differs from the local background by more than `threshold` (CIELAB units).

    Lightness differences are down-weighted because shadows mostly change lightness, not colour.
    """
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    diff = lab - local_background(lab, mask, bg_size)
    diff[:, :, 0] *= lightness_weight
    distance = np.linalg.norm(diff, axis=2)
    objects = ((distance > threshold) & (mask > 0)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    objects = cv2.morphologyEx(objects, cv2.MORPH_OPEN, kernel)
    objects = cv2.morphologyEx(objects, cv2.MORPH_CLOSE, kernel, iterations=2)
    return objects, distance


def measure(objects, px_per_mm, min_area_mm2):
    contours, _ = cv2.findContours(objects, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    results = []
    for c in contours:
        area_mm2 = cv2.contourArea(c) / px_per_mm**2
        if area_mm2 < min_area_mm2:
            continue
        (cx, cy), (a, b), angle = cv2.minAreaRect(c)
        results.append({
            "center_px": [round(cx), round(cy)],
            "length_mm": round(max(a, b) / px_per_mm, 1),
            "width_mm": round(min(a, b) / px_per_mm, 1),
            "area_mm2": round(area_mm2, 1),
            "contour": c,
            "rect": ((cx, cy), (a, b), angle),
        })
    results.sort(key=lambda o: -o["area_mm2"])
    for i, o in enumerate(results, start=1):
        o["id"] = i
    return results


def annotate(img, dish, inner_r, results):
    out = img.copy()
    if dish:
        cv2.circle(out, dish[:2], inner_r, (255, 200, 0), 1)
    for o in results:
        cv2.drawContours(out, [o["contour"]], -1, (0, 255, 0), 2)
        box = cv2.boxPoints(o["rect"]).astype(int)
        cv2.drawContours(out, [box], -1, (255, 0, 255), 1)
        x, y = o["center_px"]
        label = f"#{o['id']} {o['length_mm']}x{o['width_mm']}mm"
        cv2.putText(out, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(out, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--px-per-mm", type=float, required=True)
    ap.add_argument("--threshold", type=float, default=20, help="colour difference from background (CIELAB)")
    ap.add_argument("--inner", type=float, default=0.72, help="fraction of the rim radius to analyse (skips the rim)")
    ap.add_argument("--bg-size", type=int, default=241, help="background estimation window, px (bigger than the largest object)")
    ap.add_argument("--lightness-weight", type=float, default=0.5, help="weight of lightness vs colour (shadows are lightness)")
    ap.add_argument("--min-area", type=float, default=0.5, help="ignore blobs smaller than this, mm^2")
    ap.add_argument("--out", default="annotated.png")
    ap.add_argument("--json")
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"cannot read {args.image}")
    dish = find_dish(img)
    mask = np.zeros(img.shape[:2], np.uint8)
    if dish:
        inner_r = int(dish[2] * args.inner)
        cv2.circle(mask, dish[:2], inner_r, 255, -1)
        print(f"dish: center {dish[:2]}, rim radius {dish[2]} px ({2 * dish[2] / args.px_per_mm:.0f} mm across)")
    else:
        inner_r = 0
        mask[:] = 255
        print("dish not found; analysing the whole image")

    objects, _ = segment(img, mask, args.threshold, args.bg_size, args.lightness_weight)
    results = measure(objects, args.px_per_mm, args.min_area)
    cv2.imwrite(args.out, annotate(img, dish, inner_r, results))

    print(f"{len(results)} objects")
    for o in results:
        print(f"  #{o['id']}: {o['length_mm']} x {o['width_mm']} mm, area {o['area_mm2']} mm2, at {o['center_px']}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump([{k: v for k, v in o.items() if k not in ("contour", "rect")} for o in results], f, indent=2)


if __name__ == "__main__":
    main()
