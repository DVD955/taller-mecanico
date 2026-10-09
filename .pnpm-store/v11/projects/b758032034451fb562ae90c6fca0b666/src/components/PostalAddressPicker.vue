<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { ApiError } from '@/services/auth'
import { getMunicipalities, getSettlements, getStates } from '@/services/workshops'
import type { PostalAddress, Settlement } from '@/services/workshops'
const props = defineProps<{ modelValue: PostalAddress }>()
const emit = defineEmits<{ 'update:modelValue': [value: PostalAddress] }>()
const manual = ref(false)
const cp = ref(props.modelValue.postal_code)
const state = ref(props.modelValue.state)
const municipality = ref(props.modelValue.municipality)
const states = ref<string[]>([])
const municipalities = ref<string[]>([])
const settlements = ref<Settlement[]>([])
const selected = ref<number | null>(null)
const busy = ref(false)
const error = ref('')
const initialAddress = { ...props.modelValue }
let generation = 0
let timer: ReturnType<typeof setTimeout> | undefined
let mounted = true
const required = [(value: unknown) => !!value || 'Selecciona una opción.']
function invalidate(): void { selected.value = null; settlements.value = []; emit('update:modelValue', { postal_code: cp.value, state: '', municipality: '', neighborhood: '' }) }
function cancelLookup(): void { generation++; clearTimeout(timer); busy.value = false; error.value = '' }
function pick(value: number | null): void {
  const item = settlements.value.find(row => row.id === value)
  if (!item) { emit('update:modelValue', { postal_code: cp.value, state: state.value, municipality: municipality.value, neighborhood: '' }); return }
  cp.value = item.postal_code; state.value = item.state; municipality.value = item.municipality
  emit('update:modelValue', { postal_code: item.postal_code, state: item.state, municipality: item.municipality, neighborhood: item.neighborhood })
}
async function lookup(initial = false): Promise<void> {
  if (!/^\d{5}$/.test(cp.value)) return
  const current = ++generation
  const previousAddress = { ...props.modelValue }
  busy.value = true; error.value = ''; invalidate()
  try {
    const result = await getSettlements({ postal_code: cp.value })
    if (current !== generation) return
    settlements.value = result
    const previous = initial ? result.find(item => item.neighborhood === previousAddress.neighborhood && item.municipality === previousAddress.municipality) : undefined
    // Un CP puede tener varias colonias: prellenar una y permitir corregirla.
    // Al editar se conserva la colonia guardada, no necesariamente la primera.
    selected.value = previous?.id ?? result[0]?.id ?? null
    if (selected.value) pick(selected.value)
  } catch (cause) { if (current === generation) error.value = cause instanceof ApiError ? cause.message : 'No se pudo consultar la dirección.' }
  finally { if (current === generation) busy.value = false }
}
function searchByPostalCode(): void {
  if (manual.value) return
  cancelLookup()
  if (!/^\d{5}$/.test(cp.value)) { error.value = 'Escribe un código postal de 5 dígitos y presiona Enter.'; return }
  state.value = ''; municipality.value = ''
  // Enter consulta inmediatamente y no envía el formulario del taller.
  // Si se vuelve a consultar el mismo CP, se conserva la colonia elegida.
  void lookup(true)
}
watch(cp, () => {
  if (manual.value) return
  cancelLookup(); state.value = ''; municipality.value = ''; invalidate()
  if (/^\d{5}$/.test(cp.value)) timer = setTimeout(() => { void lookup() }, 250)
})
async function stateChanged(): Promise<void> {
  cancelLookup(); municipality.value = ''; cp.value = ''; invalidate(); municipalities.value = []
  if (!state.value) return
  busy.value = true; error.value = ''
  const current = generation
  try { const result = await getMunicipalities(state.value); if (current === generation) municipalities.value = result }
  catch (cause) { if (current === generation) error.value = cause instanceof ApiError ? cause.message : 'No se pudieron cargar los municipios.' }
  finally { if (current === generation) busy.value = false }
}
async function municipalityChanged(): Promise<void> {
  cancelLookup(); cp.value = ''; invalidate()
  if (!state.value || !municipality.value) return
  const current = generation
  busy.value = true
  try { const result = await getSettlements({ state: state.value, municipality: municipality.value }); if (current === generation) settlements.value = result }
  catch (cause) { if (current === generation) error.value = cause instanceof ApiError ? cause.message : 'No se pudieron cargar las colonias.' }
  finally { if (current === generation) busy.value = false }
}
function modeChanged(): void { cancelLookup(); cp.value = ''; state.value = ''; municipality.value = ''; municipalities.value = []; invalidate() }
onMounted(async () => {
  // El catálogo de estados no debe reiniciar una búsqueda que el usuario ya hizo.
  if (initialAddress.postal_code) void lookup(true)
  try { const result = await getStates(); if (mounted) states.value = result }
  catch (cause) { if (mounted) error.value = cause instanceof ApiError ? cause.message : 'No se pudo cargar el catálogo postal.' }
})
onUnmounted(() => { mounted = false; cancelLookup() })
</script>
<template>
  <div>
    <v-switch v-model="manual" label="No conozco mi código postal" color="secondary" hide-details class="mb-4" @update:model-value="modeChanged" />
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
    <p v-if="!manual" class="field-note mb-4">Escribe los 5 dígitos del CP y presiona Enter para llenar estado, municipio y colonia. También se consulta al terminar de escribir.</p>
    <div class="form-grid"><v-text-field v-model="cp" label="Código postal" inputmode="numeric" maxlength="5" :readonly="manual" :loading="busy && !manual" :rules="[(value: string) => /^\d{5}$/.test(value) || 'Selecciona una dirección con CP de 5 dígitos.']" variant="outlined" color="secondary" @keydown.enter.prevent.stop="searchByPostalCode" /><v-select v-if="manual" v-model="state" label="Estado" :items="states" :rules="required" :disabled="busy" variant="outlined" color="secondary" @update:model-value="stateChanged" /><v-text-field v-else :model-value="state" label="Estado" readonly variant="outlined" color="secondary" /><v-autocomplete v-if="manual" v-model="municipality" label="Municipio" :items="municipalities" :rules="required" :disabled="!state || busy" variant="outlined" color="secondary" @update:model-value="municipalityChanged" /><v-text-field v-else :model-value="municipality" label="Municipio" readonly variant="outlined" color="secondary" /><v-autocomplete v-model="selected" label="Colonia / asentamiento" :items="settlements.map(item => ({ title: `${item.neighborhood} · ${item.postal_code}`, value: item.id }))" :rules="required" :loading="busy" :disabled="busy || !settlements.length" variant="outlined" color="secondary" @update:model-value="pick" /></div>
    <v-alert v-if="!manual && !busy && settlements.length > 1" color="secondary" variant="tonal" density="compact" icon="mdi-map-marker-check-outline" class="mb-4">Este CP tiene {{ settlements.length }} colonias. Prellenamos una opción; verifica y selecciona tu colonia en el campo de arriba.</v-alert>
  </div>
</template>
