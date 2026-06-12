<template>
  <section class="page">
    <h1>Личный кабинет</h1>
    <p v-if="!currentUser">Авторизуйтесь, чтобы увидеть историю парковок, операции и свой транспорт.</p>
    <div v-else class="profile-header">
      <p>Добро пожаловать, {{ currentUser.login }}.</p>
      <button type="button" class="logout-button" @click="logout">Выйти</button>
    </div>

    <template v-if="!currentUser">
      <AccountAuthCard
        :loading="authLoading"
        :error-message="authError"
        @login="handleLogin"
        @open-register="openRegisterModal"
      />

      <RegisterModal
        v-if="registerModalOpen"
        :initial-login="registerPrefillLogin || undefined"
        @close="registerModalOpen = false"
        @success="onRegisterSuccess"
      />
    </template>

    <p v-if="profileError" class="profile-error">{{ profileError }}</p>
    <p v-if="profileLoading" class="profile-loading">Загрузка данных…</p>

    <div v-else-if="currentUser" class="profile-layout">
      <article class="profile-card">
        <h2 class="section-title">
          <Camera :size="20" class="section-title__icon" aria-hidden="true" />
          История парковок
        </h2>
        <p v-if="!parkingHistory.length" class="operation-empty">История парковок пока пуста.</p>
        <ul v-else class="parking-history">
          <li v-for="item in parkingHistory.slice(0, 3)" :key="item.id" class="parking-item">
            <img
              v-if="item.photoUrl"
              :src="item.photoUrl"
              :alt="`Фотофиксация ${item.vehicle}`"
              class="parking-item__photo"
            />
            <div v-else class="parking-item__photo parking-item__photo--placeholder">Нет фото</div>
            <div class="parking-item__content">
              <strong>{{ item.vehicle }}</strong>
              <span>{{ item.address }}</span>
              <span>{{ item.startedAt }} - {{ item.endedAt }}</span>
            </div>
          </li>
        </ul>
        <button type="button" class="more-link" @click="emit('navigate', 'parkingHistory')">
          Подробнее
          <ChevronRight :size="16" />
        </button>
      </article>

      <article class="profile-card">
        <h2 class="section-title">
          <ReceiptText :size="20" class="section-title__icon" aria-hidden="true" />
          История операций
        </h2>
        <ul class="operation-history">
          <li
            v-for="item in visibleOperationHistory"
            :key="item.id"
            class="operation-item operation-item--clickable"
            @click="selectedOperation = item"
          >
            <div>
              <strong>{{ item.title }}</strong>
              <span class="operation-item__date">{{ item.date }}</span>
            </div>
            <span class="operation-item__amount">{{ item.amount }}</span>
          </li>
        </ul>
        <p v-if="!operationHistory.length" class="operation-empty">История оплат пуста.</p>
        <button
          v-if="operationHistory.length"
          type="button"
          class="more-link"
          @click="emit('navigate', 'operationHistory')"
        >
          Подробнее
          <ChevronRight :size="16" />
        </button>
      </article>

      <article class="profile-card">
        <h2 class="section-title">Избранные парковки</h2>
        <ul v-if="favoriteParkings.length" class="favorite-list">
          <li v-for="item in favoriteParkings" :key="item.id" class="favorite-item">
            <strong>{{ item.name }}</strong>
            <span>{{ item.address }}</span>
            <span>
              Зона: {{ item.zone }} ·
              <template v-if="item.isFree || item.tariffPerHour <= 0">бесплатно</template>
              <template v-else>{{ item.tariffPerHour }} ₽/час</template>
            </span>
            <span>{{ item.schedule }}</span>
          </li>
        </ul>
        <p v-else class="favorite-empty">В избранном пока нет парковок.</p>
      </article>

      <article class="profile-card profile-card--full">
        <h2 class="section-title">
          <Car :size="20" class="section-title__icon" aria-hidden="true" />
          Мой транспорт
        </h2>
        <form class="vehicle-form" @submit.prevent="addVehicle">
          <input
            v-model.trim="vehicleForm.number"
            type="text"
            maxlength="12"
            placeholder="Номер (например А123АА178)"
            required
          />
          <input
            v-model.trim="vehicleForm.model"
            type="text"
            placeholder="Марка и модель"
            required
          />
          <button type="submit">Добавить ТС</button>
        </form>
        <ul class="vehicle-list">
          <li v-for="item in vehicles" :key="item.id" class="vehicle-item">
            <span class="vehicle-item__info">
              <strong>{{ item.number }}</strong> — {{ item.model }}
            </span>
            <button
              type="button"
              class="vehicle-remove"
              @click="removeVehicle(item.id)"
            >
              Удалить
            </button>
          </li>
        </ul>
      </article>
    </div>

    <OperationDetailsModal
      v-if="selectedOperation"
      :operation="selectedOperation"
      @close="selectedOperation = null"
    />
  </section>
