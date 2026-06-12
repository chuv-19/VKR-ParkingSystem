<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal">
      <button type="button" class="modal__close" aria-label="Закрыть" @click="$emit('close')">
        <X :size="20" />
      </button>
      <h2>{{ parking.name }}</h2>
      <p class="row">
        <MapPinned :size="16" class="row-icon" aria-hidden="true" />
        <span class="address">{{ parking.address }}</span>
      </p>
      <p class="row">
        <CircleParking :size="16" class="row-icon" aria-hidden="true" />
        <span>Зона: {{ parking.zone }}</span>
      </p>
      <p class="row">
        <RussianRuble :size="16" class="row-icon" aria-hidden="true" />
        <span>
          Тариф:
          <template v-if="parking.isFree || parking.tariffPerHour <= 0">бесплатно</template>
          <template v-else>{{ parking.tariffPerHour }} ₽/час</template>
        </span>
      </p>
      <p class="row">
        <Clock :size="16" class="row-icon" aria-hidden="true" />
        <span>{{ parking.schedule }}</span>
      </p>

      <div class="actions">
        <button
          type="button"
          class="btn primary"
          :class="{ 'btn--disabled': !allowFavorite }"
          :disabled="!allowFavorite"
          @click="$emit('toggleFavorite', parking.id)"
        >
          <Star :size="16" aria-hidden="true" />
          В избранное
        </button>
        <button type="button" class="btn" @click="$emit('close')">
          Закрыть
        </button>
      </div>
      <p v-if="!allowFavorite" class="auth-hint">Только авторизованные пользователи могут добавлять в избранное.</p>
      <p v-if="favoriteStatusMessage" class="status-hint">{{ favoriteStatusMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleParking, Clock, MapPinned, RussianRuble, Star, X } from 'lucide-vue-next'
import type { Parking } from '../types/parking'

const props = defineProps<{
  parking: Parking
  allowFavorite: boolean
  favoriteStatusMessage: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'toggleFavorite', id: string): void
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
  /* Выше панелей карты (слои, попапы ~400–700) */
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

.modal__close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0.35rem 0;
  font-size: 0.9rem;
  color: #334155;
}

.row-icon {
  flex-shrink: 0;
  color: #64748b;
  margin-top: 2px;
}

.address {
  color: #6b7280;
}

.actions {
  margin-top: 1.25rem;
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  font-size: 0.9rem;
  cursor: pointer;
}

.btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.btn--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-hint,
.status-hint {
  margin: 0.75rem 0 0;
  font-size: 0.85rem;
  color: #64748b;
}
</style>

