import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audio_pipeline import PipelineConfig, enhance_file

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except Exception:
    BaseTk = tk.Tk
    DND_FILES = None
    DND_AVAILABLE = False


SUPPORTED_EXTS = {".mp3", ".wav", ".flac"}


class EnhancerGUI(BaseTk):
    def __init__(self):
        super().__init__()
        self.title("MasterForge 320")
        self.geometry("640x340")
        self.minsize(620, 320)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.mode = tk.StringVar(value="music")
        self.status = tk.StringVar(value="Ready")
        self.is_processing = False

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._apply_theme()
        self._build_ui()

    def _apply_theme(self):
        bg = "#0F172A"
        card = "#111827"
        fg = "#E5E7EB"
        muted = "#94A3B8"
        accent = "#22C55E"
        accent_active = "#16A34A"

        self.configure(bg=bg)

        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TFrame", background=bg)
        self.style.configure("Card.TFrame", background=card)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("Card.TLabel", background=card, foreground=fg)
        self.style.configure("Muted.TLabel", background=card, foreground=muted)
        self.style.configure("Title.TLabel", background=bg, foreground="#F8FAFC", font=("Segoe UI Semibold", 16))
        self.style.configure("SubTitle.TLabel", background=bg, foreground=muted)

        self.style.configure("TEntry", fieldbackground="#0B1220", foreground=fg, borderwidth=1)
        self.style.configure("TCombobox", fieldbackground="#0B1220", background="#0B1220", foreground=fg)
        self.style.map("TCombobox", fieldbackground=[("readonly", "#0B1220")], foreground=[("readonly", fg)])

        self.style.configure("Accent.TButton", background=accent, foreground="#052E16", borderwidth=0, padding=8, font=("Segoe UI Semibold", 10))
        self.style.map("Accent.TButton", background=[("active", accent_active), ("disabled", "#475569")], foreground=[("disabled", "#CBD5E1")])

        self.style.configure("Ghost.TButton", background="#334155", foreground=fg, borderwidth=0, padding=8)
        self.style.map("Ghost.TButton", background=[("active", "#475569")])

        self.style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor="#0B1220",
            background=accent,
            bordercolor="#0B1220",
            lightcolor=accent,
            darkcolor=accent,
        )

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="MasterForge 320", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="AI Mastering + MP3 Enhancer", style="SubTitle.TLabel").pack(anchor="w", pady=(0, 12))

        card = ttk.Frame(root, style="Card.TFrame", padding=12)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Input file", style="Card.TLabel").pack(anchor="w")
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x", pady=(6, 8))

        self.input_entry = ttk.Entry(row, textvariable=self.input_path)
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(row, text="Browse", style="Ghost.TButton", command=self.pick_file).pack(side="left", padx=(8, 0))

        self.drop_label = tk.Label(
            card,
            text="Drop MP3 / WAV / FLAC here" if DND_AVAILABLE else "Drag-and-drop unavailable (install tkinterdnd2)",
            bg="#0B1220",
            fg="#CBD5E1",
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.drop_label.pack(fill="x", pady=(0, 10))

        if DND_AVAILABLE:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)

            # optional: allow dropping on input row too
            self.input_entry.drop_target_register(DND_FILES)
            self.input_entry.dnd_bind("<<Drop>>", self._on_drop)

        ttk.Label(card, text="Mode", style="Card.TLabel").pack(anchor="w")
        ttk.Combobox(
            card,
            textvariable=self.mode,
            values=["music", "speech", "aggressive"],
            state="readonly",
        ).pack(fill="x", pady=(6, 12), ipady=3)

        self.pb = ttk.Progressbar(card, orient="horizontal", mode="determinate", style="Modern.Horizontal.TProgressbar")
        self.pb.pack(fill="x")
        ttk.Label(card, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", pady=(8, 12))

        btns = ttk.Frame(card, style="Card.TFrame")
        btns.pack(fill="x")
        self.enhance_btn = ttk.Button(btns, text="Enhance", style="Accent.TButton", command=self.run_enhance)
        self.enhance_btn.pack(side="left")
        ttk.Button(btns, text="Save As...", style="Ghost.TButton", command=self.save_as).pack(side="left", padx=8)

    @staticmethod
    def _extract_first_drop_path(data: str) -> str:
        raw = (data or "").strip()
        if not raw:
            return ""

        # Try Tk splitlist first (handles {...} and spaces)
        try:
            parts = tk.Tk().splitlist(raw)  # temporary parser
            if parts:
                raw = parts[0]
        except Exception:
            pass

        # cleanup wrappers
        raw = raw.strip().strip("{}").strip('"').strip("'")
        if raw.startswith("file:///"):
            raw = raw.replace("file:///", "", 1).replace("/", os.sep)
        return raw

    def _set_input_file(self, path: str):
        self.input_path.set(path)
        self.status.set(f"Selected: {os.path.basename(path)}")

    def _on_drop(self, event):
        candidate = self._extract_first_drop_path(getattr(event, "data", ""))
        if not candidate:
            messagebox.showerror("Error", "Could not read dropped file.")
            return
        if not os.path.exists(candidate):
            messagebox.showerror("Error", f"File not found:\n{candidate}")
            return
        if os.path.splitext(candidate)[1].lower() not in SUPPORTED_EXTS:
            messagebox.showerror("Error", "Supported formats: MP3, WAV, FLAC.")
            return
        self._set_input_file(candidate)

    def pick_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.flac")])
        if path:
            self._set_input_file(path)

    def save_as(self):
        src = self.output_path.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showinfo("Info", "No enhanced file to save yet.")
            return

        dst = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3", "*.mp3")])
        if not dst:
            return

        import shutil
        shutil.copy2(src, dst)
        messagebox.showinfo("Saved", f"Saved to:\n{dst}")

    def run_enhance(self):
        inp = self.input_path.get().strip()
        if not inp:
            messagebox.showerror("Error", "Select or drop an input file first.")
            return
        if self.is_processing:
            return

        self.is_processing = True
        self.enhance_btn.configure(state="disabled")
        self.pb["value"] = 0
        self.status.set("Starting...")

        def work():
            try:
                cfg = PipelineConfig(mode=self.mode.get())
                out = enhance_file(inp, config=cfg, progress_cb=self._on_progress)
                self.after(0, lambda: self._on_success(out))
            except Exception as e:
                self.after(0, lambda err=str(e): messagebox.showerror("Error", err))
            finally:
                self.after(0, self._on_finish)

        threading.Thread(target=work, daemon=True).start()

    def _on_success(self, out_path: str):
        self.output_path.set(out_path)
        self.status.set(f"Done: {os.path.basename(out_path)}")
        messagebox.showinfo("Success", f"Enhanced file created:\n{out_path}")

    def _on_finish(self):
        self.is_processing = False
        self.enhance_btn.configure(state="normal")

    def _on_progress(self, pct: int, msg: str):
        self.after(0, lambda: (self.pb.configure(value=pct), self.status.set(msg)))


if __name__ == "__main__":
    app = EnhancerGUI()
    app.mainloop()