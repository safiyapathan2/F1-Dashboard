"""
Relational Formula 1 Team & Race Telemetry Dashboard
Course: Database Management Systems (DBMS)
Architecture: Single-file Python application utilizing SQLite3 and Tkinter/ttk
Theme: F1 Racing Paddock Dark Theme (#15151e / #e10600)

Features:
- Enforced Relational Integrity with Foreign Keys & ON DELETE CASCADE
- Auto-seeding database when empty with realistic F1 Grand Prix & Telemetry data
- Real-time Telemetry KPI Metrics (Grand Prix Events, Race Entries, Telemetry Points, Min Pit Duration)
- Smart Insert Panel: Automatic Grand Prix event ID reuse vs new event creation
- Cascade-aware Delete Panel with pre-delete impact warnings
- Real-time 4-Tab View (Multi-table JOIN view + 3 individual raw tables)
- Strict input validation (non-empty, non-negative values, date format checks)
"""

import os
import sqlite3
import datetime
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================
# DATABASE CONFIGURATION & OPERATIONS
# ==========================================

DB_FILENAME = "f1_telemetry.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, DB_FILENAME)


def get_connection():
    """
    Returns an SQLite connection with Foreign Keys and Row factory explicitly enabled.
    In SQLite, PRAGMA foreign_keys = ON must be executed for every connection!
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    Initializes tables with FOREIGN KEY constraints and ON DELETE CASCADE.
    Automatically seeds initial sample data if the database is completely empty.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Grand Prix Events Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grand_prix_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT UNIQUE NOT NULL COLLATE NOCASE,
                engineer_email TEXT NOT NULL
            );
        """)

        # 2. Race Entries Table (Child of grand_prix_events with ON DELETE CASCADE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                driver_name TEXT NOT NULL,
                race_date TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES grand_prix_events(event_id) ON DELETE CASCADE
            );
        """)

        # 3. Pit-Stop Telemetry Table (Child of race_entries with ON DELETE CASCADE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pit_stop_telemetry (
                telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                telemetry_type TEXT NOT NULL,
                measured_value REAL NOT NULL CHECK(measured_value >= 0),
                FOREIGN KEY (entry_id) REFERENCES race_entries(entry_id) ON DELETE CASCADE
            );
        """)

        # Check if database is empty to seed sample records
        cursor.execute("SELECT COUNT(*) AS cnt FROM grand_prix_events;")
        if cursor.fetchone()["cnt"] == 0:
            seed_sample_data(cursor)

        conn.commit()


def seed_sample_data(cursor):
    """Populates the database with realistic initial Formula 1 telemetry data."""
    # Seed Grand Prix Events
    sample_events = [
        ("Monaco Grand Prix", "gianpiero.lambiase@redbullracing.com"),
        ("British Grand Prix - Silverstone", "will.joseph@mclaren.com"),
        ("Italian Grand Prix - Monza", "bryan.bozzi@scuderiaferrari.com"),
        ("Belgian Grand Prix - Spa", "peter.bonnington@mercedesamgf1.com"),
    ]
    cursor.executemany(
        "INSERT INTO grand_prix_events (event_name, engineer_email) VALUES (?, ?);",
        sample_events,
    )

    # Seed Race Entries (event_id, driver_name, race_date)
    sample_entries = [
        (1, "Max Verstappen", "2026-05-24"),
        (1, "Charles Leclerc", "2026-05-24"),
        (2, "Lando Norris", "2026-07-05"),
        (2, "Oscar Piastri", "2026-07-05"),
        (3, "Lewis Hamilton", "2026-09-06"),
        (4, "George Russell", "2026-07-26"),
    ]
    cursor.executemany(
        "INSERT INTO race_entries (event_id, driver_name, race_date) VALUES (?, ?, ?);",
        sample_entries,
    )

    # Seed Pit-Stop Telemetry (entry_id, telemetry_type, measured_value)
    sample_telemetry = [
        (1, "Pit Stop Duration (s)", 2.18),
        (1, "Tyre Wear %", 42.5),
        (1, "Lap Time (s)", 74.32),
        (2, "Pit Stop Duration (s)", 2.45),
        (2, "Tyre Wear %", 58.0),
        (3, "Pit Stop Duration (s)", 1.98),
        (3, "Fuel Load (kg)", 24.2),
        (3, "Top Speed (km/h)", 332.8),
        (4, "Pit Stop Duration (s)", 2.31),
        (4, "Lap Time (s)", 89.14),
        (5, "Pit Stop Duration (s)", 2.12),
        (5, "Tyre Wear %", 66.4),
        (6, "Pit Stop Duration (s)", 2.29),
        (6, "Fuel Load (kg)", 18.5),
    ]
    cursor.executemany(
        "INSERT INTO pit_stop_telemetry (entry_id, telemetry_type, measured_value) VALUES (?, ?, ?);",
        sample_telemetry,
    )


# ==========================================
# DATABASE QUERY HELPERS
# ==========================================

