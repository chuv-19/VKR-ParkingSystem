<template>
  <section class="page">
    <ParkingFilters
      :filters="filters"
      @update:filters="onUpdateFilters"
    />

    <div class="layout">
      <div
        class="map-slot"
        :class="{ 'map-slot--hidden-for-modal': !!selectedParking }"
        :aria-hidden="selectedParking ? true : undefined"
      >
        <MapView
          :parkings="filteredParkings"
          :selectedParkingId="selectedParkingId"
          :search-active="searchActive"
          :visible="!selectedParking"
          @selectParking="onSelectParking"
        />
      </div>
      <ParkingList
        :parkings="filteredParkings"
        :selectedParkingId="selectedParkingId"
        @selectParking="onSelectParking"
      />
    </div>

    <ParkingDetailsModal
      v-if="selectedParking"
      :parking="selectedParking"
      :allow-favorite="isAuthorized"
      :favorite-status-message="favoriteStatusMessage"
      @close="selectedParkingId = null"
      @toggleFavorite="onToggleFavorite"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Parking, ParkingFilters as ParkingFiltersType } from '../types/parking'
import MapView from '../components/MapView.vue'
import ParkingList from '../components/ParkingList.vue'
import ParkingFilters from '../components/ParkingFilters.vue'
import ParkingDetailsModal from '../components/ParkingDetailsModal.vue'
import {
  addFavoriteForUser,
  getFavoritesForUser,
  readCurrentUser,
  type FavoriteParking,
} from '../utils/favorites'

// Тарифы под зоны КЗ 1–4 как в приложении «Парковки Санкт-Петербурга»
const parkings = ref<Parking[]>([
  {
    id: '1',
    name: 'Набережная канала Грибоедова, 21',
    address: 'Санкт-Петербург, Невский пр., 28',
    zone: 'КЗ 4',
    latitude: 59.9354,
    longitude: 30.3251,
    tariffPerHour: 360,
    isFree: false,
    schedule: 'Пн–Вс 08:00–22:00',
    status: 'available',
  },
  {
    id: '2',
    name: 'Наб. реки Мойки',
    address: 'Санкт-Петербург, наб. реки Мойки, 22',
    zone: 'КЗ 2',
    latitude: 59.9396,
    longitude: 30.3213,
    tariffPerHour: 280,
    isFree: false,
    schedule: 'Пн–Вс 08:00–22:00',
    status: 'available',
  },
  {
    id: '3',
    name: 'Васильевский остров, 7-я линия',
    address: 'Санкт-Петербург, 7-я линия В.О., 40',
    zone: 'КЗ 2',
    latitude: 59.9426,
    longitude: 30.2789,
    tariffPerHour: 200,
    isFree: false,
    schedule: 'Пн–Сб 09:00–21:00',
    status: 'unknown',
  },
  {
    id: '4',
    name: 'Стелла «Городу-герою Ленинграду»',
    address: 'Санкт-Петербург, Лиговский пр. / ул. Гончарная',
    zone: 'Бесплатно',
    latitude: 59.931326,
    longitude: 30.362328,
    tariffPerHour: 0,
    isFree: true,
    schedule: 'Круглосуточно',
    status: 'available',
  },
  {
    id: '5',
    name: 'Исаакиевская площадь',
    address: 'Санкт-Петербург, Исаакиевская пл.',
    zone: 'КЗ 4',
    latitude: 59.9342,
    longitude: 30.3065,
    tariffPerHour: 360,
    isFree: false,
    schedule: 'Пн–Вс 08:00–23:00',
    status: 'available',
  },
  {
    id: '6',
    name: 'ул. Бородинская, 11',
    address: 'Санкт-Петербург, ул. Бородинская, 11',
    zone: 'КЗ 4',
    latitude: 59.9248,
    longitude: 30.3324,
    tariffPerHour: 360,
    isFree: false,
    schedule: 'Пн–Вс 08:00–22:00',
    status: 'available',
  },
])

const filters = ref<ParkingFiltersType>({
  query: '',
  onlyFree: false,
  maxTariffPerHour: null,
  scheduleMode: 'any',
})

const selectedParkingId = ref<string | null>(null)
const favoriteStatusMessage = ref<string | null>(null)

const searchActive = computed(() => filters.value.query.trim().length > 0)
const currentUser = computed(() => readCurrentUser())
const isAuthorized = computed(() => !!currentUser.value)

function matchesQuery(p: Parking, q: string): boolean {
  if (!q) return true
  const n = `${p.name} ${p.address} ${p.zone}`.toLowerCase()
  return n.includes(q)
}

function matchesSchedule(p: Parking, mode: ParkingFiltersType['scheduleMode']): boolean {
  if (mode === 'any') return true
  const s = p.schedule.toLowerCase()
  if (mode === '24h') return s.includes('круглосуточ')
  if (mode === 'daytime') return !s.includes('круглосуточ')
  return true
}

const filteredParkings = computed(() => {
  const f = filters.value
  const q = f.query.trim().toLowerCase()
  return parkings.value.filter(p => {
    if (!matchesQuery(p, q)) return false
    if (f.onlyFree && !p.isFree) return false
    if (f.maxTariffPerHour != null && p.tariffPerHour > f.maxTariffPerHour) return false
    if (!matchesSchedule(p, f.scheduleMode)) return false
    return true
  })
})

const selectedParking = computed(() =>
  parkings.value.find(p => p.id === selectedParkingId.value) ?? null
)

watch(filteredParkings, list => {
  if (
    selectedParkingId.value &&
    !list.some(p => p.id === selectedParkingId.value)
  ) {
    selectedParkingId.value = null
  }
})

function onUpdateFilters(newFilters: ParkingFiltersType) {
  filters.value = newFilters
}

function onSelectParking(id: string) {
  selectedParkingId.value = id
  favoriteStatusMessage.value = null
}

function onToggleFavorite(parkingId: string) {
  favoriteStatusMessage.value = null
  const user = currentUser.value
  if (!user) {
    favoriteStatusMessage.value = 'Войдите в аккаунт, чтобы добавлять парковки в избранное.'
    return
  }

  const parking = parkings.value.find(item => item.id === parkingId)
  if (!parking) return

  const currentFavorites = getFavoritesForUser(user.id)
  if (currentFavorites.some(item => item.id === parking.id)) {
    favoriteStatusMessage.value = 'Эта парковка уже в избранном.'
    return
  }

  const payload: FavoriteParking = {
    id: parking.id,
    name: parking.name,
    address: parking.address,
    zone: parking.zone,
    tariffPerHour: parking.tariffPerHour,
    isFree: parking.isFree,
    schedule: parking.schedule,
  }

  const added = addFavoriteForUser(user.id, payload)
  favoriteStatusMessage.value = added
    ? 'Парковка добавлена в избранное.'
    : 'Не удалось сохранить избранное. Попробуйте еще раз.'
}
</script>

<style scoped>
.page {
  max-width: 1280px;
  margin: 1.5rem auto;
  padding: 0 1rem;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) minmax(320px, 1fr);
  gap: 1rem;
  margin-top: 1rem;
  align-items: start;
}

.map-slot {
  min-width: 0;
}

.map-slot--hidden-for-modal {
  visibility: hidden;
  pointer-events: none;
  opacity: 0;
}

@media (max-width: 640px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>

