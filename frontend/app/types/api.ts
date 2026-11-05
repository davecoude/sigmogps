/** Contratos del API. Reflejan los DTOs del backend (ARQ-13). */

export type VehicleStatus = 'en_movimiento' | 'detenido' | 'sin_senal'

export interface Problem {
  type: string
  title: string
  status: number
  detail: string
  instance: string
  trace_id: string
  errors?: { campo: string; mensaje: string }[]
}

export interface Role {
  name: string
  description: string
}

export interface Me {
  id: string
  email: string
  full_name: string
  role: Role
  permissions: string[]
  must_change_password: boolean
}

export interface Position {
  latitude: number
  longitude: number
  speed_kmh: number
  course_degrees: number | null
  cardinal: string | null
  altitude_m: number | null
  satellites: number | null
  reported_at: string
}

export interface CustomField {
  id: number
  name: string
  value: string
}

export interface VehicleListItem {
  id: number
  name: string
  plate: string | null
  display_name: string
  status: VehicleStatus
  position: Position | null
  driver_id: number | null
  driver_name: string | null
  minutes_since_report: number | null
}

export interface VehicleDetail extends VehicleListItem {
  custom_fields: CustomField[]
}

export interface FleetSummary {
  total: number
  en_movimiento: number
  detenidos: number
  sin_senal: number
  con_conductor: number
  sin_conductor: number
}

export interface PageMeta {
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Paged<T> {
  items: T[]
  meta: PageMeta
}
