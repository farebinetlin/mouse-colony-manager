import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mouse_colony.db")


class DB:
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
                        CHECK(status IN ('breeding','holding','waiting_split')),
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
            """)
            mouse_cols = {row["name"] for row in c.execute("PRAGMA table_info(mice)").fetchall()}
            if "litter_id" not in mouse_cols:
                c.execute("ALTER TABLE mice ADD COLUMN litter_id INTEGER REFERENCES litters(id)")
            self._migrate_mouse_statuses(c)
            self._sync_breeding_mouse_statuses(c)

    def _migrate_mouse_statuses(self, c):
        table_sql = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='mice'"
        ).fetchone()["sql"]
        if "waiting_split" in table_sql and "'active'" not in table_sql:
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
                    CHECK(status IN ('breeding','holding','waiting_split')),
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
                    WHEN status='breeding' THEN 'breeding'
                    WHEN status='genotyping' THEN 'waiting_split'
                    ELSE 'holding'
                END,
                cage_location, notes, created_at
            FROM mice
        """)
        c.execute("DROP TABLE mice")
        c.execute("ALTER TABLE mice_new RENAME TO mice")

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
                "UPDATE mice SET status='breeding', cage_location=? WHERE id=?",
                (row["cage_label"], row["mouse_id"]),
            )

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
        with self._conn() as c:
            c.execute("DELETE FROM mice WHERE id=?", (mouse_id,))

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

    def delete_cage(self, cage_id):
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
