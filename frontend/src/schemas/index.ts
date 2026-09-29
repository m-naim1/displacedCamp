import { z } from 'zod'
import {
  Gender,
  HousingType,
  MaritalStatus,
  ResidencyStatus,
  UpdateRequestStatus,
  UpdateRequestType,
  UserRole,
} from './enums'

// ---------- Auth / Users ----------

export const Token = z.object({ access_token: z.string(), token_type: z.string() })

export const UserResponse = z.object({
  username: z.string(),
  email: z.string(),
  full_name: z.string().nullable(),
  role: UserRole,
  block_id: z.number().nullable(),
  shelter_id: z.number().nullable(),
  id: z.number(),
  is_active: z.boolean(),
})
export type UserResponse = z.infer<typeof UserResponse>

export const UserCreate = z.object({
  username: z.string().min(3),
  email: z.string().email(),
  full_name: z.string().optional(),
  role: UserRole,
  block_id: z.number().int().positive().optional(),
  shelter_id: z.number().int().positive().optional(),
  password: z.string().min(8),
})
export type UserCreate = z.infer<typeof UserCreate>

export const UserUpdate = z
  .object({
    email: z.string().email().optional(),
    full_name: z.string().optional(),
    role: UserRole.optional(),
    block_id: z.number().int().positive().optional(),
    shelter_id: z.number().int().positive().optional(),
    password: z.string().min(8).optional(),
  })
  .partial()
export type UserUpdate = z.infer<typeof UserUpdate>

// ---------- Members ----------

export const MemberBase = z.object({
  id: z.number().int(),
  full_name: z.string().min(1),
  gender: Gender,
  marital_status: MaritalStatus,
  date_of_birth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD'),
  relationship_to_head_id: z.number().int().optional().default(1),
  has_chronic_disease: z.boolean().optional().default(false),
  injured: z.boolean().optional().default(false),
  disabled: z.boolean().optional().default(false),
  pregnant: z.boolean().optional().default(false),
  breastfeeding: z.boolean().optional().default(false),
})

export const MemberCreate = MemberBase
export type MemberCreate = z.infer<typeof MemberCreate>

export const MemberUpdate = z
  .object({
    full_name: z.string().min(1).optional(),
    marital_status: MaritalStatus.optional(),
    has_chronic_disease: z.boolean().optional(),
    injured: z.boolean().optional(),
    disabled: z.boolean().optional(),
    pregnant: z.boolean().optional(),
    breastfeeding: z.boolean().optional(),
  })
  .partial()
export type MemberUpdate = z.infer<typeof MemberUpdate>

export const MemberResponse = MemberBase.extend({
  family_id: z.number().int(),
  family_head_name: z.string().nullable().optional(),
})
export type MemberResponse = z.infer<typeof MemberResponse>

// ---------- Families ----------

const NationalId = z
  .number()
  .int()
  .refine((v) => v >= 400000000 && v <= 999999999, {
    message: '9 digits, first digit 4/7/8/9',
  })
  .refine(isLuhnValid, { message: 'Invalid national ID (checksum)' })

// Mirrors the backend's Palestine-ID checksum: 0-based even index * 1, odd index * 2.
function isLuhnValid(n: number): boolean {
  const digits = String(n)
  let sum = 0
  for (let i = 0; i < digits.length; i++) {
    let step = +digits[i] * ((i % 2) + 1)
    if (step > 9) step -= 9
    sum += step
  }
  return sum % 10 === 0
}

export const NationalIdField = NationalId

export const FamilyCreate = z.object({
  head_id: NationalId,
  spouse_id: NationalId.optional(),
  female_headed: z.boolean().optional(),
  child_headed: z.boolean().optional(),
  primary_phone_number: z.string().min(7),
  secondary_phone_number: z.string().optional(),
  residency_status: ResidencyStatus,
  housing_type: HousingType,
  original_city_id: z.number().int().positive(),
  current_shelter_center_id: z.number().int().positive(),
  shelter_block_id: z.number().int().positive().optional(),
  shelter_quality_id: z.number().int().positive().optional(),
  members: z.array(MemberCreate).min(1),
})
export type FamilyCreate = z.infer<typeof FamilyCreate>

