from pydantic import BaseModel


class BlockCount(BaseModel):
    name: str
    count: int


class CenterCount(BaseModel):
    name: str
    count: int


class DashboardStats(BaseModel):
    total_families: int
    active_families: int
    archived_families: int
    total_members: int
    avg_per_family: float
    disabled: int
    injured: int
    pregnant: int
    chronic: int
    block_counts: list[BlockCount]
    center_counts: list[CenterCount]
    max_block: int
    under_5: int = 0
    age_5_17: int = 0
    age_18_59: int = 0
    age_60_plus: int = 0
    pending_update_requests: int = 0