</template>

<script setup lang="ts">
import { Camera, Car, ChevronRight, ReceiptText } from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { loginRequest, type AuthOkResponse } from '../api/auth'
import {
  addVehicle as addVehicleApi,
  fetchParkingHistory,
  fetchVehicles,
  type ParkingHistoryItem as ApiHistoryItem,
  type VehicleItem,
} from '../api/parking'
import AccountAuthCard from '../components/AccountAuthCard.vue'
import OperationDetailsModal from '../components/OperationDetailsModal.vue'
import RegisterModal from '../components/RegisterModal.vue'
import { getFavoritesForUser, type FavoriteParking } from '../utils/favorites'

type User = {
  id: string
  login: string
}

type ParkingHistoryItem = {
  id: string
  vehicle: string
  address: string
  startedAt: string
  endedAt: string
  photoUrl: string
}

function mapHistoryItem(item: ApiHistoryItem): ParkingHistoryItem {
  return {
    id: item.id,
    vehicle: item.vehicle,
    address: item.address,
    startedAt: item.started_at,
    endedAt: item.ended_at,
    photoUrl: item.photo_url,
  }
}

type OperationItem = {
  id: string
  title: string
  date: string
  amount: string
}

type Vehicle = {
  id: string
  number: string
  model: string
}

const emit = defineEmits<{
  (e: 'navigate', page: 'parkingHistory'): void
  (e: 'navigate', page: 'operationHistory'): void
  (e: 'auth-changed'): void
}>()

function persistAuth(data: AuthOkResponse) {
  try {
    localStorage.setItem('auth_token', data.token)
    localStorage.setItem('auth_user', JSON.stringify(data.user))
  } catch {
    /* ignore */
  }
}

const authLoading = ref(false)
const authError = ref<string | null>(null)
const currentUser = ref<User | null>(null)

const registerModalOpen = ref(false)
const registerPrefillLogin = ref('')

const parkingHistory = ref<ParkingHistoryItem[]>([])
const profileLoading = ref(false)
const profileError = ref<string | null>(null)

const operationHistory = ref<OperationItem[]>([])
const selectedOperation = ref<OperationItem | null>(null)
const visibleOperationHistory = computed(() => operationHistory.value.slice(0, 3))

const vehicles = ref<Vehicle[]>([])
const favoriteParkings = ref<FavoriteParking[]>([])

const vehicleForm = ref({
  number: '',
  model: '',
})

async function loadProfileData(silent = false) {
  if (!currentUser.value) return
  if (!silent) profileLoading.value = true
  profileError.value = null
  try {
    const [history, vehicleList] = await Promise.all([fetchParkingHistory(), fetchVehicles()])
    parkingHistory.value = history.map(mapHistoryItem)
    vehicles.value = vehicleList.map((v: VehicleItem) => ({
      id: String(v.id),
      number: v.plate_number,
      model: v.model,
    }))
  } catch (e) {
    if (!silent) {
      profileError.value = e instanceof Error ? e.message : 'Не удалось загрузить данные профиля'
    }
  } finally {
    if (!silent) profileLoading.value = false
  }
}

async function handleLogin(payload: { login: string; password: string }) {
  authError.value = null
  authLoading.value = true
  try {
    const data = await loginRequest(payload.login, payload.password)
    persistAuth(data)
    currentUser.value = data.user
    favoriteParkings.value = getFavoritesForUser(data.user.id)
    await loadProfileData()
    emit('auth-changed')
  } catch (e) {
    authError.value = e instanceof Error ? e.message : 'Ошибка входа'
  } finally {
    authLoading.value = false
  }
}

function openRegisterModal(payload: { loginHint: string }) {
  authError.value = null
  registerPrefillLogin.value = payload.loginHint
  registerModalOpen.value = true
}

