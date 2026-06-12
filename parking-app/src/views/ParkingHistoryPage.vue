<template>
  <section class="page">
    <button type="button" class="back-link" @click="emit('navigate', 'profile')">
      <ChevronLeft :size="16" />
      В профиль
    </button>
    <h1>История парковок</h1>
    <p class="subtitle">Детальная информация о ваших парковочных сессиях.</p>

    <p v-if="loading" class="status">Загрузка истории…</p>
    <p v-else-if="error" class="status status--error">{{ error }}</p>
    <p v-else-if="!parkingHistory.length" class="status">История парковок пока пуста.</p>

    <ul v-else class="history-list">
      <li v-for="item in parkingHistory" :key="item.id" class="history-item">
        <img
          v-if="item.photo_url"
          :src="item.photo_url"
          :alt="`Парковка ${item.vehicle}`"
          class="history-item__photo"
        />
        <div v-else class="history-item__photo history-item__photo--placeholder">Нет фото</div>
        <div class="history-item__content">
          <strong>{{ item.vehicle }}</strong>
          <span>{{ item.address }}</span>
          <span>Место №{{ item.parking_slot }}</span>
          <span>{{ item.started_at }} — {{ item.ended_at }}</span>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { onMounted, onUnmounted, ref } from 'vue'
import { fetchParkingHistory, type ParkingHistoryItem } from '../api/parking'

const parkingHistory = ref<ParkingHistoryItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const emit = defineEmits<{
  (e: 'navigate', page: 'profile'): void
}>()

let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadHistory(silent = false) {
  if (!silent) loading.value = true
  error.value = null
  try {
    parkingHistory.value = await fetchParkingHistory()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить историю'
  } finally {
    if (!silent) loading.value = false
  }
}

onMounted(() => {
  void loadHistory()
  pollTimer = setInterval(() => void loadHistory(true), 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.page {
  max-width: 960px;
  margin: 1.5rem auto;
  padding: 0 1rem;
}

.subtitle {
  margin: 0 0 1rem;
  color: #64748b;
}

.status {
  color: #64748b;
}

.status--error {
  color: #b91c1c;
}

.back-link {
  border: none;
  background: transparent;
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  margin-bottom: 0.5rem;
  padding: 0;
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.history-item {
  display: flex;
  gap: 0.85rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.history-item:last-child {
  border-bottom: none;
}

.history-item__photo {
  width: 130px;
  height: 84px;
  object-fit: cover;
  border-radius: 10px;
  flex-shrink: 0;
}

.history-item__photo--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 0.8rem;
}

.history-item__content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  color: #334155;
  font-size: 0.92rem;
}
</style>
