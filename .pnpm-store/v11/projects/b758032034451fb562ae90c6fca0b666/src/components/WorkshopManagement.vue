<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import PostalAddressPicker from './PostalAddressPicker.vue'
import { ApiError } from '@/services/auth'
import { deleteWorkshop, getWorkshopImage, getWorkshops, saveWorkshop } from '@/services/workshops'
import type { PostalAddress, Workshop, WorkshopDraft } from '@/services/workshops'

const workshops = ref<Workshop[]>([])
const images = ref<Record<number, string>>({})
const busy = ref(false)
const error = ref('')
const message = ref('')
const editor = ref(false)
const editing = ref<Workshop | null>(null)
const deletion = ref<Workshop | null>(null)
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const name = ref('')
const rfc = ref('')
const email = ref('')
const street = ref('')
const number = ref('')
const address = ref<PostalAddress>({ postal_code: '', state: '', municipality: '', neighborhood: '' })
const file = ref<File | File[] | null>(null)
const selectedFile = computed(() => Array.isArray(file.value) ? file.value[0] ?? null : file.value)
const selectedPreview = ref('')
const preview = computed(() => selectedPreview.value || (editing.value ? images.value[editing.value.id] : ''))
const imageTypes = ['image/jpeg', 'image/png', 'image/webp']
const imageRules = [
  () => !!editing.value || !!selectedFile.value || 'Adjunta una fotografía del taller.',
  () => !selectedFile.value || selectedFile.value.size <= 10_000_000 || 'La imagen supera 10 MB.',
  () => !selectedFile.value || imageTypes.includes(selectedFile.value.type) || 'Usa una imagen JPG, PNG o WebP.',
]
watch(selectedFile, image => {
  if (selectedPreview.value) URL.revokeObjectURL(selectedPreview.value)
  selectedPreview.value = image && image.size <= 10_000_000 && imageTypes.includes(image.type) ? URL.createObjectURL(image) : ''
})
const required = [(value: string) => !!value?.trim() || 'Este campo es obligatorio.']
const rfcRules = [...required, (value: string) => /^[A-ZÑ&]{3,4}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[A-Z0-9]{3}$/.test(value.trim().toUpperCase()) || 'RFC inválido: 12 o 13 caracteres con homoclave.']
const emailRules = [...required, (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) || 'Correo no válido.']
let mounted = true
function clearImages(): void { Object.values(images.value).forEach(url => URL.revokeObjectURL(url)); images.value = {} }
function report(cause: unknown): void { error.value = cause instanceof ApiError ? cause.message : 'No se pudo conectar con el servidor.' }
async function refresh(): Promise<void> {
  const result = await getWorkshops()
  if (!mounted) return
  clearImages(); workshops.value = result
  await Promise.all(result.filter(item => item.has_image).map(async item => {
    try { const url = await getWorkshopImage(item.id); if (mounted) images.value[item.id] = url; else URL.revokeObjectURL(url) }
    catch (cause) { if (mounted) report(cause) }
  }))
}
onMounted(async () => { busy.value = true; try { await refresh() } catch (cause) { report(cause) } finally { busy.value = false } })
onUnmounted(() => { mounted = false; clearImages(); if (selectedPreview.value) URL.revokeObjectURL(selectedPreview.value) })
function open(item: Workshop | null): void {
  editing.value = item; name.value = item?.name ?? ''; rfc.value = item?.rfc ?? ''; street.value = item?.street ?? ''; number.value = item?.number ?? ''
  email.value = item?.email ?? ''
  address.value = { postal_code: item?.postal_code ?? '', state: item?.state ?? '', municipality: item?.municipality ?? '', neighborhood: item?.neighborhood ?? '' }
  file.value = null; error.value = ''; message.value = ''; editor.value = true
}
function closeEditor(): void { editor.value = false; file.value = null; error.value = '' }
async function save(): Promise<void> {
  if (!(await form.value?.validate())?.valid) return
  if (selectedFile.value && selectedFile.value.size > 10_000_000) { error.value = 'La imagen no debe superar 10 MB.'; return }
  if (!address.value.neighborhood) { error.value = 'Selecciona una colonia del catálogo postal.'; return }
  busy.value = true; error.value = ''; message.value = ''
  const data: WorkshopDraft = { name: name.value.trim(), rfc: rfc.value.trim().toUpperCase(), email: email.value.trim().toLowerCase(), street: street.value.trim(), number: number.value.trim(), ...address.value,
    ...(editing.value ? { version: editing.value.version } : {}) }
  try { await saveWorkshop(data, selectedFile.value, editing.value?.id); closeEditor(); message.value = editing.value ? 'Taller actualizado.' : 'Taller registrado.'; await refresh() }
  catch (cause) { report(cause) } finally { busy.value = false }
}
async function remove(): Promise<void> {
  if (!deletion.value) return
  busy.value = true; error.value = ''
  try { message.value = (await deleteWorkshop(deletion.value)).message; deletion.value = null; await refresh() }
  catch (cause) { report(cause) } finally { busy.value = false }
}
</script>
<template>
  <section class="customers-panel module-panel workshop-management-panel">
    <div class="customers-heading module-heading"><div class="module-title"><span class="module-symbol"><v-icon icon="mdi-garage-variant" size="28" /></span><div><p class="eyebrow">TALLERES MECÁNICOS</p><h2>{{ editor ? (editing ? 'Actualizar taller' : 'Alta de taller mecánico') : 'Administración de talleres' }} <span v-if="!editor" class="customer-count">{{ workshops.length }}</span></h2><p>{{ editor ? 'La identidad, ubicación e imagen de tu establecimiento en un solo registro.' : 'Consulta y mantén la información de tus establecimientos.' }}</p></div></div><v-btn v-if="!editor" color="secondary" prepend-icon="mdi-plus" :disabled="busy" @click="open(null)">Alta de taller</v-btn><v-btn v-else color="secondary" variant="text" prepend-icon="mdi-arrow-left" :disabled="busy" @click="closeEditor">Volver al catálogo</v-btn></div>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert><v-alert v-if="message" type="success" variant="tonal" class="mb-4">{{ message }}</v-alert>
    <v-progress-linear v-if="busy" indeterminate color="secondary" class="mb-4" />
    <template v-if="!editor">
      <div v-if="!busy && !workshops.length" class="customer-empty"><v-icon icon="mdi-garage-variant" size="46" /><h3>Aún no hay talleres registrados</h3><p>Selecciona “Alta de taller” para comenzar.</p></div>
      <div class="workshop-directory"><article v-for="item in workshops" :key="item.id" class="workshop-card workshop-directory-record"><img v-if="images[item.id]" :src="images[item.id]" :alt="'Imagen de ' + item.name" class="workshop-image" /><div v-else class="workshop-placeholder"><v-icon icon="mdi-garage-variant" size="54" /></div><div class="workshop-body"><div class="workshop-directory-title"><h3>{{ item.name }}</h3><v-chip color="secondary" variant="outlined" size="small">{{ item.status }}</v-chip></div><p class="workshop-fiscal"><strong>RFC</strong> {{ item.rfc }}</p><p class="workshop-contact"><v-icon icon="mdi-email-outline" size="17" /> {{ item.email }}</p><p class="workshop-address"><v-icon icon="mdi-map-marker-outline" size="17" /><span>{{ item.street }} {{ item.number }}, {{ item.neighborhood }}<br />{{ item.municipality }}, {{ item.state }} · CP {{ item.postal_code }}</span></p></div><div class="workshop-actions"><v-btn variant="text" color="secondary" prepend-icon="mdi-pencil-outline" :disabled="busy" @click="open(item)">Actualizar</v-btn><v-btn variant="text" color="secondary" prepend-icon="mdi-delete-outline" :disabled="busy" @click="deletion = item">Dar de baja</v-btn></div></article></div>
    </template>
    <v-form v-else ref="form" class="workshop-register" :disabled="busy" @submit.prevent="save">
      <div class="workshop-register-caption"><span class="record-kicker">{{ editing ? 'EDITAR REGISTRO' : 'NUEVO ESTABLECIMIENTO' }}</span><span>Todos los campos son obligatorios{{ editing ? ', excepto reemplazar la imagen' : '' }}.</span></div>
      <section class="workshop-register-section" aria-labelledby="workshop-data-title">
        <div class="workshop-section-label"><span class="workshop-section-number">01</span><h3 id="workshop-data-title">Identidad del taller</h3><p>Datos fiscales y contacto del establecimiento.</p></div>
        <div class="workshop-section-fields">
            <v-text-field v-model="name" label="Nombre del taller" placeholder="Nombre del establecimiento" :rules="[...required, (value: string) => value.trim().length >= 3 || 'Mínimo 3 caracteres.']" maxlength="120" variant="outlined" color="secondary" />
            <div class="form-grid">
              <v-text-field v-model="rfc" label="RFC" :rules="rfcRules" maxlength="13" hint="12 o 13 caracteres; se guarda en mayúsculas." persistent-hint variant="outlined" color="secondary" />
              <v-text-field v-model="email" label="Correo de contacto" type="email" :rules="emailRules" maxlength="254" variant="outlined" color="secondary" />
            </div>
        </div>
      </section>
      <section class="workshop-register-section" aria-labelledby="workshop-address-title">
        <div class="workshop-section-label"><span class="workshop-section-number">02</span><h3 id="workshop-address-title">Ubicación</h3><p>Busca por CP o encuentra tu colonia por estado y municipio.</p></div>
        <div class="workshop-section-fields">
            <div class="form-grid"><v-text-field v-model="street" label="Calle" :rules="required" maxlength="150" variant="outlined" color="secondary" /><v-text-field v-model="number" label="Número" :rules="required" maxlength="20" variant="outlined" color="secondary" /></div>
            <PostalAddressPicker :key="editing?.id ?? 'new'" v-model="address" />
        </div>
      </section>
      <section class="workshop-register-section" aria-labelledby="workshop-image-title">
        <div class="workshop-section-label"><span class="workshop-section-number">03</span><h3 id="workshop-image-title">Imagen del taller</h3><p>{{ editing ? 'Conserva o reemplaza la imagen actual.' : 'Identifica tu taller con una fotografía.' }}</p></div>
        <div class="workshop-media-row">
          <div class="workshop-photo-preview"><img v-if="preview" :src="preview" alt="Vista previa de la fotografía del taller" /><div v-else><v-icon icon="mdi-camera-outline" size="34" /><p>Vista previa</p></div></div>
          <div class="workshop-image-field"><v-file-input v-model="file" :label="editing ? 'Reemplazar imagen (opcional)' : 'Imagen del taller'" accept="image/jpeg,image/png,image/webp" hint="JPG, PNG o WebP · máximo 10 MB" persistent-hint :rules="imageRules" show-size variant="outlined" color="secondary" /><p class="field-note">Elige una foto de la fachada o del interior del establecimiento.</p></div>
        </div>
      </section>
      <div class="workshop-form-footer"><p><v-icon icon="mdi-check-circle-outline" size="20" /> Confirma tus datos y la colonia elegida.</p><div class="editor-buttons"><v-btn variant="text" color="secondary" :disabled="busy" @click="closeEditor">Cancelar</v-btn><v-btn type="submit" color="secondary" prepend-icon="mdi-content-save-outline" :loading="busy">{{ editing ? 'Guardar cambios' : 'Registrar taller' }}</v-btn></div></div>
    </v-form>
    <v-dialog :model-value="!!deletion" max-width="480" :persistent="busy" @update:model-value="!$event && (deletion = null)"><v-card class="customer-dialog"><v-card-text><h2>Dar de baja taller</h2><p class="my-4">¿Dar de baja {{ deletion?.name }}? El registro y su imagen se conservarán.</p><v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert><v-btn color="secondary" :loading="busy" @click="remove">Confirmar baja</v-btn><v-btn variant="text" :disabled="busy" @click="deletion = null">Cancelar</v-btn></v-card-text></v-card></v-dialog>
  </section>
</template>
