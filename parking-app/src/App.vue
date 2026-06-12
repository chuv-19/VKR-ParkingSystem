<script setup lang="ts">
import { computed, ref } from 'vue'
import Navbar from './components/Navbar.vue'
import MapPage from './views/MapPage.vue'
import OperationHistoryPage from './views/OperationHistoryPage.vue'
import ParkingPage from './views/ParkingPage.vue'
import ParkingHistoryPage from './views/ParkingHistoryPage.vue'
import ProfilePage from './views/ProfilePage.vue'

type Page = 'map' | 'parking' | 'profile' | 'parkingHistory' | 'operationHistory'

const currentPage = ref<Page>('map')
const isAuthorized = ref(false)

function syncAuthState() {
  try {
    const raw = localStorage.getItem('auth_user')
    isAuthorized.value = !!raw
  } catch {
    isAuthorized.value = false
  }
}

syncAuthState()

const CurrentView = computed(() => {
  if (currentPage.value === 'operationHistory') return OperationHistoryPage
  if (currentPage.value === 'parkingHistory') return ParkingHistoryPage
  if (currentPage.value === 'parking') return ParkingPage
  if (currentPage.value === 'profile') return ProfilePage
  return MapPage
})

const currentViewProps = computed(() => {
  if (currentPage.value === 'parking') {
    return { isAuthorized: isAuthorized.value }
  }
  return {}
})

function handleNavigate(page: Page) {
  syncAuthState()
  if (page === 'parking' && !isAuthorized.value) {
    currentPage.value = 'profile'
    return
  }
  currentPage.value = page
}

function handleAuthChanged() {
  syncAuthState()
}
</script>

<template>
  <div id="app-root">
    <Navbar
      :currentPage="currentPage"
      :is-authorized="isAuthorized"
      @navigate="handleNavigate"
    />
    <main>
      <component :is="CurrentView" v-bind="currentViewProps" @navigate="handleNavigate" @auth-changed="handleAuthChanged" />
    </main>
  </div>
</template>
