<template>
  <div class="filters">
    <div class="filters__field">
      <Search class="filters__field-icon" :size="18" aria-hidden="true" />
      <input
        v-model="localFilters.query"
        type="search"
        placeholder="Поиск по адресу или названию"
        class="filters__search"
        autocomplete="off"
      />
    </div>

    <label class="filters__checkbox">
      <CircleParkingOff :size="18" class="filters__checkbox-icon" aria-hidden="true" />
      <input
        v-model="localFilters.onlyFree"
        type="checkbox"
      />
      Только бесплатные
    </label>
  </div>
</template>

<script setup lang="ts">
import { CircleParkingOff, Search } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import type { ParkingFilters } from '../types/parking'

const props = defineProps<{
  filters: ParkingFilters
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: ParkingFilters): void
}>()

const localFilters = ref<ParkingFilters>({ ...props.filters })

watch(
  localFilters,
  value => {
    emit('update:filters', value)
  },
  { deep: true }
)
</script>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.filters__field {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #fff;
}

.filters__field:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.filters__field-icon {
  flex-shrink: 0;
  color: #64748b;
}

.filters__search {
  flex: 1;
  min-width: 0;
  border: none;
  padding: 0.2rem 0;
  font-size: 0.95rem;
  background: transparent;
  outline: none;
}

.filters__checkbox {
  font-size: 0.85rem;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.filters__checkbox-icon {
  flex-shrink: 0;
  color: #64748b;
}
</style>

