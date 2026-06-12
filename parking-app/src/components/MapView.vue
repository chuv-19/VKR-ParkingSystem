<template>
  <div ref="mapContainer" class="map-container"></div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Parking } from '../types/parking'

/** При таком зуме и выше показываем цену в «чипе» рядом с знаком. */
const ZOOM_SHOW_PRICE = 15
const YMAPS_SCRIPT_URL = 'https://api-maps.yandex.ru/2.1/?lang=ru_RU'

type YMaps = any
type YMapInstance = any

declare global {
  interface Window {
    ymaps?: YMaps
  }
}

let ymapsLoaderPromise: Promise<YMaps> | null = null

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function isPaid(p: Parking): boolean {
  return !p.isFree && p.tariffPerHour > 0
}

function chipLabel(p: Parking): string {
  if (isPaid(p)) return `${p.tariffPerHour}₽`
  return '0₽'
}

function estimateMarkerWidth(p: Parking, showPrice: boolean): number {
  const sign = 36
  const gap = 10
  if (!showPrice) return sign
  const chipText = chipLabel(p)
  const chipW = Math.max(44, 12 + chipText.length * 8)
  return sign + gap + chipW
}

function createMarkerLayout(ymaps: YMaps) {
  return ymaps.templateLayoutFactory.createClass(`
    <div class="{{ properties.className }}" role="button" aria-label="{{ properties.ariaLabel }}">
      <div class="map-pin__sign">P</div>
      {% if properties.showPrice %}
        <div class="map-pin__chip">{{ properties.priceLabel }}</div>
      {% endif %}
    </div>
  `)
}

function markerProperties(p: Parking, selected: boolean, zoom: number) {
  const showPrice = zoom >= ZOOM_SHOW_PRICE
  return {
    className: [
      'map-pin',
      isPaid(p) ? 'map-pin--paid' : 'map-pin--free',
      selected ? 'map-pin--selected' : '',
      showPrice ? 'map-pin--with-chip' : 'map-pin--sign-only',
    ]
      .filter(Boolean)
      .join(' '),
    ariaLabel: escapeHtml(p.name),
    showPrice,
    priceLabel: escapeHtml(chipLabel(p)),
  }
}

const props = withDefaults(
  defineProps<{
    parkings: Parking[]
    selectedParkingId: string | null
    searchActive?: boolean
    /** false когда родитель скрывает карту (модалка) — после показа пересчитываем размер */
    visible?: boolean
  }>(),
  { searchActive: false, visible: true },
)

const emit = defineEmits<{
  (e: 'selectParking', id: string): void
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
let ymaps: YMaps | null = null
let map: YMapInstance | null = null
let markerLayoutClass: any = null
const mapMarkers: any[] = []
let mapZoom = 12
/** Чтобы не сбрасывать зум при перерисовке маркеров после zoomend */
let lastPannedToSelectionId: string | null = null

function getYMaps(): Promise<YMaps> {
  if (window.ymaps) {
    return new Promise(resolve => {
      window.ymaps.ready(() => resolve(window.ymaps!))
    })
  }

  if (!ymapsLoaderPromise) {
    ymapsLoaderPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = YMAPS_SCRIPT_URL
      script.async = true
      script.onload = () => {
        if (!window.ymaps) {
          reject(new Error('Yandex Maps API не загрузилась'))
          return
        }
        window.ymaps.ready(() => resolve(window.ymaps!))
      }
      script.onerror = () => reject(new Error('Не удалось загрузить Yandex Maps API'))
      document.head.appendChild(script)
    })
  }

  return ymapsLoaderPromise
}

function onBoundsChange(e: any) {
  if (!map) return
  const z = e.get('newZoom')
  if (z === mapZoom) return
  mapZoom = z
  renderMarkers()
}

function clearMarkers() {
  if (!map) return
  mapMarkers.forEach(marker => map!.geoObjects.remove(marker))
  mapMarkers.length = 0
}

async function initMap() {
  if (!mapContainer.value || map) return

  ymaps = await getYMaps()
  const center = [59.9386, 30.3141]

  map = new ymaps.Map(mapContainer.value, {
    center,
    zoom: 12,
    controls: ['zoomControl'],
  })
  mapZoom = map.getZoom()

  markerLayoutClass = createMarkerLayout(ymaps)
  map.events.add('boundschange', onBoundsChange)
  renderMarkers()
}

