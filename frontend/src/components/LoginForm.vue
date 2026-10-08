<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, login, register, requestPasswordReset, resetPassword } from '@/services/auth'
import type { User, UserRole } from '@/types'

type Mode = 'login' | 'register' | 'forgot' | 'reset'
type FormRef = { validate: () => Promise<{ valid: boolean }>; resetValidation: () => void }
const emit = defineEmits<{ authenticated: [user: User] }>()
const query = new URLSearchParams(location.search)
const mode = ref<Mode>(query.has('reset_token') ? 'reset' : query.get('recover') === '1' ? 'forgot' : 'login')
const token = query.get('reset_token') ?? ''
const form = ref<FormRef | null>(null)
const username = ref('')
const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const role = ref<Exclude<UserRole, 'ADMINISTRADOR'>>('RECEPCIONISTA')
const showPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const required = [(value: string) => !!value || 'Este campo es obligatorio.']
const usernameRules = [...required, (value: string) => value.length >= 3 || 'Mínimo 3 caracteres.', (value: string) => /^[a-zA-Z0-9_.-]+$/.test(value) || 'Solo usa letras, números, punto, guion o guion bajo.']
const emailRules = [...required, (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) || 'Correo no válido.']
const passwordRules = [...required, (value: string) => value.length >= 8 || 'Mínimo 8 caracteres.']
const title = computed(() => ({ login: 'Iniciar sesión', register: 'Crear cuenta', forgot: 'Recuperar cuenta', reset: 'Nueva contraseña' }[mode.value]))
const subtitle = computed(() => ({ login: 'Ingresa tus datos para continuar.', register: 'Registra tus datos para acceder al sistema.', forgot: 'Escribe tu correo y te enviaremos un enlace.', reset: 'Define una nueva contraseña para tu cuenta.' }[mode.value]))

function changeMode(next: Exclude<Mode, 'reset'>): void {
  mode.value = next
  errorMessage.value = ''
  successMessage.value = ''
  password.value = ''
  confirmPassword.value = ''
  form.value?.resetValidation()
}

async function submit(): Promise<void> {
  if (!(await form.value?.validate())?.valid) return
  if ((mode.value === 'register' || mode.value === 'reset') && password.value !== confirmPassword.value) {
    errorMessage.value = 'Las contraseñas no coinciden.'
    return
  }
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (mode.value === 'login') {
      emit('authenticated', (await login(username.value.trim(), password.value)).user)
    } else if (mode.value === 'register') {
      await register(username.value.trim(), fullName.value.trim(), email.value.trim(), password.value, role.value)
      successMessage.value = 'Cuenta creada correctamente. Ya puedes iniciar sesión.'
      mode.value = 'login'
      password.value = ''
      confirmPassword.value = ''
    } else if (mode.value === 'forgot') {
      successMessage.value = (await requestPasswordReset(email.value.trim())).message
    } else {
      await resetPassword(token, password.value)
      history.replaceState({}, '', location.pathname)
      mode.value = 'login'
      password.value = ''
      successMessage.value = 'Contraseña actualizada. Ya puedes iniciar sesión.'
    }
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'No se pudo conectar con el servidor.'
  } finally { loading.value = false }
}
</script>

<template>
  <section class="auth-layout">
    <div class="brand-panel"><div class="brand-content"><v-icon icon="mdi-car-wrench" size="64" class="mb-6" /><p class="eyebrow">PLATAFORMA DE GESTIÓN</p><h1>Tu taller, siempre bajo control.</h1><p class="brand-copy">Accede de manera segura a las herramientas que mantienen tu operación en movimiento.</p></div></div>
    <div class="form-panel"><v-card class="login-card" elevation="0"><v-card-text class="pa-0">
      <div class="mobile-mark"><v-icon icon="mdi-car-wrench" size="36" /></div>
      <p class="eyebrow text-secondary">ACCESO AL SISTEMA</p><h2>{{ title }}</h2><p class="subtitle">{{ subtitle }}</p>
      <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">{{ errorMessage }}</v-alert>
      <v-alert v-if="successMessage" type="success" variant="tonal" class="mb-4">{{ successMessage }}</v-alert>
      <v-form ref="form" validate-on="submit" @submit.prevent="submit">
        <v-text-field v-if="mode === 'login' || mode === 'register'" v-model="username" label="Usuario" autocomplete="username" :rules="usernameRules" prepend-inner-icon="mdi-account-outline" variant="outlined" color="secondary" />
        <v-text-field v-if="mode === 'register'" v-model="fullName" label="Nombre completo" autocomplete="name" :rules="required" prepend-inner-icon="mdi-card-account-details-outline" variant="outlined" color="secondary" />
        <v-text-field v-if="mode === 'register' || mode === 'forgot'" v-model="email" label="Correo electrónico" type="email" autocomplete="email" :rules="emailRules" prepend-inner-icon="mdi-email-outline" variant="outlined" color="secondary" />
        <v-select v-if="mode === 'register'" v-model="role" label="Rol" :items="[{ title: 'Recepcionista', value: 'RECEPCIONISTA' }, { title: 'Mecánico', value: 'MECANICO' }]" variant="outlined" color="secondary" />
        <v-text-field v-if="mode !== 'forgot'" v-model="password" :label="mode === 'reset' ? 'Nueva contraseña' : 'Contraseña'" :type="showPassword ? 'text' : 'password'" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" :rules="passwordRules" prepend-inner-icon="mdi-lock-outline" :append-inner-icon="showPassword ? 'mdi-eye-off-outline' : 'mdi-eye-outline'" variant="outlined" color="secondary" @click:append-inner="showPassword = !showPassword" />
        <v-text-field v-if="mode === 'register' || mode === 'reset'" v-model="confirmPassword" label="Confirmar contraseña" type="password" autocomplete="new-password" :rules="passwordRules" variant="outlined" color="secondary" />
        <v-btn type="submit" block size="large" color="secondary" :loading="loading" class="mt-2 login-button">{{ mode === 'login' ? 'Entrar al sistema' : mode === 'register' ? 'Crear cuenta' : mode === 'forgot' ? 'Enviar enlace' : 'Guardar contraseña' }}</v-btn>
      </v-form>
      <div class="auth-links"><template v-if="mode === 'login'"><button type="button" @click="changeMode('register')">Crear cuenta</button><button type="button" @click="changeMode('forgot')">¿Olvidaste tu contraseña?</button></template><button v-else type="button" @click="changeMode('login')">Volver a iniciar sesión</button></div>
      <p class="security-note"><v-icon icon="mdi-shield-check-outline" size="17" /> Acceso protegido y sesión única por usuario</p>
    </v-card-text></v-card></div>
  </section>
</template>
