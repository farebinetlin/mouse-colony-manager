import os
import tempfile
import unittest

from db import DB
from survival_analysis import kaplan_meier_points


class StabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.db = DB(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_mouse(self, tag, sex="U", **kwargs):
        return self.db.add_mouse(
            tag,
            kwargs.pop("birth_date", "2026-01-01"),
            sex,
            **kwargs,
        )

    def test_current_cage_membership_excludes_moved_birth_mice(self):
        male = self.add_mouse("M1", "M", status="breeding", cage_location="B1")
        female = self.add_mouse("F1", "F", status="breeding", cage_location="B1")
        breeding = self.db.add_breeding_cage(
            "B1", cage_type="breeding", male_id=male, setup_date="2026-01-01"
        )
        self.db.set_cage_females(breeding, [female])
        waiting = self.add_mouse(
            "P1",
            "U",
            birth_cage_id=breeding,
            status="waiting_split",
            cage_location="B1",
        )
        holding = self.db.add_breeding_cage("H1", cage_type="holding")
        moved = self.add_mouse(
            "P2",
            "F",
            birth_cage_id=breeding,
            status="holding",
            cage_location="H1",
        )

        breeding_ids = {m["id"] for m in self.db.get_current_cage_mice(breeding)}
        holding_ids = {m["id"] for m in self.db.get_current_cage_mice(holding)}
        self.assertEqual(breeding_ids, {male, female, waiting})
        self.assertEqual(holding_ids, {moved})

    def test_non_parent_in_breeding_cage_becomes_waiting_split(self):
        cage = self.db.add_breeding_cage("B1", cage_type="breeding")
        mouse = self.add_mouse("P1", "M", status="breeding", cage_location="B1")
        self.assertEqual(self.db.get_mouse(mouse)["status"], "breeding")

        refreshed = DB(self.db_path)
        self.assertEqual(refreshed.get_mouse(mouse)["status"], "waiting_split")
        self.assertEqual(refreshed.get_breeding_cage(cage)["status"], "active")

    def test_safe_delete_unlinks_breeding_parent(self):
        male = self.add_mouse("M1", "M")
        cage = self.db.add_breeding_cage("B1", cage_type="breeding", male_id=male)
        self.db.set_genotype(male, "GeneA", "+", "0")
        self.db.upsert_weight(male, "2026-01-10", 20.0)

        impact = self.db.safe_delete_mouse(male)
        self.assertEqual(impact["cage_links"], 1)
        self.assertEqual(impact["genotypes"], 1)
        self.assertEqual(impact["weights"], 1)
        self.assertIsNone(self.db.get_breeding_cage(cage)["male_id"])
        self.assertIsNone(self.db.get_mouse(male))

    def test_cage_delete_is_limited_to_empty_cages(self):
        empty = self.db.add_breeding_cage("EMPTY", cage_type="holding")
        self.db.delete_cage(empty)
        self.assertIsNone(self.db.get_breeding_cage(empty))

        cage = self.db.add_breeding_cage("B1", cage_type="breeding")
        self.add_mouse("P1", birth_cage_id=cage, status="waiting_split", cage_location="B1")
        with self.assertRaisesRegex(ValueError, "End it instead"):
            self.db.delete_cage(cage)

    def test_death_restore_reconnects_parent_role(self):
        male = self.add_mouse("M1", "M", status="breeding", cage_location="B1")
        cage = self.db.add_breeding_cage("B1", cage_type="breeding", male_id=male)

        self.db.mark_mouse_dead(male, "2026-02-01", "Natural death", "mistake")
        record = self.db.get_survival_records([male])[0]
        self.assertEqual(record["outcome"], "dead")
        self.assertEqual(record["previous_cage_role"], "male")
        self.assertIsNone(self.db.get_breeding_cage(cage)["male_id"])

        result = self.db.restore_dead_mouse(male)
        restored = self.db.get_mouse(male)
        self.assertIsNone(result["warning"])
        self.assertEqual(restored["status"], "breeding")
        self.assertEqual(restored["cage_location"], "B1")
        self.assertEqual(self.db.get_breeding_cage(cage)["male_id"], male)

    def test_experimental_harvest_is_censored(self):
        mouse = self.add_mouse("M1", "M", status="holding")
        self.db.mark_mouse_dead(mouse, "2026-02-01", "Experimental harvest")
        record = self.db.get_survival_records([mouse])[0]
        self.assertEqual(record["outcome"], "censored")

    def test_death_restore_reconnects_holding_member(self):
        mouse = self.add_mouse("F1", "F", status="holding", cage_location="H1")
        cage = self.db.add_breeding_cage("H1", cage_type="holding")
        self.db.set_cage_females(cage, [mouse])

        self.db.mark_mouse_dead(mouse, "2026-02-01", "Experimental harvest")
        self.assertEqual(self.db.get_cage_females(cage), [])
        result = self.db.restore_dead_mouse(mouse)

        self.assertIsNone(result["warning"])
        self.assertEqual(result["status"], "holding")
        self.assertEqual(result["cage_location"], "H1")
        self.assertEqual([m["id"] for m in self.db.get_cage_females(cage)], [mouse])

    def test_end_cage_releases_current_mice_but_preserves_history(self):
        male = self.add_mouse("M1", "M", status="breeding", cage_location="B1")
        cage = self.db.add_breeding_cage("B1", cage_type="breeding", male_id=male)
        self.db.end_cage(cage, "2026-03-01")

        ended = self.db.get_breeding_cage(cage)
        released = self.db.get_mouse(male)
        self.assertEqual(ended["status"], "ended")
        self.assertEqual(ended["separation_date"], "2026-03-01")
        self.assertEqual(ended["male_id"], male)
        self.assertEqual(released["status"], "holding")
        self.assertIsNone(released["cage_location"])

    def test_event_dates_are_bounded_by_birth_and_today(self):
        mouse = self.add_mouse("M1", birth_date="2026-02-01")
        with self.assertRaisesRegex(ValueError, "before the birth date"):
            self.db.upsert_weight(mouse, "2026-01-01", 20.0)
        with self.assertRaisesRegex(ValueError, "future"):
            self.db.mark_mouse_dead(mouse, "2099-01-01", "Natural death")

    def test_empty_mouse_filters_return_no_records(self):
        mouse = self.add_mouse("M1")
        self.db.upsert_weight(mouse, "2026-01-10", 20.0)
        self.db.set_survival_record(mouse, "2026-02-01", "dead")
        self.assertEqual(self.db.get_weight_records([]), [])
        self.assertEqual(self.db.get_survival_records([]), [])

    def test_database_restore_validates_and_preserves_backup(self):
        self.add_mouse("OLD")
        source_path = os.path.join(self.temp_dir.name, "source.db")
        source = DB(source_path)
        source.add_mouse("NEW")
        with open(source_path, "rb") as handle:
            source_bytes = handle.read()

        backup_dir = os.path.join(self.temp_dir.name, "backups")
        backup_path = self.db.restore_from_bytes(source_bytes, backup_dir=backup_dir)
        self.assertTrue(os.path.isfile(backup_path))
        self.assertEqual([m["ear_tag"] for m in self.db.get_all_mice()], ["NEW"])
        self.assertEqual([m["ear_tag"] for m in DB(backup_path).get_all_mice()], ["OLD"])

        with self.assertRaisesRegex(ValueError, "Invalid SQLite database"):
            self.db.restore_from_bytes(b"not a database", backup_dir=backup_dir)
        self.assertEqual([m["ear_tag"] for m in self.db.get_all_mice()], ["NEW"])

    def test_kaplan_meier_handles_censoring_at_the_correct_time(self):
        points = kaplan_meier_points([10, 20, 30], [True, False, True])
        day_10 = points.loc[points["Day"] == 10, "Survival (%)"].iloc[0]
        day_30 = points.loc[points["Day"] == 30, "Survival (%)"].iloc[0]
        self.assertAlmostEqual(day_10, 100.0 * 2 / 3)
        self.assertAlmostEqual(day_30, 0.0)

    def test_kaplan_meier_all_censored_stays_at_100(self):
        points = kaplan_meier_points([10, 20], [False, False])
        self.assertTrue((points["Survival (%)"] == 100.0).all())


if __name__ == "__main__":
    unittest.main()
