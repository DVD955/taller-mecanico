<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { validateVehiclePhotos } from '@/services/vehicles'

const props = defineProps<{ modelValue: File[]; existingCount?: number; required?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [files: File[]] }>()
const previews = ref<{ url: string; name: string; size: number }[]>([])
const validation = computed(() => validateVehiclePhotos(props.modelValue, props.existingCount ?? 0, props.required ?? false))
function release(): void { for (const preview of previews.value) URL.revokeObjectURL(preview.url); previews.value = [] }
watch(() => props.modelValue, files => {
  release()
  if (validation.value === true) previews.value = files.map(file => ({ url: URL.createObjectURL(file), name: file.name, size: file.size }))
}, { immediate: true })
function select(files: File | File[] | null): void { emit('update:modelValue', files === null ? [] : Array.isArray(files) ? files : [files]) }
onBeforeUnmount(release)
</script>

<template>
  <section class="vehicle-photo-picker" aria-label="Fotos del vehículo">
    <h3>Fotografías <span class="vehicle-optional">{{ required ? 'Al menos una obligatoria' : 'Opcionales' }}</span></h3>
    <p class="subtitle">JPG, PNG o WebP. Máximo 15 MB por foto y 10 fotos por vehículo.</p>
    <p v-if="existingCount" class="mb-3">Se conservan {{ existingCount }} fotos anteriores. Las nuevas se agregarán a la galería.</p>
    <p v-if="required && existingCount" class="mb-3">La fotografía obligatoria ya está cubierta; no necesitas volver a cargarla.</p>
    <v-file-input :model-value="modelValue" label="Seleccionar una o varias fotos" accept="image/jpeg,image/png,image/webp" multiple show-size variant="outlined" color="secondary" prepend-icon="" prepend-inner-icon="mdi-camera-plus-outline" :rules="[() => validation]" @update:model-value="select" />
    <p v-if="validation !== true" role="alert">{{ validation }}</p>
    <div v-if="previews.length" class="vehicle-photo-previews">
      <figure v-for="(preview, index) in previews" :key="preview.url"><img :src="preview.url" :alt="`Vista previa: ${preview.name}`" /><figcaption>{{ preview.name }} · {{ (preview.size / 1000000).toFixed(2) }} MB</figcaption><v-btn size="small" variant="text" color="secondary" :aria-label="`Quitar ${preview.name}`" @click="emit('update:modelValue', modelValue.filter((_, item) => item !== index))">Quitar</v-btn></figure>
    </div>
  </section>
</template>
