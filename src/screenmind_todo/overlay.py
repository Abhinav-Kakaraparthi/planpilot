from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import requests


class DesktopOverlay:
    def __init__(self) -> None:
        self.mode = "answer"
        self.opacity = 0.62
        self.drag_origin_x = 0
        self.drag_origin_y = 0
        self.window_origin_x = 0
        self.window_origin_y = 0

        self.root = tk.Tk()
        self.root.title("PlanPilot Overlay")
        self.root.geometry("500x280+980+80")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.opacity)
        self.root.configure(bg="#0d2230")
        self.root.overrideredirect(False)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.session_var = tk.StringVar(value="Watcher off")
        self.title_var = tk.StringVar(value="PlanPilot Copilot")
        self.question_var = tk.StringVar(value="No meeting question detected yet.")
        self.answer_var = tk.StringVar(value="Load a meeting plan to generate a response.")
        self.follow_up_var = tk.StringVar(value="No follow-up yet.")

        self._build_ui()
        self._bind_events()
        self.refresh()

    def _configure_styles(self) -> None:
        self.style.configure(
            "Overlay.TFrame",
            background="#0d2230",
        )
        self.style.configure(
            "OverlayCard.TFrame",
            background="#133246",
            relief="flat",
        )
        self.style.configure(
            "Overlay.TLabel",
            background="#0d2230",
            foreground="#eaf7fb",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "OverlayMuted.TLabel",
            background="#0d2230",
            foreground="#9cc8d4",
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "OverlayTitle.TLabel",
            background="#0d2230",
            foreground="#f2fbff",
            font=("Segoe UI Semibold", 13),
        )
        self.style.configure(
            "OverlayAnswer.TLabel",
            background="#133246",
            foreground="#f2fbff",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Overlay.TButton",
            background="#1f8ca8",
            foreground="#f5fdff",
            borderwidth=0,
            focusthickness=3,
            focuscolor="#77d9f0",
            padding=(10, 6),
        )
        self.style.map(
            "Overlay.TButton",
            background=[("active", "#2a9cbc"), ("pressed", "#0f6f8a")],
            foreground=[("disabled", "#b7dce6")],
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="Overlay.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        self.header = ttk.Frame(outer, style="Overlay.TFrame")
        self.header.pack(fill="x")

        heading = ttk.Frame(self.header, style="Overlay.TFrame")
        heading.pack(side="left", fill="x", expand=True)

        ttk.Label(heading, textvariable=self.title_var, style="OverlayTitle.TLabel").pack(anchor="w")
        ttk.Label(heading, textvariable=self.session_var, style="OverlayMuted.TLabel").pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(self.header, style="Overlay.TFrame")
        controls.pack(side="right")

        for label, mode in [("Answer", "answer"), ("Summary", "summary"), ("Tasks", "tasks")]:
            ttk.Button(
                controls,
                text=label,
                style="Overlay.TButton",
                command=lambda next_mode=mode: self.set_mode(next_mode),
            ).pack(side="left", padx=(0, 6))

        ttk.Button(controls, text="Refresh", style="Overlay.TButton", command=self.refresh).pack(side="left")

        content = ttk.Frame(outer, style="OverlayCard.TFrame", padding=14)
        content.pack(fill="both", expand=True, pady=(12, 0))

        ttk.Label(content, text="Question", style="OverlayMuted.TLabel").pack(anchor="w")
        ttk.Label(
            content,
            textvariable=self.question_var,
            style="Overlay.TLabel",
            wraplength=440,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        ttk.Label(content, text="Suggested answer", style="OverlayMuted.TLabel").pack(anchor="w")
        ttk.Label(
            content,
            textvariable=self.answer_var,
            style="OverlayAnswer.TLabel",
            wraplength=440,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        ttk.Label(content, text="Follow-up", style="OverlayMuted.TLabel").pack(anchor="w")
        ttk.Label(
            content,
            textvariable=self.follow_up_var,
            style="Overlay.TLabel",
            wraplength=440,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        footer = ttk.Frame(outer, style="Overlay.TFrame")
        footer.pack(fill="x", pady=(10, 0))
        ttk.Label(
            footer,
            text="Keys: 1 2 3 switch mode | Arrow keys move | + / - opacity | R refresh",
            style="OverlayMuted.TLabel",
        ).pack(anchor="w")

    def _bind_events(self) -> None:
        self.header.bind("<ButtonPress-1>", self.start_drag)
        self.header.bind("<B1-Motion>", self.drag_window)
        self.root.bind("<KeyPress-1>", lambda _event: self.set_mode("answer"))
        self.root.bind("<KeyPress-2>", lambda _event: self.set_mode("summary"))
        self.root.bind("<KeyPress-3>", lambda _event: self.set_mode("tasks"))
        self.root.bind("<KeyPress-r>", lambda _event: self.refresh())
        self.root.bind("<KeyPress-R>", lambda _event: self.refresh())
        self.root.bind("<KeyPress-plus>", lambda _event: self.adjust_opacity(0.05))
        self.root.bind("<KeyPress-equal>", lambda _event: self.adjust_opacity(0.05))
        self.root.bind("<KeyPress-minus>", lambda _event: self.adjust_opacity(-0.05))
        self.root.bind("<Left>", lambda _event: self.nudge(-16, 0))
        self.root.bind("<Right>", lambda _event: self.nudge(16, 0))
        self.root.bind("<Up>", lambda _event: self.nudge(0, -16))
        self.root.bind("<Down>", lambda _event: self.nudge(0, 16))

    def start_drag(self, event: tk.Event) -> None:
        self.drag_origin_x = event.x_root
        self.drag_origin_y = event.y_root
        self.window_origin_x = self.root.winfo_x()
        self.window_origin_y = self.root.winfo_y()

    def drag_window(self, event: tk.Event) -> None:
        delta_x = event.x_root - self.drag_origin_x
        delta_y = event.y_root - self.drag_origin_y
        self.root.geometry(f"+{self.window_origin_x + delta_x}+{self.window_origin_y + delta_y}")

    def nudge(self, delta_x: int, delta_y: int) -> None:
        self.root.geometry(f"+{self.root.winfo_x() + delta_x}+{self.root.winfo_y() + delta_y}")

    def adjust_opacity(self, delta: float) -> None:
        self.opacity = max(0.28, min(0.92, self.opacity + delta))
        self.root.attributes("-alpha", self.opacity)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.refresh()

    def refresh(self) -> None:
        try:
            copilot = requests.get(
                "http://127.0.0.1:8000/api/copilot/context",
                params={"mode": self.mode},
                timeout=5,
            ).json()
            session = requests.get("http://127.0.0.1:8000/api/session/status", timeout=5).json()
        except Exception:
            self.session_var.set("PlanPilot server unavailable")
            self.title_var.set("PlanPilot Copilot")
            self.question_var.set("Start the local server first.")
            self.answer_var.set("Run uvicorn, then reopen the overlay.")
            self.follow_up_var.set("The overlay polls the local API at http://127.0.0.1:8000.")
            self.root.after(5000, self.refresh)
            return

        self.title_var.set(copilot.get("meeting_title") or "PlanPilot Copilot")
        self.session_var.set(session.get("label") or "Session idle")
        self.question_var.set(copilot.get("question") or "No meeting question detected yet.")
        self.answer_var.set(copilot.get("answer") or "No answer available.")
        self.follow_up_var.set(
            f"{copilot.get('follow_up') or 'No follow-up yet.'}  |  Screen: {copilot.get('screen_signal') or 'No signal'}"
        )
        self.root.after(5000, self.refresh)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DesktopOverlay().run()


if __name__ == "__main__":
    main()
