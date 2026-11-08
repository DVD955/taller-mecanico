<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/services/auth'
import { getCustomer, listCustomers } from '@/services/customers'
import type { Customer, Vehicle } from '@/services/customers'
import { changeVehicleOwner, deactivateVehicle, getVehicleDetails, searchVehicles } from '@/services/vehicles'
import type { VehicleDetails, VehicleListItem } from '@/services/vehicles'
import VehicleRegistration from '@/components/VehicleRegistration.vue'
import VehicleGallery from '@/components/VehicleGallery.vue'

const props = defineProps<{ role: string; initialVehicleId?: number }>()
const canWrite = computed(() => ['ADMINISTRADOR', 'RECEPCIONISTA'].includes(props.role))
const canDeactivate = computed(() => props.role === 'ADMINISTRADOR')
const items = ref<VehicleListItem[]>([])
const total = ref(0)
const page = ref(1)
const search = ref('')
const appliedSearch = ref('')
const status = ref('all')
const pages = computed(() => Math.max(1, Math.ceil(total.value / 10)))
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const detail = ref<VehicleDetails | null>(null)
const editing = ref<VehicleDetails | null>(null)
const deleting = ref<VehicleDetails | null>(null)
const ownerTarget = ref<VehicleDetails | null>(null)
const dialogError = ref('')
const customerDetail = ref<Customer | null>(null)
const registering = ref<Customer | null>(null)
const pickerOpen = ref(false)
const customerSearch = ref('')
const customerPage = ref(1)
const customerTotal = ref(0)
const customers = ref<Customer[]>([])
const selectedCustomer = ref<Customer | null>(null)
const customerLoading = ref(false)
let sequence = 0
let customerSequence = 0
const message = (reason: unknown): string => reason instanceof ApiError ? reason.message : 'No se pudo completar la operación.'
const date = (value: string): string => new Date(value).toLocaleString('es-MX')

async function load(): Promise<void> {
  const current = ++sequence
  loading.value = true; error.value = ''
  try {
    let result = await searchVehicles(page.value, appliedSearch.value, status.value)
    if (current !== sequence) return
    const lastPage = Math.max(1, Math.ceil(result.total / 10))
    if (page.value > lastPage) { page.value = lastPage; result = await searchVehicles(page.value, appliedSearch.value, status.value) }
    if (current !== sequence) return
    items.value = result.items; total.value = result.total
  } catch (reason) { if (current === sequence) error.value = message(reason) }
  finally { if (current === sequence) loading.value = false }
}
function applySearch(): void { appliedSearch.value = search.value.trim(); page.value = 1; void load() }
async function inspect(id: number, action: 'detail' | 'edit' | 'delete' | 'owner' = 'detail'): Promise<void> {
  if (busy.value) return
  busy.value = true; error.value = ''; dialogError.value = ''
  try {
    const current = await getVehicleDetails(id)
    if (action === 'edit' && canWrite.value) editing.value = current
    else if (action === 'delete' && canDeactivate.value) deleting.value = current
    else if (action === 'owner' && canWrite.value) { ownerTarget.value = current; openPicker() }
    else detail.value = current
  } catch (reason) { error.value = message(reason) }
  finally { busy.value = false }
}
async function showCustomer(): Promise<void> {
  if (!detail.value) return
  busy.value = true; dialogError.value = ''
  try { customerDetail.value = await getCustomer(detail.value.vehicle.customerId) }
  catch (reason) { dialogError.value = message(reason) }
  finally { busy.value = false }
}
function saved(vehicle: Vehicle): void {
  notice.value = `Vehículo ${vehicle.plate} ${editing.value ? 'actualizado' : 'registrado'} correctamente.`
  editing.value = null; registering.value = null
  void load()
}
async function confirmDeactivate(): Promise<void> {
  if (!deleting.value || busy.value) return
  busy.value = true; dialogError.value = ''
  try {
    await deactivateVehicle(deleting.value.vehicle.id, deleting.value.vehicle.recordVersion)
    deleting.value = null; notice.value = 'Vehículo inactivo. Se conservan sus datos, fotos, cliente e historial.'
    await load()
  } catch (reason) { dialogError.value = message(reason) }
  finally { busy.value = false }
}
function openPicker(): void {
  pickerOpen.value = true; selectedCustomer.value = null; customerSearch.value = ''; customerPage.value = 1; dialogError.value = ''
  void loadCustomers()
}
function startCreate(): void { ownerTarget.value = null; openPicker() }
async function loadCustomers(): Promise<void> {
  const current = ++customerSequence
  customerLoading.value = true; dialogError.value = ''
  try {
    const result = await listCustomers(customerPage.value, customerSearch.value.trim())
    if (current !== customerSequence) return
    customers.value = result.items.filter(customer => customer.status === 'ACTIVO' && customer.id !== ownerTarget.value?.vehicle.customerId)
    customerTotal.value = result.total
  } catch (reason) { if (current === customerSequence) dialogError.value = message(reason) }
  finally { if (current === customerSequence) customerLoading.value = false }
}
function searchCustomers(): void { customerPage.value = 1; selectedCustomer.value = null; void loadCustomers() }
async function chooseCustomer(): Promise<void> {
  if (!selectedCustomer.value || busy.value) return
  if (!ownerTarget.value) { registering.value = selectedCustomer.value; pickerOpen.value = false; return }
  busy.value = true; dialogError.value = ''
  try {
    await changeVehicleOwner(ownerTarget.value.vehicle.id, selectedCustomer.value.id, ownerTarget.value.vehicle.recordVersion)
    pickerOpen.value = false; ownerTarget.value = null
    notice.value = 'Cliente del vehículo actualizado. Se conserva la asociación anterior en la auditoría.'
    await load()
  } catch (reason) { dialogError.value = message(reason) }
  finally { busy.value = false }
}
onMounted(() => { void load(); if (props.initialVehicleId) void inspect(props.initialVehicleId) })
</script>

