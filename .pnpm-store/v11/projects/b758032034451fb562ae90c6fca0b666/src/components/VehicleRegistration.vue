<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ApiError } from '@/services/auth'
import VehiclePhotos from '@/components/VehiclePhotos.vue'
import { createVehicleWithPhotos, updateVehicle, validateVehiclePhotos } from '@/services/vehicles'
import type { Customer, Vehicle, VehicleInput } from '@/services/customers'
import { normalizeVin, normalizeMexicanPlate, validateVin, validateMexicanPlate } from '@/validation/vehicleIdentifiers'
import { validateVehicleDraft, validateVehicleMileage, validateVehicleText, validateVehicleYear } from '@/validation/vehicleForm'
import type { VehicleDraft } from '@/validation/vehicleForm'

const props = defineProps<{ customer: Pick<Customer, 'id' | 'fullName' | 'workshopName'>; vehicle?: Vehicle; existingPhotoCount?: number }>()
const emit = defineEmits<{ saved: [vehicle: Vehicle]; close: [] }>()
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const draft = reactive<VehicleDraft>({ vin: props.vehicle?.vin ?? '', plate: props.vehicle?.plate ?? '', make: props.vehicle?.make ?? '',
  model: props.vehicle?.model ?? '', year: props.vehicle ? String(props.vehicle.year) : '', version: props.vehicle?.version ?? '',
  color: props.vehicle?.color ?? '', mileage: props.vehicle?.mileage == null ? '' : String(props.vehicle.mileage) })
const photos = ref<File[]>([])
const review = ref<VehicleInput | null>(null)
const busy = ref(false)
const errorMessage = ref('')
const required = (label: string, max: number) => [(value: unknown) => validateVehicleText(value, label, max)]
const vinRules = [validateVin]
const plateRules = [validateMexicanPlate]
const yearRules = [validateVehicleYear]
const mileageRules = [(value: unknown) => validateVehicleMileage(value, !!props.vehicle)]
const draftValidation = computed(() => validateVehicleDraft(draft, !!props.vehicle))
const photoValidation = computed(() => validateVehiclePhotos(photos.value, props.existingPhotoCount ?? 0, !!props.vehicle))
const canReview = computed(() => draftValidation.value === true && photoValidation.value === true)
const incompleteMessage = computed(() => draftValidation.value !== true ? draftValidation.value : photoValidation.value !== true ? photoValidation.value : '')

async function prepare(): Promise<void> {
  errorMessage.value = ''
  if (!canReview.value) { errorMessage.value = incompleteMessage.value; await form.value?.validate(); return }
  if (!(await form.value?.validate())?.valid) return
  review.value = { vin: props.vehicle?.vin ?? normalizeVin(draft.vin ?? ''), plate: normalizeMexicanPlate(draft.plate ?? ''),
    make: draft.make?.trim() ?? '', model: draft.model?.trim() ?? '', year: Number(draft.year), version: draft.version?.trim() ?? '',
    color: draft.color?.trim() ?? '', mileage: draft.mileage === '' || draft.mileage === null ? null : Number(draft.mileage) }
}
async function confirm(): Promise<void> {
  if (!review.value || busy.value) return
  if (!canReview.value) { review.value = null; errorMessage.value = incompleteMessage.value; return }
  busy.value = true
  errorMessage.value = ''
  try {
    const result = props.vehicle
      ? await updateVehicle(props.vehicle.id, review.value, props.vehicle.recordVersion, photos.value)
      : await createVehicleWithPhotos(props.customer.id, review.value, photos.value)
    emit('saved', result.vehicle)
  }
  catch (error) { errorMessage.value = error instanceof ApiError ? error.message : props.vehicle ? 'No se pudo actualizar el vehículo.' : 'No se pudo registrar el vehículo.' }
  finally { busy.value = false }
}
</script>

