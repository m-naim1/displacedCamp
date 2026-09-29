import { createSignal, createEffect } from 'solid-js'

export type Locale = 'en' | 'ar'

const [locale, setLocale] = createSignal<Locale>(
  (localStorage.getItem('camp_locale') as Locale) || 'en',
)

export { locale, setLocale }

createEffect(() => {
  localStorage.setItem('camp_locale', locale())
  document.documentElement.lang = locale()
  document.documentElement.dir = locale() === 'ar' ? 'rtl' : 'ltr'
})

export function toggleLocale() {
  setLocale(locale() === 'en' ? 'ar' : 'en')
}

const dict: Record<string, [string, string]> = {
  // app / common
  appName: ['Camp Manager', 'مدير المخيم'],
  login: ['Login', 'تسجيل الدخول'],
  logout: ['Logout', 'تسجيل الخروج'],
  password: ['Password', 'كلمة المرور'],
  username: ['Username', 'اسم المستخدم'],
  email: ['Email', 'البريد الإلكتروني'],
  fullName: ['Full name', 'الاسم الكامل'],
  role: ['Role', 'الدور'],
  save: ['Save', 'حفظ'],
  cancel: ['Cancel', 'إلغاء'],
  delete: ['Delete', 'حذف'],
  edit: ['Edit', 'تعديل'],
  add: ['Add', 'إضافة'],
  search: ['Search', 'بحث'],
  filters: ['Filters', 'عوامل التصفية'],
  reset: ['Reset', 'إعادة تعيين'],
  loading: ['Loading…', 'جار التحميل…'],
  error: ['Error', 'خطأ'],
  empty: ['No data', 'لا توجد بيانات'],
  total: ['Total', 'الإجمالي'],
  actions: ['Actions', 'إجراءات'],
  active: ['Active', 'نشط'],
  inactive: ['Inactive', 'غير نشط'],
  archived: ['Archived', 'مؤرشف'],
  confirm: ['Confirm', 'تأكيد'],
  yes: ['Yes', 'نعم'],
  no: ['No', 'لا'],
  all: ['All', 'الكل'],
  next: ['Next', 'التالي'],
  prev: ['Previous', 'السابق'],
  page: ['Page', 'صفحة'],
  export: ['Export', 'تصدير'],
  create: ['Create', 'إنشاء'],
  update: ['Update', 'تحديث'],
  optional: ['optional', 'اختياري'],
  details: ['Details', 'التفاصيل'],
  back: ['Back', 'رجوع'],
  none: ['None', 'لا شيء'],
  sessionExpired: ['Session expired, please log in again', 'انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى'],
  saved: ['Saved successfully', 'تم الحفظ بنجاح'],
  deleted: ['Deleted successfully', 'تم الحذف بنجاح'],
  submit: ['Submit', 'إرسال'],
  close: ['Close', 'إغلاق'],

  // login
  staffLogin: ['Staff Login', 'دخول الموظفين'],
  familyLogin: ['Family Login', 'دخول العائلات'],
  familyLoginHint: ['Log in with the head of family national ID and date of birth', 'الدخول برقم هوية رب الأسرة وتاريخ الميلاد'],
  nationalId: ['National ID', 'رقم الهوية'],
  dateOfBirth: ['Date of birth', 'تاريخ الميلاد'],
  loginAsFamily: ['I am a family — log in here', 'أنا عائلة — الدخول من هنا'],
  loginAsStaff: ['I am staff — log in here', 'أنا موظف — الدخول من هنا'],
  invalidCredentials: ['Invalid credentials', 'بيانات الدخول غير صحيحة'],

  // nav
  families: ['Families', 'العائلات'],
  members: ['Members', 'الأفراد'],
  updateRequests: ['Update Requests', 'طلبات التحديث'],
  lookups: ['Lookups', 'البيانات المرجعية'],
  reports: ['Reports', 'التقارير'],
  users: ['Users', 'المستخدمون'],
  myFamily: ['My Family', 'عائلتي'],

  // family fields
  family: ['Family', 'عائلة'],
  head: ['Head of family', 'رب الأسرة'],
  spouse: ['Spouse', 'الزوج/الزوجة'],
  memberId: ['National ID', 'رقم الهوية'],
  memberName: ['Name', 'الاسم'],
  gender: ['Gender', 'الجنس'],
  male: ['Male', 'ذكر'],
  female: ['Female', 'أنثى'],
  maritalStatus: ['Marital status', 'الحالة الاجتماعية'],
  married: ['Married', 'متزوج'],
  divorced: ['Divorced', 'مطلق'],
  widowed: ['Widowed', 'أرمل'],
  single: ['Single', 'أعزب'],
  'second-wife': ['Second wife', 'زوجة ثانية'],
  abandoned: ['Abandoned', 'مهجورة'],
  dob: ['Date of birth', 'تاريخ الميلاد'],
  age: ['Age', 'العمر'],
  relationship: ['Relationship to head', 'صلة القرابة برب الأسرة'],
  residencyStatus: ['Residency status', 'حالة الإقامة'],
  displaced: ['Displaced', 'نازح'],
  resident: ['Resident', 'مقيم'],
  housingType: ['Housing type', 'نوع السكن'],
  tent: ['Tent', 'خيمة'],
  house: ['House', 'منزل'],
  caravan: ['Caravan', 'كرفان'],
  garage: ['Garage', 'كراج'],
  room: ['Room', 'غرفة'],
  school: ['School', 'مدرسة'],
  otherHousing: ['Other', 'أخرى'],
  primaryPhone: ['Primary phone', 'هاتف رئيسي'],
  secondaryPhone: ['Secondary phone', 'هاتف ثانوي'],
  femaleHeaded: ['Female-headed', 'أسرة تعولها امرأة'],
  childHeaded: ['Child-headed', 'أسرة يعولها طفل'],
  governorate: ['Governorate', 'المحافظة'],
  city: ['City', 'المدينة'],
  originalCity: ['Original city', 'المدينة الأصلية'],
  shelterCenter: ['Shelter center', 'مركز الإيواء'],
  shelterBlock: ['Block', 'القطاع'],
  shelterQuality: ['Shelter quality', 'جودة الإيواء'],
  createdAt: ['Registered at', 'تاريخ التسجيل'],

  // health flags
  hasChronic: ['Chronic disease', 'مرض مزمن'],
  injured: ['Injured', 'مصاب'],
  disabled: ['Disabled', 'إعاقة'],
  pregnant: ['Pregnant', 'حامل'],
  breastfeeding: ['Breastfeeding', 'مرضعة'],

  // families page
  newFamily: ['New family', 'عائلة جديدة'],
  editFamily: ['Edit family', 'تعديل العائلة'],
  archive: ['Archive', 'أرشفة'],
  restore: ['Restore', 'استعادة'],
  archiveConfirm: ['Archive this family?', 'أرشفة هذه العائلة؟'],
  restoreConfirm: ['Restore this family?', 'استعادة هذه العائلة؟'],
  deleteMemberConfirm: ['Delete this member permanently?', 'حذف هذا الفرد نهائياً؟'],
  addMember: ['Add member', 'إضافة فرد'],
  editMember: ['Edit member', 'تعديل الفرد'],
  membersCount: ['Members', 'عدد الأفراد'],
  headName: ['Head name', 'اسم رب الأسرة'],
  phoneNumber: ['Phone', 'الهاتف'],
  sortBy: ['Sort by', 'ترتيب حسب'],
  sortOrder: ['Order', 'الاتجاه'],
  asc: ['Ascending', 'تصاعدي'],
  desc: ['Descending', 'تنازلي'],
  familyCreated: ['Family created', 'تم إنشاء العائلة'],
  headMustBeMember: ['Head of family must be in the members list', 'رب الأسرة يجب أن يكون ضمن قائمة الأفراد'],
  invalidNationalId: ['Invalid national ID (9 digits, starts 4/7/8/9, checksum)', 'رقم هوية غير صالح (9 أرقام، يبدأ بـ 4/7/8/9، مع تحقق المجموع)'],
  pregnancyLogicError: ['Pregnancy/breastfeeding is not allowed for males or singles', 'لا يجوز الحمل/الإرضاء للذكور أو غير المتزوجات'],
  under5: ['Under 5', 'تحت 5 سنوات'],
  under18: ['Under 18', 'تحت 18 سنة'],
  elderly60: ['Elderly 60+', '60 سنة فأكثر'],
  hideColumnsHint: ['Selected columns are hidden', 'الأعمدة المحددة تكون مخفية'],

  // dashboard
  dashboard: ['Dashboard', 'لوحة التحكم'],
  avgMembers: ['Avg. members/family', 'متوسط الأفراد لكل عائلة'],
  pendingRequests: ['Pending requests', 'طلبات قيد الانتظار'],
  staffUsers: ['Staff users', 'موظفو النظام'],
  specialCases: ['Special cases', 'الحالات الخاصة'],
  ageDistribution: ['Age distribution', 'التوزيع العمري'],
  genderSplit: ['Gender split', 'توزيع الجنسين'],
  vulnerableGroups: ['Vulnerable groups', 'الفئات الهشة'],
  housingDistribution: ['Housing distribution', 'توزيع أنواع السكن'],
  residencySplit: ['Residency status', 'توزيع حالة الإقامة'],
  under2: ['Under 2', 'تحت سنتين'],
  adults: ['Adults 19–60', 'البالغون 19–60'],
  viewAll: ['View all', 'عرض الكل'],
  scopeHint: ['data scoped to your assignment', 'البيانات وفق نطاق صلاحيتك'],

  // update requests
  requestType: ['Request type', 'نوع الطلب'],
  status: ['Status', 'الحالة'],
  PENDING: ['Pending', 'قيد الانتظار'],
  APPROVED: ['Approved', 'مقبول'],
  REJECTED: ['Rejected', 'مرفوض'],
  ADD_MEMBER: ['Add member', 'إضافة فرد'],
  CHANGE_HEAD: ['Change head of family', 'تغيير رب الأسرة'],
  UPDATE_FAMILY_INFO: ['Update family info', 'تحديث بيانات العائلة'],
  UPDATE_MEMBER_INFO: ['Update member info', 'تحديث بيانات فرد'],
  approve: ['Approve', 'قبول'],
  reject: ['Reject', 'رفض'],
  approveConfirm: ['Approve and apply this request?', 'قبول هذا الطلب وتطبيقه؟'],
  rejectConfirm: ['Reject this request?', 'رفض هذا الطلب؟'],
  payload: ['Payload', 'المحتوى'],
  requestSubmitted: ['Request submitted', 'تم إرسال الطلب'],
  requestHistory: ['Request history', 'سجل الطلبات'],
  newRequest: ['New request', 'طلب جديد'],
  noPendingRequests: ['No pending requests', 'لا توجد طلبات قيد الانتظار'],

  // lookups
  governors: ['Governorates', 'المحافظات'],
  cities: ['Cities', 'المدن'],
  shelterCenters: ['Shelter centers', 'مراكز الإيواء'],
  shelterBlocks: ['Blocks', 'القطاعات'],
  shelterQualities: ['Shelter qualities', 'جودات الإيواء'],
  relationships: ['Relationships', 'صلات القرابة'],
  code: ['Code', 'الرمز'],
  nameEn: ['Name (EN)', 'الاسم (إنجليزي)'],
  nameAr: ['Name (AR)', 'الاسم (عربي)'],
  parent: ['Belongs to', 'يتبع لـ'],

  // reports
  familiesReport: ['Families report', 'تقرير العائلات'],
  membersReport: ['Members report', 'تقرير الأفراد'],
  specialOnly: ['Special cases only', 'الحالات الخاصة فقط'],
  columns: ['Columns', 'الأعمدة'],
  exportCsv: ['Export CSV', 'تصدير CSV'],
  exportJson: ['Export JSON', 'تصدير JSON'],
  exportXlsx: ['Export XLSX', 'تصدير XLSX'],
  exportColumnsHint: ['Selected columns are exported', 'الأعمدة المحددة تُصدَّر'],
  selectAll: ['Select all', 'تحديد الكل'],
  selected: ['Selected', 'المحدد'],
  selectAtLeastOne: ['Select at least one row to export', 'حدد صفاً واحداً على الأقل للتصدير'],

  // audit
  audit: ['Audit Log', 'سجل التدقيق'],
  action: ['Action', 'الإجراء'],
  actor: ['Actor', 'المنفّذ'],
  entityType: ['Entity', 'الكيان'],

  // users
  newUser: ['New user', 'مستخدم جديد'],
  editUser: ['Edit user', 'تعديل المستخدم'],
  deactivate: ['Deactivate', 'تعطيل'],
  deactivateConfirm: ['Deactivate this user?', 'تعطيل هذا المستخدم؟'],
  SUPERADMIN: ['Super Admin', 'المدير العام'],
  MANAGER: ['Manager', 'مدير'],
  BLOCK_HEAD: ['Block Head', 'رئيس قطاع'],
  FAMILY: ['Family', 'عائلة'],
  assignCampHint: ['Select a shelter center for MANAGER/BLOCK_HEAD', 'اختر مركز الإيواء للمدير/رئيس القطاع'],
  assignBlockHint: ['Select a block for BLOCK_HEAD', 'اختر القطاع لرئيس القطاع'],
  campOnly: ['your camp only', 'مخيمك فقط'],
  createManagerForCamp: ['Create manager for camp', 'إنشاء مدير للمخيم'],
  skip: ['Skip', 'تخطي'],
  minPassword: ['Password must be at least 8 characters', 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'],
  managerCreated: ['Manager account created', 'تم إنشاء حساب المدير'],
}

export function t(key: string): string {
  const entry = dict[key]
  if (!entry) return key
  return locale() === 'ar' ? entry[1] : entry[0]
}

// Translate an enum value (gender, marital status, roles, request types…)
export function tEnum(value: string | null | undefined): string {
  if (!value) return '—'
  if (value === 'other') return t('otherHousing')
  const r = dict[value]
  return r ? (locale() === 'ar' ? r[1] : r[0]) : value
}
