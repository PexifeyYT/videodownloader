import tkinter as tk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import os
import json
from downloader import download_video


# ── Config persistence ────────────────────────────────────────────────────────

_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _load_cfg() -> dict:
    try:
        with open(_CFG) as f:
            return json.load(f)
    except Exception:
        return {"theme": "dark"}


def _save_cfg(data: dict):
    try:
        with open(_CFG, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# ── Theme system ──────────────────────────────────────────────────────────────

SUCCESS = "#30d158"
ERROR   = "#ff453a"

THEMES = {
    "dark": {
        "bg":       "#1c1c1e",
        "surface":  "#2c2c2e",
        "border":   "#3a3a3c",
        "border_f": "#0a84ff",
        "text":     "#f5f5f7",
        "text2":    "#8e8e93",
        "log_bg":   "#242426",
        "accent":   "#0a84ff",
        "accent_h": "#409cff",
        "accent_p": "#007aee",
        "shadow":   "#0a0a0c",
        "btn_dis":  "#48484a",
        "tog_off":  "#48484a",
        "browse_hover": "#3a3a3c",
    },
    "light": {
        "bg":       "#f2f2f7",
        "surface":  "#ffffff",
        "border":   "#d1d1d6",
        "border_f": "#007aff",
        "text":     "#1c1c1e",
        "text2":    "#8e8e93",
        "log_bg":   "#f9f9fb",
        "accent":   "#007aff",
        "accent_h": "#3395ff",
        "accent_p": "#0051d5",
        "shadow":   "#c0c0cc",
        "btn_dis":  "#a8a8b3",
        "tog_off":  "#d1d1d6",
        "browse_hover": "#e5e5ea",
    },
}

# Mutable — all widgets read from here at draw/refresh time
T: dict = {}
T.update(THEMES[_load_cfg().get("theme", "dark")])

# Platform log styles
PLAT = {
    "tiktok":    ("♫", "#ff375f"),
    "youtube":   ("▶", "#ff453a"),
    "instagram": ("◉", "#bf5af2"),
    "unknown":   ("◦", "#8e8e93"),
}


# ── Color helpers ─────────────────────────────────────────────────────────────

def _lc(c1: str, c2: str, t: float = 0.22) -> str:
    t = max(0.0, min(1.0, t))
    def lp(a, b): return int(a + (b - a) * t)
    r = lp(int(c1[1:3], 16), int(c2[1:3], 16))
    g = lp(int(c1[3:5], 16), int(c2[3:5], 16))
    b = lp(int(c1[5:7], 16), int(c2[5:7], 16))
    return f"#{r:02x}{g:02x}{b:02x}"


def _cd(c1: str, c2: str) -> int:
    return max(
        abs(int(c1[1:3], 16) - int(c2[1:3], 16)),
        abs(int(c1[3:5], 16) - int(c2[3:5], 16)),
        abs(int(c1[5:7], 16) - int(c2[5:7], 16)),
    )


# ── FocusEntry ────────────────────────────────────────────────────────────────

class FocusEntry(tk.Frame):
    """Entry with animated focus border + placeholder."""

    def __init__(self, parent, placeholder: str = "", textvariable=None, **kw):
        super().__init__(parent, bg=T["border"], padx=1, pady=1)
        self._inner = tk.Frame(self, bg=T["surface"])
        self._inner.pack(fill="both", expand=True)

        self.var   = textvariable or tk.StringVar()
        self.entry = tk.Entry(
            self._inner, textvariable=self.var,
            bg=T["surface"], fg=T["text"], insertbackground=T["text"],
            relief="flat", font=("Segoe UI", 11), bd=0, **kw
        )
        self.entry.pack(fill="both", expand=True, padx=12, ipady=9)

        self._ph    = placeholder
        self._ph_on = False
        self._c     = T["border"]
        self._t     = T["border"]
        self._aid   = None

        if placeholder:
            self._show_ph()

        self.entry.bind("<FocusIn>",  self._fi)
        self.entry.bind("<FocusOut>", self._fo)
        self.entry.bind("<Return>",   lambda e: self.event_generate("<<Return>>"))

    def _show_ph(self):
        self._ph_on = True
        self.entry.insert(0, self._ph)
        self.entry.configure(fg=T["text2"])

    def _fi(self, _e):
        if self._ph_on:
            self.entry.delete(0, "end")
            self.entry.configure(fg=T["text"])
            self._ph_on = False
        self._anim(T["border_f"])

    def _fo(self, _e):
        if not self.entry.get():
            self._show_ph()
        self._anim(T["border"])

    def _anim(self, target: str):
        self._t = target
        if self._aid:
            self.after_cancel(self._aid)
        self._step()

    def _step(self):
        self._c = _lc(self._c, self._t)
        self.configure(bg=self._c)
        if _cd(self._c, self._t) > 2:
            self._aid = self.after(14, self._step)
        else:
            self._c = self._t
            self.configure(bg=self._c)

    def apply_theme(self):
        self._c = T["border"]
        self._t = T["border"]
        self.configure(bg=T["border"])
        self._inner.configure(bg=T["surface"])
        self.entry.configure(
            bg=T["surface"],
            fg=T["text2"] if self._ph_on else T["text"],
            insertbackground=T["text"],
        )

    def get(self) -> str:
        return "" if self._ph_on else self.var.get()

    def set(self, v: str):
        self._ph_on = False
        self.var.set(v)
        self.entry.configure(fg=T["text"])


# ── PillButton ────────────────────────────────────────────────────────────────

class PillButton(tk.Canvas):
    """Animated pill: hover fade, loading spinner, success/error flash."""

    W, H = 220, 48

    def __init__(self, parent, text: str, command, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                        bg=T["bg"], highlightthickness=0, cursor="hand2")
        self._text = text
        self._cmd  = command
        self._c    = T["accent"]
        self._t    = T["accent"]
        self._en   = True
        self._load = False
        self._ang  = 0
        self._aids: list = []

        self.bind("<Enter>",           lambda e: self._hover(True))
        self.bind("<Leave>",           lambda e: self._hover(False))
        self.bind("<Button-1>",        self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _pts(self, ox=1, oy=2):
        w, h = self.W - ox * 2, self.H - oy * 2
        r = h // 2
        return [ox+r,oy, ox+w-r,oy, ox+w,oy, ox+w,oy+r, ox+w,oy+h-r,
                ox+w,oy+h, ox+w-r,oy+h, ox+r,oy+h, ox,oy+h, ox,oy+h-r,
                ox,oy+r, ox,oy]

    def _draw(self):
        self.delete("all")
        w, h = self.W, self.H
        self.configure(bg=T["bg"])
        self.create_polygon(self._pts(2, 4), smooth=True, fill=T["shadow"], outline="")
        fill = self._c if self._en else T["btn_dis"]
        self.create_polygon(self._pts(1, 1), smooth=True, fill=fill, outline="")
        if self._load:
            cx, cy, rs = w / 2, h / 2 + 1, 10
            self.create_arc(cx-rs, cy-rs, cx+rs, cy+rs,
                           start=self._ang, extent=255,
                           style="arc", outline="white", width=2.5)
        else:
            self.create_text(w/2, h/2+1, text=self._text, fill="white",
                            font=("Segoe UI", 12, "bold"))

    def _hover(self, on: bool):
        if not self._en or self._load:
            return
        self._t = T["accent_h"] if on else T["accent"]
        self._anim()

    def _press(self, _e):
        if not self._en:
            return
        self._cancel()
        self._c = T["accent_p"]
        self._draw()
        self._cmd()

    def _release(self, _e):
        if not self._en:
            return
        self._t = T["accent_h"]
        self._anim()

    def _cancel(self):
        for a in self._aids:
            try: self.after_cancel(a)
            except Exception: pass
        self._aids.clear()

    def _anim(self):
        self._cancel()
        self._step()

    def _step(self):
        self._c = _lc(self._c, self._t)
        self._draw()
        if _cd(self._c, self._t) > 2:
            self._aids.append(self.after(14, self._step))
        else:
            self._c = self._t
            self._draw()

    def set_loading(self, on: bool):
        self._load = on
        self._en   = not on
        if on:
            self._cancel()
            self._c = T["accent_p"]
            self._spin()
        else:
            self._c = T["accent"]
            self._t = T["accent"]
            self._draw()

    def flash(self, kind: str = "ok"):
        self._load = False
        self._en   = False
        self._cancel()
        self._c = SUCCESS if kind == "ok" else ERROR
        self._t = self._c
        self._draw()
        self.after(700, self._unflash)

    def _unflash(self):
        self._en = True
        self._t  = T["accent"]
        self._anim()

    def _spin(self):
        if not self._load:
            return
        self._ang = (self._ang + 9) % 360
        self._draw()
        self.after(18, self._spin)

    def apply_theme(self):
        self.configure(bg=T["bg"])
        if self._en and not self._load:
            self._c = T["accent"]
            self._t = T["accent"]
        self._draw()


# ── ThemeToggle ───────────────────────────────────────────────────────────────

class ThemeToggle(tk.Canvas):
    """Sliding pill toggle. Right = dark, left = light."""

    W, H = 50, 28

    def __init__(self, parent, on_toggle, theme: str = "dark"):
        super().__init__(parent, width=self.W, height=self.H,
                        bg=T["bg"], highlightthickness=0, cursor="hand2")
        self._dark = (theme == "dark")
        self._cb   = on_toggle
        self._cx   = float(self.W - 14) if self._dark else 14.0
        self._tx   = self._cx
        self.bind("<Button-1>", self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        self.configure(bg=T["bg"])
        w, h, p = self.W, self.H, 2
        r = (h - p * 2) // 2
        pts = [p+r,p, w-p-r,p, w-p,p, w-p,p+r, w-p,h-p-r,
               w-p,h-p, w-p-r,h-p, p+r,h-p, p,h-p, p,h-p-r, p,p+r, p,p]
        track = T["accent"] if self._dark else T["tog_off"]
        self.create_polygon(pts, smooth=True, fill=track, outline="")
        cy = h / 2
        cr = h / 2 - 3
        self.create_oval(self._cx-cr, cy-cr, self._cx+cr, cy+cr,
                        fill="white", outline="")

    def _click(self, _e):
        self._dark = not self._dark
        self._tx   = float(self.W - 14) if self._dark else 14.0
        self._slide()
        self._cb("dark" if self._dark else "light")

    def _slide(self):
        diff = self._tx - self._cx
        if abs(diff) < 0.8:
            self._cx = self._tx
            self._draw()
            return
        self._cx += diff * 0.28
        self._draw()
        self.after(14, self._slide)

    def apply_theme(self):
        self._draw()


# ── App ───────────────────────────────────────────────────────────────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._themed: list[tuple[tk.Widget, dict]] = []
        self._canvas_ws: list = []

        cfg = _load_cfg()
        self._theme = cfg.get("theme", "dark")
        T.update(THEMES[self._theme])

        self._out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(self._out, exist_ok=True)

        root.title("Multi-Platform Video Downloader")
        root.geometry("500x590")
        root.resizable(False, False)
        root.configure(bg=T["bg"])

        root.update_idletasks()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"500x590+{(sw-500)//2}+{(sh-590)//2}")

        self._build()

    # ── Registration helpers ──────────────────────────────────────────────────

    def _reg(self, widget: tk.Widget, **key_map) -> tk.Widget:
        self._themed.append((widget, key_map))
        return widget

    def _rcanvas(self, widget):
        self._canvas_ws.append(widget)
        return widget

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = self._reg(tk.Frame(self.root, bg=T["bg"]), bg="bg")
        hdr.pack(fill="x", padx=32, pady=(28, 18))

        # Icon
        self._icon_c = tk.Canvas(hdr, width=46, height=46, bg=T["bg"],
                                 highlightthickness=0)
        self._icon_c.pack(side="left", padx=(0, 14))
        self._draw_icon()
        self._canvas_ws.append(self._icon_c)

        # Title group
        titles = self._reg(tk.Frame(hdr, bg=T["bg"]), bg="bg")
        titles.pack(side="left", anchor="center")
        self._title_lbl = self._reg(
            tk.Label(titles, text="Video Downloader", bg=T["bg"], fg=T["text"],
                     font=("Segoe UI", 17, "bold")),
            bg="bg", fg="text"
        )
        self._title_lbl.pack(anchor="w")
        self._sub_lbl = self._reg(
            tk.Label(titles, text="TikTok  ·  YouTube  ·  Instagram",
                     bg=T["bg"], fg=T["text2"], font=("Segoe UI", 10)),
            bg="bg", fg="text2"
        )
        self._sub_lbl.pack(anchor="w", pady=(1, 0))

        # Theme toggle (right-aligned)
        tog_col = self._reg(tk.Frame(hdr, bg=T["bg"]), bg="bg")
        tog_col.pack(side="right", anchor="center")
        self._toggle = ThemeToggle(tog_col, self._switch_theme, self._theme)
        self._toggle.pack()
        self._canvas_ws.append(self._toggle)
        self._reg(
            tk.Label(tog_col, text="Dark", bg=T["bg"], fg=T["text2"],
                     font=("Segoe UI", 8)),
            bg="bg", fg="text2"
        ).pack()

        # ── Input card ────────────────────────────────────────────────────────
        self._card_outer = self._reg(tk.Frame(self.root, bg=T["border"]), bg="border")
        self._card_outer.pack(fill="x", padx=24)
        self._card = self._reg(tk.Frame(self._card_outer, bg=T["surface"]), bg="surface")
        self._card.pack(fill="both", expand=True, padx=1, pady=1)

        # URL input
        self._reg(
            tk.Label(self._card, text="URL", bg=T["surface"], fg=T["text2"],
                     font=("Segoe UI", 8, "bold")),
            bg="surface", fg="text2"
        ).pack(anchor="w", padx=20, pady=(18, 5))

        self._url = FocusEntry(self._card,
                               placeholder="TikTok, YouTube, or Instagram URL…")
        self._url.pack(fill="x", padx=20, pady=(0, 18))
        self._canvas_ws.append(self._url)
        self._url.bind("<<Return>>", lambda e: self._on_dl())

        self._reg(tk.Frame(self._card, height=1, bg=T["border"]), bg="border"
                  ).pack(fill="x", padx=20)

        # Folder input
        self._reg(
            tk.Label(self._card, text="SAVE TO", bg=T["surface"], fg=T["text2"],
                     font=("Segoe UI", 8, "bold")),
            bg="surface", fg="text2"
        ).pack(anchor="w", padx=20, pady=(14, 5))

        frow = self._reg(tk.Frame(self._card, bg=T["surface"]), bg="surface")
        frow.pack(fill="x", padx=20, pady=(0, 18))

        self._fol = FocusEntry(frow)
        self._fol.set(self._out)
        self._fol.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._canvas_ws.append(self._fol)

        self._browse_btn = tk.Button(
            frow, text="Browse", command=self._browse,
            bg=T["bg"], fg=T["accent"],
            activebackground=T["browse_hover"], activeforeground=T["accent"],
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            padx=10, pady=7, bd=0
        )
        self._browse_btn.pack(side="left")
        self._reg(self._browse_btn, bg="bg", fg="accent")

        # ── Download button ───────────────────────────────────────────────────
        bf = self._reg(tk.Frame(self.root, bg=T["bg"]), bg="bg")
        bf.pack(pady=20)
        self._btn = PillButton(bf, "Download", self._on_dl)
        self._btn.pack()
        self._canvas_ws.append(self._btn)

        # ── Log ───────────────────────────────────────────────────────────────
        lo = self._reg(tk.Frame(self.root, bg=T["border"]), bg="border")
        lo.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        li = self._reg(tk.Frame(lo, bg=T["log_bg"]), bg="log_bg")
        li.pack(fill="both", expand=True, padx=1, pady=1)

        self._log = ScrolledText(
            li, bg=T["log_bg"], fg=T["text2"],
            font=("Consolas", 9), relief="flat", bd=0,
            padx=14, pady=10, state="disabled",
            cursor="arrow", wrap="word", height=8,
            highlightthickness=0,
        )
        self._log.pack(fill="both", expand=True)
        self._setup_log_tags()
        self._emit("Ready — paste a URL and hit Download", "dim")

    def _draw_icon(self):
        self._icon_c.configure(bg=T["bg"])
        self._icon_c.delete("all")
        self._icon_c.create_oval(1, 1, 45, 45, fill=T["accent"], outline="")
        self._icon_c.create_text(23, 25, text="↓", fill="white",
                                 font=("Segoe UI", 19, "bold"))

    def _setup_log_tags(self):
        self._log.tag_config("ok",       foreground=SUCCESS)
        self._log.tag_config("err",      foreground=ERROR)
        self._log.tag_config("dim",      foreground=T["text2"])
        self._log.tag_config("sym_ok",   foreground=SUCCESS, font=("Segoe UI", 10, "bold"))
        self._log.tag_config("sym_err",  foreground=ERROR,   font=("Segoe UI", 10, "bold"))
        self._log.tag_config("plat_tiktok",    foreground=PLAT["tiktok"][1],
                              font=("Segoe UI", 9, "bold"))
        self._log.tag_config("plat_youtube",   foreground=PLAT["youtube"][1],
                              font=("Segoe UI", 9, "bold"))
        self._log.tag_config("plat_instagram", foreground=PLAT["instagram"][1],
                              font=("Segoe UI", 9, "bold"))
        self._log.tag_config("plat_unknown",   foreground=PLAT["unknown"][1],
                              font=("Segoe UI", 9, "bold"))

    # ── Theme switching ───────────────────────────────────────────────────────

    def _switch_theme(self, name: str):
        self._theme = name
        T.update(THEMES[name])
        self._refresh_theme()
        _save_cfg({"theme": name})

    def _refresh_theme(self):
        self.root.configure(bg=T["bg"])
        for widget, km in self._themed:
            try:
                widget.configure(**{p: T[k] for p, k in km.items()})
            except tk.TclError:
                pass
        for cw in self._canvas_ws:
            cw.apply_theme()
        # Update dark/light label under toggle
        self._browse_btn.configure(
            activebackground=T["browse_hover"],
            activeforeground=T["accent"],
        )
        self._draw_icon()
        self._log.configure(bg=T["log_bg"], fg=T["text2"])
        self._setup_log_tags()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._fol.get() or self._out)
        if d:
            self._fol.set(d)

    def _emit(self, msg: str, kind: str = "dim", platform: str = ""):
        self._log.configure(state="normal")
        if platform and platform in PLAT:
            sym, _ = PLAT[platform]
            self._log.insert("end", f"  {sym} {platform.upper()}\n",
                            f"plat_{platform}")
        if kind == "ok":
            self._log.insert("end", "  ✓ ", "sym_ok")
            self._log.insert("end", msg + "\n", "ok")
        elif kind == "err":
            self._log.insert("end", "  ✗ ", "sym_err")
            self._log.insert("end", msg + "\n", "err")
        else:
            self._log.insert("end", "    " + msg + "\n", "dim")
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Download flow ─────────────────────────────────────────────────────────

    def _on_dl(self):
        url = self._url.get().strip()
        fol = self._fol.get().strip()
        if not url:
            self._emit("Paste a URL first", "err")
            return
        if not fol:
            self._emit("Select a save folder", "err")
            return
        self._btn.set_loading(True)
        self._emit("Fetching…", "dim")
        threading.Thread(target=self._dl, args=(url, fol), daemon=True).start()

    def _dl(self, url: str, fol: str):
        (ok, msg, fname), plat = download_video(url, fol)

        def done():
            if ok:
                self._emit(fname, "ok", platform=plat)
                self._url.set("")
                self._btn.flash("ok")
            else:
                self._emit(msg, "err", platform=plat)
                self._btn.flash("err")

        self.root.after(0, done)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
