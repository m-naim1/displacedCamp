import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, Base, engine
from app.models.audit import AuditLog  # noqa: F401
from app.models.enums import UserRole
from app.models.family import Family, FamilyUpdateRequest, Member  # noqa: F401
from app.models.lookups import (
    City,
    Governor,
    RelationshipToHead,
    ShelterBlock,
    ShelterCenter,
    ShelterQuality,
)
from app.models.user import User

# ==========================================
# 1. SEED DATA DEFINITIONS
# ==========================================

GOVERNORS = [
    {
        "id": 1,
        "code": "gza-north",
        "name_en": "North Gaza",
        "name_ar": "شمال غزة",
        "is_active": True,
    },
    {
        "id": 2,
        "code": "gza-city",
        "name_en": "Gaza",
        "name_ar": "غزة",
        "is_active": True,
    },
    {
        "id": 3,
        "code": "gza-deir",
        "name_en": "Deir al-Balah",
        "name_ar": "دير البلح",
        "is_active": True,
    },
    {
        "id": 4,
        "code": "gza-khan-younis",
        "name_en": "Khan Yunis",
        "name_ar": "خان يونس",
        "is_active": True,
    },
    {
        "id": 5,
        "code": "gza-rafah",
        "name_en": "Rafah",
        "name_ar": "رفح",
        "is_active": True,
    },
]

RELATIONSHIPS = [
    {
        "id": 1,
        "code": "head",
        "name_en": "Head of Family",
        "name_ar": "رب الأسرة",
        "is_active": True,
    },
    {
        "id": 2,
        "code": "spouse",
        "name_en": "Spouse",
        "name_ar": "زوج/ة",
        "is_active": True,
    },
    {"id": 3, "code": "son", "name_en": "Son", "name_ar": "ابن", "is_active": True},
    {
        "id": 4,
        "code": "daughter",
        "name_en": "Daughter",
        "name_ar": "ابنة",
        "is_active": True,
    },
    {
        "id": 5,
        "code": "father",
        "name_en": "Father",
        "name_ar": "أب",
        "is_active": True,
    },
    {
        "id": 6,
        "code": "mother",
        "name_en": "Mother",
        "name_ar": "أم",
        "is_active": True,
    },
    {
        "id": 7,
        "code": "brother",
        "name_en": "Brother",
        "name_ar": "أخ",
        "is_active": True,
    },
    {
        "id": 8,
        "code": "sister",
        "name_en": "Sister",
        "name_ar": "أخت",
        "is_active": True,
    },
    {
        "id": 9,
        "code": "grandson",
        "name_en": "Grandson",
        "name_ar": "حفيد",
        "is_active": True,
    },
    {
        "id": 10,
        "code": "granddaughter",
        "name_en": "Granddaughter",
        "name_ar": "حفيدة",
        "is_active": True,
    },
    {
        "id": 11,
        "code": "other",
        "name_en": "Other",
        "name_ar": "آخر",
        "is_active": True,
    },
]

SHELTER_QUALITIES = [
    {"id": 1, "code": "good", "name_en": "Good", "name_ar": "جيد", "is_active": True},
    {"id": 2, "code": "fair", "name_en": "Fair", "name_ar": "متوسط", "is_active": True},
    {"id": 3, "code": "poor", "name_en": "Poor", "name_ar": "سيء", "is_active": True},
]

