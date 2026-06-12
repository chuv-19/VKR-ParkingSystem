<template>
  <div class="parking-list">
    <div
      v-for="parking in parkings"
      :key="parking.id"
      class="parking-list-item"
      :class="{ active: parking.id === selectedParkingId }"
      @click="$emit('selectParking', parking.id)"
    >
      <h3 class="title-row">
        <MapPin :size="16" class="title-icon" aria-hidden="true" />
        <span>{{ parking.name }}</span>
      </h3>
      <p class="address">{{ parking.address }}</p>
      <p class="tariff">
        <RussianRuble :size="15" class="tariff-icon" aria-hidden="true" />
        <span v-if="parking.isFree || parking.tariffPerHour <= 0">Бесплатно</span>
        <span v-else>{{ parking.tariffPerHour }} ₽/час</span>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { MapPin, RussianRuble } from 'lucide-vue-next'
import type { Parking } from '../types/parking'

const props = defineProps<{
  parkings: Parking[]
  selectedParkingId: string | null
}>()

const emit = defineEmits<{
  (e: 'selectParking', id: string): void
}>()
</script>

<style scoped>
.parking-list {
  max-height: 320px;
  overflow-y: auto;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background-color: #ffffff;
}

.parking-list-item {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
}

.parking-list-item:last-child {
  border-bottom: none;
}

.parking-list-item.active {
  background-color: #eff6ff;
}

.title-row {
  display: flex;
  align-items: flex-start;
  gap: 0.35rem;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.3;
}

.title-icon {
  flex-shrink: 0;
  color: #3b82f6;
  margin-top: 2px;
}

.address {
  font-size: 0.85rem;
  color: #6b7280;
}

.tariff {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: #111827;
  margin-top: 0.25rem;
}

.tariff-icon {
  flex-shrink: 0;
  color: #64748b;
}
</style>

