<template>
  <section class="page">
    <button type="button" class="back-link" @click="emit('navigate', 'profile')">
      <ChevronLeft :size="16" />
      В профиль
    </button>
    <h1>История оплат</h1>
    <p class="subtitle">Полный журнал операций по оплате парковки.</p>

    <ul v-if="operationHistory.length" class="history-list">
      <li v-for="item in operationHistory" :key="item.id" class="history-item">
        <div>
          <strong>{{ item.title }}</strong>
          <span class="history-item__date">{{ item.date }}</span>
        </div>
        <span class="history-item__amount">{{ item.amount }}</span>
      </li>
    </ul>
    <p v-else class="empty-state">История оплат пуста.</p>
  </section>
</template>

<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { ref } from 'vue'

type OperationItem = {
  id: string
  title: string
  date: string
  amount: string
}

const emit = defineEmits<{
  (e: 'navigate', page: 'profile'): void
}>()

const operationHistory = ref<OperationItem[]>([])
</script>

<style scoped>
.page {
  max-width: 960px;
  margin: 1.5rem auto;
  padding: 0 1rem;
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

.subtitle {
  margin: 0 0 1rem;
  color: #64748b;
}

.empty-state {
  margin: 0;
  color: #64748b;
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.history-item {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.history-item:last-child {
  border-bottom: none;
}

.history-item__date {
  display: block;
  margin-top: 0.2rem;
  font-size: 0.9rem;
  color: #64748b;
}

.history-item__amount {
  font-weight: 600;
}
</style>
