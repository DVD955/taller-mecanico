<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { ApiError, updateEmail } from '@/services/auth'
import type { User } from '@/types'
import CustomerManagement from '@/components/CustomerManagement.vue'
import RoleManagement from '@/components/RoleManagement.vue'
import RoleCreation from '@/components/RoleCreation.vue'
import WorkshopManagement from '@/components/WorkshopManagement.vue'

const props = defineProps<{ user: User }>()
const emit = defineEmits<{ logout: []; updated: [user: User] }>()
const canManage = computed(() => ['ADMINISTRADOR', 'RECEPCIONISTA'].includes(props.user.role))
type WorkspaceView = 'customers' | 'workshops' | 'create-role' | 'roles' | 'profile'
const view = ref<WorkspaceView>(canManage.value ? 'customers' : 'profile')
const modules = computed(() => {
  const items: { value: WorkspaceView; title: string; icon: string }[] = []
  if (canManage.value) items.push({ value: 'customers', title: 'Administración de clientes', icon: 'mdi-account-group-outline' }, { value: 'workshops', title: 'Administración de talleres', icon: 'mdi-garage-variant' })
  if (props.user.role === 'ADMINISTRADOR') items.push({ value: 'create-role', title: 'Crear rol', icon: 'mdi-shield-plus-outline' }, { value: 'roles', title: 'Administrar roles', icon: 'mdi-shield-account-outline' })
  items.push({ value: 'profile', title: 'Mi cuenta', icon: 'mdi-account-circle-outline' })
  return items
})
const ownEmail = ref(props.user.email ?? '')
const initials = computed(() => props.user.full_name.split(' ').filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase())
const busy = ref(false)
const message = ref('')
const errorMessage = ref('')
const emailRules = [(value: string) => !!value || 'Este campo es obligatorio.', (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) || 'Correo no válido.']

async function navigate(event: KeyboardEvent): Promise<void> {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const items = modules.value
  const current = items.findIndex(item => item.value === view.value)
  const index = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (current + (event.key === 'ArrowRight' ? 1 : -1) + items.length) % items.length
  const target = items[index]
  if (!target) return
  view.value = target.value
  await nextTick()
  document.getElementById(`module-${target.value}`)?.focus()
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
    <header class="dashboard-header"><div class="dashboard-header-inner"><div class="dashboard-logo"><span class="brand-monogram"><v-icon icon="mdi-car-wrench" size="24" /></span><div><strong>Taller Mecánico</strong><span>PLATAFORMA DE GESTIÓN</span></div></div><div class="dashboard-header-actions"><span class="header-session"><v-icon icon="mdi-shield-check-outline" size="16" /> Sesión protegida</span><v-btn variant="outlined" color="primary" prepend-icon="mdi-logout" @click="$emit('logout')">Cerrar sesión</v-btn></div></div></header>
    <main class="dashboard-content">
      <div class="workspace-welcome"><div><p class="eyebrow">TU ESPACIO DE TRABAJO</p><h1>Hola, {{ user.full_name }}</h1><p>{{ canManage ? 'Gestiona la información de tu taller desde un solo lugar.' : 'Consulta tu cuenta y mantén tus datos actualizados.' }}</p></div><span class="session-indicator"><span aria-hidden="true"></span> Sesión activa</span></div>
      <div class="workspace-identity"><span class="identity-avatar" aria-hidden="true">{{ initials }}</span><dl><div><dt>Usuario</dt><dd>{{ user.username }}</dd></div><div><dt>Rol</dt><dd>{{ user.role_name }}</dd></div><div><dt>Estado</dt><dd><v-chip color="secondary" variant="tonal" size="small">{{ user.status }}</v-chip></dd></div></dl></div>
      <v-alert v-if="message" type="success" variant="tonal" class="mt-6">{{ message }}</v-alert>
      <v-alert v-if="errorMessage" type="error" variant="tonal" class="mt-6">{{ errorMessage }}</v-alert>
      <v-alert v-if="user.role === 'INVITADO'" color="secondary" variant="tonal" class="mt-6">Tu cuenta es Invitado. El administrador puede asignarte un rol de personal.</v-alert>
      <nav class="workspace-navigation" aria-label="Módulos del sistema"><div class="dashboard-tabs" role="tablist" aria-label="Seleccionar módulo"><v-btn v-for="item in modules" :id="`module-${item.value}`" :key="item.value" role="tab" class="workspace-tab" :class="{ 'workspace-tab-selected': view === item.value }" :aria-selected="view === item.value" aria-controls="workspace-content" :tabindex="view === item.value ? 0 : -1" variant="text" @click="view = item.value" @keydown="navigate"><v-icon :icon="item.icon" start /><span>{{ item.title }}</span></v-btn></div></nav>
      <div id="workspace-content" role="tabpanel" :aria-labelledby="`module-${view}`">
      <CustomerManagement v-if="canManage && view === 'customers'" />
      <WorkshopManagement v-if="canManage && view === 'workshops'" />
      <RoleCreation v-if="user.role === 'ADMINISTRADOR' && view === 'create-role'" @manage="view = 'roles'" />
      <RoleManagement v-if="user.role === 'ADMINISTRADOR' && view === 'roles'" />
      <v-card v-if="view === 'profile'" class="profile-card account-settings" elevation="0"><v-card-text class="d-block">
        <p class="eyebrow">DATOS DE TU CUENTA</p><h2>Correo de recuperación</h2><p class="subtitle">Usaremos este correo para enviarte un enlace si olvidas tu contraseña.</p>
        <v-text-field v-model="ownEmail" label="Tu correo electrónico" type="email" autocomplete="email" :rules="emailRules" variant="outlined" color="secondary" />
        <v-btn color="secondary" :loading="busy" @click="saveEmail">Guardar correo</v-btn>
      </v-card-text></v-card>
      </div>
    </main>
  </div>
</template>
