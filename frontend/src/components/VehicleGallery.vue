<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ApiError } from '@/services/auth'
import { getVehiclePhotoUrl } from '@/services/vehicles'
import type { VehiclePhoto } from '@/services/vehicles'

const props = defineProps<{ vehicleId: number; photos: VehiclePhoto[] }>()
const selected = ref(0)
const url = ref('')
const loading = ref(false)
const error = ref('')
let sequence = 0
watch([() => props.vehicleId, () => props.photos, selected], async () => {
  const current = ++sequence
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''; error.value = ''
  const photo = props.photos[selected.value]
  if (!photo) { loading.value = false; return }
  loading.value = true
  try {
    const loaded = await getVehiclePhotoUrl(props.vehicleId, photo.id)
    if (current === sequence) url.value = loaded
    else URL.revokeObjectURL(loaded)
  } catch (reason) { if (current === sequence) error.value = reason instanceof ApiError ? reason.message : 'No se pudo cargar la foto.' }
  finally { if (current === sequence) loading.value = false }
}, { immediate: true })
onBeforeUnmount(() => { sequence++; if (url.value) URL.revokeObjectURL(url.value) })
</script>

<template>
  <section class="vehicle-gallery" aria-label="Galería privada del vehículo">
    <h3>Fotos del vehículo <span class="vehicle-optional">{{ photos.length }}</span></h3>
    <div v-if="!photos.length" class="vehicle-gallery-empty"><v-icon icon="mdi-image-outline" size="36" /><p>Este vehículo no tiene fotos registradas.</p></div>
    <template v-else>
      <div class="vehicle-gallery-stage" aria-live="polite"><v-progress-circular v-if="loading" indeterminate color="secondary" /><p v-else-if="error" role="alert">{{ error }}</p><img v-else-if="url" :src="url" :alt="`Foto ${selected + 1} del vehículo`" /></div>
      <div class="vehicle-gallery-controls"><v-btn variant="text" color="secondary" icon="mdi-chevron-left" aria-label="Foto anterior" :disabled="selected === 0" @click="selected--" /><span>Foto {{ selected + 1 }} de {{ photos.length }}</span><v-btn variant="text" color="secondary" icon="mdi-chevron-right" aria-label="Foto siguiente" :disabled="selected >= photos.length - 1" @click="selected++" /></div>
    </template>
  </section>
</template>