function renderMarkers() {
  if (!map || !ymaps || !markerLayoutClass) return
  clearMarkers()

  let selectedCoords: [number, number] | null = null
  const zoom = map.getZoom()

  props.parkings.forEach(parking => {
    const selected = parking.id === props.selectedParkingId
    const showPrice = zoom >= ZOOM_SHOW_PRICE
    const markerWidth = estimateMarkerWidth(parking, showPrice)
    const markerHeight = 42

    const marker = new ymaps.Placemark(
      [parking.latitude, parking.longitude],
      markerProperties(parking, selected, zoom),
      {
        iconLayout: 'default#imageWithContent',
        iconImageHref:
          'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==',
        iconImageSize: [1, 1],
        iconImageOffset: [0, 0],
        iconContentLayout: markerLayoutClass,
        iconContentOffset: [-markerWidth / 2, -markerHeight],
        iconShape: {
          type: 'Rectangle',
          coordinates: [
            [-markerWidth / 2, -markerHeight],
            [markerWidth / 2, 0],
          ],
        },
      },
    )
    marker.events.add('click', () => emit('selectParking', parking.id))
    map.geoObjects.add(marker)
    mapMarkers.push(marker)

    if (parking.id === props.selectedParkingId) {
      selectedCoords = [parking.latitude, parking.longitude]
    }
  })

  if (selectedCoords && props.selectedParkingId) {
    if (lastPannedToSelectionId !== props.selectedParkingId) {
      lastPannedToSelectionId = props.selectedParkingId
      map.setCenter(selectedCoords, 14, { duration: 200 })
    }
  } else {
    lastPannedToSelectionId = null
  }

  if (!selectedCoords && props.searchActive && props.parkings.length > 0) {
    if (props.parkings.length === 1) {
      const p = props.parkings[0]
      map.setCenter([p.latitude, p.longitude], 15, { duration: 200 })
    } else {
      const bounds = ymaps.util.bounds.fromPoints(
        props.parkings.map(p => [p.latitude, p.longitude]),
      )
      map.setBounds(bounds, { checkZoomRange: true, zoomMargin: 40, duration: 200 }).then(() => {
        if (map && map.getZoom() > 16) {
          map.setZoom(16, { duration: 150 })
        }
      })
    }
  }
}

onMounted(async () => {
  await initMap()
})

onBeforeUnmount(() => {
  clearMarkers()
  if (map) {
    map.events.remove('boundschange', onBoundsChange)
    map.destroy()
    map = null
  }
  ymaps = null
  markerLayoutClass = null
})

watch(
  () => props.parkings,
  () => {
    renderMarkers()
  },
  { deep: true },
)

watch(
  () => props.selectedParkingId,
  () => {
    renderMarkers()
  },
)

watch(
  () => props.searchActive,
  () => {
    renderMarkers()
  },
)

watch(
  () => props.visible,
  async v => {
    if (v && map) {
      await nextTick()
      map.container.fitToViewport()
    }
  },
)
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 320px;
  border-radius: 12px;
  border: 1px solid #d0d0d0;
  overflow: hidden;
}
</style>

<style>
.map-pin {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  filter: drop-shadow(0 2px 6px rgba(15, 23, 42, 0.2));
  cursor: pointer;
  user-select: none;
}

.map-pin__sign {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 900;
  line-height: 1;
  color: #ffffff;
  border: 2px solid rgba(255, 255, 255, 0.95);
  flex-shrink: 0;
  box-sizing: border-box;
}

.map-pin--paid .map-pin__sign {
  background: linear-gradient(145deg, #3b82f6 0%, #1d4ed8 100%);
}

.map-pin--free .map-pin__sign {
  background: linear-gradient(145deg, #94a3b8 0%, #64748b 100%);
}

.map-pin__chip {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #0f172a;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  white-space: nowrap;
  line-height: 1.2;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.map-pin--selected .map-pin__sign {
  outline: 3px solid #0f172a;
  outline-offset: 2px;
}

.map-pin--selected .map-pin__chip {
  border-color: #1d4ed8;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.25);
}
</style>
