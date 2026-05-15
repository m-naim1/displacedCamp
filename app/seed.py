from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lookups import (
    Governor,
    City,
    RelationshipToHead,
    ShelterQuality,
)

GOVERNORS = [
    {"id": 1, "code": "gza-north", "name_en": "North Gaza", "name_ar": "شمال غزة"},
    {"id": 2, "code": "gza-city", "name_en": "Gaza", "name_ar": "غزة"},
    {"id": 3, "code": "gza-deir", "name_en": "Deir al-Balah", "name_ar": "دير البلح"},
    {
        "id": 4,
        "code": "gza-khan-younis",
        "name_en": "Khan Yunis",
        "name_ar": "خان يونس",
    },
    {"id": 5, "code": "gza-rafah", "name_en": "Rafah", "name_ar": "رفح"},
]

CITIES = [
    {
        "id": 1,
        "code": "n-gaza-beit-hanoun",
        "name_en": "Beit Hanoun",
        "name_ar": "بيت حانون",
        "governor_id": 1,
    },
    {
        "id": 2,
        "code": "n-gaza-beit-lahia",
        "name_en": "Beit Lahia",
        "name_ar": "بيت لاهيا",
        "governor_id": 1,
    },
    {
        "id": 3,
        "code": "n-gaza-jabalia",
        "name_en": "Jabalia",
        "name_ar": "جباليا",
        "governor_id": 1,
    },
    {
        "id": 4,
        "code": "n-gaza-umm-nasr",
        "name_en": "Umm al-Nasr",
        "name_ar": "أم النصر",
        "governor_id": 1,
    },
    {
        "id": 5,
        "code": "gza-gaza-city",
        "name_en": "Gaza City",
        "name_ar": "مدينة غزة",
        "governor_id": 2,
    },
    {
        "id": 6,
        "code": "gza-al-zahra",
        "name_en": "Al-Zahra",
        "name_ar": "الزهراء",
        "governor_id": 2,
    },
    {
        "id": 7,
        "code": "dair-deir-balah",
        "name_en": "Deir al-Balah",
        "name_ar": "دير البلح",
        "governor_id": 3,
    },
    {
        "id": 8,
        "code": "dair-al-maghazi",
        "name_en": "Al-Maghazi",
        "name_ar": "المغازي",
        "governor_id": 3,
    },
    {
        "id": 9,
        "code": "dair-al-bureij",
        "name_en": "Al-Bureij",
        "name_ar": "البريج",
        "governor_id": 3,
    },
    {
        "id": 10,
        "code": "dair-al-nuseirat",
        "name_en": "Al-Nuseirat",
        "name_ar": "النصيرات",
        "governor_id": 3,
    },
    {
        "id": 11,
        "code": "dair-al-zawayda",
        "name_en": "Al-Zawayda",
        "name_ar": "الزوايدة",
        "governor_id": 3,
    },
    {
        "id": 12,
        "code": "khan-younis-city",
        "name_en": "Khan Yunis",
        "name_ar": "خان يونس",
        "governor_id": 4,
    },
    {
        "id": 13,
        "code": "khan-bani-suheila",
        "name_en": "Bani Suheila",
        "name_ar": "بني سهيلا",
        "governor_id": 4,
    },
    {
        "id": 14,
        "code": "khan-al-qarara",
        "name_en": "Al-Qarara",
        "name_ar": "القرارة",
        "governor_id": 4,
    },
    {
        "id": 15,
        "code": "khan-khuzaa",
        "name_en": "Khuza'a",
        "name_ar": "خزاعة",
        "governor_id": 4,
    },
    {
        "id": 16,
        "code": "khan-abasan",
        "name_en": "Abasan",
        "name_ar": "عبسان",
        "governor_id": 4,
    },
    {
        "id": 17,
        "code": "rafah-city",
        "name_en": "Rafah",
        "name_ar": "رفح",
        "governor_id": 5,
    },
    {
        "id": 18,
        "code": "rafah-shokat-sufi",
        "name_en": "Shokat al-Sufi",
        "name_ar": "شوكة الصوفي",
        "governor_id": 5,
    },
    {
        "id": 19,
        "code": "rafah-al-nasr",
        "name_en": "Al-Nasr",
        "name_ar": "النصر",
        "governor_id": 5,
    },
    {
        "id": 20,
        "code": "rafah-al-shoka",
        "name_en": "Al-Shoka",
        "name_ar": "الشوكة",
        "governor_id": 5,
    },
]

RELATIONSHIPS = [
    {"id": 1, "code": "head", "name_en": "Head of Family", "name_ar": "رب الأسرة"},
    {"id": 2, "code": "spouse", "name_en": "Spouse", "name_ar": "زوج/ة"},
    {"id": 3, "code": "son", "name_en": "Son", "name_ar": "ابن"},
    {"id": 4, "code": "daughter", "name_en": "Daughter", "name_ar": "ابنة"},
    {"id": 5, "code": "father", "name_en": "Father", "name_ar": "أب"},
    {"id": 6, "code": "mother", "name_en": "Mother", "name_ar": "أم"},
    {"id": 7, "code": "brother", "name_en": "Brother", "name_ar": "أخ"},
    {"id": 8, "code": "sister", "name_en": "Sister", "name_ar": "أخت"},
    {"id": 9, "code": "grandson", "name_en": "Grandson", "name_ar": "حفيد"},
    {"id": 10, "code": "granddaughter", "name_en": "Granddaughter", "name_ar": "حفيدة"},
    {"id": 11, "code": "other", "name_en": "Other", "name_ar": "آخر"},
]

SHELTER_QUALITIES = [
    {"id": 1, "code": "good", "name_en": "Good", "name_ar": "جيد"},
    {"id": 2, "code": "fair", "name_en": "Fair", "name_ar": "متوسط"},
    {"id": 3, "code": "poor", "name_en": "Poor", "name_ar": "سيء"},
]


async def seed_all(db: AsyncSession):
    for g in GOVERNORS:
        result = await db.execute(select(Governor).where(Governor.id == g["id"]))
        if not result.scalar_one_or_none():
            db.add(Governor(**g))
    for c in CITIES:
        result = await db.execute(select(City).where(City.id == c["id"]))
        if not result.scalar_one_or_none():
            db.add(City(**c))
    for r in RELATIONSHIPS:
        result = await db.execute(
            select(RelationshipToHead).where(RelationshipToHead.id == r["id"])
        )
        if not result.scalar_one_or_none():
            db.add(RelationshipToHead(**r))
    for q in SHELTER_QUALITIES:
        result = await db.execute(
            select(ShelterQuality).where(ShelterQuality.id == q["id"])
        )
        if not result.scalar_one_or_none():
            db.add(ShelterQuality(**q))
    await db.commit()
    print(
        "[OK] Lookup data seeded (governors, cities, relationships, shelter qualities)"
    )