def fetch_kpis():
    """Retrieves high-level metrics for the header KPI cards."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total_events FROM grand_prix_events;")
        total_events = cursor.fetchone()["total_events"]

        cursor.execute("SELECT COUNT(*) AS total_entries FROM race_entries;")
        total_entries = cursor.fetchone()["total_entries"]

        cursor.execute("SELECT COUNT(*) AS total_telemetry FROM pit_stop_telemetry;")
        total_telemetry = cursor.fetchone()["total_telemetry"]

        # Fastest recorded pit stop duration
        cursor.execute("""
            SELECT MIN(measured_value) AS fastest_pit 
            FROM pit_stop_telemetry 
            WHERE telemetry_type LIKE '%Pit Stop%';
        """)
        fastest_pit_row = cursor.fetchone()
        fastest_pit = fastest_pit_row["fastest_pit"] if fastest_pit_row and fastest_pit_row["fastest_pit"] is not None else 0.0

        return total_events, total_entries, total_telemetry, fastest_pit


def fetch_multi_table_join():
    """Tab 1: Multi-table JOIN combining Entry, Grand Prix Event, and Telemetry details."""
    query = """
        SELECT 
            r.entry_id,
            g.event_name,
            g.engineer_email,
            r.driver_name,
            r.race_date,
            t.telemetry_id,
            t.telemetry_type,
            t.measured_value
        FROM race_entries r
        JOIN grand_prix_events g ON r.event_id = g.event_id
        LEFT JOIN pit_stop_telemetry t ON r.entry_id = t.entry_id
        ORDER BY r.entry_id DESC, t.telemetry_id ASC;
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()


def fetch_raw_events():
    """Tab 2: Standalone Grand Prix Events table view."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT event_id, event_name, engineer_email FROM grand_prix_events ORDER BY event_id ASC;"
        ).fetchall()


def fetch_raw_entries():
    """Tab 3: Standalone Race Entries table view with resolved Event Name for clarity."""
    query = """
        SELECT r.entry_id, r.event_id, g.event_name, r.driver_name, r.race_date
        FROM race_entries r
        JOIN grand_prix_events g ON r.event_id = g.event_id
        ORDER BY r.entry_id ASC;
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()


def fetch_raw_telemetry():
    """Tab 4: Standalone Pit-Stop Telemetry table view with resolved Entry ID & Driver Name."""
    query = """
        SELECT t.telemetry_id, t.entry_id, r.driver_name, g.event_name, t.telemetry_type, t.measured_value
        FROM pit_stop_telemetry t
        JOIN race_entries r ON t.entry_id = r.entry_id
        JOIN grand_prix_events g ON r.event_id = g.event_id
        ORDER BY t.telemetry_id ASC;
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()


def insert_race_telemetry(event_name, engineer_email, driver_name, race_date, telemetry_type, measured_value):
    """
    Business Logic Check:
    - If Grand Prix event exists (case-insensitive name match), re-use its event_id.
    - If new Grand Prix event, insert new profile with provided engineer email.
    - Creates one race entry for that event and posts one pit-stop telemetry record under it.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Check for existing event
        cursor.execute("SELECT event_id, engineer_email FROM grand_prix_events WHERE event_name = ? COLLATE NOCASE;", (event_name,))
        existing_event = cursor.fetchone()

        if existing_event:
            event_id = existing_event["event_id"]
            if engineer_email and engineer_email.strip() and engineer_email.strip().lower() != existing_event["engineer_email"].lower():
                cursor.execute("UPDATE grand_prix_events SET engineer_email = ? WHERE event_id = ?;", (engineer_email.strip(), event_id))
            event_status = f"Existing Event (ID: {event_id})"
        else:
            cursor.execute("INSERT INTO grand_prix_events (event_name, engineer_email) VALUES (?, ?);", (event_name.strip(), engineer_email.strip()))
            event_id = cursor.lastrowid
            event_status = f"New GP Event Registered (ID: {event_id})"

        # Insert Race Entry
        cursor.execute(
            "INSERT INTO race_entries (event_id, driver_name, race_date) VALUES (?, ?, ?);",
            (event_id, driver_name.strip(), race_date.strip()),
        )
        entry_id = cursor.lastrowid

        # Insert Pit-Stop Telemetry
        cursor.execute(
            "INSERT INTO pit_stop_telemetry (entry_id, telemetry_type, measured_value) VALUES (?, ?, ?);",
            (entry_id, telemetry_type.strip(), float(measured_value)),
        )
        telemetry_id = cursor.lastrowid

        conn.commit()
        return event_status, entry_id, telemetry_id


def get_delete_options(target_type):
    """
    Dynamically generates deletion candidates with informative labels.
    """
    options = []
    with get_connection() as conn:
        cursor = conn.cursor()

        if target_type == "Grand Prix Event":
            cursor.execute("""
                SELECT 
                    g.event_id, 
                    g.event_name,
                    (SELECT COUNT(*) FROM race_entries r WHERE r.event_id = g.event_id) AS entry_cnt,
                    (SELECT COUNT(*) FROM pit_stop_telemetry t 
                     JOIN race_entries r ON t.entry_id = r.entry_id 
                     WHERE r.event_id = g.event_id) AS telemetry_cnt
                FROM grand_prix_events g
                ORDER BY g.event_name ASC;
            """)
            for row in cursor.fetchall():
                label = f"ID #{row['event_id']} - {row['event_name']} ({row['entry_cnt']} entries, {row['telemetry_cnt']} telemetry points)"
                options.append((label, row["event_id"]))

        elif target_type == "Race Entry":
            cursor.execute("""
                SELECT 
                    r.entry_id, 
                    g.event_name, 
                    r.driver_name, 
                    r.race_date,
                    (SELECT COUNT(*) FROM pit_stop_telemetry t WHERE t.entry_id = r.entry_id) AS telemetry_cnt
                FROM race_entries r
                JOIN grand_prix_events g ON r.event_id = g.event_id
                ORDER BY r.entry_id DESC;
            """)
            for row in cursor.fetchall():
                label = f"Entry #{row['entry_id']} - {row['driver_name']} @ {row['event_name']} ({row['race_date']}) - {row['telemetry_cnt']} telemetry pts"
                options.append((label, row["entry_id"]))

        elif target_type == "Pit-Stop Telemetry":
            cursor.execute("""
                SELECT 
                    t.telemetry_id, 
                    t.entry_id, 
                    r.driver_name, 
                    g.event_name, 
                    t.telemetry_type, 
                    t.measured_value
                FROM pit_stop_telemetry t
                JOIN race_entries r ON t.entry_id = r.entry_id
                JOIN grand_prix_events g ON r.event_id = g.event_id
                ORDER BY t.telemetry_id DESC;
            """)
            for row in cursor.fetchall():
                label = f"Telemetry #{row['telemetry_id']} - Entry #{row['entry_id']} ({row['driver_name']}): {row['telemetry_type']} = {row['measured_value']}"
                options.append((label, row["telemetry_id"]))

    return options


