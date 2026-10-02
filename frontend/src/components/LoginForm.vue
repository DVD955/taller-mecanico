<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, login, register, resetPassword } from '@/services/auth'
import type { User, UserRole } from '@/types'

type View = 'login' | 'register' | 'recover'
type FormValidation = { valid: boolean }
type FormRef = { validate: () => Promise<FormValidation>; resetValidation: () => void }
const emit = defineEmits<{ authenticated: [user: User] }>()
const view = ref<View>('login')
const form = ref<FormRef | null>(null)
const username = ref('')
const fullName = ref('')
const password = ref('')
const confirmPassword = ref('')
const role = ref<Exclude<UserRole, 'ADMINISTRADOR'>>('RECEPCIONISTA')
const recoveryCode = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const generatedCode = ref('')

const usernameRules = [(value: string) => !!value || 'El usuario es obligatorio.', (value: string) => value.length >= 3 || 'Mínimo 3 caracteres.', (value: string) => /^[a-zA-Z0-9_.-]+$/.test(value) || 'Solo usa letras, números, punto, guion o guion bajo.']
const requiredRules = [(value: string) => !!value || 'Este campo es obligatorio.']
const passwordRules = [(value: string) => !!value || 'La contraseña es obligatoria.', (value: string) => value.length >= 8 || 'Mínimo 8 caracteres.']
const confirmRules = [...passwordRules, (value: string) => value === password.value || 'Las contraseñas no coinciden.']
const roleOptions = [{ title: 'Recepcionista', value: 'RECEPCIONISTA' }, { title: 'Mecánico', value: 'MECANICO' }]
const title = computed(() => ({ login: 'Iniciar sesión', register: 'Crear cuenta', recover: 'Recuperar cuenta' }[view.value]))
const subtitle = computed(() => ({ login: 'Ingresa tus datos para continuar.', register: 'Crea una cuenta para operar en el taller.', recover: 'Usa el código de recuperación que recibiste al crear tu cuenta.' }[view.value]))
const buttonLabel = computed(() => ({ login: 'Entrar al sistema', register: 'Crear mi cuenta', recover: 'Restablecer contraseña' }[view.value]))

function changeView(nextView: View): void {
  view.value = nextView
  errorMessage.value = ''
  successMessage.value = ''
  generatedCode.value = ''
  password.value = ''
  confirmPassword.value = ''
  recoveryCode.value = ''
  form.value?.resetValidation()
}

async function submit(): Promise<void> {
  const validation = await form.value?.validate()
  if (!validation?.valid) return
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (view.value === 'login') {
      const response = await login(username.value.trim(), password.value)
      emit('authenticated', response.user)
    } else if (view.value === 'register') {
      const response = await register(username.value.trim(), fullName.value.trim(), password.value, role.value)
      generatedCode.value = response.recovery_code
      successMessage.value = 'Cuenta creada. Guarda el código de recuperación antes de continuar.'
    } else {
      await resetPassword(username.value.trim(), recoveryCode.value.trim(), password.value)
      successMessage.value = 'Contraseña actualizada. Ya puedes iniciar sesión.'
      view.value = 'login'
      password.value = ''
    }
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'No se pudo conectar con el servidor. Intenta nuevamente.'
  } finally { loading.value = false }
}
</script>

<template>
  <section class="auth-layout">
    <div class="brand-panel"><div class="brand-content"><v-icon icon="mdi-car-wrench" size="64" class="mb-6" /><p class="eyebrow">PLATAFORMA DE GESTIÓN</p><h1>Tu taller, siempre bajo control.</h1><p class="brand-copy">Accede de manera segura a las herramientas que mantienen tu operación en movimiento.</p></div></div>
    <div class="form-panel"><v-card class="login-card" elevation="0"><v-card-text class="pa-0">
      <div class="mobile-mark"><v-icon icon="mdi-car-wrench" size="36" /></div>
      <p class="eyebrow text-secondary">{{ view === 'login' ? 'BIENVENIDO' : 'GESTIÓN DE CUENTA' }}</p>
      <h2>{{ title }}</h2><p class="subtitle">{{ subtitle }}</p>
      <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-4" closable @click:close="errorMessage = ''">{{ errorMessage }}</v-alert>
      <v-alert v-if="successMessage" type="success" variant="tonal" density="compact" class="mb-4">{{ successMessage }}</v-alert>
      <v-alert v-if="generatedCode" type="warning" variant="tonal" class="mb-4"><strong>Tu código de recuperación:</strong><br><code class="recovery-code">{{ generatedCode }}</code><br><small>Guárdalo en un lugar seguro. No se volverá a mostrar.</small></v-alert>
      <v-form ref="form" validate-on="submit" @submit.prevent="submit">
        <v-text-field v-model="username" label="Usuario" autocomplete="username" prepend-inner-icon="mdi-account-outline" :rules="usernameRules" variant="outlined" color="secondary" class="mb-1" />
        <v-text-field v-if="view === 'register'" v-model="fullName" label="Nombre completo" autocomplete="name" prepend-inner-icon="mdi-card-account-details-outline" :rules="requiredRules" variant="outlined" color="secondary" class="mb-1" />
        <v-select v-if="view === 'register'" v-model="role" label="Rol" :items="roleOptions" prepend-inner-icon="mdi-account-cog-outline" variant="outlined" color="secondary" class="mb-1" />
        <v-text-field v-if="view === 'recover'" v-model="recoveryCode" label="Código de recuperación" prepend-inner-icon="mdi-key-outline" :rules="requiredRules" variant="outlined" color="secondary" class="mb-1" />
        <v-text-field v-model="password" :label="view === 'recover' ? 'Nueva contraseña' : 'Contraseña'" :type="showPassword ? 'text' : 'password'" :autocomplete="view === 'login' ? 'current-password' : 'new-password'" prepend-inner-icon="mdi-lock-outline" :append-inner-icon="showPassword ? 'mdi-eye-off-outline' : 'mdi-eye-outline'" :rules="passwordRules" variant="outlined" color="secondary" @click:append-inner="showPassword = !showPassword" />
        <v-text-field v-if="view !== 'login'" v-model="confirmPassword" label="Confirmar contraseña" type="password" autocomplete="new-password" prepend-inner-icon="mdi-lock-check-outline" :rules="confirmRules" variant="outlined" color="secondary" />
        <v-btn type="submit" block size="large" color="secondary" :loading="loading" class="mt-2 login-button">{{ buttonLabel }}<v-icon end icon="mdi-arrow-right" /></v-btn>
      </v-form>
      <div class="auth-links"><button v-if="view !== 'login'" type="button" @click="changeView('login')">Volver a iniciar sesión</button><template v-else><button type="button" @click="changeView('register')">Crear cuenta</button><button type="button" @click="changeView('recover')">¿Olvidaste tu contraseña?</button></template></div>
      <p class="security-note"><v-icon icon="mdi-shield-check-outline" size="17" /> Acceso protegido y sesión única por usuario</p>
    </v-card-text></v-card></div>
  </section>
</template>