<template>
  <section class="module-panel vehicles-panel" aria-labelledby="vehicles-title">
    <div class="module-heading"><div class="module-title"><span class="module-symbol"><v-icon icon="mdi-car-multiple" size="28" /></span><div><p class="eyebrow">CONTROL VEHICULAR</p><h2 id="vehicles-title">Vehículos <span class="customer-count">{{ total }}</span></h2><p>Identificación, propietario y fotografías en un solo expediente.</p></div></div><v-btn v-if="canWrite" color="secondary" prepend-icon="mdi-car-plus" @click="startCreate">Registrar vehículo</v-btn></div>
    <v-alert v-if="notice" color="secondary" variant="tonal" closable class="mb-4" aria-live="polite" @click:close="notice = ''">{{ notice }}</v-alert>
    <form class="customer-toolbar vehicle-toolbar" role="search" @submit.prevent="applySearch"><v-text-field v-model="search" label="Buscar por placa, VIN, marca, modelo o cliente" maxlength="120" prepend-inner-icon="mdi-magnify" hide-details variant="outlined" color="secondary" /><v-select v-model="status" label="Estado" :items="[{ title: 'Todos', value: 'all' }, { title: 'Activos', value: 'active' }, { title: 'Inactivos', value: 'inactive' }]" hide-details variant="outlined" color="secondary" @update:model-value="applySearch" /><v-btn type="submit" color="secondary" :disabled="loading">Buscar</v-btn><v-btn icon="mdi-refresh" variant="outlined" color="secondary" aria-label="Actualizar vehículos" :loading="loading" @click="load" /></form>
    <v-alert v-if="error" color="secondary" variant="tonal" role="alert" class="mb-4">{{ error }} <v-btn variant="text" @click="load">Reintentar</v-btn></v-alert>
    <div v-if="loading" class="customer-empty" role="status"><v-progress-circular indeterminate color="secondary" /><p>Cargando vehículos…</p></div>
    <div v-else-if="!items.length && !error" class="customer-empty"><v-icon icon="mdi-car-search-outline" size="48" /><h3>No hay vehículos para esta búsqueda</h3><p>Revisa los filtros o registra un vehículo asociado a un cliente activo.</p></div>
    <div v-else class="vehicle-records">
      <article v-for="item in items" :key="item.vehicle.id" class="vehicle-record">
        <div class="vehicle-record-identification"><span class="vehicle-record-icon"><v-icon icon="mdi-car-side" size="30" /></span><div><button class="customer-name-button vehicle-plate" :disabled="busy" :aria-label="`Consultar vehículo ${item.vehicle.plate}`" @click="inspect(item.vehicle.id)">{{ item.vehicle.plate }}</button><h3>{{ item.vehicle.make }} {{ item.vehicle.model }} · {{ item.vehicle.year }}</h3><small>VIN {{ item.vehicle.vin }}</small></div></div>
        <div class="vehicle-record-owner"><span class="eyebrow">CLIENTE ASOCIADO</span><strong>{{ item.customerName }}</strong><small>{{ item.workshopName || 'Sin taller · registro anterior' }}</small></div>
        <div class="vehicle-record-state"><v-chip size="small" color="secondary" :variant="item.vehicle.status === 'ACTIVO' ? 'tonal' : 'outlined'">{{ item.vehicle.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</v-chip><small><v-icon icon="mdi-image-multiple-outline" size="16" /> {{ item.photoCount }} fotos</small></div>
        <div class="customer-actions"><v-btn icon="mdi-eye-outline" variant="text" size="small" color="secondary" title="Consultar expediente" :aria-label="`Consultar ${item.vehicle.plate}`" :disabled="busy" @click="inspect(item.vehicle.id)" /><template v-if="item.vehicle.status === 'ACTIVO'"><v-btn v-if="canWrite" icon="mdi-pencil-outline" variant="text" size="small" color="secondary" title="Actualizar vehículo" :aria-label="`Actualizar ${item.vehicle.plate}`" :disabled="busy" @click="inspect(item.vehicle.id, 'edit')" /><v-btn v-if="canWrite" icon="mdi-account-switch-outline" variant="text" size="small" color="secondary" title="Cambiar cliente" :aria-label="`Cambiar cliente de ${item.vehicle.plate}`" :disabled="busy" @click="inspect(item.vehicle.id, 'owner')" /><v-btn v-if="canDeactivate" icon="mdi-car-off" variant="text" size="small" color="secondary" title="Desactivar vehículo" :aria-label="`Desactivar ${item.vehicle.plate}`" :disabled="busy" @click="inspect(item.vehicle.id, 'delete')" /></template></div>
      </article>
    </div>
    <footer v-if="total" class="customer-footer"><span>{{ total }} vehículos encontrados</span><v-pagination v-if="pages > 1" v-model="page" :length="pages" :total-visible="4" color="secondary" :disabled="loading" @update:model-value="load" /></footer>
  </section>

  <v-dialog :model-value="detail !== null" max-width="900" scrollable @update:model-value="detail = null">
    <v-card v-if="detail" class="customer-dialog"><v-card-text class="d-block"><p class="eyebrow">EXPEDIENTE DEL VEHÍCULO</p><h2>{{ detail.vehicle.plate }}</h2><p class="subtitle">{{ detail.vehicle.make }} {{ detail.vehicle.model }} · {{ detail.vehicle.year }}</p><div class="vehicle-detail-grid"><div><dl class="customer-detail"><dt>VIN</dt><dd>{{ detail.vehicle.vin }}</dd><dt>Versión</dt><dd>{{ detail.vehicle.version }}</dd><dt>Color</dt><dd>{{ detail.vehicle.color }}</dd><dt>Kilometraje</dt><dd>{{ detail.vehicle.mileage === null ? 'No registrado' : `${detail.vehicle.mileage.toLocaleString('es-MX')} km` }}</dd><dt>Estado</dt><dd>{{ detail.vehicle.status === 'ACTIVO' ? 'Activo' : 'Inactivo · baja lógica' }}</dd><dt>Cliente</dt><dd>{{ detail.customerName }}</dd><dt>Taller</dt><dd>{{ detail.workshopName || 'Sin taller · registro anterior' }}</dd></dl><v-btn variant="outlined" color="secondary" class="my-4" :loading="busy" @click="showCustomer">Consultar cliente asociado</v-btn><v-alert v-if="dialogError" color="secondary" variant="tonal" role="alert">{{ dialogError }}</v-alert></div><VehicleGallery :vehicle-id="detail.vehicle.id" :photos="detail.photos" /></div><h3 class="mt-6 mb-3">Historial de movimientos</h3><p class="subtitle">Últimos 100 movimientos. La auditoría completa se conserva en la base de datos.</p><ol class="vehicle-audit"><li v-for="entry in detail.auditEntries" :key="entry.id"><strong>{{ entry.action.replace(/^UC-CV-\d+ /, '').replace(/([a-z])([A-Z])/g, '$1 $2') }}</strong><span>{{ entry.actorUsername }} · {{ date(entry.occurredAt) }}</span><small v-if="entry.previousCustomerId">Cambio de cliente con asociación anterior conservada.</small></li></ol></v-card-text><v-card-actions><v-btn color="secondary" variant="text" @click="detail = null">Cerrar</v-btn></v-card-actions></v-card>
  </v-dialog>
  <v-dialog :model-value="editing !== null || registering !== null" max-width="840" persistent scrollable><VehicleRegistration v-if="editing || registering" :key="editing?.vehicle.id ?? 'new'" :customer="registering ?? { id: editing!.vehicle.customerId, fullName: editing!.customerName, workshopName: editing!.workshopName }" :vehicle="editing?.vehicle" :existing-photo-count="editing?.photos.length" @saved="saved" @close="editing = null; registering = null" /></v-dialog>
  <v-dialog :model-value="deleting !== null" max-width="520" persistent><v-card v-if="deleting" class="customer-dialog"><v-card-text><p class="eyebrow">BAJA LÓGICA</p><h2>¿Desactivar {{ deleting.vehicle.plate }}?</h2><p class="mt-4">El vehículo quedará inactivo. No se borrarán sus fotos, datos, relación con {{ deleting.customerName }} ni historial.</p><v-alert v-if="dialogError" color="secondary" variant="tonal" class="mt-4" role="alert">{{ dialogError }}</v-alert></v-card-text><v-card-actions class="flex-wrap"><v-btn :disabled="busy" color="secondary" variant="text" @click="deleting = null">Cancelar</v-btn><v-btn :loading="busy" color="secondary" @click="confirmDeactivate">Confirmar baja</v-btn></v-card-actions></v-card></v-dialog>
  <v-dialog v-model="pickerOpen" max-width="700" persistent scrollable><v-card class="customer-dialog"><v-card-text class="d-block"><p class="eyebrow">ASOCIACIÓN CLIENTE–VEHÍCULO</p><h2>{{ ownerTarget ? 'Cambiar cliente del vehículo' : 'Seleccionar cliente activo' }}</h2><p class="subtitle">{{ ownerTarget ? `Vehículo ${ownerTarget.vehicle.plate}. Cliente actual: ${ownerTarget.customerName}.` : 'El vehículo quedará asociado al cliente que selecciones.' }}</p><form class="customer-toolbar" @submit.prevent="searchCustomers"><v-text-field v-model="customerSearch" label="Buscar cliente por nombre o contacto" maxlength="120" variant="outlined" color="secondary" hide-details /><v-btn type="submit" color="secondary" :loading="customerLoading">Buscar</v-btn></form><v-select v-model="selectedCustomer" :items="customers" item-title="fullName" item-value="id" return-object label="Cliente activo" :loading="customerLoading" variant="outlined" color="secondary" no-data-text="No hay clientes activos en esta página. Busca por nombre o cambia de página." /><div v-if="selectedCustomer" class="customer-workshop-summary"><v-icon icon="mdi-account-check-outline" /><div><strong>{{ selectedCustomer.fullName }}</strong><span>{{ selectedCustomer.workshopName || 'Sin taller · registro anterior' }}</span><small>{{ selectedCustomer.contacts.email || selectedCustomer.contacts.mobile }}</small></div></div><v-pagination v-if="customerTotal > 10" v-model="customerPage" :length="Math.ceil(customerTotal / 10)" :total-visible="4" :disabled="customerLoading" color="secondary" @update:model-value="loadCustomers" /><p v-if="ownerTarget" class="mt-4">Al confirmar se conservarán el vehículo y sus fotos. La auditoría registrará el cliente anterior y el nuevo. No se modifica el taller de ningún cliente.</p><v-alert v-if="dialogError" color="secondary" variant="tonal" class="mt-4" role="alert">{{ dialogError }}</v-alert></v-card-text><v-card-actions class="flex-wrap"><v-btn :disabled="busy" color="secondary" variant="text" @click="pickerOpen = false; ownerTarget = null">Cancelar</v-btn><v-btn :disabled="!selectedCustomer || customerLoading" :loading="busy" color="secondary" @click="chooseCustomer">{{ ownerTarget ? 'Confirmar cambio de cliente' : 'Continuar al registro' }}</v-btn></v-card-actions></v-card></v-dialog>
  <v-dialog :model-value="customerDetail !== null" max-width="600" @update:model-value="customerDetail = null"><v-card v-if="customerDetail" class="customer-dialog"><v-card-text><p class="eyebrow">CLIENTE ASOCIADO</p><h2>{{ customerDetail.fullName }}</h2><dl class="customer-detail mt-5"><dt>Taller</dt><dd>{{ customerDetail.workshopName || 'Sin taller · registro anterior' }}</dd><dt>Correo</dt><dd>{{ customerDetail.contacts.email || 'No registrado' }}</dd><dt>Celular</dt><dd>{{ customerDetail.contacts.mobile || 'No registrado' }}</dd><dt>Alternativo</dt><dd>{{ customerDetail.contacts.alternative || 'No registrado' }}</dd><dt>Dirección</dt><dd>{{ customerDetail.address.street }} {{ customerDetail.address.number }}, {{ customerDetail.address.neighborhood }}, {{ customerDetail.address.municipality }}, {{ customerDetail.address.state }}</dd></dl></v-card-text><v-card-actions><v-btn color="secondary" variant="text" @click="customerDetail = null">Cerrar</v-btn></v-card-actions></v-card></v-dialog>
</template>
