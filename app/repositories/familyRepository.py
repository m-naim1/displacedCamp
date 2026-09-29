from datetime import UTC, datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models.enums import Gender
from app.models.family import Family, Member
from app.models.lookups import City, Governor, ShelterBlock, ShelterCenter
from app.repositories.base import IFamilyRepository
from app.schemas.family import FamilyCreate, FamilyUpdate
from app.schemas.filters import FamilyFilterParams


class FamilyRepository(IFamilyRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create(self, family_data: FamilyCreate) -> Family:
        existing_head = await self.db.execute(
            select(Member).where(Member.id == family_data.head_id)
        )
        if existing_head.scalar_one_or_none():
            raise ConflictError(
                code="family_already_exists",
                message=(
                    f"The head member with id {family_data.head_id} already exists."
                ),
            )
        family = Family(
            **family_data.model_dump(exclude={"members", "head_id", "spouse_id"})
        )
        self.db.add(family)
        await self.db.flush()
        await self.db.refresh(family)
        return family

    async def get_all(
        self, filters: FamilyFilterParams, skip: int = 0, limit: int = 100
    ) -> list[Family]:
        query = select(Family).options(joinedload(Family.head))

        # Single-value filters (Equality)
        if filters.is_active is not None:
            query = query.where(Family.is_active == filters.is_active)
        if filters.residency_status:
            query = query.where(Family.residency_status == filters.residency_status)
        if filters.female_headed is not None:
            query = query.where(Family.female_headed == filters.female_headed)
        if filters.child_headed is not None:
            query = query.where(Family.child_headed == filters.child_headed)

        # --- MULTI-VALUE FILTERS (.in_) ---
        if filters.housing_type:
            query = query.where(Family.housing_type.in_(filters.housing_type))
        if filters.current_shelter_center_id:
            query = query.where(
                Family.current_shelter_center_id.in_(filters.current_shelter_center_id)
            )
        if filters.shelter_block_id:
            query = query.where(Family.shelter_block_id.in_(filters.shelter_block_id))
        if filters.original_city_id:
            query = query.where(Family.original_city_id.in_(filters.original_city_id))
        if filters.shelter_quality_id:
            query = query.where(
                Family.shelter_quality_id.in_(filters.shelter_quality_id)
            )

        # --- CITY / GOVERNOR FILTERS (via ShelterCenter for current) ---
        if filters.current_city_id or filters.current_governor_id:
            CurrentShelterCenter = aliased(ShelterCenter)
            query = query.join(
                CurrentShelterCenter,
                Family.current_shelter_center_id == CurrentShelterCenter.id,
            )
            if filters.current_city_id:
                query = query.where(
                    CurrentShelterCenter.city_id.in_(filters.current_city_id)
                )
            if filters.current_governor_id:
                CurrentCity = aliased(City)
                query = query.join(
                    CurrentCity, CurrentShelterCenter.city_id == CurrentCity.id
                ).where(CurrentCity.governor_id.in_(filters.current_governor_id))

        if filters.original_governor_id:
            OriginalCity = aliased(City)
            query = query.join(
                OriginalCity, Family.original_city_id == OriginalCity.id
            ).where(OriginalCity.governor_id.in_(filters.original_governor_id))

        # Text search filters
        if filters.phone_number:
            query = query.where(
                Family.primary_phone_number.ilike(f"%{filters.phone_number}%")
            )

        if filters.head_name:
            query = (
                query.join(Member, Family.head_id == Member.id)
                .where(Member.full_name.ilike(f"%{filters.head_name}%"))
                .order_by(func.similarity(Member.full_name, filters.head_name).desc())
            )

        # Dynamic Sorting
        sort_by_field = filters.sort_by or "id"
        sort_column = getattr(Family, sort_by_field, Family.id)

        if filters.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_head_id(self, head_id: int) -> Family | None:
        result = await self.db.execute(select(Family).where(Family.head_id == head_id))
        family = result.scalar_one_or_none()
        if not family:
            return None
        return family

    async def get_by_family_id(self, family_id: int) -> Family | None:
        result = await self.db.execute(
            select(Family)
            .options(selectinload(Family.members))
            .options(joinedload(Family.head))
            .options(joinedload(Family.spouse))
            .where(Family.id == family_id)
        )
        return result.unique().scalar_one_or_none()

    async def archive(self, family_id: int) -> Family:
        family = await self.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with id {family_id} not found",
            )
        family.is_active = False
        family.archived_at = datetime.now(UTC)
        await self.db.commit()
        return family

    async def activate(self, family_id: int) -> Family:
        family = await self.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with id {family_id} not found",
            )
        family.is_active = True
        family.archived_at = None
        await self.db.commit()
        return family

    async def update(self, family_id: int, family_data: FamilyUpdate) -> Family:
        family = await self.get_by_family_id(family_id=family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with family id {family_id} not found",
            )
        for key, value in family_data.model_dump(exclude_unset=True).items():
            setattr(family, key, value)
        await self.db.commit()
        return family

    async def get_families_report_data(
        self,
        shelter_center_id: int | None = None,
        shelter_block_ids: list[int] | None = None,
        selected_ids: list[int] | None = None,
    ) -> list[dict]:
        HeadMember = aliased(Member)
        SpouseMember = aliased(Member)
        OriginalCity = aliased(City)
        OriginalGovernor = aliased(Governor)
        CurrentCity = aliased(City)

        age_expr = func.date_part(
            "year", func.age(func.current_date(), Member.date_of_birth)
        )

        # Core set of family ids the report should cover (used to scope the
        # member aggregation subquery so it never scans the whole members table).
        scoped_family_ids = select(Family.id)
        if shelter_center_id:
            scoped_family_ids = scoped_family_ids.where(
                Family.current_shelter_center_id == shelter_center_id
            )
        if shelter_block_ids:
            scoped_family_ids = scoped_family_ids.where(
                Family.shelter_block_id.in_(shelter_block_ids)
            )
        if selected_ids:
            scoped_family_ids = scoped_family_ids.where(Family.id.in_(selected_ids))

        # 1. Subquery to aggregate member stats per family
        member_agg = (
            select(
                Member.family_id,
                func.count(Member.id).label("member_count"),
                func.sum(case((Member.gender == Gender.MALE, 1), else_=0)).label(
                    "male_count"
                ),
                func.sum(case((Member.gender == Gender.FEMALE, 1), else_=0)).label(
                    "female_count"
                ),
                func.sum(
                    case(
                        (and_(age_expr < 18, Member.gender == Gender.MALE), 1), else_=0
                    )
                ).label("sons_count"),
                func.sum(
                    case(
                        (and_(age_expr < 18, Member.gender == Gender.FEMALE), 1),
                        else_=0,
                    )
                ).label("daughters_count"),
                func.sum(
                    case(
                        (and_(age_expr >= 18, Member.gender == Gender.FEMALE), 1),
                        else_=0,
                    )
                ).label("females_18_plus_count"),
                func.sum(case((age_expr < 2, 1), else_=0)).label("under_2_count"),
                func.sum(
                    case((and_(age_expr < 2, Member.gender == Gender.MALE), 1), else_=0)
                ).label("under_2_male_count"),
                func.sum(
                    case(
                        (and_(age_expr < 2, Member.gender == Gender.FEMALE), 1), else_=0
                    )
                ).label("under_2_female_count"),
                func.sum(case((age_expr < 3, 1), else_=0)).label("under_3_count"),
                func.sum(case((age_expr < 5, 1), else_=0)).label("under_5_count"),
                func.sum(case((age_expr < 18, 1), else_=0)).label("under_18_count"),
                func.sum(case((age_expr >= 18, 1), else_=0)).label("adult_count"),
                func.sum(case((and_(age_expr >= 3, age_expr <= 5), 1), else_=0)).label(
                    "age_3_5_count"
                ),
                func.sum(
                    case(
                        (
                            and_(
                                age_expr >= 3,
                                age_expr <= 5,
                                Member.gender == Gender.MALE,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("age_3_5_male_count"),
                func.sum(
                    case(
                        (
                            and_(
                                age_expr >= 3,
                                age_expr <= 5,
                                Member.gender == Gender.FEMALE,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("age_3_5_female_count"),
                func.sum(case((and_(age_expr >= 6, age_expr <= 18), 1), else_=0)).label(
                    "age_6_18_count"
                ),
                func.sum(
                    case(
                        (
                            and_(
                                age_expr >= 6,
                                age_expr <= 18,
                                Member.gender == Gender.MALE,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("age_6_18_male_count"),
                func.sum(
                    case(
                        (
                            and_(
                                age_expr >= 6,
                                age_expr <= 18,
                                Member.gender == Gender.FEMALE,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("age_6_18_female_count"),
                func.sum(
                    case((and_(age_expr >= 19, age_expr <= 60), 1), else_=0)
                ).label("age_19_60_count"),
                func.sum(
                    case(
                        (
                            and_(
                                age_expr >= 19,
                                age_expr <= 60,
                                Member.gender == Gender.MALE,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("age_19_60_male_count"),
                func.sum(
                    case(
                        (
                            and_(
                                age_expr >= 19,
                                age_expr <= 60,
                                Member.gender == Gender.FEMALE,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("age_19_60_female_count"),
                func.sum(case((age_expr > 60, 1), else_=0)).label(
                    "elderly_60_plus_count"
                ),
                func.sum(
                    case(
                        (and_(age_expr > 60, Member.gender == Gender.MALE), 1), else_=0
                    )
                ).label("elderly_60_plus_male_count"),
                func.sum(
                    case(
                        (and_(age_expr > 60, Member.gender == Gender.FEMALE), 1),
                        else_=0,
                    )
                ).label("elderly_60_plus_female_count"),
                func.sum(case((Member.disabled == True, 1), else_=0)).label(
                    "disabled_count"
                ),
                func.sum(case((Member.injured == True, 1), else_=0)).label(
                    "injured_count"
                ),
                func.sum(case((Member.has_chronic_disease == True, 1), else_=0)).label(
                    "chronic_count"
                ),
                func.sum(case((Member.pregnant == True, 1), else_=0)).label(
                    "pregnant_count"
                ),
                func.sum(case((Member.breastfeeding == True, 1), else_=0)).label(
                    "breastfeeding_count"
                ),
                func.max(case((Member.disabled == True, 1), else_=0)).label(
                    "disabled_any"
                ),
                func.max(case((Member.has_chronic_disease == True, 1), else_=0)).label(
                    "chronic_any"
                ),
                func.max(
                    case(
                        (or_(Member.pregnant == True, Member.breastfeeding == True), 1),
                        else_=0,
                    )
                ).label("pregnant_or_breastfeeding_any"),
                func.max(case((age_expr >= 18, 1), else_=0)).label("has_adult"),
            )
            .where(Member.family_id.in_(scoped_family_ids))
            .group_by(Member.family_id)
            .subquery()
        )

        # 2. Main Query
        stmt = (
            select(
                Family.id.label("family_id"),
                Family.is_active,
                Family.female_headed.label("women_headed"),
                Family.child_headed,
                Family.residency_status,
                Family.housing_type.label("shelter_type"),
                Family.created_at,
                Family.archived_at.label("updated_at"),
                Family.primary_phone_number.label("phone_1"),
                Family.secondary_phone_number.label("phone_2"),
                HeadMember.id.label("head_id_number"),
                HeadMember.full_name.label("head_name"),
                HeadMember.gender.label("head_gender"),
                HeadMember.marital_status.label("head_marital_status"),
                SpouseMember.full_name.label("spouse_name"),
                SpouseMember.id.label("spouse_id_number"),
                OriginalGovernor.name_en.label("original_governorate"),
                OriginalCity.name_en.label("original_city"),
                CurrentCity.name_en.label("current_city"),
                ShelterCenter.name_en.label("site"),
                ShelterCenter.code.label("site_code"),
                ShelterCenter.name_en.label("camp_name"),
                ShelterBlock.name_en.label("block"),
                ShelterBlock.code.label("block_code"),
                func.coalesce(member_agg.c.member_count, 0).label("member_count"),
                func.coalesce(member_agg.c.male_count, 0).label("male_count"),
                func.coalesce(member_agg.c.female_count, 0).label("female_count"),
                func.coalesce(member_agg.c.sons_count, 0).label("sons_count"),
                func.coalesce(member_agg.c.daughters_count, 0).label("daughters_count"),
                func.coalesce(member_agg.c.females_18_plus_count, 0).label(
                    "females_18_plus_count"
                ),
                func.coalesce(member_agg.c.under_2_count, 0).label("under_2_count"),
                func.coalesce(member_agg.c.under_2_male_count, 0).label(
                    "under_2_male_count"
                ),
                func.coalesce(member_agg.c.under_2_female_count, 0).label(
                    "under_2_female_count"
                ),
                func.coalesce(member_agg.c.under_3_count, 0).label("under_3_count"),
                func.coalesce(member_agg.c.under_5_count, 0).label("under_5_count"),
                func.coalesce(member_agg.c.under_18_count, 0).label("under_18_count"),
                func.coalesce(member_agg.c.adult_count, 0).label("adult_count"),
                func.coalesce(member_agg.c.age_3_5_count, 0).label("age_3_5_count"),
                func.coalesce(member_agg.c.age_3_5_male_count, 0).label(
                    "age_3_5_male_count"
                ),
                func.coalesce(member_agg.c.age_3_5_female_count, 0).label(
                    "age_3_5_female_count"
                ),
                func.coalesce(member_agg.c.age_6_18_count, 0).label("age_6_18_count"),
                func.coalesce(member_agg.c.age_6_18_male_count, 0).label(
                    "age_6_18_male_count"
                ),
                func.coalesce(member_agg.c.age_6_18_female_count, 0).label(
                    "age_6_18_female_count"
                ),
                func.coalesce(member_agg.c.age_19_60_count, 0).label("age_19_60_count"),
                func.coalesce(member_agg.c.age_19_60_male_count, 0).label(
                    "age_19_60_male_count"
                ),
                func.coalesce(member_agg.c.age_19_60_female_count, 0).label(
                    "age_19_60_female_count"
                ),
                func.coalesce(member_agg.c.elderly_60_plus_count, 0).label(
                    "elderly_60_plus_count"
                ),
                func.coalesce(member_agg.c.elderly_60_plus_male_count, 0).label(
                    "elderly_60_plus_male_count"
                ),
                func.coalesce(member_agg.c.elderly_60_plus_female_count, 0).label(
                    "elderly_60_plus_female_count"
                ),
                func.coalesce(member_agg.c.disabled_count, 0).label("disabled_count"),
                func.coalesce(member_agg.c.disabled_any, 0).label("disabled_any"),
                func.coalesce(member_agg.c.injured_count, 0).label("injured_count"),
                func.coalesce(member_agg.c.chronic_count, 0).label("chronic_count"),
                func.coalesce(member_agg.c.chronic_any, 0).label("chronic_any"),
                func.coalesce(member_agg.c.pregnant_count, 0).label("pregnant_count"),
                func.coalesce(member_agg.c.breastfeeding_count, 0).label(
                    "breastfeeding_count"
                ),
                case(
                    (
                        func.coalesce(member_agg.c.has_adult, 0) == 0,
                        func.coalesce(member_agg.c.under_18_count, 0),
                    ),
                    else_=0,
                ).label("unaccompanied_children_count"),
                case(
                    (
                        func.coalesce(member_agg.c.has_adult, 0) > 0,
                        func.coalesce(member_agg.c.under_18_count, 0),
                    ),
                    else_=0,
                ).label("accompanied_child_count"),
                (
                    func.coalesce(member_agg.c.pregnant_count, 0)
                    + func.coalesce(member_agg.c.breastfeeding_count, 0)
                ).label("pregnant_or_breastfeeding_count"),
                func.coalesce(member_agg.c.pregnant_or_breastfeeding_any, 0).label(
                    "pregnant_or_breastfeeding_any"
                ),
            )
            .outerjoin(member_agg, Family.id == member_agg.c.family_id)
            .outerjoin(HeadMember, Family.head_id == HeadMember.id)
            .outerjoin(SpouseMember, Family.spouse_id == SpouseMember.id)
            .outerjoin(OriginalCity, Family.original_city_id == OriginalCity.id)
            .outerjoin(
                OriginalGovernor, OriginalCity.governor_id == OriginalGovernor.id
            )
            .outerjoin(
                ShelterCenter, Family.current_shelter_center_id == ShelterCenter.id
            )
            .outerjoin(CurrentCity, ShelterCenter.city_id == CurrentCity.id)
            .outerjoin(ShelterBlock, Family.shelter_block_id == ShelterBlock.id)
        )

        if shelter_center_id:
            stmt = stmt.where(Family.current_shelter_center_id == shelter_center_id)
        if shelter_block_ids:
            stmt = stmt.where(Family.shelter_block_id.in_(shelter_block_ids))
        if selected_ids:
            stmt = stmt.where(Family.id.in_(selected_ids))

        result = await self.db.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()
