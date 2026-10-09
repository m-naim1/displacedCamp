# app/services/report_service.py
import asyncio
import csv
import io
from collections.abc import Sequence

from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.scoping import require_block_head_scope, require_manager_shelter_id
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.schemas.report import FamilyReportRow, MemberReportRow


class ReportService:
    def __init__(self, family_repo: FamilyRepository, member_repo: MemberRepository):
        self.family_repo = family_repo
        self.member_repo = member_repo

    def _get_scope(self, current_user: User) -> tuple[int | None, list[int] | None]:
        if current_user.role == UserRole.MANAGER:
            return require_manager_shelter_id(current_user), None
        elif current_user.role == UserRole.BLOCK_HEAD:
            shelter_id, block_id = require_block_head_scope(current_user)
            return shelter_id, [block_id]
        return None, None  # Superadmin

    async def get_families_report(
        self,
        current_user: User,
        block_ids: list[int] | None = None,
        selected_ids: list[int] | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[FamilyReportRow]:

        shelter_id, scope_block_ids = self._get_scope(current_user)
        effective_blocks = scope_block_ids if scope_block_ids else block_ids

        raw_data = await self.family_repo.get_families_report_data(
            shelter_center_id=shelter_id,
            shelter_block_ids=effective_blocks,
            selected_ids=selected_ids,
            skip=skip,
            limit=limit,
        )
        return await asyncio.to_thread(
            lambda: [FamilyReportRow(**row) for row in raw_data]
        )

    async def get_members_report(
        self,
        current_user: User,
        block_ids: list[int] | None = None,
        special_only: bool = False,
        selected_ids: list[int] | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[MemberReportRow]:

        shelter_id, scope_block_ids = self._get_scope(current_user)
        effective_blocks = scope_block_ids if scope_block_ids else block_ids

        raw_data = await self.member_repo.get_members_report_data(
            shelter_center_id=shelter_id,
            shelter_block_ids=effective_blocks,
            special_only=special_only,
            selected_ids=selected_ids,
            skip=skip,
            limit=limit,
        )
        return await asyncio.to_thread(
            lambda: [MemberReportRow(**row) for row in raw_data]
        )

    def generate_csv(
        self, data: Sequence[BaseModel], selected_columns: Sequence[str] | None = None
    ) -> StreamingResponse:
        if not data:
            return StreamingResponse(io.StringIO("No data"), media_type="text/csv")

        headers = (
            selected_columns if selected_columns else list(data[0].model_dump().keys())
        )
        headers = [
            col for col in headers if hasattr(data[0], col)
        ]  # Filter invalid columns

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for row in data:
            row_dict = row.model_dump()
            writer.writerow({k: row_dict.get(k, "") for k in headers})

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=report.csv"},
        )
