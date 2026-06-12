export interface Parking {
  id: string
  name: string
  address: string
  zone: string
  latitude: number
  longitude: number
  tariffPerHour: number
  isFree: boolean
  schedule: string
  status: 'available' | 'busy' | 'unknown'
}

export interface ParkingFilters {
  query: string
  onlyFree: boolean
  maxTariffPerHour: number | null
  scheduleMode: 'any' | '24h' | 'daytime'
}

