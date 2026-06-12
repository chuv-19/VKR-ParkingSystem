<template>
  <nav class="navbar">
    <div class="navbar__brand">
      <CircleParking :size="22" class="navbar__logo" aria-hidden="true" />
      <span>Parking App</span>
    </div>
    <ul class="navbar__links">
      <li>
        <button
          class="nav-link"
          :class="{ active: currentPage === 'map' }"
          @click="$emit('navigate', 'map')"
        >
          <MapPinned :size="18" class="ui-icon" aria-hidden="true" />
          <span>Карта</span>
        </button>
      </li>
      <li>
        <button
          class="nav-link"
          :class="{ active: currentPage === 'profile' }"
          @click="$emit('navigate', 'profile')"
        >
          <UserRound :size="18" class="ui-icon" aria-hidden="true" />
          <span>Профиль</span>
        </button>
      </li>
      <li v-if="isAuthorized">
        <button
          class="nav-link nav-link--icon"
          :class="{ active: currentPage === 'parking' }"
          @click="$emit('navigate', 'parking')"
          aria-label="Уведомления"
          title="Уведомления"
        >
          <Bell :size="18" class="ui-icon" aria-hidden="true" />
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup lang="ts">
import { Bell, CircleParking, MapPinned, UserRound } from 'lucide-vue-next'

defineProps<{
  currentPage: 'map' | 'parking' | 'profile' | 'parkingHistory' | 'operationHistory'
  isAuthorized: boolean
}>()

defineEmits<{
  (e: 'navigate', page: 'map' | 'parking' | 'profile' | 'parkingHistory' | 'operationHistory'): void
}>()
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e5e5;
  background-color: #ffffff;
}

.navbar__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}

.navbar__logo {
  flex-shrink: 0;
  color: #2563eb;
}

.navbar__links {
  display: flex;
  gap: 1rem;
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.95rem;
  color: #555;
}

.nav-link {
  border: none;
  background: transparent;
  padding: 0.35rem 0.65rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.nav-link .ui-icon {
  flex-shrink: 0;
}

.nav-link--icon {
  padding: 0.35rem;
}

.nav-link.active {
  background-color: #2563eb;
  color: #ffffff;
}

.nav-link.active .ui-icon {
  color: #ffffff;
}
</style>

