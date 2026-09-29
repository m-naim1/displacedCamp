"""
Generate large dataset: 6,000 camps (shelter centers) + 100,000 families.

Usage:
    python scripts/generate_large_dataset.py

Requires the base seed data (governors, cities, relationships, qualities) to
already exist. Run `python -m app.seed` first.
"""

import asyncio
import random
import string
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

# ── Path setup ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.session import AsyncSessionLocal, engine, Base  # noqa: E402
from app.models.family import Family, Member  # noqa: E402
from app.models.lookups import ShelterBlock, ShelterCenter  # noqa: E402

# ── Constants ───────────────────────────────────────────────────────────
NUM_CAMPS = 6_000
NUM_FAMILIES = 100_000
BLOCKS_PER_CAMP = (3, 5)
MEMBERS_PER_FAMILY = (2, 7)
BATCH_SIZE = 2_000

CITY_IDS = list(range(1, 21))
QUALITY_IDS = [1, 2, 3]
REL_HEAD = 1
REL_SPOUSE = 2
REL_SON = 3
REL_DAUGHTER = 4

MALE_NAMES = [
    "محمد", "أحمد", "علي", "حسين", "عبدالله", "عمر", "يوسف", "إبراهيم",
    "خالد", "حسن", "مصطفى", "سعيد", "كمال", "جمال", "تامر", "رائد",
    "ماجد", "سامي", "أشرف", "حاتم", "وليد", "جاسم", "فؤاد", "نبيل",
    "كريم", "ياسر", "عادل", "طارق", "عماد", "صلاح", "سليم", "منير",
    "هشام", "زياد", "بلال", "وسيم", "رامي", "يحيى", "ламия", "ماهر",
]

FEMALE_NAMES = [
    "فاطمة", "خديجة", "عائشة", "زينب", "مريم", "هدى", "نورة", "سارة",
    "آمنة", "سمية", "ريم", "دانا", "لينا", "رنا", "جنى", "ملاك",
    "هبة", "ياسمين", "كويثر", "حور", "نادين", "دينا", "سلمى", "ريماس",
    "أروى", "نور", "سناء", "منى", "هدى", " absolut", "ضياء", "لمياء",
]

HOUSING_TYPES = ["tent", "house", "caravan", "garage", "room", "school", "other"]
RESIDENCY_STATUSES = ["displaced", "resident"]
GENDERS = ["male", "female"]
MARITAL_HEAD = ["married", "married", "married", "widowed", "divorced"]
MARITAL_CHILD = ["single", "single", "single", "married"]


# ── Helpers ─────────────────────────────────────────────────────────────

def luhn_checksum_digit(partial: str) -> int:
    total = 0
    for i, ch in enumerate(partial):
        step = int(ch) * ((i % 2) + 1)
        if step > 9:
            step -= 9
        total += step
    return (10 - (total % 10)) % 10


_used_ids: set[int] = set()


def gen_nid() -> int:
    while True:
        first = random.choice("4789")
        body = "".join(random.choices("0123456789", k=7))
        check = luhn_checksum_digit(first + body)
        nid = int(first + body + str(check))
        if nid not in _used_ids:
            _used_ids.add(nid)
            return nid


def random_phone() -> str:
    return random.choice(["059", "056", "052"]) + "".join(
        random.choices("0123456789", k=7)
    )


def random_dob(min_age: int, max_age: int) -> date:
    today = date.today()
    age = random.randint(min_age, max_age)
    return today - timedelta(days=age * 365 + random.randint(0, 364))


def weighted_choice(items: list, weights: list):
    return random.choices(items, weights=weights, k=1)[0]


# ── Bulk insert ─────────────────────────────────────────────────────────

async def bulk_insert(session, model, rows: list[dict]):
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        await session.execute(
            insert(model).values(batch).on_conflict_do_nothing(index_elements=["id"])
        )
        await session.flush()
        done = min(i + BATCH_SIZE, len(rows))
        if done % 50_000 == 0 or done == len(rows):
            print(f"    {done}/{len(rows)} {model.__name__}")


async def update_family_heads(session, families: list[dict]):
    upsert = insert(Family)
    for i in range(0, len(families), BATCH_SIZE):
        batch = families[i : i + BATCH_SIZE]
        await session.execute(
            upsert.values(batch).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "head_id": upsert.excluded.head_id,
                    "spouse_id": upsert.excluded.spouse_id,
                },
            )
        )
        await session.flush()