export const FamilyBase = z.object({
  head_id: z.number().int(),
  spouse_id: z.number().int().nullable(),
  female_headed: z.boolean().nullable(),
  child_headed: z.boolean().nullable(),
  primary_phone_number: z.string(),
  secondary_phone_number: z.string().nullable(),
  residency_status: ResidencyStatus,
  housing_type: HousingType,
  original_city_id: z.number().int(),
  current_shelter_center_id: z.number().int(),
  shelter_block_id: z.number().int().nullable(),
  shelter_quality_id: z.number().int().nullable(),
})

export const FamilyResponse = FamilyBase.extend({
  id: z.number().int(),
  is_active: z.boolean(),
  created_at: z.string(),
  archived_at: z.string().nullable(),
  head: MemberResponse,
  spouse: MemberResponse.nullable(),
  members: z.array(MemberResponse),
})
export type FamilyResponse = z.infer<typeof FamilyResponse>

export const FamilyListResponse = FamilyBase.extend({
  id: z.number().int(),
  is_active: z.boolean(),
  created_at: z.string(),
  archived_at: z.string().nullable(),
  head_name: z.string().nullable().optional(),
})
export type FamilyListResponse = z.infer<typeof FamilyListResponse>

export const FamilyUpdate = z
  .object({
    primary_phone_number: z.string().min(7).optional(),
    secondary_phone_number: z.string().optional(),
    residency_status: ResidencyStatus.optional(),
    housing_type: HousingType.optional(),
    female_headed: z.boolean().optional(),
    child_headed: z.boolean().optional(),
    original_city_id: z.number().int().positive().optional(),
    current_shelter_center_id: z.number().int().positive().optional(),
    shelter_block_id: z.number().int().positive().optional(),
    shelter_quality_id: z.number().int().positive().optional(),
  })
  .partial()
export type FamilyUpdate = z.infer<typeof FamilyUpdate>

// ---------- Update requests ----------

export const UpdateRequestCreate = z.object({
  request_type: UpdateRequestType,
  payload: z.record(z.string(), z.unknown()),
})
export type UpdateRequestCreate = z.infer<typeof UpdateRequestCreate>

// The API returns raw ORM rows; keep parsing permissive.
export const UpdateRequestRow = z.object({
  id: z.number().int(),
  family_id: z.number().int(),
  request_type: UpdateRequestType,
  status: UpdateRequestStatus,
  payload: z.unknown(),
  created_at: z.string().nullable().optional(),
  reviewed_at: z.string().nullable().optional(),
})
export type UpdateRequestRow = z.infer<typeof UpdateRequestRow>

export const UpdateRequestCreated = z.object({
  message: z.string(),
  id: z.number().int(),
})

// ---------- Lookups ----------

export const LookupBase = z.object({
  id: z.number().int(),
  is_active: z.boolean(),
  code: z.string(),
  name_en: z.string(),
  name_ar: z.string(),
})
export type LookupBase = z.infer<typeof LookupBase>

export const Governor = LookupBase
export type Governor = z.infer<typeof Governor>
export const City = LookupBase.extend({ governor_id: z.number().int() })
export type City = z.infer<typeof City>
export const ShelterCenter = LookupBase.extend({ city_id: z.number().int() })
export type ShelterCenter = z.infer<typeof ShelterCenter>
export const ShelterBlock = LookupBase.extend({ shelter_center_id: z.number().int() })
export type ShelterBlock = z.infer<typeof ShelterBlock>
export const ShelterQuality = LookupBase
export type ShelterQuality = z.infer<typeof ShelterQuality>
export const RelationshipToHead = LookupBase
export type RelationshipToHead = z.infer<typeof RelationshipToHead>

export const LookupCreate = z.object({
  code: z.string().min(1),
  name_en: z.string().min(1),
  name_ar: z.string().min(1),
})
export type LookupCreate = z.infer<typeof LookupCreate>
export const LookupUpdate = LookupCreate.partial().extend({
  is_active: z.boolean().optional(),
})
export type LookupUpdate = z.infer<typeof LookupUpdate>

// ---------- Reports ----------

const num = z.number().nullable()
const opt = <T extends z.ZodTypeAny>(s: T) => s.nullish()

