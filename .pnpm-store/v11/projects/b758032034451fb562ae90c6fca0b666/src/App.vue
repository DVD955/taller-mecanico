<script setup lang="ts">
import { onMounted, ref } from 'vue'
import LoginForm from '@/components/LoginForm.vue'
import DashboardView from '@/components/DashboardView.vue'
import { ApiError, getCurrentUser, logout } from '@/services/auth'
import type { User } from '@/types'

const user = ref<User | null>(null)
const loadingSession = ref(true)

onMounted(async () => {
  try { user.value = await getCurrentUser() }
  catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) console.error(error)
  } finally { loadingSession.value = false }
})

async function handleLogout(): Promise<void> {
  await logout()
  user.value = null
}
</script>

<template>
  <v-app>
    <v-main>
      <div v-if="loadingSession" class="loading-screen"><v-progress-circular indeterminate color="secondary" /></div>
      <DashboardView v-else-if="user" :user="user" @logout="handleLogout" @updated="user = $event" />
      <LoginForm v-else @authenticated="user = $event" />
    </v-main>
  </v-app>
</template>
