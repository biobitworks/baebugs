"""Live view of a camera (default: the microscope, camera 1) with a focus meter.

Put something with fine detail in view (e.g. ruler ticks), turn the focus knob until the
sharpness number peaks, then press Space to save a full-resolution photo.

Usage: python live_view.py [--camera 1] [--save-dir vision/captures]
Keys: Space = save photo, R = reset best sharpness, Esc = quit
"""
import argparse
import time
import tkinter as tk
from pathlib import Path

import cv2
from PIL import Image, ImageTk


def sharpness(frame):
    """Variance of the Laplacian over the central half of the image: higher means sharper."""
    h, w = frame.shape[:2]
    center = frame[h // 4:3 * h // 4, w // 4:3 * w // 4]
    gray = cv2.cvtColor(cv2.resize(center, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


class Viewer:
    def __init__(self, root, cap, save_dir):
        self.root, self.cap, self.save_dir = root, cap, save_dir
        self.frame, self.best = None, 0.0
        self.message, self.message_until = "", 0.0
        # fit the preview on screen (tkinter isn't DPI-aware, so use the logical screen size)
        self.max_w = int(root.winfo_screenwidth() * 0.8)
        self.max_h = int(root.winfo_screenheight() * 0.7)

        self.image_label = tk.Label(root)
        self.image_label.pack()
        self.status = tk.Label(root, font=("Segoe UI", 13), anchor="w")
        self.status.pack(fill="x", padx=8, pady=4)
        buttons = tk.Frame(root)
        buttons.pack(pady=(0, 8))
        tk.Button(buttons, text="Save photo (Space)", command=self.save).pack(side="left", padx=4)
        tk.Button(buttons, text="Reset best (R)", command=self.reset).pack(side="left", padx=4)
        root.bind("<space>", lambda e: self.save())
        root.bind("r", lambda e: self.reset())
        root.bind("<Escape>", lambda e: root.destroy())
        self.update()

    def update(self):
        ok, frame = self.cap.read()
        if ok:
            self.frame = frame
            score = sharpness(frame)
            self.best = max(self.best, score)
            h, w = frame.shape[:2]
            scale = min(self.max_w / w, self.max_h / h, 1.0)
            preview = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)))
            self.image_label.configure(image=img)
            self.image_label.image = img  # keep a reference so Tk doesn't discard it
            text = f"Sharpness {score:,.0f}   best {self.best:,.0f}   ({100 * score / self.best:.0f}% of best)   {w}x{h}"
            if time.time() < self.message_until:
                text += f"   |   {self.message}"
            self.status.configure(text=text)
        self.root.after(10, self.update)

    def save(self):
        if self.frame is None:
            return
        self.save_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}"
        path = self.save_dir / f"capture_{stamp}.png"
        cv2.imwrite(str(path), self.frame)
        self.message, self.message_until = f"saved {path.name}", time.time() + 3

    def reset(self):
        self.best = 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=1, help="camera number (microscope is 1 on this laptop)")
    ap.add_argument("--width", type=int, default=2048)
    ap.add_argument("--height", type=int, default=1536)
    ap.add_argument("--save-dir", type=Path, default=Path(__file__).with_name("captures"))
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit(f"camera {args.camera} not available (unplugged, or open in another app?)")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    root = tk.Tk()
    root.title(f"Live view - camera {args.camera}")
    Viewer(root, cap, args.save_dir)
    try:
        root.mainloop()
    finally:
        cap.release()


if __name__ == "__main__":
    main()
