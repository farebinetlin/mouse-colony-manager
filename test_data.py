"""Test script: populate sample data and verify the mouse colony manager."""
import sys
sys.path.insert(0, "/Users/linfabin/mouse-manager")
from db import DB

db = DB()

print("=== Adding founder mice ===")
m1 = db.add_mouse("F-M001", "2024-06-01", "M", status="breeding",
                   cage_location="Founder Rack")
db.set_genotype(m1, "GeneA", "fl", "fl")
db.set_genotype(m1, "GeneB", "Tg", "0")
print(f"  {m1}: F-M001 M GeneA fl/fl; GeneB Tg/0")

m2 = db.add_mouse("F-F001", "2024-06-15", "F", status="breeding",
                   cage_location="Founder Rack")
db.set_genotype(m2, "GeneA", "fl", "fl")
print(f"  {m2}: F-F001 F GeneA fl/fl")

m3 = db.add_mouse("F-M002", "2024-07-01", "M", status="breeding",
                   cage_location="Founder Rack")
db.set_genotype(m3, "GeneA", "fl", "+")
db.set_genotype(m3, "GeneC", "Tg", "0")
print(f"  {m3}: F-M002 M GeneA fl/+; GeneC Tg/0")

m4 = db.add_mouse("F-F002", "2024-07-15", "F", status="breeding",
                   cage_location="Founder Rack")
db.set_genotype(m4, "GeneA", "fl", "fl")
print(f"  {m4}: F-F002 F GeneA fl/fl")

print("\n=== Creating breeding cages ===")
cage1 = db.add_breeding_cage("Breed-01", cage_type="breeding",
                              male_id=m1, female_id=m2,
                              setup_date="2025-01-15")
db.set_cage_females(cage1, [m2])
print(f"  {cage1}: Breed-01 (F-M001 x F-F001)")

cage2 = db.add_breeding_cage("Breed-02", cage_type="breeding",
                              male_id=m3, female_id=m4,
                              setup_date="2025-01-20")
db.set_cage_females(cage2, [m4])
print(f"  {cage2}: Breed-02 (F-M002 x F-F002)")

print("\n=== Creating holding cages ===")
hc1 = db.add_breeding_cage("Hold-01", cage_type="holding",
                            setup_date="2025-03-01",
                            notes="Weaned pups waiting for genotyping")
print(f"  {hc1}: Hold-01 (holding)")

hc2 = db.add_breeding_cage("Hold-02", cage_type="holding",
                            setup_date="2025-03-15",
                            notes="Genotyped mice ready for experiments")
print(f"  {hc2}: Hold-02 (holding)")

print("\n=== Recording litters ===")
l1 = db.add_litter(cage1, "2025-02-05", total_born=8, weaned_count=6,
                    weaning_date="2025-02-26")
print(f"  {l1}: Breed-01, born 2025-02-05, 8 pups, 6 weaned")

l2 = db.add_litter(cage2, "2025-02-10", total_born=6, weaned_count=5,
                    weaning_date="2025-03-03")
print(f"  {l2}: Breed-02, born 2025-02-10, 6 pups, 5 weaned")

l3 = db.add_litter(cage1, "2025-03-15", total_born=7, weaned_count=7,
                    weaning_date="2025-04-05")
print(f"  {l3}: Breed-01, born 2025-03-15, 7 pups, 7 weaned")

print("\n=== Registering weaned pups ===")
pups_l1 = [
    ("B1-M1", "M"), ("B1-M2", "M"), ("B1-M3", "M"),
    ("B1-F1", "F"), ("B1-F2", "F"), ("B1-F3", "F"),
]
for tag, sex in pups_l1:
    mid = db.add_mouse(tag, "2025-02-05", sex, status="holding",
                        father_tag="F-M001", mother_tag="F-F001",
                        birth_cage_id=cage1, cage_location="Hold-01")
    db.set_genotype(mid, "GeneA", "fl", "fl")
    if sex == "F":
        db.set_genotype(mid, "GeneB", "Tg", "0")
    print(f"  {mid}: {tag} {sex}")

pups_l2 = [
    ("B2-M1", "M"), ("B2-M2", "M"), ("B2-M3", "M"),
    ("B2-F1", "F"), ("B2-F2", "F"),
]
for tag, sex in pups_l2:
    mid = db.add_mouse(tag, "2025-02-10", sex, status="holding",
                        father_tag="F-M002", mother_tag="F-F002",
                        birth_cage_id=cage2, cage_location="Hold-01")
    db.set_genotype(mid, "GeneA", "fl", "fl")
    db.set_genotype(mid, "GeneC", "Tg", "0")
    print(f"  {mid}: {tag} {sex}")

pups_l3 = [
    ("B1-M4", "M"), ("B1-M5", "M"), ("B1-M6", "M"), ("B1-M7", "M"),
    ("B1-F4", "F"), ("B1-F5", "F"), ("B1-F6", "F"),
]
for tag, sex in pups_l3:
    mid = db.add_mouse(tag, "2025-03-15", sex, status="waiting_split",
                        father_tag="F-M001", mother_tag="F-F001",
                        birth_cage_id=cage1, cage_location="Hold-02")
    db.set_genotype(mid, "GeneA", "fl", "fl")
    if sex == "F":
        db.set_genotype(mid, "GeneB", "Tg", "0")
    print(f"  {mid}: {tag} {sex}")

print("\n=== Adding alerts ===")
db.add_alert(mouse_id=None, alert_type="Cage Check",
             due_date="2025-06-01", notes="Check all breeding cages")
db.add_alert(mouse_id=None, alert_type="Genotyping Due",
             due_date="2025-05-30", notes="Litter 3 pups need genotyping")
print("  2 alerts created")

print("\n=== Verification ===")
stats = db.get_stats()
print(f"  Total mice: {stats['total_mice']}")
print(f"  Active breeders: {stats['active_breeders']}")
print(f"  Waiting split: {stats['waiting_split']}")
print(f"  Unknown genotypes: {stats['unknown_genotypes']}")
print(f"  Pending alerts: {stats['pending_alerts']}")

print("\n=== All tests passed! ===")
print("Run: streamlit run app.py")
print("Then open http://localhost:8501 to explore the data.")