export const FamilyReportRow = z.object({
  family_id: z.number().int(),
  serial_no: opt(z.string()),
  head_name: opt(z.string()),
  head_id_number: num,
  head_gender: opt(z.string()),
  head_marital_status: opt(z.string()),
  spouse_name: opt(z.string()),
  spouse_id_number: num,
  phone_1: opt(z.string()),
  phone_2: opt(z.string()),
  original_governorate: opt(z.string()),
  original_city: opt(z.string()),
  current_city: opt(z.string()),
  site: opt(z.string()),
  site_code: opt(z.string()),
  camp_name: opt(z.string()),
  block: opt(z.string()),
  block_code: opt(z.string()),
  shelter_type: opt(z.string()),
  residency_status: opt(z.string()),
  women_headed: z.boolean().default(false),
  child_headed: z.boolean().default(false),
  is_active: z.boolean().default(false),
  member_count: z.number().default(0),
  male_count: z.number().default(0),
  female_count: z.number().default(0),
  daughters_count: z.number().default(0),
  sons_count: z.number().default(0),
  females_18_plus_count: z.number().default(0),
  under_2_count: z.number().default(0),
  under_3_count: z.number().default(0),
  under_5_count: z.number().default(0),
  under_18_count: z.number().default(0),
  adult_count: z.number().default(0),
  age_3_5_count: z.number().default(0),
  age_6_18_count: z.number().default(0),
  age_19_60_count: z.number().default(0),
  elderly_60_plus_count: z.number().default(0),
  disabled_any: z.boolean().default(false),
  disabled_count: z.number().default(0),
  injured_count: z.number().default(0),
  chronic_any: z.boolean().default(false),
  chronic_count: z.number().default(0),
  pregnant_count: z.number().default(0),
  breastfeeding_count: z.number().default(0),
  pregnant_or_breastfeeding_count: z.number().default(0),
  unaccompanied_children_count: z.number().default(0),
  accompanied_child_count: z.number().default(0),
  created_at: opt(z.string()),
  updated_at: opt(z.string()),
})
export type FamilyReportRow = z.infer<typeof FamilyReportRow>

export const MemberReportRow = z.object({
  serial_no: opt(z.string()),
  member_id: z.number().int(),
  member_name: opt(z.string()),
  member_id_number: num,
  family_id: num,
  family_head_name: opt(z.string()),
  family_phone_1: opt(z.string()),
  age: num,
  dob: opt(z.string()),
  gender: opt(z.string()),
  relation: opt(z.string()),
  marital_status: opt(z.string()),
  site: opt(z.string()),
  block: opt(z.string()),
  disabled: z.boolean().default(false),
  injured: z.boolean().default(false),
  chronic_disease: z.boolean().default(false),
  pregnant: z.boolean().default(false),
  breastfeeding: z.boolean().default(false),
  accompanied_child: z.boolean().default(false),
  family_is_active: z.boolean().default(false),
})
export type MemberReportRow = z.infer<typeof MemberReportRow>

// ---------- Audit ----------

export const AuditLogRow = z.object({
  id: z.number().int(),
  user_id: z.number().int().nullable().optional(),
  actor_username: z.string(),
  actor_role: z.string(),
  action: z.string(),
  entity_type: z.string(),
  entity_id: z.string().nullable().optional(),
  details: z.unknown().nullable().optional(),
  created_at: z.string(),
})
export type AuditLogRow = z.infer<typeof AuditLogRow>

// ---------- Dashboard ----------

export const DashboardStats = z.object({
  total_families: z.number().int(),
  active_families: z.number().int(),
  archived_families: z.number().int(),
  total_members: z.number().int(),
  avg_per_family: z.number(),
  disabled: z.number().int(),
  injured: z.number().int(),
  pregnant: z.number().int(),
  chronic: z.number().int(),
  block_counts: z.array(z.object({ name: z.string(), count: z.number().int() })),
  center_counts: z.array(z.object({ name: z.string(), count: z.number().int() })),
  max_block: z.number().int(),
  under_5: z.number().int().default(0),
  age_5_17: z.number().int().default(0),
  age_18_59: z.number().int().default(0),
  age_60_plus: z.number().int().default(0),
  pending_update_requests: z.number().int().default(0),
})
export type DashboardStats = z.infer<typeof DashboardStats>
