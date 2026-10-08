<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, register, updateEmail } from '@/services/auth'
import type { User, UserRole } from '@/types'
import CustomerManagement from '@/components/CustomerManagement.vue'

const props = defineProps<{ user: User }>()
const emit = defineEmits<{ logout: []; updated: [user: User] }>()
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const username = ref('')
const fullName = ref('')
const email = ref('')
const password = ref('')
const role = ref<Exclude<UserRole, 'ADMINISTRADOR'>>('RECEPCIONISTA')
const ownEmail = ref(props.user.email ?? '')
const busy = ref(false)
const message = ref('')
const errorMessage = ref('')
const required = [(value: string) => !!value || 'Este campo es obligatorio.']
const emailRules = [...required, (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) || 'Correo no válido.']
const passwordRules = [...required, (value: string) => value.length >= 8 || 'Mínimo 8 caracteres.']

async function createAccount(): Promise<void> {
  if (!(await form.value?.validate())?.valid) return
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const created = await register(username.value.trim(), fullName.value.trim(), email.value.trim(), password.value, role.value)
    message.value = `Cuenta ${created.username} creada como ${created.role}.`
    username.value = ''; fullName.value = ''; email.value = ''; password.value = ''
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'No se pudo crear la cuenta.'
  } finally { busy.value = false }
}

async function saveEmail(): Promise<void> {
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    emit('updated', await updateEmail(ownEmail.value.trim()))
    message.value = 'Correo de recuperación actualizado.'
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'No se pudo actualizar el correo.'
  } finally { busy.value = false }
}
</script>

<template>
  <div class="dashboard">
    <header class="dashboard-header"><div class="dashboard-logo"><v-icon icon="mdi-car-wrench" /> <strong>Taller Mecánico</strong></div><v-btn variant="text" color="secondary" prepend-icon="mdi-logout" @click="$emit('logout')">Cerrar sesión</v-btn></header>
    <main class="dashboard-content">
      <p class="eyebrow text-secondary">SESIÓN ACTIVA</p><h1>Hola, {{ user.full_name }}</h1>
      <p class="subtitle">Has iniciado sesión correctamente.</p>
      <v-card class="profile-card" elevation="0"><v-card-text>
        <div class="profile-icon"><v-icon icon="mdi-account-check-outline" size="34" /></div>
        <div><p class="profile-label">USUARIO</p><strong>{{ user.username }}</strong></div><v-divider vertical class="mx-5" />
        <div><p class="profile-label">ROL</p><strong>{{ user.role }}</strong></div><v-divider vertical class="mx-5" />
        <div><p class="profile-label">ESTADO</p><v-chip color="success" size="small">{{ user.status }}</v-chip></div>
      </v-card-text></v-card>
      <v-alert v-if="message" type="success" variant="tonal" class="mt-6">{{ message }}</v-alert>
      <v-alert v-if="errorMessage" type="error" variant="tonal" class="mt-6">{{ errorMessage }}</v-alert>
      <CustomerManagement v-if="user.role === 'ADMINISTRADOR' || user.role === 'RECEPCIONISTA'" />
      <v-card class="profile-card" elevation="0"><v-card-text class="d-block">
        <h2>Correo de recuperación</h2><p class="subtitle">Usaremos este correo para enviarte un enlace si olvidas tu contraseña.</p>
        <v-text-field v-model="ownEmail" label="Tu correo electrónico" type="email" autocomplete="email" :rules="emailRules" variant="outlined" color="secondary" />
        <v-btn color="secondary" :loading="busy" @click="saveEmail">Guardar correo</v-btn>
      </v-card-text></v-card>
      <v-card v-if="user.role === 'ADMINISTRADOR'" class="profile-card" elevation="0"><v-card-text class="d-block">
        <h2>Crear cuenta de personal</h2><p class="subtitle">Solo los administradores pueden dar de alta usuarios.</p>
        <v-form ref="form" validate-on="submit" @submit.prevent="createAccount">
          <v-text-field v-model="username" label="Usuario" :rules="required" variant="outlined" color="secondary" />
          <v-text-field v-model="fullName" label="Nombre completo" :rules="required" variant="outlined" color="secondary" />
          <v-text-field v-model="email" label="Correo electrónico" type="email" :rules="emailRules" variant="outlined" color="secondary" />
          <v-select v-model="role" label="Rol" :items="[{ title: 'Recepcionista', value: 'RECEPCIONISTA' }, { title: 'Mecánico', value: 'MECANICO' }]" variant="outlined" color="secondary" />
          <v-text-field v-model="password" label="Contraseña inicial" type="password" :rules="passwordRules" variant="outlined" color="secondary" />
          <v-btn type="submit" color="secondary" :loading="busy">Crear cuenta</v-btn>
        </v-form>
      </v-card-text></v-card>
    </main>
  </div>
</template>
