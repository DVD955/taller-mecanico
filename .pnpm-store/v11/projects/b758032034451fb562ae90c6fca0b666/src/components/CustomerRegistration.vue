<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ApiError } from '@/services/auth'
import { previewCustomer, registerCustomer, previewCustomerUpdate, updateCustomer } from '@/services/customers'
import type { Customer, CustomerInput, PreviewResult, SavedCustomer } from '@/services/customers'

const props = defineProps<{ initialOpen?: boolean; customer?: Customer }>()
const emit = defineEmits<{ saved: [customer: Customer]; close: [] }>()
const open = ref(props.initialOpen ?? false)
const busy = ref(false)
const errorMessage = ref('')
const review = ref<PreviewResult | null>(null)
const saved = ref<SavedCustomer | null>(null)
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const empty = (): CustomerInput => ({ fullName: '', address: { street: '', number: '', neighborhood: '', municipality: '', state: '' }, contacts: { email: '', mobile: '', alternative: '' } })
const input = reactive<CustomerInput>(props.customer ? {
  fullName: props.customer.fullName, address: { ...props.customer.address }, contacts: { ...props.customer.contacts },
} : empty())
const required = (max: number) => [(v: string) => !!v?.trim() || 'Este campo es obligatorio.', (v: string) => (v?.length ?? 0) <= max || `Máximo ${max} caracteres.`]
const nameRules = [...required(120), (v: string) => (v?.trim().length ?? 0) >= 3 || 'Mínimo 3 caracteres.', (v: string) => /^[\p{L}\p{M} .'-]+$/u.test(v) || 'Usa letras y espacios.']
const emailRules = [(v: string | null) => !v?.trim() || (v.trim().length <= 254 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.trim())) || 'Correo no válido.']
const phoneRules = [(v: string | null) => {
  if (!v?.trim()) return true
  if (!/^\+?[0-9() .-]+$/.test(v.trim())) return 'Teléfono no válido.'
  const clean = v.trim().replace(/[() .-]/g, '')
  return /^[0-9]{10}$/.test(clean) || /^\+[1-9][0-9]{7,14}$/.test(clean) || 'Usa 10 dígitos o +código de país.'
}]

function start(): void {
  Object.assign(input, empty())
  open.value = true; review.value = null; saved.value = null; errorMessage.value = ''
}

function cancel(): void { open.value = false; review.value = null; emit('close') }

async function prepare(): Promise<void> {
  errorMessage.value = ''
  if (!(await form.value?.validate())?.valid) return
  if (!Object.values(input.contacts).some(v => v?.trim())) {
    errorMessage.value = 'Captura al menos un correo, celular o teléfono alternativo.'
    return
  }
  busy.value = true
  try { review.value = props.customer
    ? await previewCustomerUpdate(props.customer.id, input, props.customer.version)
    : await previewCustomer(input) }
  catch (error) { errorMessage.value = error instanceof ApiError ? error.message : 'No se pudo revisar el cliente.' }
  finally { busy.value = false }
}

async function confirm(): Promise<void> {
  const preview = review.value
  if (!preview?.previewToken || preview.matches.length) return
  busy.value = true; errorMessage.value = ''
  try {
    const { fullName, address, contacts } = preview.customer
    saved.value = props.customer
      ? await updateCustomer(props.customer.id, { fullName, address, contacts }, props.customer.version, preview.previewToken)
      : await registerCustomer({ fullName, address, contacts }, preview.previewToken)
    open.value = false; review.value = null
    emit('saved', saved.value.customer)
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'No se pudo guardar el cliente.'
    // Obliga a revisar nuevamente tras conflicto, expiración o fallo de comunicación.
    review.value = null
  } finally { busy.value = false }
}
</script>

<template>
  <v-card :class="initialOpen ? 'customer-editor' : 'profile-card'" elevation="0"><v-card-text class="d-block">
    <h2>{{ customer ? 'Actualizar cliente' : 'Registrar cliente' }}</h2>
    <p class="subtitle">{{ customer ? 'Actualiza los datos del cliente y revisa las coincidencias antes de confirmar.' : 'Registra los datos del cliente y revisa las coincidencias antes de confirmar.' }}</p>
    <v-alert v-if="saved" color="secondary" variant="tonal" class="mb-4" aria-live="polite">
      Cliente #{{ saved.customer.id }} {{ saved.customer.fullName }} registrado como activo.
      Agregado por {{ saved.auditEntry.actorUsername }} el {{ new Date(saved.auditEntry.occurredAt).toLocaleString('es-MX') }}.
    </v-alert>
    <v-btn v-if="!open" color="secondary" prepend-icon="mdi-account-plus-outline" @click="start">Registrar cliente</v-btn>
    <v-alert v-if="errorMessage" color="secondary" variant="tonal" class="my-4" role="alert">{{ errorMessage }}</v-alert>
    <v-form v-if="open && !review" ref="form" validate-on="submit" @submit.prevent="prepare">
      <v-text-field v-model="input.fullName" label="Nombre completo" autocomplete="name" :rules="nameRules" variant="outlined" color="secondary" />
      <h3 class="mb-3">Dirección</h3>
      <v-row>
        <v-col cols="12" sm="8"><v-text-field v-model="input.address.street" label="Calle" :rules="required(150)" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="4"><v-text-field v-model="input.address.number" label="Número (o S/N)" :rules="required(20)" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="6"><v-text-field v-model="input.address.neighborhood" label="Colonia" :rules="required(100)" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="6"><v-text-field v-model="input.address.municipality" label="Municipio" :rules="required(100)" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12"><v-text-field v-model="input.address.state" label="Estado" :rules="required(100)" variant="outlined" color="secondary" /></v-col>
      </v-row>
      <h3>Contacto</h3><p class="mb-3">Al menos uno es obligatorio. Los teléfonos de 10 dígitos se registran con +52.</p>
      <v-row>
        <v-col cols="12" md="4"><v-text-field v-model="input.contacts.email" label="Correo" type="email" :rules="emailRules" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" md="4"><v-text-field v-model="input.contacts.mobile" label="Celular" type="tel" :rules="phoneRules" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" md="4"><v-text-field v-model="input.contacts.alternative" label="Teléfono alternativo" type="tel" :rules="phoneRules" variant="outlined" color="secondary" /></v-col>
      </v-row>
      <div class="d-flex flex-wrap ga-3"><v-btn type="submit" color="secondary" :loading="busy">Revisar datos y coincidencias</v-btn><v-btn variant="text" color="secondary" :disabled="busy" @click="cancel">Cancelar</v-btn></div>
    </v-form>
    <div v-if="open && review">
      <h3 class="mb-3">Revisión del cliente</h3>
      <p><strong>{{ review.customer.fullName }}</strong></p>
      <p>{{ review.customer.address.street }} {{ review.customer.address.number }}, {{ review.customer.address.neighborhood }}, {{ review.customer.address.municipality }}, {{ review.customer.address.state }}</p>
      <p class="mt-2">Correo: {{ review.customer.contacts.email || 'Sin correo' }}</p>
      <p>Celular: {{ review.customer.contacts.mobile || 'Sin celular' }}</p>
      <p>Alternativo: {{ review.customer.contacts.alternative || 'Sin alternativo' }}</p>
      <v-alert v-if="review.matches.length" color="secondary" variant="tonal" class="my-4" role="alert">
        Se encontraron coincidencias con otros clientes. No se pueden guardar datos duplicados.
        <p v-for="match in review.matches" :key="match.id">Cliente #{{ match.id }}: {{ match.fullName }} · {{ match.status }}</p>
      </v-alert>
      <p v-else class="my-4">{{ customer ? 'No hay coincidencias con otros clientes. Confirma para guardar los cambios.' : 'No se encontraron coincidencias. Confirma para guardar este cliente como activo.' }}</p>
      <div class="d-flex flex-wrap ga-3">
        <v-btn v-if="review.previewToken && !review.matches.length" color="secondary" :loading="busy" @click="confirm">{{ customer ? 'Confirmar cambios' : 'Confirmar y registrar' }}</v-btn>
        <v-btn variant="outlined" color="secondary" :disabled="busy" @click="review = null">Editar datos</v-btn>
        <v-btn variant="text" color="secondary" :disabled="busy" @click="cancel">Cancelar</v-btn>
      </div>
    </div>
  </v-card-text></v-card>
</template>
