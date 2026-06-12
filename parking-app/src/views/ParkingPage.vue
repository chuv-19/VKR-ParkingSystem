<template>
  <section class="page">
    <h1>Уведомления</h1>
    <p v-if="!isAuthorized">Уведомления доступны только зарегистрированным пользователям.</p>
    <template v-else>
      <p v-if="loading" class="status">Загрузка уведомлений…</p>
      <p v-else-if="error" class="status status--error">{{ error }}</p>
      <p v-else-if="!notifications.length" class="status">
        Пока нет уведомлений. Они появятся после фиксации вашего автомобиля на парковке.
      </p>
      <ul v-else class="notifications">
        <li
          v-for="item in notifications"
          :key="item.id"
          class="notification"
          :class="`notification--${item.level}`"
        >
          <div class="notification__header">
            <strong>{{ item.plate_number }}</strong>
            <time>{{ formatDate(item.created_at) }}</time>
          </div>
          <p class="notification__message">{{ item.message }}</p>
        </li>
      </ul>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { fetchNotifications, type NotificationItem } from '../api/parking'

const props = defineProps<{
  isAuthorized?: boolean
}>()

const notifications = ref<NotificationItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return iso
  }
}

async function loadNotifications() {
  if (!props.isAuthorized) return
  loading.value = notifications.value.length === 0
  error.value = null
  try {
    notifications.value = await fetchNotifications()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить уведомления'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadNotifications()
  pollTimer = setInterval(() => void loadNotifications(), 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

watch(
  () => props.isAuthorized,
  authorized => {
    if (authorized) void loadNotifications()
    else notifications.value = []
  },
)
</script>

<style scoped>
.page {
  max-width: 960px;
  margin: 1.5rem auto;
  padding: 0 1rem;
}

h1 {
  margin-bottom: 0.5rem;
}

.status {
  color: #64748b;
}

.status--error {
  color: #b91c1c;
}

.notifications {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.notification {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  background: #fff;
}

.notification--warning {
  border-color: #fcd34d;
  background: #fffbeb;
}

.notification--critical {
  border-color: #fca5a5;
  background: #fef2f2;
}

.notification__header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
  font-size: 0.9rem;
}

.notification__header time {
  color: #64748b;
  white-space: nowrap;
}

.notification__message {
  margin: 0;
  color: #334155;
  line-height: 1.45;
}
</style>