# ── Data generation ─────────────────────────────────────────────────────

def generate_camps() -> list[dict]:
    print(f"Generating {NUM_CAMPS} camps...")
    return [
        {
            "id": i,
            "code": f"camp-{i:05d}",
            "name_en": f"Shelter Camp {i}",
            "name_ar": f"مأوى مخيم {i}",
            "city_id": random.choice(CITY_IDS),
            "is_active": True,
        }
        for i in range(1, NUM_CAMPS + 1)
    ]


def generate_blocks(camps: list[dict]) -> list[dict]:
    print("Generating blocks...")
    blocks = []
    bid = 1
    arabic_letters = ["أ", "ب", "ج", "د", "ه"]
    for camp in camps:
        for j in range(random.randint(*BLOCKS_PER_CAMP)):
            blocks.append(
                {
                    "id": bid,
                    "code": f"camp-{camp['id']:05d}-{string.ascii_uppercase[j]}",
                    "name_en": f"Block {string.ascii_uppercase[j]}",
                    "name_ar": f"بلوك {arabic_letters[j]}",
                    "shelter_center_id": camp["id"],
                    "is_active": True,
                }
            )
            bid += 1
    print(f"  → {len(blocks)} blocks")
    return blocks


def generate_families(camps, camp_blocks) -> tuple[list[dict], list[dict]]:
    print(f"Generating {NUM_FAMILIES} families + members...")
    families: list[dict] = []
    members: list[dict] = []

    for fi in range(1, NUM_FAMILIES + 1):
        camp = random.choice(camps)
        cid = camp["id"]
        blks = camp_blocks.get(cid, [])
        blk_id = random.choice(blks) if blks else None

        n_total = max(2, random.randint(*MEMBERS_PER_FAMILY))
        head_gender = weighted_choice(GENDERS, [65, 35])
        head_age = random.randint(28, 65)

        head_nid = gen_nid()
        head_name = random.choice(MALE_NAMES if head_gender == "male" else FEMALE_NAMES)
        head_marital = (
            random.choice(["single", "married", "married"])
            if head_age < 30
            else random.choice(MARITAL_HEAD)
        )

        has_spouse = head_marital in ("married", "second-wife") and random.random() < 0.85
        spouse_gender = "female" if head_gender == "male" else "male"
        spouse_age = max(18, head_age - random.randint(-5, 10))
        spouse_nid = gen_nid() if has_spouse else None
        spouse_name = (
            random.choice(FEMALE_NAMES if spouse_gender == "female" else MALE_NAMES)
            if has_spouse
            else None
        )

        female_headed = head_gender == "female" and not has_spouse
        child_headed = head_age < 18

        # Head
        members.append(
            {
                "id": head_nid,
                "family_id": fi,
                "full_name": head_name,
                "gender": head_gender,
                "marital_status": head_marital,
                "date_of_birth": random_dob(head_age, head_age),
                "relationship_to_head_id": REL_HEAD,
                "has_chronic_disease": random.random() < (0.15 if head_age > 40 else 0.05),
                "injured": random.random() < 0.05,
                "disabled": random.random() < 0.03,
                "pregnant": False,
                "breastfeeding": False,
            }
        )

        # Spouse
        if has_spouse:
            is_preg = (
                spouse_gender == "female"
                and 18 <= spouse_age <= 45
                and random.random() < 0.12
            )
            is_bf = (
                spouse_gender == "female"
                and not is_preg
                and 18 <= spouse_age <= 40
                and random.random() < 0.10
            )
            members.append(
                {
                    "id": spouse_nid,
                    "family_id": fi,
                    "full_name": spouse_name,
                    "gender": spouse_gender,
                    "marital_status": "married",
                    "date_of_birth": random_dob(spouse_age, spouse_age),
                    "relationship_to_head_id": REL_SPOUSE,
                    "has_chronic_disease": random.random() < 0.08,
                    "injured": random.random() < 0.03,
                    "disabled": random.random() < 0.02,
                    "pregnant": is_preg,
                    "breastfeeding": is_bf,
                }
            )

        # Children
        for _ in range(n_total - (1 + int(has_spouse))):
            cg = weighted_choice(GENDERS, [52, 48])
            ca = max(0, random.randint(0, min(head_age - 16, 30)) if head_age > 18 else random.randint(0, 12))
            cm = random.choice(MARITAL_CHILD) if ca >= 18 else "single"
            is_preg = (
                cg == "female"
                and cm != "single"
                and 18 <= ca <= 42
                and random.random() < 0.08
            )
            is_bf = (
                cg == "female"
                and cm != "single"
                and not is_preg
                and 18 <= ca <= 38
                and random.random() < 0.06
            )
            members.append(
                {
                    "id": gen_nid(),
                    "family_id": fi,
                    "full_name": random.choice(MALE_NAMES if cg == "male" else FEMALE_NAMES),
                    "gender": cg,
                    "marital_status": cm,
                    "date_of_birth": random_dob(ca, ca),
                    "relationship_to_head_id": REL_SON if cg == "male" else REL_DAUGHTER,
                    "has_chronic_disease": random.random() < (0.02 if ca < 18 else 0.04),
                    "injured": random.random() < 0.02,
                    "disabled": random.random() < 0.01,
                    "pregnant": is_preg,
                    "breastfeeding": is_bf,
                }
            )

        families.append(
            {
                "id": fi,
                "head_id": head_nid,
                "spouse_id": spouse_nid,
                "residency_status": weighted_choice(RESIDENCY_STATUSES, [80, 20]),
                "female_headed": female_headed,
                "child_headed": child_headed,
                "primary_phone_number": random_phone(),
                "secondary_phone_number": random_phone() if random.random() < 0.3 else None,
                "original_city_id": random.choice(CITY_IDS),
                "current_shelter_center_id": cid,
                "shelter_block_id": blk_id,
                "housing_type": weighted_choice(HOUSING_TYPES, [40, 20, 15, 5, 10, 5, 5]),
                "shelter_quality_id": random.choice(QUALITY_IDS),
                "is_active": random.random() > 0.05,
            }
        )

        if fi % 10_000 == 0:
            print(f"  → {fi}/{NUM_FAMILIES} ({len(members)} members)")

    print(f"  → {len(families)} families, {len(members)} members")
    return families, members