def calculate_cascade_impact(target_type, entity_id):
    """Calculates how many records will be cascaded before executing deletion."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if target_type == "Grand Prix Event":
            cursor.execute("SELECT event_name FROM grand_prix_events WHERE event_id = ?;", (entity_id,))
            event_row = cursor.fetchone()
            name = event_row["event_name"] if event_row else "Unknown Event"

            cursor.execute("SELECT COUNT(*) AS cnt FROM race_entries WHERE event_id = ?;", (entity_id,))
            entries_cnt = cursor.fetchone()["cnt"]

            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM pit_stop_telemetry t 
                JOIN race_entries r ON t.entry_id = r.entry_id 
                WHERE r.event_id = ?;
            """, (entity_id,))
            telemetry_cnt = cursor.fetchone()["cnt"]

            return (
                f"Grand Prix Event: '{name}' (ID: {entity_id})\n"
                f"• Cascaded Race Entries to delete: {entries_cnt}\n"
                f"• Cascaded Pit-Stop Telemetry logs to delete: {telemetry_cnt}\n\n"
                f"Action: ON DELETE CASCADE will permanently wipe this Grand Prix Event and ALL related Entries and Telemetry!"
            )

        elif target_type == "Race Entry":
            cursor.execute("""
                SELECT r.entry_id, r.driver_name, g.event_name 
                FROM race_entries r JOIN grand_prix_events g ON r.event_id = g.event_id 
                WHERE r.entry_id = ?;
            """, (entity_id,))
            row = cursor.fetchone()
            info = f"Entry #{row['entry_id']} ({row['driver_name']} @ {row['event_name']})" if row else "Unknown Entry"

            cursor.execute("SELECT COUNT(*) AS cnt FROM pit_stop_telemetry WHERE entry_id = ?;", (entity_id,))
            telemetry_cnt = cursor.fetchone()["cnt"]

            return (
                f"{info}\n"
                f"• Cascaded Pit-Stop Telemetry logs to delete: {telemetry_cnt}\n"
                f"• Parent Grand Prix Event profile will remain intact.\n\n"
                f"Action: ON DELETE CASCADE will wipe this Race Entry and all its telemetry data."
            )

        elif target_type == "Pit-Stop Telemetry":
            cursor.execute("""
                SELECT t.telemetry_id, t.telemetry_type, t.measured_value, t.entry_id, r.driver_name 
                FROM pit_stop_telemetry t 
                JOIN race_entries r ON t.entry_id = r.entry_id 
                WHERE t.telemetry_id = ?;
            """, (entity_id,))
            row = cursor.fetchone()
            desc = f"Telemetry #{row['telemetry_id']} ({row['driver_name']}: {row['telemetry_type']} = {row['measured_value']})" if row else "Unknown"
            return (
                f"{desc}\n"
                f"• Isolated Delete: Parent Race Entry #{row['entry_id']} and Grand Prix Event remain completely intact.\n\n"
                f"Action: Only this single telemetry metric row will be removed."
            )