<template>
  <v-card class="customer-editor vehicle-editor" elevation="0"><v-card-text class="d-block">
    <p class="eyebrow">{{ vehicle ? 'ADMINISTRACIÓN DE VEHÍCULOS' : 'REGISTRO DE VEHÍCULO' }}</p><h2>{{ vehicle ? 'Actualizar vehículo' : 'Asociar vehículo' }}</h2>
    <p class="subtitle">{{ vehicle ? 'Completa los datos editables y conserva o agrega al menos una fotografía.' : 'Registra su identificación y confirma a quién pertenece.' }}</p>
    <div class="customer-workshop-summary mb-6"><v-icon icon="mdi-account-outline" /><div><span>Cliente seleccionado</span><strong>{{ customer.fullName }}</strong><small>{{ customer.workshopName || 'Sin taller · registro anterior' }}</small></div></div>
    <v-alert v-if="errorMessage" variant="tonal" color="secondary" role="alert" class="mb-4">{{ errorMessage }}</v-alert>
    <v-form v-if="!review" ref="form" validate-on="submit" @submit.prevent="prepare">
      <h3 class="mb-3">Identificación</h3>
      <v-row>
        <v-col cols="12" sm="7">
          <v-text-field v-if="vehicle" :model-value="vehicle.vin" label="VIN / número de serie" readonly
            hint="VIN registrado · solo lectura" persistent-hint variant="outlined" color="secondary" />
          <v-text-field v-else v-model="draft.vin" label="VIN / número de serie *" maxlength="17" :rules="vinRules"
            placeholder="1HGCM82633A004352" hint="17 caracteres, sin I/O/Q; los últimos 4 son números." persistent-hint variant="outlined" color="secondary" />
        </v-col>
        <v-col cols="12" sm="5"><v-text-field v-model="draft.plate" label="Placa mexicana *" maxlength="20" :rules="plateRules" placeholder="ABC-123-D" hint="Ejemplos: ABC-123-D, A12-BCD, ABC-12-34, 123-ABC." persistent-hint variant="outlined" color="secondary" /></v-col>
      </v-row>
      <h3 class="mt-2 mb-3">Datos del vehículo</h3>
      <v-row>
        <v-col cols="12" sm="6"><v-text-field v-model="draft.make" label="Marca *" :rules="required('Marca', 60)" maxlength="60" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="6"><v-text-field v-model="draft.model" label="Modelo *" :rules="required('Modelo', 60)" maxlength="60" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="4"><v-text-field v-model="draft.year" label="Año *" inputmode="numeric" maxlength="4" :rules="yearRules" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="8"><v-text-field v-model="draft.version" label="Versión *" :rules="required('Versión', 60)" maxlength="60" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="6"><v-text-field v-model="draft.color" label="Color *" :rules="required('Color', 40)" maxlength="40" variant="outlined" color="secondary" /></v-col>
        <v-col cols="12" sm="6"><v-text-field v-model="draft.mileage" :label="vehicle ? 'Kilometraje *' : 'Kilometraje (opcional)'" inputmode="numeric" suffix="km" :rules="mileageRules" variant="outlined" color="secondary" /></v-col>
      </v-row>
      <VehiclePhotos v-model="photos" :existing-count="existingPhotoCount" :required="!!vehicle" />
      <p v-if="vehicle && !canReview" class="mb-4" role="status" aria-live="polite">{{ incompleteMessage }}</p>
      <div class="d-flex flex-wrap ga-3"><v-btn type="submit" color="secondary" :disabled="busy || (!!vehicle && !canReview)">{{ vehicle ? 'Revisar modificación' : 'Revisar vehículo' }}</v-btn><v-btn variant="text" color="secondary" @click="emit('close')">Cancelar</v-btn></div>
    </v-form>
    <div v-else>
      <h3 class="mb-4">{{ vehicle ? 'Confirmar actualización' : 'Confirmar asociación' }}</h3>
      <dl class="customer-detail"><dt>Vehículo</dt><dd>{{ review.make }} {{ review.model }} {{ review.year }}</dd><dt>Versión y color</dt><dd>{{ review.version }} · {{ review.color }}</dd><dt>VIN</dt><dd>{{ review.vin }}</dd><dt>Placa</dt><dd>{{ review.plate }}</dd><dt>Kilometraje</dt><dd>{{ review.mileage === null ? 'No registrado' : `${review.mileage.toLocaleString('es-MX')} km` }}</dd></dl>
      <p class="my-5">{{ vehicle ? 'Se actualizará el vehículo asociado a' : 'El vehículo se registrará activo y asociado a' }} <strong>{{ customer.fullName }}</strong>.</p>
      <p class="mb-5">{{ photos.length }} fotos nuevas de hasta 15 MB. {{ existingPhotoCount ? `Se conservan las ${existingPhotoCount} fotos anteriores.` : '' }}</p>
      <div class="d-flex flex-wrap ga-3"><v-btn color="secondary" :loading="busy" :disabled="!canReview" @click="confirm">{{ vehicle ? 'Confirmar cambios' : 'Confirmar y asociar' }}</v-btn><v-btn variant="outlined" color="secondary" :disabled="busy" @click="review = null">Editar datos</v-btn><v-btn variant="text" color="secondary" :disabled="busy" @click="emit('close')">Cancelar</v-btn></div>
    </div>
  </v-card-text></v-card>
</template>