# ── Main ────────────────────────────────────────────────────────────────

async def main():
    t0 = time.time()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Clear existing generated data for clean re-runs
        await conn.execute(text("TRUNCATE TABLE members CASCADE"))
        await conn.execute(text("TRUNCATE TABLE families CASCADE"))
        await conn.execute(text("TRUNCATE TABLE shelter_block CASCADE"))
        await conn.execute(text("DELETE FROM shelter_centers WHERE id > 3"))
        await conn.execute(text("ALTER SEQUENCE shelter_centers_id_seq RESTART WITH 4"))
        print("Cleared old data.\n")

    print("Tables verified.\n")

    camps = generate_camps()
    blocks = generate_blocks(camps)

    camp_blocks: dict[int, list[int]] = {}
    for b in blocks:
        camp_blocks.setdefault(b["shelter_center_id"], []).append(b["id"])

    families, members = generate_families(camps, camp_blocks)

    async with AsyncSessionLocal() as session:
        print("\nInserting camps...")
        await bulk_insert(session, ShelterCenter, camps)
        await session.commit()
        print("  ✓ done\n")

        print("Inserting blocks...")
        await bulk_insert(session, ShelterBlock, blocks)
        await session.commit()
        print("  ✓ done\n")

        # head_id/spouse_id FK to members, so insert families without heads first
        family_rows = [
            {**f, "head_id": None, "spouse_id": None} for f in families
        ]
        print("Inserting families...")
        await bulk_insert(session, Family, family_rows)
        await session.commit()
        print("  ✓ done\n")

        print("Inserting members...")
        await bulk_insert(session, Member, members)
        await session.commit()
        print("  ✓ done\n")

        print("Updating family heads...")
        await update_family_heads(session, families)
        await session.commit()
        print("  ✓ done\n")

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s")
    print(f"  Camps:    {NUM_CAMPS}")
    print(f"  Blocks:   {len(blocks)}")
    print(f"  Families: {NUM_FAMILIES}")
    print(f"  Members:  {len(members)}")


if __name__ == "__main__":
    asyncio.run(main())
