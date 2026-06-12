# admingui.py
# ─────────────────────────────────────────────────────────────
# ADMIN GUI — Graphical User Interface for System Operator
#
# Built with Tkinter (built into Python — no install needed)
# Run with: python admingui.py
#
# Features:
#   - Dashboard showing system status
#   - Register new participants
#   - View all participants
#   - Create early warning alerts
#   - View and resolve active alerts
#   - Trigger manual broadcast
#   - View send statistics
# ─────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import datetime
import sys
import os

# Add project root to path so modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.database import (
    create_tables, add_user, get_active_users,
    add_alert, get_active_alerts, list_all_alerts,
    resolve_alert, get_send_stats, get_next_tip
)
from modules.broadcaster import broadcast_alerts, broadcast_awareness, daily_broadcast
from modules.sms_sender import validate_phone
from config import TEST_MODE, SMS_PROVIDER, TEST_TARGET

# ── COLOURS ───────────────────────────────────────────────────
BG_MAIN    = "#1C2B3A"   # dark navy background
BG_CARD    = "#243447"   # card background
BG_SIDEBAR = "#162030"   # sidebar
PURPLE     = "#7B5EA7"   # purple accent
GOLD       = "#C9A227"   # gold accent
GREEN      = "#27AE60"   # success green
RED        = "#E74C3C"   # alert red
ORANGE     = "#E67E22"   # warning orange
WHITE      = "#FFFFFF"
LGRAY      = "#B0BEC5"
DGRAY      = "#546E7A"
FONT       = "Segoe UI"


class AdminGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SMS Cybersecurity Early Warning & Awareness System — Admin Panel")
        self.root.geometry("1100x700")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)

        # Initialise database
        create_tables()

        # Worker threads hand UI updates back to the main thread through this
        # queue; Tkinter is not thread-safe, so widgets are only ever touched
        # by the poller below, which runs on the main (event-loop) thread.
        self._ui_queue = queue.Queue()
        self._poll_ui_queue()

        # Build UI
        self._build_header()
        self._build_layout()
        self._show_dashboard()

    # ── THREAD-SAFE UI BRIDGE ──────────────────────────────────
    def _ui(self, fn):
        """Schedule `fn` to run on the main thread. Safe to call from workers."""
        self._ui_queue.put(fn)

    def _poll_ui_queue(self):
        try:
            while True:
                self._ui_queue.get_nowait()()
        except queue.Empty:
            pass
        except Exception:
            pass
        self.root.after(100, self._poll_ui_queue)

    # ── HEADER ─────────────────────────────────────────────────
    def _build_header(self):
        header = tk.Frame(self.root, bg=BG_SIDEBAR, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header,
                 text="  SMS Cybersecurity Early Warning & Awareness System",
                 font=(FONT, 14, "bold"), fg=WHITE, bg=BG_SIDEBAR
                 ).pack(side="left", padx=10, pady=15)

        mode_color = RED if not TEST_MODE else GREEN
        if TEST_MODE:
            mode_text = f"  TEST MODE → {TEST_TARGET.upper()}  "
        else:
            mode_text = "  LIVE MODE  "
        tk.Label(header, text=mode_text, font=(FONT, 10, "bold"),
                 fg=WHITE, bg=mode_color).pack(side="right", padx=20, pady=15)

        tk.Label(header, text=f"Provider: {SMS_PROVIDER.upper()}",
                 font=(FONT, 9), fg=LGRAY, bg=BG_SIDEBAR
                 ).pack(side="right", padx=10, pady=15)

    # ── LAYOUT ─────────────────────────────────────────────────
    def _build_layout(self):
        # Main container
        container = tk.Frame(self.root, bg=BG_MAIN)
        container.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(container, bg=BG_SIDEBAR, width=200)
        self.sidebar.pack(fill="y", side="left")
        self.sidebar.pack_propagate(False)

        # Content area
        self.content = tk.Frame(container, bg=BG_MAIN)
        self.content.pack(fill="both", expand=True, side="left")

        # Sidebar buttons
        tk.Label(self.sidebar, text="NAVIGATION",
                 font=(FONT, 8, "bold"), fg=DGRAY, bg=BG_SIDEBAR
                 ).pack(pady=(20, 5), padx=15, anchor="w")

        nav_items = [
            ("Dashboard",        self._show_dashboard),
            ("Participants",     self._show_participants),
            ("Register New",     self._show_register),
            ("Active Alerts",    self._show_alerts),
            ("Create Alert",     self._show_create_alert),
            ("Send Blast",       self._show_send),
            ("Statistics",       self._show_stats),
        ]
        for label, command in nav_items:
            btn = tk.Button(self.sidebar, text=f"  {label}",
                           font=(FONT, 10), fg=WHITE, bg=BG_SIDEBAR,
                           activebackground=PURPLE, activeforeground=WHITE,
                           relief="flat", anchor="w", cursor="hand2",
                           command=command)
            btn.pack(fill="x", padx=5, pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=PURPLE))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG_SIDEBAR))

        # Version info at bottom of sidebar
        tk.Label(self.sidebar,
                 text="ZCAS University\nSCEWAS Admin Panel\nv1.0",
                 font=(FONT, 8), fg=DGRAY, bg=BG_SIDEBAR,
                 justify="center").pack(side="bottom", pady=20)

    # ── HELPER: clear content area ─────────────────────────────
    def _clear(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _page_title(self, title, subtitle=""):
        tk.Label(self.content, text=title,
                 font=(FONT, 18, "bold"), fg=WHITE, bg=BG_MAIN
                 ).pack(anchor="w", padx=25, pady=(20, 0))
        if subtitle:
            tk.Label(self.content, text=subtitle,
                     font=(FONT, 10), fg=LGRAY, bg=BG_MAIN
                     ).pack(anchor="w", padx=25, pady=(2, 15))

    def _card(self, parent, title, value, color=PURPLE, width=180):
        frame = tk.Frame(parent, bg=BG_CARD, width=width, height=90)
        frame.pack_propagate(False)
        frame.pack(side="left", padx=8, pady=8)
        tk.Label(frame, text=title, font=(FONT, 9), fg=LGRAY, bg=BG_CARD
                 ).pack(pady=(12, 2))
        tk.Label(frame, text=str(value), font=(FONT, 22, "bold"),
                 fg=color, bg=BG_CARD).pack()
        return frame

    def _section(self, text):
        tk.Label(self.content, text=text,
                 font=(FONT, 11, "bold"), fg=GOLD, bg=BG_MAIN
                 ).pack(anchor="w", padx=25, pady=(15, 5))

    def _log(self, widget, message, color=None):
        # The widget may already be destroyed if the operator navigated to
        # another page before a background broadcast finished writing to it.
        if not widget.winfo_exists():
            return
        widget.config(state="normal")
        line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}]  {message}\n"
        if color:
            tag = "c" + color.lstrip("#")
            widget.tag_config(tag, foreground=color)
            widget.insert("end", line, tag)
        else:
            widget.insert("end", line)
        widget.see("end")
        widget.config(state="disabled")

    # ══════════════════════════════════════════════════════════
    #  DASHBOARD
    # ══════════════════════════════════════════════════════════
    def _show_dashboard(self):
        self._clear()
        self._page_title("Dashboard", "System overview and quick actions")

        # Stats cards
        cards_frame = tk.Frame(self.content, bg=BG_MAIN)
        cards_frame.pack(anchor="w", padx=17, pady=5)

        users   = get_active_users()
        alerts  = get_active_alerts()
        stats   = get_send_stats()
        tip     = get_next_tip()
        total   = sum(s["total_sent"] for s in stats) if stats else 0

        self._card(cards_frame, "Active Participants", len(users), PURPLE)
        self._card(cards_frame, "Active Alerts",       len(alerts), RED if alerts else GREEN)
        self._card(cards_frame, "Messages Sent",       total,       GOLD)
        self._card(cards_frame, "Next Tip ID",         tip["id"] if tip else "—", GREEN)

        # Active alerts warning
        if alerts:
            warn = tk.Frame(self.content, bg="#3D1A1A")
            warn.pack(fill="x", padx=25, pady=5)
            tk.Label(warn,
                     text=f"  ⚠  {len(alerts)} ACTIVE ALERT(S) — click 'Send Blast' to broadcast",
                     font=(FONT, 10, "bold"), fg=RED, bg="#3D1A1A"
                     ).pack(anchor="w", padx=10, pady=8)

        # Quick actions
        self._section("Quick Actions")
        btn_frame = tk.Frame(self.content, bg=BG_MAIN)
        btn_frame.pack(anchor="w", padx=25)

        actions = [
            ("Send Awareness Blast", GREEN,  self._send_awareness_now),
            ("Broadcast Alerts Now", RED,    self._send_alerts_now),
            ("Full Daily Broadcast", PURPLE, self._send_full_now),
        ]
        for text, color, cmd in actions:
            tk.Button(btn_frame, text=text,
                      font=(FONT, 10, "bold"), fg=WHITE, bg=color,
                      relief="flat", padx=20, pady=8, cursor="hand2",
                      command=cmd).pack(side="left", padx=5)

        # Recent activity log
        self._section("System Log")
        log = scrolledtext.ScrolledText(
            self.content, height=8, bg=BG_CARD, fg=GREEN,
            font=("Courier New", 9), state="disabled", relief="flat"
        )
        log.pack(fill="x", padx=25, pady=5)
        self._log(log, "Admin panel loaded successfully.")
        self._log(log, f"Active participants: {len(users)}")
        self._log(log, f"Active alerts: {len(alerts)}")
        self._log(log, f"Total messages sent: {total}")
        if tip:
            self._log(log, f"Next tip: ID={tip['id']} | {tip['category']}")

    # ══════════════════════════════════════════════════════════
    #  PARTICIPANTS
    # ══════════════════════════════════════════════════════════
    def _show_participants(self):
        self._clear()
        self._page_title("Participants", "All registered active participants")

        users = get_active_users()

        # Treeview table
        frame = tk.Frame(self.content, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=25, pady=10)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Treeview",
                        background=BG_CARD, foreground=WHITE,
                        fieldbackground=BG_CARD, rowheight=30,
                        font=(FONT, 10))
        style.configure("Custom.Treeview.Heading",
                        background=PURPLE, foreground=WHITE,
                        font=(FONT, 10, "bold"))
        style.map("Custom.Treeview", background=[("selected", PURPLE)])

        cols = ("ID", "Name", "Language", "Area", "Registered")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            style="Custom.Treeview")

        widths = [50, 200, 100, 120, 180]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center" if w < 150 else "w")

        for u in users:
            tree.insert("", "end", values=(
                u["id"], u["name"], u["language"],
                u["area"], u["created_at"][:16] if u["created_at"] else ""
            ))

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(self.content,
                 text=f"Total active participants: {len(users)}",
                 font=(FONT, 9), fg=LGRAY, bg=BG_MAIN
                 ).pack(anchor="w", padx=25, pady=5)

    # ══════════════════════════════════════════════════════════
    #  REGISTER NEW PARTICIPANT
    # ══════════════════════════════════════════════════════════
    def _show_register(self):
        self._clear()
        self._page_title("Register New Participant",
                         "Add a new participant to the system")

        form = tk.Frame(self.content, bg=BG_CARD)
        form.pack(padx=25, pady=10, anchor="w")

        fields = [
            ("Full Name",        "e.g. Bwalya Mutale"),
            ("Phone Number",     "e.g. +260977123456"),
            ("Area / District",  "e.g. Lusaka"),
        ]
        entries = {}
        for label, placeholder in fields:
            row = tk.Frame(form, bg=BG_CARD)
            row.pack(fill="x", padx=20, pady=8)
            tk.Label(row, text=label, font=(FONT, 10, "bold"),
                     fg=WHITE, bg=BG_CARD, width=18, anchor="w"
                     ).pack(side="left")
            entry = tk.Entry(row, font=(FONT, 10), bg="#2C4158",
                             fg=WHITE, insertbackground=WHITE,
                             relief="flat", width=35)
            entry.insert(0, placeholder)
            entry.config(fg=DGRAY)
            entry.bind("<FocusIn>",  lambda e, en=entry, ph=placeholder: self._clear_placeholder(e, en, ph))
            entry.bind("<FocusOut>", lambda e, en=entry, ph=placeholder: self._restore_placeholder(e, en, ph))
            entry.pack(side="left", padx=10, ipady=6)
            entries[label] = entry

        # Language dropdown
        lang_row = tk.Frame(form, bg=BG_CARD)
        lang_row.pack(fill="x", padx=20, pady=8)
        tk.Label(lang_row, text="Language", font=(FONT, 10, "bold"),
                 fg=WHITE, bg=BG_CARD, width=18, anchor="w"
                 ).pack(side="left")
        lang_var = tk.StringVar(value="english")
        lang_menu = ttk.Combobox(lang_row, textvariable=lang_var,
                                 values=["english", "bemba", "nyanja"],
                                 state="readonly", width=33, font=(FONT, 10))
        lang_menu.pack(side="left", padx=10, ipady=4)

        # Status label
        status = tk.Label(form, text="", font=(FONT, 10),
                          bg=BG_CARD, fg=GREEN)
        status.pack(pady=5)

        def _value(label, placeholder):
            """Return the typed value, treating leftover placeholder text as empty."""
            v = entries[label].get().strip()
            return "" if v == placeholder else v

        def register():
            name  = _value("Full Name",       "e.g. Bwalya Mutale")
            phone = _value("Phone Number",     "e.g. +260977123456")
            area  = _value("Area / District",  "e.g. Lusaka")
            lang  = lang_var.get()

            if not name:
                status.config(text="Please enter a name.", fg=RED)
                return
            if not validate_phone(phone):
                status.config(
                    text="Enter a valid phone — '+' followed by 10–15 digits (e.g. +260977123456).",
                    fg=RED)
                return
            if any(u.get("phone") == phone for u in get_active_users()):
                status.config(text=f"{phone} is already registered.", fg=RED)
                return

            try:
                add_user(name, phone, lang, area or "Unknown")
            except Exception as e:
                status.config(text=f"Registration failed: {e}", fg=RED)
                return

            status.config(text=f"✓  {name} registered successfully!", fg=GREEN)

            # Reset the form so the operator can add another participant.
            for lbl, ph in fields:
                en = entries[lbl]
                en.delete(0, "end")
                en.insert(0, ph)
                en.config(fg=DGRAY)
            lang_var.set("english")

        tk.Button(form, text="  Register Participant  ",
                  font=(FONT, 11, "bold"), fg=WHITE, bg=PURPLE,
                  relief="flat", padx=15, pady=8, cursor="hand2",
                  command=register).pack(pady=15, padx=20, anchor="w")

    def _clear_placeholder(self, event, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.config(fg=WHITE)

    def _restore_placeholder(self, event, entry, placeholder):
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(fg=DGRAY)

    # ── HELPER: vertically scrollable body ─────────────────────
    def _scrollable_body(self, parent):
        """Return an inner frame inside a vertically scrolling canvas that fills
        `parent`. Pack content into the returned frame — the canvas scrolls when
        the content grows past the visible height."""
        canvas = tk.Canvas(parent, bg=BG_MAIN, highlightthickness=0)
        vbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_MAIN)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        # Keep the scroll region matched to the content height, and make the
        # inner frame track the canvas width so cards fill the row.
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))

        # Mouse-wheel scrolling, active only while the pointer is over the canvas.
        def _wheel(e):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-e.delta / 120), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return inner

    # ══════════════════════════════════════════════════════════
    #  ACTIVE ALERTS
    # ══════════════════════════════════════════════════════════
    def _show_alerts(self):
        self._clear()
        self._page_title("Active Alerts", "Currently broadcasting early warning alerts")

        alerts = get_active_alerts()

        if not alerts:
            tk.Label(self.content,
                     text="No active alerts at this time.",
                     font=(FONT, 12), fg=LGRAY, bg=BG_MAIN
                     ).pack(pady=40)
            return

        body = self._scrollable_body(self.content)
        for alert in alerts:
            card = tk.Frame(body, bg=BG_CARD)
            card.pack(fill="x", padx=25, pady=6)

            # Severity colour
            sev_color = RED if alert["severity"] == "HIGH" else ORANGE if alert["severity"] == "MEDIUM" else GOLD

            header = tk.Frame(card, bg=sev_color)
            header.pack(fill="x")
            tk.Label(header,
                     text=f"  [{alert['severity']}]  {alert['category'].upper()}  — Alert ID: {alert['id']}",
                     font=(FONT, 10, "bold"), fg=WHITE, bg=sev_color
                     ).pack(side="left", padx=10, pady=6)

            tk.Label(card, text=alert["english"],
                     font=(FONT, 9), fg=WHITE, bg=BG_CARD,
                     wraplength=700, justify="left"
                     ).pack(anchor="w", padx=15, pady=8)

            tk.Label(card,
                     text=f"Created: {alert['created_at']}",
                     font=(FONT, 8), fg=DGRAY, bg=BG_CARD
                     ).pack(anchor="w", padx=15, pady=(0, 5))

            def resolve(aid=alert["id"]):
                if messagebox.askyesno("Resolve Alert",
                                       f"Mark Alert {aid} as resolved?\nIt will stop broadcasting."):
                    resolve_alert(aid)
                    self._show_alerts()

            tk.Button(card, text="Resolve Alert",
                      font=(FONT, 9), fg=WHITE, bg=DGRAY,
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=resolve).pack(anchor="e", padx=15, pady=8)

    # ══════════════════════════════════════════════════════════
    #  CREATE ALERT
    # ══════════════════════════════════════════════════════════
    def _show_create_alert(self):
        self._clear()
        self._page_title("Create Early Warning Alert",
                         "Alert will be broadcast immediately to all participants")

        form = tk.Frame(self.content, bg=BG_CARD)
        form.pack(padx=25, pady=10, fill="x")

        # Category
        cat_row = tk.Frame(form, bg=BG_CARD)
        cat_row.pack(fill="x", padx=20, pady=8)
        tk.Label(cat_row, text="Category", font=(FONT, 10, "bold"),
                 fg=WHITE, bg=BG_CARD, width=12, anchor="w").pack(side="left")
        cat_var = tk.StringVar(value="smishing")
        ttk.Combobox(cat_row, textvariable=cat_var,
                     values=["smishing", "mobile_money", "vishing", "phishing", "general"],
                     state="readonly", width=30, font=(FONT, 10)
                     ).pack(side="left", padx=10, ipady=4)

        # Severity
        sev_row = tk.Frame(form, bg=BG_CARD)
        sev_row.pack(fill="x", padx=20, pady=8)
        tk.Label(sev_row, text="Severity", font=(FONT, 10, "bold"),
                 fg=WHITE, bg=BG_CARD, width=12, anchor="w").pack(side="left")
        sev_var = tk.StringVar(value="HIGH")
        for val, color in [("HIGH", RED), ("MEDIUM", ORANGE), ("LOW", GOLD)]:
            tk.Radiobutton(sev_row, text=val, variable=sev_var, value=val,
                           font=(FONT, 10, "bold"), fg=color, bg=BG_CARD,
                           selectcolor=BG_CARD, activebackground=BG_CARD
                           ).pack(side="left", padx=10)

        # English message
        tk.Label(form, text="Alert Message (English)",
                 font=(FONT, 10, "bold"), fg=WHITE, bg=BG_CARD
                 ).pack(anchor="w", padx=20, pady=(10, 2))
        msg_box = tk.Text(form, height=3, font=(FONT, 10),
                          bg="#2C4158", fg=WHITE, insertbackground=WHITE,
                          relief="flat", wrap="word")
        msg_box.pack(fill="x", padx=20, pady=4, ipady=4)

        char_label = tk.Label(form, text="0 / 160 characters",
                              font=(FONT, 8), fg=LGRAY, bg=BG_CARD)
        char_label.pack(anchor="e", padx=20)

        def update_char(event=None):
            count = len(msg_box.get("1.0", "end-1c"))
            color = RED if count > 160 else LGRAY
            char_label.config(text=f"{count} / 160 characters", fg=color)
        msg_box.bind("<KeyRelease>", update_char)

        # Bemba / Nyanja (optional)
        tk.Label(form, text="Bemba Translation (optional — NLLB-200 used if blank)",
                 font=(FONT, 9), fg=LGRAY, bg=BG_CARD
                 ).pack(anchor="w", padx=20, pady=(10, 2))
        bemba_box = tk.Text(form, height=2, font=(FONT, 10),
                            bg="#2C4158", fg=WHITE, insertbackground=WHITE,
                            relief="flat", wrap="word")
        bemba_box.pack(fill="x", padx=20, pady=4, ipady=4)

        tk.Label(form, text="Nyanja Translation (optional — NLLB-200 used if blank)",
                 font=(FONT, 9), fg=LGRAY, bg=BG_CARD
                 ).pack(anchor="w", padx=20, pady=(8, 2))
        nyanja_box = tk.Text(form, height=2, font=(FONT, 10),
                             bg="#2C4158", fg=WHITE, insertbackground=WHITE,
                             relief="flat", wrap="word")
        nyanja_box.pack(fill="x", padx=20, pady=4, ipady=4)

        status = tk.Label(form, text="", font=(FONT, 10), bg=BG_CARD, fg=GREEN)
        status.pack(pady=5)

        def create():
            english = msg_box.get("1.0", "end-1c").strip()
            bemba   = bemba_box.get("1.0", "end-1c").strip()
            nyanja  = nyanja_box.get("1.0", "end-1c").strip()

            if not english:
                status.config(text="Alert message cannot be empty.", fg=RED)
                return

            if len(english) > 160 and not messagebox.askyesno(
                    "Message exceeds 160 characters",
                    f"This message is {len(english)} characters and will be sent as "
                    f"multiple SMS parts. Send anyway?"):
                return

            if not messagebox.askyesno("Confirm Broadcast",
                                       f"Broadcast this {sev_var.get()} alert immediately to all participants?"):
                return

            try:
                add_alert(cat_var.get(), english, bemba, nyanja, sev_var.get())
            except Exception as e:
                status.config(text=f"Failed to create alert: {e}", fg=RED)
                return

            status.config(text="✓  Alert created. Broadcasting now...", fg=GREEN)

            def broadcast():
                try:
                    broadcast_alerts()
                    msg, color = "✓  Alert broadcast complete!", GREEN
                except Exception as e:
                    msg, color = f"Broadcast error: {e}", RED
                # Tkinter is not thread-safe — marshal the update to the main thread.
                self._ui(lambda: status.config(text=msg, fg=color))

            threading.Thread(target=broadcast, daemon=True).start()

        tk.Button(form, text="  Create & Broadcast Alert  ",
                  font=(FONT, 11, "bold"), fg=WHITE, bg=RED,
                  relief="flat", padx=15, pady=8, cursor="hand2",
                  command=create).pack(pady=15, padx=20, anchor="w")

    # ══════════════════════════════════════════════════════════
    #  SEND BLAST
    # ══════════════════════════════════════════════════════════
    def _show_send(self, auto=None):
        self._clear()
        self._page_title("Send Broadcast",
                         "Manually trigger message delivery")

        log = scrolledtext.ScrolledText(
            self.content, height=12, bg=BG_CARD, fg=GREEN,
            font=("Courier New", 9), state="disabled", relief="flat"
        )
        log.pack(fill="x", padx=25, pady=10)
        self._send_log = log
        self._log(log, "Ready. Click a button below to send.")

        btn_frame = tk.Frame(self.content, bg=BG_MAIN)
        btn_frame.pack(anchor="w", padx=25, pady=5)

        btns = [
            ("Send Awareness Tip",   GREEN,  broadcast_awareness, "Awareness blast"),
            ("Broadcast Alerts",     RED,    broadcast_alerts,    "Alert broadcast"),
            ("Full Daily Broadcast", PURPLE, daily_broadcast,     "Full daily broadcast"),
        ]
        for text, color, func, label in btns:
            tk.Button(btn_frame, text=f"  {text}  ",
                      font=(FONT, 11, "bold"), fg=WHITE, bg=color,
                      relief="flat", padx=15, pady=8, cursor="hand2",
                      command=lambda f=func, l=label: self._run_broadcast(f, l)
                      ).pack(side="left", padx=5)

        # When opened from a Dashboard quick action, start that job immediately.
        if auto:
            func, label = auto
            self._run_broadcast(func, label)

    def _run_broadcast(self, func, label):
        """Run a broadcast off the UI thread, capturing its console output into
        the send log. Tkinter is not thread-safe, so every widget update is
        marshalled back to the main thread via root.after()."""
        log = self._send_log
        self._log(log, f"Starting: {label}...")

        def task():
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            try:
                with redirect_stdout(f):
                    func()
                done, color = f"✓ {label} complete.", GREEN
            except Exception as e:
                done, color = f"✗ {label} failed: {e}", RED
            lines = [ln for ln in f.getvalue().splitlines() if ln.strip()]

            def flush():
                for line in lines:
                    self._log(log, line)
                self._log(log, done, color)
            self._ui(flush)

        threading.Thread(target=task, daemon=True).start()

    def _send_awareness_now(self):
        self._show_send(auto=(broadcast_awareness, "Awareness blast"))

    def _send_alerts_now(self):
        self._show_send(auto=(broadcast_alerts, "Alert broadcast"))

    def _send_full_now(self):
        self._show_send(auto=(daily_broadcast, "Full daily broadcast"))

    # ══════════════════════════════════════════════════════════
    #  STATISTICS
    # ══════════════════════════════════════════════════════════
    def _show_stats(self):
        self._clear()
        self._page_title("Send Statistics",
                         "Message delivery summary by type and language")

        stats = get_send_stats()

        if not stats:
            tk.Label(self.content,
                     text="No messages have been sent yet.",
                     font=(FONT, 12), fg=LGRAY, bg=BG_MAIN
                     ).pack(pady=40)
            return

        frame = tk.Frame(self.content, bg=BG_MAIN)
        frame.pack(padx=25, pady=10, anchor="w")

        for s in stats:
            card = tk.Frame(frame, bg=BG_CARD, width=220, height=120)
            card.pack_propagate(False)
            card.pack(side="left", padx=8, pady=8)

            color = RED if s["message_type"] == "alert" else GREEN
            tk.Label(card,
                     text=f"{s['message_type'].upper()} — {s['language'].upper()}",
                     font=(FONT, 9, "bold"), fg=color, bg=BG_CARD
                     ).pack(pady=(12, 2))
            tk.Label(card,
                     text=str(s["total_sent"]),
                     font=(FONT, 28, "bold"), fg=WHITE, bg=BG_CARD
                     ).pack()
            tk.Label(card,
                     text=f"messages  |  {s['unique_users']} participants",
                     font=(FONT, 8), fg=LGRAY, bg=BG_CARD
                     ).pack()


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app = AdminGUI(root)
    root.mainloop()