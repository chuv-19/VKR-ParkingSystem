<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal">
      <button type="button" class="modal__close" aria-label="Закрыть" @click="$emit('close')">
        <X :size="20" />
      </button>
      <h2>{{ operation.title }}</h2>
      <p class="row"><strong>Дата:</strong> {{ operation.date }}</p>
      <p class="row"><strong>Сумма:</strong> {{ operation.amount }}</p>
      <p class="row"><strong>Статус:</strong> Успешно</p>
      <p class="row"><strong>Способ оплаты:</strong> Банковская карта</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { X } from 'lucide-vue-next'

type OperationItem = {
  id: string
  title: string
  date: string
  amount: string
}

defineProps<{
  operation: OperationItem
}>()

defineEmits<{
  (e: 'close'): void
}>()
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal {
  position: relative;
  background: #ffffff;
  border-radius: 12px;
  padding: 1.5rem;
  padding-top: 2.75rem;
  width: min(420px, 100vw - 2rem);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
}

.modal__close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: none;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  cursor: pointer;
}

.row {
  margin: 0.45rem 0;
  color: #334155;
}
</style>
