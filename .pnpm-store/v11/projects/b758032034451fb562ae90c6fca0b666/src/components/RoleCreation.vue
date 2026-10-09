<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ApiError } from '@/services/auth'
import { createRole, getRoles } from '@/services/administration'
import type { Role } from '@/services/administration'

const emit = defineEmits<{ manage: [] }>()
const roles = ref<Role[]>([])
const name = ref('')
const description = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const message = ref('')
const form = ref<{ validate: () => Promise<{ valid: boolean }>; resetValidation: () => void } | null>(null)
const normalize = (value: string): string => value.normalize('NFC').trim().replace(/\s+/g, ' ')
const roleCode = (value: string): string => normalize(value).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '')
const duplicate = computed(() => !!roleCode(name.value) && roles.value.some(role => roleCode(role.name) === roleCode(name.value) || role.code === roleCode(name.value)))
const nameRules = [
  (value: string) => normalize(value).length >= 3 || 'Escribe al menos 3 caracteres.',
  (value: string) => normalize(value).length <= 50 || 'Máximo 50 caracteres.',
  (value: string) => roleCode(value).length >= 3 && roleCode(value).length <= 50 || 'Incluye entre 3 y 50 letras o números.',
  () => !duplicate.value || 'Ya existe un rol con ese nombre.',
]
const descriptionRules = [(value: string) => normalize(value).length <= 200 || 'Máximo 200 caracteres.']
function report(cause: unknown): void { error.value = cause instanceof ApiError ? cause.message : 'No se pudo conectar con el servidor.' }
async function load(): Promise<void> {
  loading.value = true; error.value = ''
  try { roles.value = await getRoles() } catch (cause) { report(cause) } finally { loading.value = false }
}
onMounted(load)
async function save(): Promise<void> {
  if (saving.value || loading.value || !(await form.value?.validate())?.valid) return
  saving.value = true; error.value = ''; message.value = ''
  try {
    const created = await createRole(normalize(name.value), normalize(description.value))
    roles.value = [...roles.value, created].sort((a, b) => a.name.localeCompare(b.name, 'es'))
    message.value = `Rol «${created.name}» creado y activo. Puedes asignarlo desde Administrar roles.`
    name.value = ''; description.value = ''
    await nextTick()
    form.value?.resetValidation()
  } catch (cause) { report(cause) } finally { saving.value = false }
}
</script>

<template>
  <section class="customers-panel module-panel role-creation-panel">
    <div class="customers-heading module-heading">
      <div class="module-title"><span class="module-symbol"><v-icon icon="mdi-shield-plus-outline" size="28" /></span><div><p class="eyebrow">CONFIGURACIÓN DE ACCESO</p><h2>Crear rol</h2><p>Un nombre, una función y un acceso bien definido.</p></div></div>
      <v-btn color="secondary" variant="outlined" prepend-icon="mdi-account-cog-outline" @click="emit('manage')">Administrar roles</v-btn>
    </div>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }} <v-btn v-if="!roles.length" variant="text" :loading="loading" @click="load">Reintentar</v-btn></v-alert>
    <v-alert v-if="message" type="success" variant="tonal" class="mb-4">{{ message }}</v-alert>
    <div class="role-composer">
      <v-form ref="form" class="role-create-form" :disabled="saving || loading" @submit.prevent="save">
        <div class="composer-intro"><span class="record-kicker">NUEVO REGISTRO</span><p>Solo el administrador puede crear roles. Podrás asignarlo a las cuentas después de guardarlo.</p></div>
        <div class="role-compose-fields">
          <v-text-field v-model="name" label="Nombre del rol" placeholder="Ej. Coordinador de servicio" :rules="nameRules" maxlength="50" counter="50" variant="outlined" color="secondary" />
          <v-textarea v-model="description" label="Descripción (opcional)" placeholder="Describe la función de este rol" :rules="descriptionRules" maxlength="200" counter="200" rows="3" variant="outlined" color="secondary" />
        </div>
        <div class="composer-footer"><p><v-icon icon="mdi-shield-check-outline" size="20" /> El nombre debe ser único.</p><v-btn type="submit" color="secondary" prepend-icon="mdi-plus" :loading="saving" :disabled="loading || !!error && !roles.length">Crear rol</v-btn></div>
      </v-form>
      <aside class="role-reference" aria-labelledby="role-reference-title">
        <div class="reference-heading"><h3 id="role-reference-title">Ya están en el catálogo</h3><span>{{ roles.length }} roles</span></div>
        <p class="field-note">Mayúsculas, acentos o espacios no distinguen un rol nuevo. También se comprueban los roles suspendidos.</p>
        <v-progress-linear v-if="loading" indeterminate color="secondary" class="my-4" />
        <ul class="role-reference-list"><li v-for="role in roles" :key="role.id"><v-icon :icon="role.bin_status === 1 ? 'mdi-circle-small' : 'mdi-pause-circle-outline'" size="18" /><span>{{ role.name }}<small v-if="role.bin_status !== 1"> · {{ role.status }}</small></span></li></ul>
        <div class="role-reference-note"><v-icon icon="mdi-information-outline" size="20" /><p>Crear un rol no concede permisos de administración automáticamente. Las cuentas públicas siguen registrándose como Invitado.</p></div>
      </aside>
    </div>
  </section>
</template>