CITIES = [
    {
        "id": 1,
        "code": "n-gaza-beit-hanoun",
        "name_en": "Beit Hanoun",
        "name_ar": "بيت حانون",
        "governor_id": 1,
        "is_active": True,
    },
    {
        "id": 2,
        "code": "n-gaza-beit-lahia",
        "name_en": "Beit Lahia",
        "name_ar": "بيت لاهيا",
        "governor_id": 1,
        "is_active": True,
    },
    {
        "id": 3,
        "code": "n-gaza-jabalia",
        "name_en": "Jabalia",
        "name_ar": "جباليا",
        "governor_id": 1,
        "is_active": True,
    },
    {
        "id": 4,
        "code": "n-gaza-umm-nasr",
        "name_en": "Umm al-Nasr",
        "name_ar": "أم النصر",
        "governor_id": 1,
        "is_active": True,
    },
    {
        "id": 5,
        "code": "gza-gaza-city",
        "name_en": "Gaza City",
        "name_ar": "مدينة غزة",
        "governor_id": 2,
        "is_active": True,
    },
    {
        "id": 6,
        "code": "gza-al-zahra",
        "name_en": "Al-Zahra",
        "name_ar": "الزهراء",
        "governor_id": 2,
        "is_active": True,
    },
    {
        "id": 7,
        "code": "dair-deir-balah",
        "name_en": "Deir al-Balah",
        "name_ar": "دير البلح",
        "governor_id": 3,
        "is_active": True,
    },
    {
        "id": 8,
        "code": "dair-al-maghazi",
        "name_en": "Al-Maghazi",
        "name_ar": "المغازي",
        "governor_id": 3,
        "is_active": True,
    },
    {
        "id": 9,
        "code": "dair-al-bureij",
        "name_en": "Al-Bureij",
        "name_ar": "البريج",
        "governor_id": 3,
        "is_active": True,
    },
    {
        "id": 10,
        "code": "dair-al-nuseirat",
        "name_en": "Al-Nuseirat",
        "name_ar": "النصيرات",
        "governor_id": 3,
        "is_active": True,
    },
    {
        "id": 11,
        "code": "dair-al-zawayda",
        "name_en": "Al-Zawayda",
        "name_ar": "الزوايدة",
        "governor_id": 3,
        "is_active": True,
    },
    {
        "id": 12,
        "code": "khan-younis-city",
        "name_en": "Khan Yunis",
        "name_ar": "خان يونس",
        "governor_id": 4,
        "is_active": True,
    },
    {
        "id": 13,
        "code": "khan-bani-suheila",
        "name_en": "Bani Suheila",
        "name_ar": "بني سهيلا",
        "governor_id": 4,
        "is_active": True,
    },
    {
        "id": 14,
        "code": "khan-al-qarara",
        "name_en": "Al-Qarara",
        "name_ar": "القرارة",
        "governor_id": 4,
        "is_active": True,
    },
    {
        "id": 15,
        "code": "khan-khuzaa",
        "name_en": "Khuza'a",
        "name_ar": "خزاعة",
        "governor_id": 4,
        "is_active": True,
    },
    {
        "id": 16,
        "code": "khan-abasan",
        "name_en": "Abasan",
        "name_ar": "عبسان",
        "governor_id": 4,
        "is_active": True,
    },
    {
        "id": 17,
        "code": "rafah-city",
        "name_en": "Rafah",
        "name_ar": "رفح",
        "governor_id": 5,
        "is_active": True,
    },
    {
        "id": 18,
        "code": "rafah-shokat-sufi",
        "name_en": "Shokat al-Sufi",
        "name_ar": "شوكة الصوفي",
        "governor_id": 5,
        "is_active": True,
    },
    {
        "id": 19,
        "code": "rafah-al-nasr",
        "name_en": "Al-Nasr",
        "name_ar": "النصر",
        "governor_id": 5,
        "is_active": True,
    },
    {
        "id": 20,
        "code": "rafah-al-shoka",
        "name_en": "Al-Shoka",
        "name_ar": "الشوكة",
        "governor_id": 5,
        "is_active": True,
    },
]

SHELTER_CENTERS = [
    {
        "id": 1,
        "code": "shelter-north-1",
        "name_en": "North Gaza School Shelter",
        "name_ar": "مأوى مدرسة شمال غزة",
        "city_id": 1,
        "is_active": True,
    },
    {
        "id": 2,
        "code": "shelter-gaza-1",
        "name_en": "Gaza City UNRWA Shelter",
        "name_ar": "مأوى أونروا مدينة غزة",
        "city_id": 5,
        "is_active": True,
    },
    {
        "id": 3,
        "code": "shelter-rafah-1",
        "name_en": "Rafah Tent Camp",
        "name_ar": "مخيم خيام رفح",
        "city_id": 17,
        "is_active": True,
    },
]

SHELTER_BLOCKS = [
    {
        "id": 1,
        "code": "block-a",
        "name_en": "Block A",
        "name_ar": "بلوك أ",
        "shelter_center_id": 1,
        "is_active": True,
    },
    {
        "id": 2,
        "code": "block-b",
        "name_en": "Block B",
        "name_ar": "بلوك ب",
        "shelter_center_id": 1,
        "is_active": True,
    },
    {
        "id": 3,
        "code": "block-c",
        "name_en": "Block C",
        "name_ar": "بلوك ج",
        "shelter_center_id": 2,
        "is_active": True,
    },
    {
        "id": 4,
        "code": "block-d",
        "name_en": "Block D",
        "name_ar": "بلوك د",
        "shelter_center_id": 3,
        "is_active": True,
    },
]

# ==========================================
# 2. SEEDING LOGIC
# ==========================================


async def seed_all():
    """
    Creates tables and seeds all initial data idempotently.
    Safe to run multiple times or concurrently across multiple workers.
    """
    # 1. Create Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables verified/created.")

    # 2. Seed Data
    async with AsyncSessionLocal() as session:
        # Bulk insert lookups (Postgres ignores duplicates based on ID)
        await session.execute(
            insert(Governor)
            .values(GOVERNORS)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(
            insert(RelationshipToHead)
            .values(RELATIONSHIPS)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(
            insert(ShelterQuality)
            .values(SHELTER_QUALITIES)
            .on_conflict_do_nothing(index_elements=["id"])
        )

        await session.execute(
            insert(City).values(CITIES).on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(
            insert(ShelterCenter)
            .values(SHELTER_CENTERS)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(
            insert(ShelterBlock)
            .values(SHELTER_BLOCKS)
            .on_conflict_do_nothing(index_elements=["id"])
        )

        # Seed Superadmin
        hashed_pw = await get_password_hash(settings.ADMIN_PASSWORD)
        admin_data = {
            "username": settings.ADMIN_USERNAME,
            "email": settings.ADMIN_EMAIL,
            "full_name": "System Admin",
            "hashed_password": hashed_pw,
            "role": UserRole.SUPERADMIN,
            "is_active": True,
        }
        await session.execute(
            insert(User)
            .values(**admin_data)
            .on_conflict_do_nothing(index_elements=["username"])
        )

        await session.commit()
    print("Database seeded successfully.")


# Allows running manually via CLI: python -m app.seed
if __name__ == "__main__":
    asyncio.run(seed_all())
