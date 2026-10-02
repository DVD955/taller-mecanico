<script setup lang="ts">
import type { User } from '@/types'
defineProps<{ user: User }>()
defineEmits<{ logout: [] }>()
</script>

<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="dashboard-logo"><v-icon icon="mdi-car-wrench" /> <strong>Taller Mecánico</strong></div>
      <v-btn variant="text" color="secondary" prepend-icon="mdi-logout" @click="$emit('logout')">Cerrar sesión</v-btn>
    </header>
    <main class="dashboard-content">
      <p class="eyebrow text-secondary">SESIÓN ACTIVA</p>
      <h1>Hola, {{ user.full_name }}</h1>
      <p class="subtitle">Has iniciado sesión correctamente. El módulo de gestión estará disponible aquí.</p>
      <v-card class="profile-card" elevation="0">
        <v-card-text>
          <div class="profile-icon"><v-icon icon="mdi-account-check-outline" size="34" /></div>
          <div><p class="profile-label">USUARIO</p><strong>{{ user.username }}</strong></div>
          <v-divider vertical class="mx-5" />
          <div><p class="profile-label">ROL</p><strong>{{ user.role }}</strong></div>
          <v-divider vertical class="mx-5" />
          <div><p class="profile-label">ESTADO</p><v-chip color="success" size="small">{{ user.status }}</v-chip></div>
        </v-card-text>
      </v-card>
    </main>
  </div>
</template>
