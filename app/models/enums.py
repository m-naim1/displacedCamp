from enum import StrEnum


class UserRole(StrEnum):
    SUPERADMIN = "SUPERADMIN"
    MANAGER = "MANAGER"
    BLOCK_HEAD = "BLOCK_HEAD"
    FAMILY = "FAMILY"


class ResidencyStatus(StrEnum):
    DISPLACED = "displaced"
    RESIDENT = "resident"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class MaritalStatus(StrEnum):
    MARRIED = "married"  # متزوج/ة
    DIVORCED = "divorced"  # مطلق/ة
    WIDOWED = "widowed"  # ارمل/ة
    SINGLE = "single"  # اعزب/عزباء
    SECOND_WIFE = "second-wife"  # زوجة ثانية
    ABANDONED = "abandoned"  # مهجورة


class HousingType(StrEnum):
    TENT = "tent"
    HOUSE = "house"
    CARAVAN = "caravan"
    GARAGE = "garage"
    ROOM = "room"
    SCHOOL = "school"
    OTHER = "other"


class UpdateRequestType(StrEnum):
    ADD_MEMBER = "ADD_MEMBER"
    CHANGE_HEAD = "CHANGE_HEAD"
    UPDATE_FAMILY_INFO = "UPDATE_FAMILY_INFO"
    UPDATE_MEMBER_INFO = "UPDATE_MEMBER_INFO"


class UpdateRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditAction:
    """Plain string constants (not an enum) so new actions don't need a
    migration or check-constraint change on the audit_logs table."""

    # families
    FAMILY_CREATED = "FAMILY_CREATED"
    FAMILY_UPDATED = "FAMILY_UPDATED"
    FAMILY_ARCHIVED = "FAMILY_ARCHIVED"
    FAMILY_RESTORED = "FAMILY_RESTORED"
    # members
    MEMBER_ADDED = "MEMBER_ADDED"
    MEMBER_UPDATED = "MEMBER_UPDATED"
    MEMBER_DELETED = "MEMBER_DELETED"
    # family self-service
    UPDATE_REQUEST_CREATED = "UPDATE_REQUEST_CREATED"
    UPDATE_REQUEST_APPROVED = "UPDATE_REQUEST_APPROVED"
    UPDATE_REQUEST_REJECTED = "UPDATE_REQUEST_REJECTED"
    # users
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    # bulk operations
    BULK_IMPORT = "BULK_IMPORT"
