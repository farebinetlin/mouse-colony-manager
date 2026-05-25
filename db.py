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
                    status TEXT DEFAULT 'active'
                        CHECK(status IN ('active','breeding','genotyping','assigned','sacrificed','dead')),
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
            """)

    # ── Mice ──────────────────────────────────────────────

    def add_mouse(self, ear_tag, birth_date=None, sex="U", father_tag=None,
                  mother_tag=None, birth_cage_id=None, status="active", cage_location=None, notes=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO mice (ear_tag, birth_date, sex, father_tag, mother_tag, birth_cage_id, status, cage_location, notes) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (ear_tag, birth_date, sex, father_tag, mother_tag, birth_cage_id, status, cage_location, notes),
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
        valid = {"ear_tag", "birth_date", "sex", "father_tag", "mother_tag", "birth_cage_id", "status", "cage_location", "notes"}
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
                "pending_genotyping": c.execute(
                    "SELECT COUNT(*) FROM mice WHERE status='genotyping'"
                ).fetchone()[0],
                "unknown_genotypes": c.execute(
                    "SELECT COUNT(DISTINCT mouse_id) FROM genotypes WHERE allele1='?' OR allele2='?'"
                ).fetchone()[0],
                "pending_alerts": c.execute(
                    "SELECT COUNT(*) FROM alerts WHERE resolved=0"
                ).fetchone()[0],
            }
