import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import queue

import cv2
import numpy as np
from PIL import Image, ImageTk

from detector import ANPRProcessor, draw_boxes

MODEL_PATH = Path("best.pt")


def cv2_to_tk(image: np.ndarray, max_width: int = 600, max_height: int = 400) -> ImageTk.PhotoImage:
    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return ImageTk.PhotoImage(Image.new("RGB", (1, 1)))
    scale = min(max_width / w, max_height / h, 1.0)
    new_w, new_h = int(w * scale), int(h * scale)
    new_w = max(new_w, 1)
    new_h = max(new_h, 1)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(rgb))


class ANPRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ANPR — Licence Plate Recognition")
        self.root.geometry("1200x800")
        self.root.minsize(900, 500)

        self.processor = None
        self.current_image_path = None
        self.result_queue = queue.Queue()

        self._build_ui()

    def _ensure_processor(self) -> bool:
        if self.processor is not None:
            return True
        return self._reload_model(silent=True)

    def _build_ui(self):
        self.top_frame = ttk.Frame(self.root, padding=5)
        self.top_frame.pack(fill=tk.X)

        ttk.Label(self.top_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.model_var = tk.StringVar(value=str(MODEL_PATH))
        ttk.Entry(self.top_frame, textvariable=self.model_var, width=40).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(self.top_frame, text="Select Photo", command=self.select_photo).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_frame, text="Load Model", command=self._load_model_click).pack(side=tk.LEFT, padx=5)

        self.main_pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pw.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.left_frame = ttk.LabelFrame(self.main_pw, text="Detection", padding=5)
        self.main_pw.add(self.left_frame, weight=3)

        self.main_canvas = tk.Canvas(self.left_frame, bg="#1a1a1a", highlightthickness=0)
        self.main_canvas.pack(fill=tk.BOTH, expand=True)
        self.main_canvas.bind("<Configure>", lambda e: self._redraw_main())

        self.right_frame = ttk.Frame(self.main_pw, padding=5)
        self.main_pw.add(self.right_frame, weight=2)

        self.plates_frame = ttk.LabelFrame(self.right_frame, text="Recognized Plates", padding=5)
        self.plates_frame.pack(fill=tk.BOTH, expand=True)

        self.plates_canvas = tk.Canvas(self.plates_frame, bg="#1a1a1a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.plates_frame, orient=tk.VERTICAL, command=self.plates_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.plates_canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.plates_canvas.configure(
            scrollregion=self.plates_canvas.bbox("all")
        ))

        self.plates_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="scrollable")
        self.plates_canvas.configure(yscrollcommand=scrollbar.set)

        self.plates_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.plates_canvas.bind("<Configure>", lambda e: self.plates_canvas.itemconfig(
            "scrollable", width=e.width
        ))

        self.bottom_frame = ttk.Frame(self.root, padding=3)
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Ready — load a model and select a photo")
        ttk.Label(self.bottom_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(self.bottom_frame, mode="indeterminate")

        self._main_photo = None
        self._original_img = None
        self._results_data = []

    def _load_model_click(self):
        self._reload_model(silent=False)

    def _reload_model(self, silent: bool = False) -> bool:
        model_path = self.model_var.get()
        self.status_var.set(f"Loading model: {model_path}...")
        self.root.update_idletasks()
        try:
            self.processor = ANPRProcessor(model_path)
            self.status_var.set(f"Model loaded: {model_path}")
            return True
        except FileNotFoundError:
            msg = f"Model file not found: {model_path}"
            self.status_var.set(msg)
            if not silent:
                messagebox.showerror("Model Error", msg)
            return False
        except Exception as e:
            msg = str(e)
            self.status_var.set(f"Failed to load model: {msg}")
            if not silent:
                messagebox.showerror("Model Error", msg)
            return False

    def select_photo(self):
        path = filedialog.askopenfilename(
            title="Select a photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return

        if not self._ensure_processor():
            return

        self.current_image_path = path
        self._clear_plates()
        self._main_photo = None
        self.main_canvas.delete("all")
        self._display_main_image(Path(path))
        self._run_detection(Path(path))

    def _display_main_image(self, image_path: Path):
        img = cv2.imread(str(image_path))
        if img is None:
            return
        self._original_img = img
        photo = cv2_to_tk(img)
        self._main_photo = photo
        self._redraw_main()

    def _redraw_main(self):
        if self._main_photo is None:
            return
        cw = self.main_canvas.winfo_width()
        ch = self.main_canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        self.main_canvas.delete("all")
        self.main_canvas.create_image(cw // 2, ch // 2, image=self._main_photo, anchor=tk.CENTER)

    def _run_detection(self, image_path: Path):
        self.progress.pack(side=tk.LEFT, padx=(10, 0))
        self.progress.start()
        self.status_var.set("Processing...")

        thread = threading.Thread(target=self._detect_thread, args=(image_path,), daemon=True)
        thread.start()
        self.root.after(100, self._check_result)

    def _detect_thread(self, image_path: Path):
        try:
            results = self.processor.process(str(image_path))
            self.result_queue.put(("ok", results))
        except Exception as e:
            self.result_queue.put(("error", str(e)))

    def _check_result(self):
        try:
            status, data = self.result_queue.get_nowait()
            self.progress.stop()
            self.progress.pack_forget()
            if status == "ok":
                self._show_results(data)
            else:
                self.status_var.set(f"Error: {data}")
                messagebox.showerror("Detection Error", data)
        except queue.Empty:
            self.root.after(100, self._check_result)

    def _draw_main_boxes(self, results):
        img = self._original_img.copy()
        boxes = [r["box"] for r in results]
        img_with_boxes = draw_boxes(img, boxes)
        self._main_photo = cv2_to_tk(img_with_boxes)
        self._redraw_main()

    def _show_results(self, results):
        self._results_data = results
        self._draw_main_boxes(results)
        if not results:
            self.status_var.set("No plates detected.")
            ttk.Label(self.scrollable_frame, text="No licence plates detected.",
                      foreground="gray").pack(pady=20)
            return

        self.status_var.set(f"Found {len(results)} plate(s)")

        for i, r in enumerate(results):
            plate_text = r["plate_text"] or "(not recognised)"
            crop = r["crop"]
            variants = r.get("variants", {})

            frame = ttk.Frame(self.scrollable_frame, padding=5)
            frame.pack(fill=tk.X, pady=5)

            header = ttk.Frame(frame)
            header.pack(fill=tk.X)
            ttk.Label(header, text=f"Plate {i + 1}:", font=("", 11, "bold")).pack(side=tk.LEFT)

            text_label = ttk.Label(frame, text=plate_text, font=("Courier", 16, "bold"),
                                   foreground="#00cc00")
            text_label.pack(anchor=tk.W, pady=(0, 5))

            if r["raw_text"] and r["raw_text"] != plate_text:
                ttk.Label(frame, text=f"Raw OCR: {r['raw_text']}",
                          foreground="gray", font=("", 9)).pack(anchor=tk.W)

            crop_row = ttk.Frame(frame)
            crop_row.pack(fill=tk.X, pady=(2, 5))
            if crop is not None and crop.size > 0:
                plate_photo = cv2_to_tk(crop, max_width=300, max_height=80)
                lbl = ttk.Label(crop_row, image=plate_photo)
                lbl.image = plate_photo
                lbl.pack(side=tk.LEFT, padx=(0, 5))
                ttk.Label(crop_row, text="Crop", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(0, 15))

            if variants:
                show_variants_btn = ttk.Button(
                    frame, text="Show preprocessing variants",
                    command=lambda b=None, pf=frame, v=variants: self._toggle_variants(pf, v)
                )
                show_variants_btn.pack(anchor=tk.W, pady=(2, 0))

            ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 0))

    def _toggle_variants(self, parent_frame, variants):
        existing = None
        for child in list(parent_frame.winfo_children()):
            if hasattr(child, "_variant_grid"):
                existing = child
                break

        if existing is not None:
            existing.destroy()
            for child in list(parent_frame.winfo_children()):
                if isinstance(child, ttk.Button) and "processing" in str(child.cget("text")).lower():
                    child.configure(text="Show preprocessing variants")
            return

        for child in list(parent_frame.winfo_children()):
            if isinstance(child, ttk.Button) and "processing" in str(child.cget("text")).lower():
                child.configure(text="Hide preprocessing variants")

        grid = ttk.Frame(parent_frame)
        grid._variant_grid = True
        grid.pack(fill=tk.X, pady=5)

        cols = 4
        row = 0
        col = 0

        for name in variants:
            img = variants[name]
            cell = ttk.Frame(grid, padding=2)
            cell.grid(row=row, column=col, padx=2, pady=2)

            photo = cv2_to_tk(img, max_width=100, max_height=40)
            lbl = ttk.Label(cell, image=photo)
            lbl.image = photo
            lbl.pack()

            ttk.Label(cell, text=name, font=("", 7), foreground="gray").pack()

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _clear_plates(self):
        for w in self.scrollable_frame.winfo_children():
            w.destroy()


def main():
    root = tk.Tk()
    ANPRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
