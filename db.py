import sqlite3
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import date, datetime

DB_PATH = os.environ.get(
    "MOUSE_COLONY_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "mouse_colony.db"),
)


class DB:
    CORE_SCHEMA = {
        "mice": {"id", "ear_tag", "birth_date", "sex", "status"},
        "genotypes": {"id", "mouse_id", "gene", "allele1", "allele2"},
        "breeding_cages": {"id", "cage_label", "cage_type", "status"},
        "cage_females": {"id", "cage_id", "mouse_id"},
        "litters": {"id", "cage_id", "birth_date"},
    }

    def __init__(self, path=DB_PATH):
        self.path = path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def validate_database_file(cls, path):
        if not path or not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise ValueError("Database file is empty or missing.")
        uri = f"file:{os.path.abspath(path)}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"Database integrity check failed: {integrity}")
            foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_errors:
                raise ValueError("Database contains broken foreign-key references.")
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing_tables = sorted(set(cls.CORE_SCHEMA) - tables)
            if missing_tables:
                raise ValueError(
                    "Database is missing required tables: " + ", ".join(missing_tables)
                )
            for table, required_columns in cls.CORE_SCHEMA.items():
                columns = {
                    row["name"]
                    for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
                missing_columns = sorted(required_columns - columns)
                if missing_columns:
                    raise ValueError(
                        f"Table '{table}' is missing columns: " + ", ".join(missing_columns)
                    )
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"Invalid SQLite database: {exc}") from None
        finally:
            if "conn" in locals():
                conn.close()
        return True

    def backup_to(self, destination):
        destination = os.path.abspath(destination)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        if os.path.exists(destination):
            os.remove(destination)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        self.validate_database_file(destination)
        return destination

    def restore_from_bytes(self, data, backup_dir=None):
        if not data:
            raise ValueError("Uploaded database is empty.")
        base_dir = os.path.dirname(os.path.abspath(self.path))
        fd, candidate_path = tempfile.mkstemp(
            prefix=".mouse_colony_restore_", suffix=".db", dir=base_dir
        )
        try:
            with os.fdopen(fd, "wb") as candidate:
                candidate.write(data)
            self.validate_database_file(candidate_path)

            backup_dir = backup_dir or os.path.join(base_dir, "backups")
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = os.path.join(
                backup_dir, f"mouse_colony-before-restore-{timestamp}.db"
            )
            self.backup_to(backup_path)

            os.replace(candidate_path, self.path)
            candidate_path = None
            try:
                self._init_db()
                self.validate_database_file(self.path)
            except Exception as exc:
                shutil.copy2(backup_path, self.path)
                self._init_db()
                raise ValueError(
                    f"Restore failed; the previous database was restored: {exc}"
                ) from None
            return backup_path
        finally:
            if candidate_path and os.path.exists(candidate_path):
                os.remove(candidate_path)

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS mice (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ear_tag TEXT UNIQUE NOT NULL,
                    birth_date TEXT,
                    sex TEXT CHECK(sex IN ('M', 'F', 'U')),
                    father_tag TEXT,
                    mother_tag TEXT,
                    birth_cage_id INTEGER REFERENCES breeding_cages(id),
                    litter_id INTEGER REFERENCES litters(id),
                    status TEXT DEFAULT 'holding'
                        CHECK(status IN ('breeding','holding','waiting_split','dead')),
                    cage_location TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS genotypes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mouse_id INTEGER NOT NULL REFERENCES mice(id) ON DELETE CASCADE,
                    gene TEXT NOT NULL,
                    allele1 TEXT NOT NULL DEFAULT '?',
                    allele2 TEXT NOT NULL DEFAULT '?',
                    UNIQUE(mouse_id, gene)
                );

                CREATE TABLE IF NOT EXISTS breeding_cages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cage_label TEXT UNIQUE NOT NULL,
                    cage_type TEXT DEFAULT 'breeding'
                        CHECK(cage_type IN ('breeding','holding')),
                    male_id INTEGER REFERENCES mice(id),
                    female_id INTEGER REFERENCES mice(id),
                    setup_date TEXT,
                    separation_date TEXT,
                    status TEXT DEFAULT 'active'
                        CHECK(status IN ('active','separated','ended')),
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS cage_females (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cage_id INTEGER NOT NULL REFERENCES breeding_cages(id) ON DELETE CASCADE,
                    mouse_id INTEGER NOT NULL REFERENCES mice(id) ON DELETE CASCADE,
                    UNIQUE(cage_id, mouse_id)
                );

                CREATE TABLE IF NOT EXISTS litters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cage_id INTEGER NOT NULL REFERENCES breeding_cages(id) ON DELETE CASCADE,
                    birth_date TEXT NOT NULL,
                    total_born INTEGER,
                    weaned_count INTEGER,
                    weaning_date TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS split_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cage_id INTEGER NOT NULL REFERENCES breeding_cages(id) ON DELETE CASCADE,
                    due_date TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    resolved_date TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS mouse_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mouse_id INTEGER NOT NULL REFERENCES mice(id) ON DELETE CASCADE,
                    measure_date TEXT NOT NULL,
                    weight_g REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(mouse_id, measure_date)
                );

                CREATE TABLE IF NOT EXISTS mouse_survival (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mouse_id INTEGER NOT NULL REFERENCES mice(id) ON DELETE CASCADE,
                    end_date TEXT NOT NULL,
                    outcome TEXT NOT NULL
                        CHECK(outcome IN ('dead','euthanized','censored')),
                    death_method TEXT,
                    previous_status TEXT,
                    previous_cage_location TEXT,
                    previous_cage_id INTEGER REFERENCES breeding_cages(id),
                    previous_cage_role TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(mouse_id)
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mouse_id INTEGER REFERENCES mice(id) ON DELETE CASCADE,
                    alert_type TEXT NOT NULL,
                    due_date TEXT,
                    resolved INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS custom_genes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gene TEXT UNIQUE NOT NULL,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS gene_colors (
                    gene TEXT PRIMARY KEY,
                    color TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                );
            """)
            mouse_cols = {row["name"] for row in c.execute("PRAGMA table_info(mice)").fetchall()}
            if "litter_id" not in mouse_cols:
                c.execute("ALTER TABLE mice ADD COLUMN litter_id INTEGER REFERENCES litters(id)")
            self._migrate_mouse_statuses(c)
            self._migrate_survival_columns(c)
            self._sync_breeding_mouse_statuses(c)

    def _migrate_mouse_statuses(self, c):
        table_sql = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='mice'"
        ).fetchone()["sql"]
        if "waiting_split" in table_sql and "'active'" not in table_sql and "'dead'" in table_sql:
            return

        c.execute("PRAGMA foreign_keys=OFF")
        c.execute("""
            CREATE TABLE mice_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ear_tag TEXT UNIQUE NOT NULL,
                birth_date TEXT,
                sex TEXT CHECK(sex IN ('M', 'F', 'U')),
                father_tag TEXT,
                mother_tag TEXT,
                birth_cage_id INTEGER REFERENCES breeding_cages(id),
                litter_id INTEGER REFERENCES litters(id),
                status TEXT DEFAULT 'holding'
                    CHECK(status IN ('breeding','holding','waiting_split','dead')),
                cage_location TEXT,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        c.execute("""
            INSERT INTO mice_new (
                id, ear_tag, birth_date, sex, father_tag, mother_tag,
                birth_cage_id, litter_id, status, cage_location, notes, created_at
            )
            SELECT
                id, ear_tag, birth_date, sex, father_tag, mother_tag,
                birth_cage_id, litter_id,
                CASE
                    WHEN status='dead' THEN 'dead'
                    WHEN status='breeding' THEN 'breeding'
                    WHEN status='genotyping' THEN 'waiting_split'
                    ELSE 'holding'
                END,
                cage_location, notes, created_at
            FROM mice
        """)
        c.execute("DROP TABLE mice")
        c.execute("ALTER TABLE mice_new RENAME TO mice")

    def _migrate_survival_columns(self, c):
        survival_cols = {row["name"] for row in c.execute("PRAGMA table_info(mouse_survival)").fetchall()}
        if "death_method" not in survival_cols:
            c.execute("ALTER TABLE mouse_survival ADD COLUMN death_method TEXT")
        if "previous_status" not in survival_cols:
            c.execute("ALTER TABLE mouse_survival ADD COLUMN previous_status TEXT")
        if "previous_cage_location" not in survival_cols:
            c.execute("ALTER TABLE mouse_survival ADD COLUMN previous_cage_location TEXT")
        if "previous_cage_id" not in survival_cols:
            c.execute("ALTER TABLE mouse_survival ADD COLUMN previous_cage_id INTEGER REFERENCES breeding_cages(id)")
        if "previous_cage_role" not in survival_cols:
            c.execute("ALTER TABLE mouse_survival ADD COLUMN previous_cage_role TEXT")

    def _sync_breeding_mouse_statuses(self, c):
        rows = c.execute("""
            SELECT bc.cage_label, bc.male_id AS mouse_id
            FROM breeding_cages bc
            WHERE bc.cage_type='breeding' AND bc.status='active' AND bc.male_id IS NOT NULL
            UNION
            SELECT bc.cage_label, cf.mouse_id
            FROM breeding_cages bc
            JOIN cage_females cf ON cf.cage_id = bc.id
            WHERE bc.cage_type='breeding' AND bc.status='active'
        """).fetchall()
        for row in rows:
            c.execute(
                "UPDATE mice SET status='breeding', cage_location=? WHERE id=? AND status!='dead'",
                (row["cage_label"], row["mouse_id"]),
            )

        # A mouse in an active breeding cage is a breeder only when it is linked
        # as a male or female parent. Other residents are pups waiting to split.
        c.execute("""
            UPDATE mice
            SET status='waiting_split'
            WHERE status='breeding'
              AND status!='dead'
              AND EXISTS (
                  SELECT 1 FROM breeding_cages bc
                  WHERE bc.cage_type='breeding'
                    AND bc.status='active'
                    AND bc.cage_label=mice.cage_location
              )
              AND NOT EXISTS (
                  SELECT 1 FROM breeding_cages bc
                  WHERE bc.cage_type='breeding'
                    AND bc.status='active'
                    AND bc.male_id=mice.id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM cage_females cf
                  JOIN breeding_cages bc ON bc.id=cf.cage_id
                  WHERE bc.cage_type='breeding'
                    AND bc.status='active'
                    AND cf.mouse_id=mice.id
              )
        """)

        c.execute("""
            UPDATE mice
            SET status='holding'
            WHERE status!='dead'
              AND EXISTS (
                  SELECT 1 FROM breeding_cages bc
                  WHERE bc.cage_type='holding'
                    AND bc.status='active'
                    AND bc.cage_label=mice.cage_location
              )
        """)

    # ── Mice ──────────────────────────────────────────────

    def add_mouse(self, ear_tag, birth_date=None, sex="U", father_tag=None,
                  mother_tag=None, birth_cage_id=None, litter_id=None,
                  status="holding", cage_location=None, notes=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO mice (ear_tag, birth_date, sex, father_tag, mother_tag, birth_cage_id, litter_id, status, cage_location, notes) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ear_tag, birth_date, sex, father_tag, mother_tag, birth_cage_id, litter_id, status, cage_location, notes),
            )
            return c.lastrowid

    def get_mouse(self, mouse_id):
        with self._conn() as c:
            return c.execute("SELECT * FROM mice WHERE id=?", (mouse_id,)).fetchone()

    def get_mouse_by_tag(self, ear_tag):
        with self._conn() as c:
            return c.execute("SELECT * FROM mice WHERE ear_tag=?", (ear_tag,)).fetchone()

    def get_all_mice(self, status_filter=None):
        with self._conn() as c:
            if status_filter:
                return c.execute(
                    "SELECT * FROM mice WHERE status=? ORDER BY id DESC", (status_filter,)
                ).fetchall()
            return c.execute("SELECT * FROM mice ORDER BY id DESC").fetchall()

    def update_mouse(self, mouse_id, **kwargs):
        valid = {"ear_tag", "birth_date", "sex", "father_tag", "mother_tag", "birth_cage_id", "litter_id", "status", "cage_location", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in valid}
        if not updates:
            return
        set_clause = ", ".join(f"{k}=?" for k in updates)
        with self._conn() as c:
            c.execute(
                f"UPDATE mice SET {set_clause} WHERE id=?",
                (*updates.values(), mouse_id),
            )

    def delete_mouse(self, mouse_id):
        return self.safe_delete_mouse(mouse_id)

    def get_mouse_delete_impact(self, mouse_id):
        with self._conn() as c:
            mouse = c.execute("SELECT * FROM mice WHERE id=?", (mouse_id,)).fetchone()
            if not mouse:
                raise ValueError("Mouse not found.")
            counts = {
                "genotypes": c.execute(
                    "SELECT COUNT(*) AS n FROM genotypes WHERE mouse_id=?", (mouse_id,)
                ).fetchone()["n"],
                "weights": c.execute(
                    "SELECT COUNT(*) AS n FROM mouse_weights WHERE mouse_id=?", (mouse_id,)
                ).fetchone()["n"],
                "survival": c.execute(
                    "SELECT COUNT(*) AS n FROM mouse_survival WHERE mouse_id=?", (mouse_id,)
                ).fetchone()["n"],
                "cage_links": c.execute(
                    """SELECT (
                           SELECT COUNT(*) FROM breeding_cages
                           WHERE male_id=? OR female_id=?
                       ) + (
                           SELECT COUNT(*) FROM cage_females WHERE mouse_id=?
                       ) AS n""",
                    (mouse_id, mouse_id, mouse_id),
                ).fetchone()["n"],
                "children": c.execute(
                    "SELECT COUNT(*) AS n FROM mice WHERE father_tag=? OR mother_tag=?",
                    (mouse["ear_tag"], mouse["ear_tag"]),
                ).fetchone()["n"],
            }
            return counts

    def safe_delete_mouse(self, mouse_id):
        impact = self.get_mouse_delete_impact(mouse_id)
        with self._conn() as c:
            mouse = c.execute("SELECT id FROM mice WHERE id=?", (mouse_id,)).fetchone()
            if not mouse:
                raise ValueError("Mouse not found.")
            c.execute(
                "UPDATE breeding_cages SET male_id=NULL WHERE male_id=?",
                (mouse_id,),
            )
            c.execute(
                "UPDATE breeding_cages SET female_id=NULL WHERE female_id=?",
                (mouse_id,),
            )
            c.execute("DELETE FROM cage_females WHERE mouse_id=?", (mouse_id,))
            c.execute("DELETE FROM mice WHERE id=?", (mouse_id,))
        return impact

    def _validated_mouse_event_date(self, c, mouse_id, event_date, label):
        mouse = c.execute(
            "SELECT birth_date FROM mice WHERE id=?", (mouse_id,)
        ).fetchone()
        if not mouse:
            raise ValueError("Mouse not found.")
        try:
            parsed = date.fromisoformat(str(event_date))
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a valid date.") from None
        if parsed > date.today():
            raise ValueError(f"{label} cannot be in the future.")
        if mouse["birth_date"]:
            try:
                birth = date.fromisoformat(mouse["birth_date"])
            except ValueError:
                birth = None
            if birth and parsed < birth:
                raise ValueError(f"{label} cannot be before the birth date.")
        return parsed

    # ── Weights and Survival ─────────────────────────────

    def upsert_weight(self, mouse_id, measure_date, weight_g, notes=None):
        if weight_g <= 0:
            raise ValueError("Weight must be greater than 0 g.")
        with self._conn() as c:
            self._validated_mouse_event_date(c, mouse_id, measure_date, "Weight date")
            c.execute(
                """INSERT INTO mouse_weights (mouse_id, measure_date, weight_g, notes)
                   VALUES (?,?,?,?)
                   ON CONFLICT(mouse_id, measure_date)
                   DO UPDATE SET weight_g=excluded.weight_g, notes=excluded.notes""",
                (mouse_id, measure_date, weight_g, notes),
            )

    def delete_weight(self, weight_id):
        with self._conn() as c:
            c.execute("DELETE FROM mouse_weights WHERE id=?", (weight_id,))

    def get_weight_records(self, mouse_ids=None):
        if mouse_ids is not None and not mouse_ids:
            return []
        with self._conn() as c:
            sql = """SELECT w.*, m.ear_tag, m.sex, m.birth_date, m.cage_location
                     FROM mouse_weights w
                     JOIN mice m ON w.mouse_id = m.id"""
            params = []
            if mouse_ids is not None:
                placeholders = ",".join("?" for _ in mouse_ids)
                sql += f" WHERE w.mouse_id IN ({placeholders})"
                params.extend(mouse_ids)
            sql += " ORDER BY w.measure_date, m.ear_tag"
            return c.execute(sql, params).fetchall()

    def set_survival_record(self, mouse_id, end_date, outcome, notes=None,
                            death_method=None, previous_status=None,
                            previous_cage_location=None, previous_cage_id=None,
                            previous_cage_role=None):
        with self._conn() as c:
            self._validated_mouse_event_date(c, mouse_id, end_date, "Endpoint date")
            c.execute(
                """INSERT INTO mouse_survival (
                       mouse_id, end_date, outcome, death_method,
                       previous_status, previous_cage_location,
                       previous_cage_id, previous_cage_role, notes
                   )
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(mouse_id)
                   DO UPDATE SET end_date=excluded.end_date,
                                 outcome=excluded.outcome,
                                 death_method=excluded.death_method,
                                 previous_status=COALESCE(mouse_survival.previous_status, excluded.previous_status),
                                 previous_cage_location=COALESCE(mouse_survival.previous_cage_location, excluded.previous_cage_location),
                                 previous_cage_id=COALESCE(mouse_survival.previous_cage_id, excluded.previous_cage_id),
                                 previous_cage_role=COALESCE(mouse_survival.previous_cage_role, excluded.previous_cage_role),
                                 notes=excluded.notes""",
                (
                    mouse_id, end_date, outcome, death_method, previous_status,
                    previous_cage_location, previous_cage_id,
                    previous_cage_role, notes,
                ),
            )

    def _mouse_cage_assignment(self, c, mouse):
        return c.execute(
            """SELECT bc.*,
                      CASE
                          WHEN bc.male_id=? THEN 'male'
                          WHEN EXISTS (
                              SELECT 1 FROM cage_females cf
                              WHERE cf.cage_id=bc.id AND cf.mouse_id=?
                          ) THEN CASE WHEN bc.cage_type='breeding' THEN 'female' ELSE 'member' END
                          ELSE 'location'
                      END AS cage_role
               FROM breeding_cages bc
               WHERE bc.male_id=?
                  OR EXISTS (
                      SELECT 1 FROM cage_females cf
                      WHERE cf.cage_id=bc.id AND cf.mouse_id=?
                  )
                  OR bc.cage_label=?
               ORDER BY (bc.cage_label=?) DESC,
                        (bc.status='active') DESC,
                        bc.id DESC
               LIMIT 1""",
            (
                mouse["id"], mouse["id"], mouse["id"], mouse["id"],
                mouse["cage_location"], mouse["cage_location"],
            ),
        ).fetchone()

    def mark_mouse_dead(self, mouse_id, death_date, death_method, notes=None):
        with self._conn() as c:
            mouse = c.execute("SELECT * FROM mice WHERE id=?", (mouse_id,)).fetchone()
            if not mouse:
                raise ValueError("Mouse not found.")
            self._validated_mouse_event_date(c, mouse_id, death_date, "Death date")
            existing = c.execute(
                "SELECT * FROM mouse_survival WHERE mouse_id=?", (mouse_id,)
            ).fetchone()
            assignment = self._mouse_cage_assignment(c, mouse)
            previous_status = (
                existing["previous_status"] if existing and existing["previous_status"]
                else (mouse["status"] if mouse["status"] != "dead" else "holding")
            )
            previous_cage = (
                existing["previous_cage_location"] if existing and existing["previous_cage_location"]
                else mouse["cage_location"]
            )
            previous_cage_id = (
                existing["previous_cage_id"] if existing and existing["previous_cage_id"]
                else (assignment["id"] if assignment else None)
            )
            previous_cage_role = (
                existing["previous_cage_role"] if existing and existing["previous_cage_role"]
                else (assignment["cage_role"] if assignment else None)
            )
            outcome = "dead" if death_method == "Natural death" else "censored"
            c.execute(
                """INSERT INTO mouse_survival (
                       mouse_id, end_date, outcome, death_method,
                       previous_status, previous_cage_location,
                       previous_cage_id, previous_cage_role, notes
                   )
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(mouse_id)
                   DO UPDATE SET end_date=excluded.end_date,
                                 outcome=excluded.outcome,
                                 death_method=excluded.death_method,
                                 previous_status=COALESCE(mouse_survival.previous_status, excluded.previous_status),
                                 previous_cage_location=COALESCE(mouse_survival.previous_cage_location, excluded.previous_cage_location),
                                 previous_cage_id=COALESCE(mouse_survival.previous_cage_id, excluded.previous_cage_id),
                                 previous_cage_role=COALESCE(mouse_survival.previous_cage_role, excluded.previous_cage_role),
                                 notes=excluded.notes""",
                (
                    mouse_id, death_date, outcome, death_method, previous_status,
                    previous_cage, previous_cage_id, previous_cage_role, notes,
                ),
            )
            c.execute("DELETE FROM cage_females WHERE mouse_id=?", (mouse_id,))
            c.execute("UPDATE breeding_cages SET male_id=NULL WHERE male_id=?", (mouse_id,))
            c.execute("UPDATE breeding_cages SET female_id=NULL WHERE female_id=?", (mouse_id,))
            c.execute("UPDATE mice SET status='dead', cage_location=NULL WHERE id=?", (mouse_id,))

    def restore_dead_mouse(self, mouse_id):
        with self._conn() as c:
            record = c.execute(
                "SELECT * FROM mouse_survival WHERE mouse_id=?", (mouse_id,)
            ).fetchone()
            if not record:
                raise ValueError("No death record found for this mouse.")
            status = record["previous_status"] or "holding"
            if status not in ("breeding", "holding", "waiting_split"):
                status = "holding"
            previous_cage_id = record["previous_cage_id"]
            if not previous_cage_id and record["previous_cage_location"]:
                row = c.execute(
                    "SELECT id FROM breeding_cages WHERE cage_label=?",
                    (record["previous_cage_location"],),
                ).fetchone()
                previous_cage_id = row["id"] if row else None

            cage = None
            if previous_cage_id:
                cage = c.execute(
                    "SELECT * FROM breeding_cages WHERE id=?", (previous_cage_id,)
                ).fetchone()

            warning = None
            location = None
            role = record["previous_cage_role"]
            if cage and cage["status"] == "active":
                location = cage["cage_label"]
                if role == "male":
                    if cage["male_id"] in (None, mouse_id):
                        c.execute(
                            "UPDATE breeding_cages SET male_id=? WHERE id=?",
                            (mouse_id, cage["id"]),
                        )
                        status = "breeding"
                    else:
                        location = None
                        status = "holding"
                        warning = "Original male slot is already occupied; restored as unassigned holding."
                elif role == "female":
                    c.execute(
                        "INSERT OR IGNORE INTO cage_females (cage_id, mouse_id) VALUES (?,?)",
                        (cage["id"], mouse_id),
                    )
                    status = "breeding"
                elif role in ("member", "location") and cage["cage_type"] == "holding":
                    c.execute(
                        "INSERT OR IGNORE INTO cage_females (cage_id, mouse_id) VALUES (?,?)",
                        (cage["id"], mouse_id),
                    )
                    status = "holding"
                elif not role and cage["cage_type"] == "holding":
                    c.execute(
                        "INSERT OR IGNORE INTO cage_females (cage_id, mouse_id) VALUES (?,?)",
                        (cage["id"], mouse_id),
                    )
                    status = "holding"
                elif cage["cage_type"] == "breeding":
                    status = "waiting_split"
            else:
                status = "holding"
                warning = "Original cage is unavailable or inactive; restored as unassigned holding."
            c.execute(
                "UPDATE mice SET status=?, cage_location=? WHERE id=?",
                (status, location, mouse_id),
            )
            c.execute("DELETE FROM mouse_survival WHERE mouse_id=?", (mouse_id,))
            return {"status": status, "cage_location": location, "warning": warning}

    def delete_survival_record(self, mouse_id):
        with self._conn() as c:
            c.execute("DELETE FROM mouse_survival WHERE mouse_id=?", (mouse_id,))

    def get_survival_records(self, mouse_ids=None):
        if mouse_ids is not None and not mouse_ids:
            return []
        with self._conn() as c:
            sql = """SELECT s.*, m.ear_tag, m.sex, m.birth_date, m.cage_location, m.status
                     FROM mouse_survival s
                     JOIN mice m ON s.mouse_id = m.id"""
            params = []
            if mouse_ids is not None:
                placeholders = ",".join("?" for _ in mouse_ids)
                sql += f" WHERE s.mouse_id IN ({placeholders})"
                params.extend(mouse_ids)
            sql += " ORDER BY s.end_date DESC, m.ear_tag"
            return c.execute(sql, params).fetchall()

    def get_death_archive(self):
        with self._conn() as c:
            return c.execute(
                """SELECT m.*, s.end_date, s.outcome, s.death_method,
                          s.previous_status, s.previous_cage_location,
                          s.previous_cage_id, s.previous_cage_role,
                          s.notes AS death_notes
                   FROM mouse_survival s
                   JOIN mice m ON s.mouse_id = m.id
                   WHERE m.status='dead' OR s.death_method IS NOT NULL
                   ORDER BY s.end_date DESC, m.ear_tag"""
            ).fetchall()

    def search_mice(self, query):
        with self._conn() as c:
            q = f"%{query}%"
            return c.execute(
                "SELECT * FROM mice WHERE ear_tag LIKE ? OR notes LIKE ? OR cage_location LIKE ? OR father_tag LIKE ? OR mother_tag LIKE ?",
                (q, q, q, q, q),
            ).fetchall()

    def get_mice_by_birth_cage(self, cage_id):
        with self._conn() as c:
            return c.execute(
                "SELECT * FROM mice WHERE birth_cage_id=? ORDER BY ear_tag", (cage_id,)
            ).fetchall()

    def get_mice_by_litter(self, litter_id):
        with self._conn() as c:
            return c.execute(
                "SELECT * FROM mice WHERE litter_id=? ORDER BY ear_tag", (litter_id,)
            ).fetchall()

    def find_existing_ear_tags(self, ear_tags):
        if not ear_tags:
            return []
        placeholders = ",".join("?" for _ in ear_tags)
        with self._conn() as c:
            rows = c.execute(
                f"SELECT ear_tag FROM mice WHERE ear_tag IN ({placeholders}) ORDER BY ear_tag",
                tuple(ear_tags),
            ).fetchall()
            return [r["ear_tag"] for r in rows]

    def get_mice_by_genotype(self, gene, allele):
        with self._conn() as c:
            return c.execute(
                """SELECT DISTINCT m.* FROM mice m
                   JOIN genotypes g ON m.id = g.mouse_id
                   WHERE g.gene=? AND (g.allele1=? OR g.allele2=?)""",
                (gene, allele, allele),
            ).fetchall()

    # ── Genotypes ─────────────────────────────────────────

    def set_genotype(self, mouse_id, gene, allele1, allele2):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO genotypes (mouse_id, gene, allele1, allele2) "
                "VALUES (?,?,?,?)",
                (mouse_id, gene, allele1, allele2),
            )

    def get_mouse_genotypes(self, mouse_id):
        with self._conn() as c:
            return c.execute(
                "SELECT * FROM genotypes WHERE mouse_id=?", (mouse_id,)
            ).fetchall()

    def get_all_genotypes(self):
        with self._conn() as c:
            return c.execute(
                """SELECT g.*, m.ear_tag, m.sex, m.status,
                          m.father_tag, m.mother_tag, m.cage_location, m.notes, m.birth_date
                   FROM genotypes g JOIN mice m ON g.mouse_id = m.id
                   ORDER BY m.id, g.gene"""
            ).fetchall()

    def get_distinct_genes(self):
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT gene FROM genotypes ORDER BY gene"
            ).fetchall()
            return [r["gene"] for r in rows]

    def get_custom_genes(self):
        with self._conn() as c:
            rows = c.execute(
                "SELECT gene FROM custom_genes ORDER BY gene"
            ).fetchall()
            return [r["gene"] for r in rows]

    def add_custom_gene(self, gene):
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO custom_genes (gene) VALUES (?)", (gene.strip(),)
            )

    def remove_custom_gene(self, gene):
        with self._conn() as c:
            c.execute("DELETE FROM custom_genes WHERE gene=?", (gene.strip(),))

    def get_gene_colors(self):
        with self._conn() as c:
            rows = c.execute("SELECT gene, color FROM gene_colors ORDER BY gene").fetchall()
            return {r["gene"]: r["color"] for r in rows}

    def set_gene_color(self, gene, color):
        gene = gene.strip()
        color = color.strip()
        if not gene or not color:
            return
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO gene_colors (gene, color, updated_at) "
                "VALUES (?, ?, datetime('now','localtime'))",
                (gene, color),
            )

    def delete_gene_color(self, gene):
        with self._conn() as c:
            c.execute("DELETE FROM gene_colors WHERE gene=?", (gene.strip(),))

    def set_custom_genes(self, genes):
        with self._conn() as c:
            c.execute("DELETE FROM custom_genes")
            for gene in genes:
                gene = gene.strip()
                if gene:
                    c.execute("INSERT OR IGNORE INTO custom_genes (gene) VALUES (?)", (gene,))

    def get_mice_for_gene(self, gene):
        with self._conn() as c:
            return c.execute(
                """SELECT m.*, g.allele1, g.allele2, g.id AS genotype_id
                   FROM mice m
                   JOIN genotypes g ON m.id = g.mouse_id
                   WHERE g.gene = ?
                   ORDER BY m.ear_tag""",
                (gene,),
            ).fetchall()

    def delete_genotype(self, genotype_id):
        with self._conn() as c:
            c.execute("DELETE FROM genotypes WHERE id=?", (genotype_id,))

    # ── Breeding Cages ────────────────────────────────────

    def add_breeding_cage(self, cage_label, cage_type="breeding", male_id=None,
                          setup_date=None, notes=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO breeding_cages (cage_label, cage_type, male_id, setup_date, notes) "
                "VALUES (?,?,?,?,?)",
                (cage_label, cage_type, male_id, setup_date, notes),
            )
            return c.lastrowid

    def set_cage_females(self, cage_id, mouse_ids):
        with self._conn() as c:
            c.execute("DELETE FROM cage_females WHERE cage_id=?", (cage_id,))
            for mid in mouse_ids:
                if mid is not None:
                    c.execute(
                        "INSERT OR IGNORE INTO cage_females (cage_id, mouse_id) VALUES (?,?)",
                        (cage_id, mid),
                    )

    def get_cage_females(self, cage_id):
        with self._conn() as c:
            return c.execute(
                "SELECT m.* FROM cage_females cf JOIN mice m ON cf.mouse_id = m.id WHERE cf.cage_id=? ORDER BY m.ear_tag",
                (cage_id,),
            ).fetchall()

    def _female_subquery(self):
        return """(SELECT GROUP_CONCAT(mf.ear_tag, ', ')
                   FROM cage_females cf
                   JOIN mice mf ON cf.mouse_id = mf.id
                   WHERE cf.cage_id = bc.id) AS female_tags,
                  (SELECT COUNT(*) FROM cage_females cf WHERE cf.cage_id = bc.id) AS female_count"""

    def get_breeding_cage(self, cage_id):
        with self._conn() as c:
            return c.execute(
                f"""SELECT bc.*, m.ear_tag AS male_tag, {self._female_subquery()}
                   FROM breeding_cages bc
                   LEFT JOIN mice m ON bc.male_id = m.id
                   WHERE bc.id=?""",
                (cage_id,),
            ).fetchone()

    def get_all_breeding_cages(self, status_filter=None):
        with self._conn() as c:
            base = f"""SELECT bc.*, m.ear_tag AS male_tag, {self._female_subquery()}
                      FROM breeding_cages bc
                      LEFT JOIN mice m ON bc.male_id = m.id"""
            if status_filter:
                return c.execute(
                    base + " WHERE bc.status=? ORDER BY bc.id DESC", (status_filter,)
                ).fetchall()
            return c.execute(base + " ORDER BY bc.id DESC").fetchall()

    def get_cage_by_label(self, cage_label):
        with self._conn() as c:
            return c.execute(
                f"""SELECT bc.*, m.ear_tag AS male_tag, {self._female_subquery()}
                   FROM breeding_cages bc
                   LEFT JOIN mice m ON bc.male_id = m.id
                   WHERE bc.cage_label=?""",
                (cage_label,),
            ).fetchone()

    def get_current_cage_mice(self, cage_id):
        with self._conn() as c:
            cage = c.execute(
                "SELECT * FROM breeding_cages WHERE id=?", (cage_id,)
            ).fetchone()
            if not cage:
                return []
            return c.execute(
                """SELECT DISTINCT m.*
                   FROM mice m
                   WHERE m.status!='dead'
                     AND (
                         m.cage_location=?
                         OR m.id=?
                         OR m.id=?
                         OR EXISTS (
                             SELECT 1 FROM cage_females cf
                             WHERE cf.cage_id=? AND cf.mouse_id=m.id
                         )
                     )
                   ORDER BY m.ear_tag""",
                (cage["cage_label"], cage["male_id"], cage["female_id"], cage_id),
            ).fetchall()

    def get_or_create_holding_cage(self, cage_label, setup_date=None, notes=None):
        existing = self.get_cage_by_label(cage_label)
        if existing:
            if existing["cage_type"] != "holding":
                raise ValueError(f"Cage '{cage_label}' already exists and is not a holding cage.")
            return existing["id"]
        return self.add_breeding_cage(
            cage_label=cage_label,
            cage_type="holding",
            male_id=None,
            setup_date=setup_date,
            notes=notes,
        )

    def update_breeding_cage(self, cage_id, **kwargs):
        valid = {"cage_label", "cage_type", "male_id", "setup_date",
                 "separation_date", "status", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in valid}
        if not updates:
            return
        set_clause = ", ".join(f"{k}=?" for k in updates)
        with self._conn() as c:
            c.execute(
                f"UPDATE breeding_cages SET {set_clause} WHERE id=?",
                (*updates.values(), cage_id),
            )

    def get_cage_delete_impact(self, cage_id):
        with self._conn() as c:
            cage = c.execute(
                "SELECT * FROM breeding_cages WHERE id=?", (cage_id,)
            ).fetchone()
            if not cage:
                raise ValueError("Cage not found.")
            linked_members = c.execute(
                """SELECT (CASE WHEN ? IS NULL THEN 0 ELSE 1 END) +
                          (CASE WHEN ? IS NULL THEN 0 ELSE 1 END) +
                          (SELECT COUNT(*) FROM cage_females WHERE cage_id=?) AS n""",
                (cage["male_id"], cage["female_id"], cage_id),
            ).fetchone()["n"]
            impact = {
                "linked_members": linked_members,
                "located_mice": c.execute(
                    "SELECT COUNT(*) AS n FROM mice WHERE cage_location=? AND status!='dead'",
                    (cage["cage_label"],),
                ).fetchone()["n"],
                "birth_mice": c.execute(
                    "SELECT COUNT(*) AS n FROM mice WHERE birth_cage_id=?", (cage_id,)
                ).fetchone()["n"],
                "litters": c.execute(
                    "SELECT COUNT(*) AS n FROM litters WHERE cage_id=?", (cage_id,)
                ).fetchone()["n"],
                "reminders": c.execute(
                    "SELECT COUNT(*) AS n FROM split_reminders WHERE cage_id=?", (cage_id,)
                ).fetchone()["n"],
            }
            impact["can_delete"] = not any(impact.values())
            return impact

    def end_cage(self, cage_id, separation_date=None):
        separation_date = separation_date or str(date.today())
        with self._conn() as c:
            cage = c.execute(
                "SELECT * FROM breeding_cages WHERE id=?", (cage_id,)
            ).fetchone()
            if not cage:
                raise ValueError("Cage not found.")
            c.execute(
                "UPDATE breeding_cages SET status='ended', separation_date=? WHERE id=?",
                (separation_date, cage_id),
            )
            c.execute(
                """UPDATE mice
                   SET status='holding', cage_location=NULL
                   WHERE cage_location=? AND status!='dead'""",
                (cage["cage_label"],),
            )

    def delete_cage(self, cage_id):
        impact = self.get_cage_delete_impact(cage_id)
        if not impact["can_delete"]:
            raise ValueError("This cage has mice or history. End it instead of deleting it.")
        with self._conn() as c:
            c.execute("DELETE FROM cage_females WHERE cage_id=?", (cage_id,))
            c.execute("DELETE FROM breeding_cages WHERE id=?", (cage_id,))

    # ── Litters ───────────────────────────────────────────

    def add_litter(self, cage_id, birth_date, total_born,
                   weaning_date=None, weaned_count=None, notes=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO litters (cage_id, birth_date, total_born, weaning_date, weaned_count, notes) "
                "VALUES (?,?,?,?,?,?)",
                (cage_id, birth_date, total_born, weaning_date, weaned_count, notes),
            )
            return c.lastrowid

    def get_litters_for_cage(self, cage_id):
        with self._conn() as c:
            return c.execute(
                "SELECT * FROM litters WHERE cage_id=? ORDER BY birth_date DESC",
                (cage_id,),
            ).fetchall()

    def get_litter(self, litter_id):
        with self._conn() as c:
            return c.execute("SELECT * FROM litters WHERE id=?", (litter_id,)).fetchone()

    def get_all_litters(self):
        with self._conn() as c:
            return c.execute(
                """SELECT l.*, bc.cage_label
                   FROM litters l
                   JOIN breeding_cages bc ON l.cage_id = bc.id
                   ORDER BY l.birth_date DESC"""
            ).fetchall()

    def update_litter(self, litter_id, **kwargs):
        valid = {"birth_date", "total_born", "weaned_count", "weaning_date", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in valid}
        if not updates:
            return
        set_clause = ", ".join(f"{k}=?" for k in updates)
        with self._conn() as c:
            c.execute(
                f"UPDATE litters SET {set_clause} WHERE id=?",
                (*updates.values(), litter_id),
            )

    def delete_litter(self, litter_id, delete_pups=False):
        with self._conn() as c:
            if delete_pups:
                c.execute("DELETE FROM mice WHERE litter_id=?", (litter_id,))
            else:
                c.execute("UPDATE mice SET litter_id=NULL WHERE litter_id=?", (litter_id,))
            c.execute("DELETE FROM litters WHERE id=?", (litter_id,))

    def split_litter(self, litter_id, assignments, male_cage_label, female_cage_label,
                     weaning_date, weaned_count=None):
        """Assign litter pups to male/female holding cages and mark the litter weaned."""
        male_cage_id = self.get_or_create_holding_cage(
            male_cage_label, setup_date=weaning_date, notes=f"Auto-created for litter #{litter_id}"
        )
        female_cage_id = self.get_or_create_holding_cage(
            female_cage_label, setup_date=weaning_date, notes=f"Auto-created for litter #{litter_id}"
        )
        male_cage = self.get_breeding_cage(male_cage_id)
        female_cage = self.get_breeding_cage(female_cage_id)
        cage_for_sex = {"M": male_cage["cage_label"], "F": female_cage["cage_label"]}

        with self._conn() as c:
            for mouse_id, sex in assignments:
                if sex not in ("M", "F"):
                    continue
                c.execute(
                    "UPDATE mice SET sex=?, status='holding', cage_location=? WHERE id=?",
                    (sex, cage_for_sex[sex], mouse_id),
                )
            c.execute(
                "UPDATE litters SET weaning_date=?, weaned_count=? WHERE id=?",
                (weaning_date, weaned_count if weaned_count is not None else len(assignments), litter_id),
            )

    # ── Split Reminders ─────────────────────────────────────

    def add_split_reminder(self, cage_id, due_date, notes=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO split_reminders (cage_id, due_date, notes) VALUES (?,?,?)",
                (cage_id, due_date, notes),
            )
            return c.lastrowid

    def get_split_reminders_for_cage(self, cage_id, active_only=False):
        with self._conn() as c:
            sql = "SELECT * FROM split_reminders WHERE cage_id=?"
            params = [cage_id]
            if active_only:
                sql += " AND resolved=0"
            sql += " ORDER BY resolved ASC, due_date ASC, id DESC"
            return c.execute(sql, params).fetchall()

    def get_all_split_reminders(self, active_only=False):
        with self._conn() as c:
            sql = """SELECT sr.*, bc.cage_label
                     FROM split_reminders sr
                     JOIN breeding_cages bc ON sr.cage_id = bc.id"""
            if active_only:
                sql += " WHERE sr.resolved=0"
            sql += " ORDER BY sr.resolved ASC, sr.due_date ASC, sr.id DESC"
            return c.execute(sql).fetchall()

    def resolve_split_reminder(self, reminder_id, resolved_date):
        with self._conn() as c:
            c.execute(
                "UPDATE split_reminders SET resolved=1, resolved_date=? WHERE id=?",
                (resolved_date, reminder_id),
            )

    def delete_split_reminder(self, reminder_id):
        with self._conn() as c:
            c.execute("DELETE FROM split_reminders WHERE id=?", (reminder_id,))

    # ── Alerts ────────────────────────────────────────────

    def add_alert(self, mouse_id=None, alert_type="", due_date=None, notes=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO alerts (mouse_id, alert_type, due_date, notes) VALUES (?,?,?,?)",
                (mouse_id, alert_type, due_date, notes),
            )
            return c.lastrowid

    def get_pending_alerts(self):
        with self._conn() as c:
            return c.execute(
                """SELECT a.*, m.ear_tag FROM alerts a
                   LEFT JOIN mice m ON a.mouse_id = m.id
                   WHERE a.resolved=0 ORDER BY a.due_date"""
            ).fetchall()

    def get_all_alerts(self):
        with self._conn() as c:
            return c.execute(
                """SELECT a.*, m.ear_tag FROM alerts a
                   LEFT JOIN mice m ON a.mouse_id = m.id
                   ORDER BY a.resolved, a.due_date"""
            ).fetchall()

    def resolve_alert(self, alert_id):
        with self._conn() as c:
            c.execute("UPDATE alerts SET resolved=1 WHERE id=?", (alert_id,))

    # ── Stats ─────────────────────────────────────────────

    def get_stats(self):
        with self._conn() as c:
            return {
                "total_mice": c.execute("SELECT COUNT(*) FROM mice").fetchone()[0],
                "active_breeders": c.execute(
                    "SELECT COUNT(*) FROM breeding_cages WHERE status='active' AND cage_type='breeding'"
                ).fetchone()[0],
                "waiting_split": c.execute(
                    "SELECT COUNT(*) FROM mice WHERE status='waiting_split'"
                ).fetchone()[0],
                "unknown_genotypes": c.execute(
                    "SELECT COUNT(DISTINCT mouse_id) FROM genotypes WHERE allele1='?' OR allele2='?'"
                ).fetchone()[0],
                "pending_alerts": c.execute(
                    "SELECT COUNT(*) FROM alerts WHERE resolved=0"
                ).fetchone()[0],
            }
