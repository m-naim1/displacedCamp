import { z } from 'zod'

export const UserRole = z.enum(['SUPERADMIN', 'MANAGER', 'BLOCK_HEAD', 'FAMILY'])
export type UserRole = z.infer<typeof UserRole>

export const Gender = z.enum(['male', 'female'])
export type Gender = z.infer<typeof Gender>

export const MaritalStatus = z.enum([
  'married',
  'divorced',
  'widowed',
  'single',
  'second-wife',
  'abandoned',
])
export type MaritalStatus = z.infer<typeof MaritalStatus>

export const ResidencyStatus = z.enum(['displaced', 'resident'])
export type ResidencyStatus = z.infer<typeof ResidencyStatus>

export const HousingType = z.enum([
  'tent',
  'house',
  'caravan',
  'garage',
  'room',
  'school',
  'other',
])
export type HousingType = z.infer<typeof HousingType>

export const UpdateRequestType = z.enum([
  'ADD_MEMBER',
  'CHANGE_HEAD',
  'UPDATE_FAMILY_INFO',
  'UPDATE_MEMBER_INFO',
])
export type UpdateRequestType = z.infer<typeof UpdateRequestType>

export const UpdateRequestStatus = z.enum(['PENDING', 'APPROVED', 'REJECTED'])
export type UpdateRequestStatus = z.infer<typeof UpdateRequestStatus>