def delete_record(target_type, entity_id):
    """Executes the deletion with SQLite PRAGMA foreign_keys = ON ensuring cascades work."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if target_type == "Grand Prix Event":
            cursor.execute("DELETE FROM grand_prix_events WHERE event_id = ?;", (entity_id,))
        elif target_type == "Race Entry":
            cursor.execute("DELETE FROM race_entries WHERE entry_id = ?;", (entity_id,))
        elif target_type == "Pit-Stop Telemetry":
            cursor.execute("DELETE FROM pit_stop_telemetry WHERE telemetry_id = ?;", (entity_id,))
        conn.commit()


# ==========================================
# GRAPHICAL USER INTERFACE (TKINTER / TTK)
# ==========================================

class F1TelemetryDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Formula 1 Team & Race Telemetry Dashboard")
        self.root.geometry("1220x840")
        self.root.minsize(1080, 740)

        # Apply Modern Styling
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._configure_f1_theme()

        # Cached delete options mapping: display_label -> entity_id
        self.current_delete_mapping = {}

        # Build UI Components
        self._build_header_kpis()
        self._build_control_panels()
        self._build_tabbed_display()
        self._build_status_bar()

        # Initial Data Refresh
        self.refresh_all_views()

    def _configure_f1_theme(self):
        """Configures the F1 dark racing paddock palette and typography."""
        # Theme Palette
        self.c_bg_dark = "#15151e"        # Carbon dark black
        self.c_card_bg = "#1f1f2e"        # Deep slate card background
        self.c_card_inner = "#262638"     # Input container background
        self.c_f1_red = "#e10600"         # Formula 1 Official Racing Red
        self.c_text_bright = "#ffffff"    # Pure white
        self.c_text_dim = "#94a3b8"       # Light muted slate
        self.c_telemetry_cyan = "#00d2be" # Mercedes/Telemetry Cyan
        self.c_border = "#33334d"         # Subtle borders

        self.root.configure(bg=self.c_bg_dark)

        # Fonts
        self.font_title = ("Segoe UI", 16, "bold")
        self.font_subtitle = ("Segoe UI", 9)
        self.font_card_num = ("Segoe UI", 16, "bold")
        self.font_bold = ("Segoe UI", 9, "bold")
        self.font_regular = ("Segoe UI", 9)

        # Style Combobox & Treeview
        self.style.configure(
            "TCombobox",
            fieldbackground="#2d2d42",
            background="#2d2d42",
            foreground="#ffffff",
            arrowcolor="#e10600",
        )
        self.style.map("TCombobox", fieldbackground=[("readonly", "#2d2d42")], foreground=[("readonly", "#ffffff")])

        # Treeview styling (Dark telemetry aesthetic)
        self.style.configure(
            "Treeview",
            background="#1e1e2d",
            foreground="#f1f5f9",
            rowheight=26,
            fieldbackground="#1e1e2d",
            font=self.font_regular,
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#2d2d44",
            foreground="#ffffff",
            relief="flat",
        )
        self.style.map("Treeview", background=[("selected", "#e10600")], foreground=[("selected", "#ffffff")])

        # Notebook (tabs) styling
        self.style.configure("TNotebook", background=self.c_bg_dark)
        self.style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 9, "bold"),
            padding=[16, 6],
            background="#1f1f2e",
            foreground="#cbd5e1",
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#e10600")],
            foreground=[("selected", "#ffffff")],
        )

    # -------------------------------------------------------------
    # 1. Header & Live Telemetry KPI Cards
    # -------------------------------------------------------------
    def _build_header_kpis(self):
        header_frame = tk.Frame(self.root, bg=self.c_bg_dark, padx=20, pady=12)
        header_frame.pack(fill="x", side="top")

        # Title & Subtitle with F1 Red Accent Line
        title_box = tk.Frame(header_frame, bg=self.c_bg_dark)
        title_box.pack(side="left", fill="y")

        lbl_f1 = tk.Label(
            title_box,
            text="FORMULA 1 // RACE TELEMETRY DASHBOARD",
            font=self.font_title,
            fg=self.c_text_bright,
            bg=self.c_bg_dark,
        )
        lbl_f1.pack(anchor="w")

        lbl_sub = tk.Label(
            title_box,
            text="Team Front-Desk & Trackside Paddock DB • Relational SQLite with ON DELETE CASCADE",
            font=self.font_subtitle,
            fg=self.c_text_dim,
            bg=self.c_bg_dark,
        )
        lbl_sub.pack(anchor="w")

        # KPI Metric Cards Frame
        kpi_container = tk.Frame(header_frame, bg=self.c_bg_dark)
        kpi_container.pack(side="right")

        self.kpi_events_val = tk.StringVar(value="0")
        self.kpi_entries_val = tk.StringVar(value="0")
        self.kpi_telemetry_val = tk.StringVar(value="0")
        self.kpi_fastest_pit_val = tk.StringVar(value="0.00s")

        self._create_kpi_card(kpi_container, "GRAND PRIX EVENTS", self.kpi_events_val, "#e10600")
        self._create_kpi_card(kpi_container, "RACE ENTRIES", self.kpi_entries_val, "#ff8000")
        self._create_kpi_card(kpi_container, "TELEMETRY LOGS", self.kpi_telemetry_val, "#00d2be")
        self._create_kpi_card(kpi_container, "BEST PIT STOP", self.kpi_fastest_pit_val, "#38a169")

    def _create_kpi_card(self, parent, title, var, accent_color):
        card = tk.Frame(parent, bg=self.c_card_bg, padx=14, pady=6, relief="ridge", bd=1)
        card.pack(side="left", padx=5)

        # Top border accent bar
        accent_strip = tk.Frame(card, bg=accent_color, height=3)
        accent_strip.pack(fill="x", side="top", pady=(0, 4))

        lbl_title = tk.Label(card, text=title, font=("Segoe UI", 7, "bold"), fg=self.c_text_dim, bg=self.c_card_bg)
        lbl_title.pack(anchor="center")

        lbl_num = tk.Label(card, textvariable=var, font=self.font_card_num, fg=self.c_text_bright, bg=self.c_card_bg)
        lbl_num.pack(anchor="center")

    # -------------------------------------------------------------
    # 2. Control Panels: Insert & Delete Panels
    # -------------------------------------------------------------
    def _build_control_panels(self):
        controls_container = tk.Frame(self.root, bg=self.c_bg_dark, padx=16, pady=6)
        controls_container.pack(fill="x", side="top")

        controls_container.columnconfigure(0, weight=6)
        controls_container.columnconfigure(1, weight=5)

        # ==================== INSERT PANEL ====================
        insert_group = tk.LabelFrame(
            controls_container,
            text="  📥 Trackside Entry & Pit-Stop Telemetry Logging  ",
            font=self.font_bold,
            fg=self.c_text_bright,
            bg=self.c_card_bg,
            padx=14,
            pady=10,
            relief="groove",
            bd=1,
        )
        insert_group.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Row 1: Event Name & Engineer Email
        tk.Label(insert_group, text="Grand Prix Event Name *", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).grid(row=0, column=0, sticky="w", pady=2)
        self.entry_event_name = ttk.Entry(insert_group, width=24)
        self.entry_event_name.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(0, 6))
        self.entry_event_name.bind("<KeyRelease>", self._on_event_name_key)

        tk.Label(insert_group, text="Race Engineer Email *", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).grid(row=0, column=1, sticky="w", pady=2)
        self.entry_engineer_email = ttk.Entry(insert_group, width=26)
        self.entry_engineer_email.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(0, 6))

        # Row 2: Driver Name & Race Date
        tk.Label(insert_group, text="Driver Name *", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).grid(row=2, column=0, sticky="w", pady=2)
        self.combo_driver = ttk.Combobox(
            insert_group,
            values=[
                "Max Verstappen",
                "Lando Norris",
                "Charles Leclerc",
                "Oscar Piastri",
                "Lewis Hamilton",
                "George Russell",
                "Carlos Sainz",
                "Fernando Alonso",
            ],
            width=22,
        )
        self.combo_driver.set("Max Verstappen")
        self.combo_driver.grid(row=3, column=0, sticky="w", padx=(0, 10), pady=(0, 6))

        tk.Label(insert_group, text="Race Date * (YYYY-MM-DD)", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).grid(row=2, column=1, sticky="w", pady=2)
        date_box = tk.Frame(insert_group, bg=self.c_card_bg)
        date_box.grid(row=3, column=1, sticky="w", padx=(0, 10), pady=(0, 6))

        self.entry_race_date = ttk.Entry(date_box, width=16)
        self.entry_race_date.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.entry_race_date.pack(side="left", padx=(0, 4))

        btn_today = tk.Button(
            date_box,
            text="Today",
            font=("Segoe UI", 8),
            bg="#33334d",
            fg="#ffffff",
            relief="flat",
            padx=6,
            command=self._set_today_date,
        )
        btn_today.pack(side="left")

        # Row 3: Telemetry Type & Measured Value
        tk.Label(insert_group, text="Telemetry Type *", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).grid(row=4, column=0, sticky="w", pady=2)
        self.combo_telemetry_type = ttk.Combobox(
            insert_group,
            values=[
                "Pit Stop Duration (s)",
                "Tyre Wear %",
                "Lap Time (s)",
                "Fuel Load (kg)",
                "Top Speed (km/h)",
                "Tyre Temp (°C)",
            ],
            width=22,
        )
        self.combo_telemetry_type.set("Pit Stop Duration (s)")
        self.combo_telemetry_type.grid(row=5, column=0, sticky="w", padx=(0, 10), pady=(0, 8))

        tk.Label(insert_group, text="Measured Value * (Numeric >= 0)", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).grid(row=4, column=1, sticky="w", pady=2)
        self.entry_measured_value = ttk.Entry(insert_group, width=16)
        self.entry_measured_value.insert(0, "2.25")
        self.entry_measured_value.grid(row=5, column=1, sticky="w", padx=(0, 10), pady=(0, 8))

        # Insert Action Buttons & Logic Status
        insert_btn_bar = tk.Frame(insert_group, bg=self.c_card_bg)
        insert_btn_bar.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        btn_add = tk.Button(
            insert_btn_bar,
            text="⚡ Log Race Telemetry",
            font=self.font_bold,
            bg=self.c_f1_red,
            fg="#ffffff",
            activebackground="#b30500",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.handle_insert,
        )
        btn_add.pack(side="left", padx=(0, 8))

        btn_clear = tk.Button(
            insert_btn_bar,
            text="Reset Form",
            font=self.font_regular,
            bg="#2d2d42",
            fg="#cbd5e1",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.clear_insert_form,
        )
        btn_clear.pack(side="left")

        self.lbl_event_status = tk.Label(
            insert_btn_bar,
            text="* Existing GP Event reuses ID; new name creates profile automatically.",
            font=("Segoe UI", 8, "italic"),
            fg=self.c_text_dim,
            bg=self.c_card_bg,
        )
        self.lbl_event_status.pack(side="right")

        # ==================== DELETE PANEL ====================
        delete_group = tk.LabelFrame(
            controls_container,
            text="  🗑️ Cascade Deletion & Relational Integrity Panel  ",
            font=self.font_bold,
            fg="#ff4d4d",
            bg=self.c_card_bg,
            padx=14,
            pady=10,
            relief="groove",
            bd=1,
        )
        delete_group.grid(row=0, column=1, sticky="nsew")

        # Target Entity Type Radio buttons
        tk.Label(delete_group, text="Select Target Entity Type:", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).pack(anchor="w", pady=(0, 2))

        type_radio_frame = tk.Frame(delete_group, bg=self.c_card_bg)
        type_radio_frame.pack(fill="x", pady=(0, 6))

        self.delete_target_type = tk.StringVar(value="Grand Prix Event")
        for ent_type in ["Grand Prix Event", "Race Entry", "Pit-Stop Telemetry"]:
            rb = tk.Radiobutton(
                type_radio_frame,
                text=ent_type,
                value=ent_type,
                variable=self.delete_target_type,
                command=self._on_delete_type_change,
                fg="#f1f5f9",
                bg=self.c_card_bg,
                selectcolor="#2d2d42",
                activebackground=self.c_card_bg,
                activeforeground="#ffffff",
                font=self.font_regular,
            )
            rb.pack(side="left", padx=(0, 10))

        # Dynamic Dropdown Selector
        tk.Label(delete_group, text="Select Specific Record to Delete:", font=self.font_bold, fg=self.c_text_bright, bg=self.c_card_bg).pack(anchor="w", pady=(0, 2))
        self.combo_delete_record = ttk.Combobox(delete_group, state="readonly", width=55)
        self.combo_delete_record.pack(fill="x", pady=(0, 8))
        self.combo_delete_record.bind("<<ComboboxSelected>>", self._on_delete_record_selected)

        # Dynamic Cascade Warning Box
        self.cascade_info_box = tk.Label(
            delete_group,
            text="Select an item above to inspect relational cascade impact.",
            font=("Segoe UI", 8),
            fg="#e2e8f0",
            bg="#262638",
            relief="solid",
            bd=1,
            padx=8,
            pady=6,
            justify="left",
            wraplength=410,
        )
        self.cascade_info_box.pack(fill="x", pady=(0, 8))

        # Delete Button
        self.btn_delete = tk.Button(
            delete_group,
            text="⚠️ Execute Deletion with Cascade",
            font=self.font_bold,
            bg="#b91c1c",
            fg="#ffffff",
            activebackground="#991b1b",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.handle_delete,
        )
        self.btn_delete.pack(anchor="w")

    # -------------------------------------------------------------
    # 3. Tabbed Display Panel (Notebook)
    # -------------------------------------------------------------
    def _build_tabbed_display(self):
        display_frame = tk.Frame(self.root, bg=self.c_bg_dark, padx=16, pady=4)
        display_frame.pack(fill="both", expand=True, side="top")

        self.notebook = ttk.Notebook(display_frame)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Combined Multi-Table JOIN
        self.tab_join = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_join, text=" 🏎️ Multi-Table Combined Telemetry (JOIN) ")
        self.tree_join = self._create_treeview(
            self.tab_join,
            columns=[
                ("entry_id", "Entry ID", 70, "center"),
                ("event_name", "Grand Prix Event", 180, "w"),
                ("engineer_email", "Engineer Email", 190, "w"),
                ("driver_name", "Driver Name", 140, "w"),
                ("race_date", "Race Date", 100, "center"),
                ("telemetry_id", "Telemetry ID", 90, "center"),
                ("telemetry_type", "Telemetry Type", 150, "w"),
                ("measured_value", "Measured Value", 110, "e"),
            ],
        )

        # Tab 2: Raw Grand Prix Events
        self.tab_events = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_events, text=" 🏁 Grand Prix Events (Raw Table) ")
        self.tree_events = self._create_treeview(
            self.tab_events,
            columns=[
                ("event_id", "Event ID", 90, "center"),
                ("event_name", "Grand Prix Event Name", 280, "w"),
                ("engineer_email", "Assigned Race Engineer Email", 320, "w"),
            ],
        )

        # Tab 3: Raw Race Entries
        self.tab_entries = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_entries, text=" 🚦 Race Entries (Raw Table) ")
        self.tree_entries = self._create_treeview(
            self.tab_entries,
            columns=[
                ("entry_id", "Entry ID", 90, "center"),
                ("event_id", "Event ID (FK)", 110, "center"),
                ("event_name", "Referenced Event Name", 240, "w"),
                ("driver_name", "Driver Name", 180, "w"),
                ("race_date", "Race Date", 130, "center"),
            ],
        )

        # Tab 4: Raw Pit-Stop Telemetry
        self.tab_telemetry = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_telemetry, text=" ⏱️ Pit-Stop Telemetry (Raw Table) ")
        self.tree_telemetry = self._create_treeview(
            self.tab_telemetry,
            columns=[
                ("telemetry_id", "Telemetry ID", 100, "center"),
                ("entry_id", "Entry ID (FK)", 110, "center"),
                ("driver_name", "Driver Name", 160, "w"),
                ("event_name", "Grand Prix Event", 200, "w"),
                ("telemetry_type", "Telemetry Type", 180, "w"),
                ("measured_value", "Measured Value", 120, "e"),
            ],
        )

    def _create_treeview(self, parent_tab, columns):
        """Helper to create a configured Treeview with dual scrollbars and alternate row striping."""
        container = tk.Frame(parent_tab, bg=self.c_card_bg)
        container.pack(fill="both", expand=True, padx=4, pady=4)

        col_ids = [c[0] for c in columns]
        tree = ttk.Treeview(container, columns=col_ids, show="headings", selectmode="browse")

        # Scrollbars
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid placement
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # Setup column headers
        for col_id, col_name, width, anchor in columns:
            tree.heading(col_id, text=col_name, anchor=anchor)
            tree.column(col_id, width=width, anchor=anchor, stretch=True)

        # Striping tags for dark theme
        tree.tag_configure("oddrow", background="#1a1a27")
        tree.tag_configure("evenrow", background="#222233")

        return tree

    # -------------------------------------------------------------
    # 4. Status Bar
    # -------------------------------------------------------------
    def _build_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg="#0d0d14", height=24, padx=12)
        self.status_bar.pack(fill="x", side="bottom")

        self.status_text = tk.StringVar(value="Ready. SQLite Relational Integrity & Cascades ACTIVE.")
        lbl_status = tk.Label(
            self.status_bar,
            textvariable=self.status_text,
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0d0d14",
            anchor="w",
        )
        lbl_status.pack(side="left")

        lbl_engine = tk.Label(
            self.status_bar,
            text=f"Engine: SQLite 3 • Storage: {DB_FILENAME}",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#0d0d14",
            anchor="e",
        )
        lbl_engine.pack(side="right")

    # -------------------------------------------------------------
    # EVENT HANDLERS & LOGIC CHECKS
    # -------------------------------------------------------------
    def _set_today_date(self):
        self.entry_race_date.delete(0, tk.END)
        self.entry_race_date.insert(0, datetime.date.today().strftime("%Y-%m-%d"))

    def _on_event_name_key(self, event):
        """As the user types a Grand Prix event name, check if it exists and pre-fill engineer email."""
        name = self.entry_event_name.get().strip()
        if not name:
            self.lbl_event_status.config(
                text="* Existing GP Event reuses ID; new name creates profile automatically.",
                fg=self.c_text_dim,
            )
            return

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id, engineer_email FROM grand_prix_events WHERE event_name = ? COLLATE NOCASE;", (name,))
            row = cursor.fetchone()
            if row:
                self.lbl_event_status.config(
                    text=f"✓ Found existing GP Event #{row['event_id']}. ID will be reused.",
                    fg="#00d2be",
                )
                if not self.entry_engineer_email.get().strip():
                    self.entry_engineer_email.delete(0, tk.END)
                    self.entry_engineer_email.insert(0, row["engineer_email"])
            else:
                self.lbl_event_status.config(
                    text="✨ New Grand Prix detected. Profile will be created on submit.",
                    fg="#38a169",
                )

    def _on_delete_type_change(self):
        """Refreshes the delete combo box whenever user switches target entity."""
        self._populate_delete_combobox()

    def _populate_delete_combobox(self):
        target_type = self.delete_target_type.get()
        options = get_delete_options(target_type)

        self.current_delete_mapping = {label: entity_id for label, entity_id in options}
        labels = [label for label, _ in options]

        self.combo_delete_record["values"] = labels
        if labels:
            self.combo_delete_record.current(0)
            self._on_delete_record_selected(None)
            self.btn_delete.config(state="normal")
        else:
            self.combo_delete_record.set("")
            self.cascade_info_box.config(
                text=f"No {target_type} records currently exist in the database.",
                fg="#94a3b8",
            )
            self.btn_delete.config(state="disabled")

    def _on_delete_record_selected(self, event):
        """Updates the pre-delete cascade warning box when an item is selected."""
        selected_label = self.combo_delete_record.get()
        if not selected_label or selected_label not in self.current_delete_mapping:
            self.cascade_info_box.config(text="Select a valid item to inspect cascade impact.")
            return

        target_type = self.delete_target_type.get()
        entity_id = self.current_delete_mapping[selected_label]
        impact_msg = calculate_cascade_impact(target_type, entity_id)
        self.cascade_info_box.config(text=impact_msg, fg="#ffffff")

    def clear_insert_form(self):
        """Resets insert form fields."""
        self.entry_event_name.delete(0, tk.END)
        self.entry_engineer_email.delete(0, tk.END)
        self.combo_driver.set("Max Verstappen")
        self._set_today_date()
        self.combo_telemetry_type.set("Pit Stop Duration (s)")
        self.entry_measured_value.delete(0, tk.END)
        self.entry_measured_value.insert(0, "2.25")
        self.lbl_event_status.config(
            text="* Existing GP Event reuses ID; new name creates profile automatically.",
            fg=self.c_text_dim,
        )

    # -------------------------------------------------------------
    # ACTION: INSERT RECORD
    # -------------------------------------------------------------
    def handle_insert(self):
        # 1. Validation: Non-blank fields
        event_name = self.entry_event_name.get().strip()
        engineer_email = self.entry_engineer_email.get().strip()
        driver = self.combo_driver.get().strip()
        race_date = self.entry_race_date.get().strip()
        telemetry_type = self.combo_telemetry_type.get().strip()
        val_raw = self.entry_measured_value.get().strip()

        if not event_name:
            messagebox.showerror("Validation Error", "Grand Prix Event Name cannot be blank.")
            self.entry_event_name.focus_set()
            return

        if not engineer_email:
            messagebox.showerror("Validation Error", "Race Engineer Email cannot be blank.")
            self.entry_engineer_email.focus_set()
            return

        if not driver:
            messagebox.showerror("Validation Error", "Driver Name cannot be blank.")
            self.combo_driver.focus_set()
            return

        if not race_date:
            messagebox.showerror("Validation Error", "Race Date cannot be blank.")
            self.entry_race_date.focus_set()
            return

        # Date Format Check (YYYY-MM-DD)
        try:
            datetime.datetime.strptime(race_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Validation Error",
                "Invalid Race Date format. Please use YYYY-MM-DD (e.g. 2026-05-24).",
            )
            self.entry_race_date.focus_set()
            return

        if not telemetry_type:
            messagebox.showerror("Validation Error", "Telemetry Type cannot be blank.")
            self.combo_telemetry_type.focus_set()
            return

        # Numeric and Non-Negative Measured Value Validation
        try:
            val_dec = Decimal(val_raw)
            if val_dec < 0:
                raise ValueError("Negative value")
        except (InvalidOperation, ValueError):
            messagebox.showerror(
                "Validation Error",
                "Measured Value must be a valid, non-negative numeric value (e.g., 2.18, 45.0).",
            )
            self.entry_measured_value.focus_set()
            return

        # 2. Database Insertion with Logic Check
        try:
            status_msg, entry_id, telemetry_id = insert_race_telemetry(
                event_name, engineer_email, driver, race_date, telemetry_type, float(val_dec)
            )
            messagebox.showinfo(
                "Telemetry Logged",
                f"✓ Successfully processed!\n\n"
                f"• Event Status: {status_msg}\n"
                f"• Race Entry Created: ID #{entry_id} ({driver} @ {event_name})\n"
                f"• Telemetry Posted: ID #{telemetry_id} ({telemetry_type}: {float(val_dec)})",
            )
            self.status_text.set(f"Record Added: Entry #{entry_id} ({driver}) - {telemetry_type}: {float(val_dec)}")

            # 3. Clear Form & Instantly Update Everything
            self.clear_insert_form()
            self.refresh_all_views()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to insert telemetry record: {str(e)}")

    # -------------------------------------------------------------
    # ACTION: DELETE RECORD (WITH CASCADE CONFIRMATION)
    # -------------------------------------------------------------
    def handle_delete(self):
        selected_label = self.combo_delete_record.get()
        if not selected_label or selected_label not in self.current_delete_mapping:
            messagebox.showwarning("Selection Required", "Please select a valid record to delete.")
            return

        target_type = self.delete_target_type.get()
        entity_id = self.current_delete_mapping[selected_label]
        impact_details = calculate_cascade_impact(target_type, entity_id)

        # Strict Confirmation Dialog
        confirm = messagebox.askyesno(
            f"Confirm {target_type} Deletion",
            f"Are you sure you want to delete this record?\n\n{impact_details}\n\nThis operation CANNOT be undone.",
            icon="warning",
        )

        if not confirm:
            return

        try:
            delete_record(target_type, entity_id)
            messagebox.showinfo(
                "Deletion Completed",
                f"✓ {target_type} #{entity_id} deleted successfully.\nAll child relationships were cascaded properly.",
            )
            self.status_text.set(f"Deleted {target_type} #{entity_id}. Relational cascade complete.")

            # Instantly update views and dropdowns (preventing stale pointers)
            self.refresh_all_views()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Deletion failed: {str(e)}")

    # -------------------------------------------------------------
    # REFRESH VIEWS & DATA TABLES
    # -------------------------------------------------------------
    def refresh_all_views(self):
        """Fetches fresh data, updates KPI metrics, all 4 Treeviews, and dropdowns."""
        self._refresh_kpis()
        self._populate_delete_combobox()
        self._refresh_tab_join()
        self._refresh_tab_events()
        self._refresh_tab_entries()
        self._refresh_tab_telemetry()

    def _refresh_kpis(self):
        total_ev, total_en, total_tel, fastest_pit = fetch_kpis()
        self.kpi_events_val.set(str(total_ev))
        self.kpi_entries_val.set(str(total_en))
        self.kpi_telemetry_val.set(str(total_tel))
        self.kpi_fastest_pit_val.set(f"{fastest_pit:.2f}s" if fastest_pit > 0 else "N/A")

    def _refresh_tab_join(self):
        for item in self.tree_join.get_children():
            self.tree_join.delete(item)

        rows = fetch_multi_table_join()
        for idx, r in enumerate(rows):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            tel_id = r["telemetry_id"] if r["telemetry_id"] is not None else "-"
            tel_type = r["telemetry_type"] if r["telemetry_type"] is not None else "(No telemetry)"
            val = f"{r['measured_value']:.2f}" if r["measured_value"] is not None else "0.00"

            self.tree_join.insert(
                "",
                "end",
                values=(
                    r["entry_id"],
                    r["event_name"],
                    r["engineer_email"],
                    r["driver_name"],
                    r["race_date"],
                    tel_id,
                    tel_type,
                    val,
                ),
                tags=(tag,),
            )

    def _refresh_tab_events(self):
        for item in self.tree_events.get_children():
            self.tree_events.delete(item)

        rows = fetch_raw_events()
        for idx, r in enumerate(rows):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_events.insert(
                "",
                "end",
                values=(r["event_id"], r["event_name"], r["engineer_email"]),
                tags=(tag,),
            )

    def _refresh_tab_entries(self):
        for item in self.tree_entries.get_children():
            self.tree_entries.delete(item)

        rows = fetch_raw_entries()
        for idx, r in enumerate(rows):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_entries.insert(
                "",
                "end",
                values=(r["entry_id"], r["event_id"], r["event_name"], r["driver_name"], r["race_date"]),
                tags=(tag,),
            )

    def _refresh_tab_telemetry(self):
        for item in self.tree_telemetry.get_children():
            self.tree_telemetry.delete(item)

        rows = fetch_raw_telemetry()
        for idx, r in enumerate(rows):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_telemetry.insert(
                "",
                "end",
                values=(
                    r["telemetry_id"],
                    r["entry_id"],
                    r["driver_name"],
                    r["event_name"],
                    r["telemetry_type"],
                    f"{r['measured_value']:.2f}",
                ),
                tags=(tag,),
            )


# ==========================================
# MAIN EXECUTION ENTRY POINT
# ==========================================

def main():
    # 1. Initialize DB and seed if empty
    init_database()

    # 2. Launch GUI
    root = tk.Tk()
    app = F1TelemetryDashboardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