async function onRegisterSuccess(data: AuthOkResponse) {
  authError.value = null
  registerModalOpen.value = false
  persistAuth(data)
  currentUser.value = data.user
  favoriteParkings.value = getFavoritesForUser(data.user.id)
  await loadProfileData()
  emit('auth-changed')
}

function logout() {
  try {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  } catch {
    /* ignore */
  }
  currentUser.value = null
  favoriteParkings.value = []
  emit('auth-changed')
}

async function addVehicle() {
  profileError.value = null
  try {
    const created = await addVehicleApi(vehicleForm.value.number, vehicleForm.value.model)
    vehicles.value.unshift({
      id: String(created.id),
      number: created.plate_number,
      model: created.model,
    })
    vehicleForm.value.number = ''
    vehicleForm.value.model = ''
  } catch (e) {
    profileError.value = e instanceof Error ? e.message : 'Не удалось добавить ТС'
  }
}

function removeVehicle(id: string) {
  vehicles.value = vehicles.value.filter(item => item.id !== id)
}

let profilePollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const stored = localStorage.getItem('auth_user')
    currentUser.value = stored ? (JSON.parse(stored) as User) : null
    favoriteParkings.value = currentUser.value ? getFavoritesForUser(currentUser.value.id) : []
    if (currentUser.value) await loadProfileData()
  } catch {
    currentUser.value = null
    favoriteParkings.value = []
  }

  profilePollTimer = setInterval(() => {
    if (currentUser.value) void loadProfileData(true)
  }, 5000)
})

onUnmounted(() => {
  if (profilePollTimer) clearInterval(profilePollTimer)
})
</script>

<style scoped>
.page {
  max-width: 1060px;
  margin: 1.5rem auto;
  padding: 0 1rem;
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.profile-header p {
  margin: 0;
}

.profile-error {
  margin: 0.75rem 0 0;
  color: #b91c1c;
}

.profile-loading {
  margin: 0.75rem 0 0;
  color: #64748b;
}

.logout-button {
  border: 1px solid #dc2626;
  border-radius: 8px;
  background: #fff1f2;
  color: #b91c1c;
  padding: 0.45rem 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.profile-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.profile-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  padding: 1rem;
}

.profile-card--full {
  grid-column: 1 / -1;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.section-title__icon {
  flex-shrink: 0;
  color: #3b82f6;
}

.parking-history,
.operation-history,
.vehicle-list,
.favorite-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.favorite-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.92rem;
  color: #334155;
}

.favorite-item:last-child {
  border-bottom: none;
}

.favorite-empty {
  margin: 0;
  color: #64748b;
  font-size: 0.92rem;
}

.parking-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.parking-item:last-child,
.operation-item:last-child {
  border-bottom: none;
}

.parking-item__photo {
  width: 110px;
  height: 72px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
}

.parking-item__photo--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 0.75rem;
}

.parking-item__content {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.9rem;
  color: #334155;
}

.operation-item {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.operation-item--clickable {
  cursor: pointer;
}

.operation-item__date {
  display: block;
  font-size: 0.9rem;
  color: #64748b;
}

.operation-item__amount {
  font-weight: 600;
}

.operation-empty {
  margin: 0;
  color: #64748b;
  font-size: 0.92rem;
}

.more-link {
  margin-top: 0.75rem;
  border: none;
  background: transparent;
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0;
}

.vehicle-form {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.vehicle-form input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0.55rem 0.7rem;
}

.vehicle-form button {
  border: 1px solid #2563eb;
  border-radius: 8px;
  background: #2563eb;
  color: #ffffff;
  padding: 0.55rem 0.9rem;
  font-weight: 600;
  cursor: pointer;
}

.vehicle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.vehicle-item:last-child {
  border-bottom: none;
}

.vehicle-item__info {
  font-size: 0.95rem;
  color: #334155;
}

.vehicle-remove {
  flex-shrink: 0;
  border: 1px solid #dc2626;
  border-radius: 8px;
  background: #fff1f2;
  color: #b91c1c;
  padding: 0.35rem 0.65rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.vehicle-remove:hover {
  background: #fee2e2;
}

@media (max-width: 768px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }

  .profile-card--full {
    grid-column: auto;
  }

  .vehicle-form {
    grid-template-columns: 1fr;
  }
}
</style>
