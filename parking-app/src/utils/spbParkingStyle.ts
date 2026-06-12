import type { Parking } from '../types/parking'

/** Зоны оплаты как в приложении «Парковки Санкт-Петербурга» (КЗ 1–4). */
export type SpbKz = 'free' | 'kz1' | 'kz2' | 'kz3' | 'kz4'

/** Тарифы 1-го часа для кат. «В» (ориентир по официальной схеме). */
export const SPB_KZ_TARIFFS = {
  kz1: 100,
  kz2: 200,
  kz3: 280,
  kz4: 360,
} as const

export function getSpbKz(p: Parking): SpbKz {
  if (p.isFree || p.tariffPerHour <= 0) return 'free'
  const t = p.tariffPerHour
  if (t <= SPB_KZ_TARIFFS.kz1) return 'kz1'
  if (t <= SPB_KZ_TARIFFS.kz2) return 'kz2'
  if (t <= SPB_KZ_TARIFFS.kz3) return 'kz3'
  return 'kz4'
}

export function spbKzShortLabel(kz: SpbKz): string {
  if (kz === 'free') return 'Бесплатно'
  return `КЗ ${kz.slice(2)}`
}
