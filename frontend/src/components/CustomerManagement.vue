<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CustomerRegistration from '@/components/CustomerRegistration.vue'
import VehicleRegistration from '@/components/VehicleRegistration.vue'
import { ApiError } from '@/services/auth'
import { deleteCustomer, getCustomer, listCustomers, listVehicles } from '@/services/customers'
import type { Customer, Vehicle } from '@/services/customers'

const props = defineProps<{ role: string }>()
const emit = defineEmits<{ vehicle: [id: number] }>()
const canCreate = computed(() => ['ADMINISTRADOR', 'RECEPCIONISTA'].includes(props.role))
const canUpdate = computed(() => ['ADMINISTRADOR', 'SECRETARIA'].includes(props.role))
const canDeactivate = computed(() => props.role === 'ADMINISTRADOR')
const vehicles = ref<Vehicle[]>([])
const vehicleTarget = ref<Customer | null>(null)

const customers = ref<Customer[]>([])
const total = ref(0)
const page = ref(1)
const search = ref<string | null>('')
const appliedSearch = ref('')
const loading = ref(false)
const fetching = ref<number | null>(null)
const errorMessage = ref('')
const notice = ref('')
const editorOpen = ref(false)
const editTarget = ref<Customer | undefined>(undefined)
const detail = ref<Customer | null>(null)
const deleteTarget = ref<Customer | null>(null)
const deleting = ref(false)
const deleteError = ref('')
const pages = computed(() => Math.max(1, Math.ceil(total.value / 10)))
let loadSequence = 0
const message = (error: unknown): string => error instanceof ApiError ? error.message : 'No se pudo completar la operación. Intenta nuevamente.'
const initials = (name: string): string => name.split(' ').filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase()

async function load(): Promise<void> {
  const sequence = ++loadSequence
  loading.value = true; errorMessage.value = ''
  try {
    let result = await listCustomers(page.value, appliedSearch.value)
    if (sequence !== loadSequence) return
    const lastPage = Math.max(1, Math.ceil(result.total / 10))
    if (page.value > lastPage) {
      page.value = lastPage
      result = await listCustomers(page.value, appliedSearch.value)
    }
    if (sequence !== loadSequence) return
    customers.value = result.items; total.value = result.total
  } catch (error) { if (sequence === loadSequence) errorMessage.value = message(error) }
  finally { if (sequence === loadSequence) loading.value = false }
}
function applySearch(): void { appliedSearch.value = (search.value ?? '').trim(); page.value = 1; void load() }
function clearSearch(): void { search.value = ''; applySearch() }
function changePage(value: number): void { page.value = value; void load() }
function create(): void { if (!canCreate.value) return; editTarget.value = undefined; editorOpen.value = true }
async function inspect(customer: Customer, edit: boolean): Promise<void> {
  fetching.value = customer.id; errorMessage.value = ''
  try {
    const current = await getCustomer(customer.id)
    if (edit && canUpdate.value) { editTarget.value = current; editorOpen.value = true }
    else { vehicles.value = await listVehicles(current.id); detail.value = current }
  } catch (error) { errorMessage.value = message(error) }
  finally { fetching.value = null }
}
function saved(customer: Customer): void {
  notice.value = `${customer.fullName} ${editTarget.value ? 'actualizado' : 'registrado'} correctamente.`
  editorOpen.value = false
  void load()
}
function askDelete(customer: Customer): void { if (!canDeactivate.value) return; deleteTarget.value = customer; deleteError.value = '' }
async function associate(customer: Customer): Promise<void> {
  if (!canCreate.value || customer.status !== 'ACTIVO') return
  fetching.value = customer.id
  errorMessage.value = ''
  try {
    const current = await getCustomer(customer.id)
    if (current.status !== 'ACTIVO') throw new ApiError(409, 'El cliente debe estar activo para asociar un vehículo.')
    vehicleTarget.value = current
  } catch (error) { errorMessage.value = message(error) }
  finally { fetching.value = null }
}
function vehicleSaved(vehicle: Vehicle): void {
  notice.value = `Vehículo ${vehicle.plate} asociado a ${vehicleTarget.value?.fullName ?? 'su cliente'} correctamente.`
  vehicleTarget.value = null
}
async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value || deleting.value) return
  const target = deleteTarget.value
  deleting.value = true; deleteError.value = ''
  try {
    await deleteCustomer(target.id, target.version)
    notice.value = `${target.fullName} desactivado. Se conservan sus datos, vehículos e historial.`
    deleteTarget.value = null
    await load()
  } catch (error) { deleteError.value = message(error) }
  finally { deleting.value = false }
}
onMounted(() => { void load() })
</script>

<template>
  <section class="customers-panel module-panel clients-management-panel" aria-labelledby="customers-title">
    <div class="customers-heading module-heading">
      <div class="module-title"><span class="module-symbol"><v-icon icon="mdi-account-group-outline" size="28" /></span><div><p class="eyebrow">DIRECTORIO DEL TALLER</p><h2 id="customers-title">Clientes <span class="customer-count">{{ total }}</span></h2><p>Consulta sus datos y mantén su información al día.</p></div></div>
      <v-btn v-if="canCreate" color="secondary" prepend-icon="mdi-account-plus-outline" @click="create">Nuevo cliente</v-btn>
    </div>
    <v-alert v-if="notice" color="secondary" variant="tonal" closable class="mb-4" aria-live="polite" @click:close="notice = ''">{{ notice }}</v-alert>
    <form class="customer-toolbar" role="search" @submit.prevent="applySearch">
      <v-text-field v-model="search" label="Buscar por nombre, contacto o municipio" prepend-inner-icon="mdi-magnify" variant="outlined" color="secondary" hide-details clearable maxlength="120" @click:clear="clearSearch" />
      <v-btn type="submit" variant="flat" color="secondary" :disabled="loading">Buscar</v-btn>
      <v-btn variant="outlined" color="secondary" icon="mdi-refresh" aria-label="Actualizar listado de clientes" :loading="loading" @click="load" />
    </form>
    <v-alert v-if="errorMessage" color="secondary" variant="tonal" class="mb-4" role="alert">{{ errorMessage }} <v-btn variant="text" color="secondary" @click="load">Reintentar</v-btn></v-alert>
    <div v-if="loading" class="customer-empty" role="status"><v-progress-circular indeterminate color="secondary" /><p>Cargando clientes…</p></div>
    <div v-else-if="!customers.length && !errorMessage" class="customer-empty">
      <v-icon size="48" color="secondary">mdi-account-search-outline</v-icon>
      <h3>{{ appliedSearch ? 'No encontramos coincidencias' : 'Aún no hay clientes registrados' }}</h3>
      <p>{{ appliedSearch ? 'Prueba con otro nombre, contacto o municipio.' : 'Registra al primer cliente para comenzar tu directorio.' }}</p>
      <v-btn v-if="appliedSearch || canCreate" color="secondary" variant="outlined" @click="appliedSearch ? clearSearch() : create()">{{ appliedSearch ? 'Ver todos los clientes' : 'Registrar cliente' }}</v-btn>
    </div>
    <template v-else-if="customers.length">
      <div class="customer-table-wrap">
        <table class="customer-table"><caption class="sr-only">Listado de clientes del taller</caption>
          <thead><tr><th scope="col">Cliente</th><th scope="col">Taller</th><th scope="col">Contacto</th><th scope="col">Dirección</th><th scope="col">Acciones</th></tr></thead>
          <tbody><tr v-for="customer in customers" :key="customer.id">
            <td><div class="customer-person"><span class="customer-avatar" aria-hidden="true">{{ initials(customer.fullName) }}</span><div><button class="customer-name-button" :disabled="fetching !== null" :aria-label="`${canUpdate ? 'Actualizar' : 'Ver datos de'} ${customer.fullName}`" @click="inspect(customer, canUpdate)">{{ customer.fullName }}</button><small>{{ customer.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</small></div></div></td>
            <td><span class="customer-workshop-name">{{ customer.workshopName || 'Sin taller · registro anterior' }}</span></td>
            <td><div class="customer-contact"><span v-if="customer.contacts.email"><v-icon size="15">mdi-email-outline</v-icon>{{ customer.contacts.email }}</span><span v-if="customer.contacts.mobile"><v-icon size="15">mdi-cellphone</v-icon>{{ customer.contacts.mobile }}</span><span v-if="customer.contacts.alternative"><v-icon size="15">mdi-phone-outline</v-icon>{{ customer.contacts.alternative }} <small>Alternativo</small></span></div></td>
            <td><div class="customer-address">{{ customer.address.street }} {{ customer.address.number }}<small>{{ customer.address.neighborhood }}</small><small>{{ customer.address.municipality }}, {{ customer.address.state }}</small></div></td>
            <td><div class="customer-actions">
              <v-btn icon="mdi-eye-outline" size="small" variant="text" color="secondary" :aria-label="`Ver datos de ${customer.fullName}`" title="Ver datos" :disabled="fetching !== null" @click="inspect(customer, false)" />
              <v-btn v-if="canUpdate" icon="mdi-pencil-outline" size="small" variant="text" color="secondary" :aria-label="`Editar datos de ${customer.fullName}`" title="Actualizar" :disabled="fetching !== null" @click="inspect(customer, true)" />
              <v-btn v-if="canCreate && customer.status === 'ACTIVO'" icon="mdi-car-plus" size="small" variant="text" color="secondary" :aria-label="`Asociar vehículo a ${customer.fullName}`" title="Asociar vehículo" :disabled="fetching !== null" @click="associate(customer)" />
              <v-btn v-if="canDeactivate" icon="mdi-account-off-outline" size="small" variant="text" color="secondary" :aria-label="`Desactivar ${customer.fullName}`" title="Desactivar" @click="askDelete(customer)" />
            </div></td>
          </tr></tbody>
        </table>
      </div>
      <div class="customer-mobile-list">
        <article v-for="customer in customers" :key="customer.id" class="customer-mobile-card">
          <div class="customer-person"><span class="customer-avatar" aria-hidden="true">{{ initials(customer.fullName) }}</span><div><h3><button class="customer-name-button" :disabled="fetching !== null" @click="inspect(customer, canUpdate)">{{ customer.fullName }}</button></h3><small>{{ customer.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</small></div></div>
          <p class="customer-workshop-name"><v-icon icon="mdi-garage-variant" size="18" /> {{ customer.workshopName || 'Sin taller · registro anterior' }}</p>
          <div class="customer-contact"><span v-if="customer.contacts.email"><v-icon size="16">mdi-email-outline</v-icon>{{ customer.contacts.email }}</span><span v-if="customer.contacts.mobile"><v-icon size="16">mdi-cellphone</v-icon>{{ customer.contacts.mobile }}</span><span v-if="customer.contacts.alternative"><v-icon size="16">mdi-phone-outline</v-icon>{{ customer.contacts.alternative }} (alternativo)</span></div>
          <p class="customer-address">{{ customer.address.street }} {{ customer.address.number }}, {{ customer.address.neighborhood }}<small>{{ customer.address.municipality }}, {{ customer.address.state }}</small></p>
          <div class="customer-mobile-actions"><v-btn size="small" variant="text" color="secondary" :disabled="fetching !== null" @click="inspect(customer, false)">Ver datos</v-btn><v-btn v-if="canUpdate" size="small" variant="text" color="secondary" :disabled="fetching !== null" @click="inspect(customer, true)">Actualizar</v-btn><v-btn v-if="canCreate && customer.status === 'ACTIVO'" size="small" variant="text" color="secondary" :disabled="fetching !== null" @click="associate(customer)">Asociar vehículo</v-btn><v-btn v-if="canDeactivate" size="small" variant="text" color="secondary" @click="askDelete(customer)">Desactivar</v-btn></div>
        </article>
      </div>
      <footer class="customer-footer"><span>{{ (page - 1) * 10 + 1 }}–{{ Math.min(page * 10, total) }} de {{ total }} clientes</span><v-pagination v-if="pages > 1" :model-value="page" :length="pages" :total-visible="4" :disabled="loading" color="secondary" density="comfortable" @update:model-value="changePage" /></footer>
    </template>
  </section>

  <v-dialog v-model="editorOpen" max-width="820" persistent scrollable aria-label="Formulario de cliente">
    <CustomerRegistration v-if="editorOpen" :key="editTarget?.id ?? 'new'" :initial-open="true" :customer="editTarget" @saved="saved" @close="editorOpen = false" />
  </v-dialog>
  <v-dialog :model-value="detail !== null" max-width="620" @update:model-value="detail = null">
    <v-card v-if="detail" class="customer-dialog"><v-card-text>
      <p class="eyebrow">EXPEDIENTE DEL CLIENTE</p><h2>{{ detail.fullName }}</h2><v-chip class="my-3" color="secondary" variant="tonal">{{ detail.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</v-chip>
      <div class="customer-workshop-summary"><v-icon icon="mdi-garage-variant" /><div><span>Taller asociado</span><strong>{{ detail.workshopName || 'Sin taller · registro anterior' }}</strong></div></div>
      <h3 class="mt-4 mb-2">Dirección</h3><dl class="customer-detail"><dt>Calle y número</dt><dd>{{ detail.address.street }} {{ detail.address.number }}</dd><dt>Colonia</dt><dd>{{ detail.address.neighborhood }}</dd><dt>Municipio</dt><dd>{{ detail.address.municipality }}</dd><dt>Estado</dt><dd>{{ detail.address.state }}</dd></dl>
      <h3 class="mt-5 mb-2">Contacto</h3><dl class="customer-detail"><dt>Correo</dt><dd>{{ detail.contacts.email || 'No registrado' }}</dd><dt>Celular</dt><dd>{{ detail.contacts.mobile || 'No registrado' }}</dd><dt>Alternativo</dt><dd>{{ detail.contacts.alternative || 'No registrado' }}</dd></dl>
      <h3 class="mt-5 mb-3">Vehículos asociados <span class="customer-count">{{ vehicles.length }}</span></h3>
      <p v-if="!vehicles.length">Este cliente aún no tiene vehículos registrados.</p>
      <article v-for="vehicle in vehicles" :key="vehicle.id" class="customer-vehicle-card"><v-icon icon="mdi-car-outline" /><div><strong>{{ vehicle.make }} {{ vehicle.model }} · {{ vehicle.year }}</strong><span>{{ vehicle.plate }} · {{ vehicle.color }} · {{ vehicle.version }}</span><small>VIN: {{ vehicle.vin }}</small><small>{{ vehicle.mileage === null ? 'Kilometraje no registrado' : `${vehicle.mileage.toLocaleString('es-MX')} km` }} · {{ vehicle.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</small><v-btn variant="text" size="small" color="secondary" @click="emit('vehicle', vehicle.id)">Consultar expediente y fotos</v-btn></div></article>
    </v-card-text><v-card-actions><v-btn color="secondary" variant="text" @click="detail = null">Cerrar</v-btn></v-card-actions></v-card>
  </v-dialog>
  <v-dialog :model-value="deleteTarget !== null" max-width="500" persistent aria-label="Confirmar eliminación de cliente">
    <v-card v-if="deleteTarget" class="customer-dialog"><v-card-text>
      <v-icon color="secondary" size="38" class="mb-3">mdi-account-off-outline</v-icon><h2>¿Desactivar este cliente?</h2>
      <p class="mt-4"><strong>{{ deleteTarget.fullName }}</strong></p><p class="mt-3">Quedará inactivo y no podrá recibir nuevos vehículos. Se conservarán sus datos, vehículos y auditorías.</p>
      <v-alert v-if="deleteError" variant="tonal" color="secondary" class="mt-4" role="alert">{{ deleteError }}</v-alert>
    </v-card-text><v-card-actions class="flex-wrap"><v-btn color="secondary" variant="text" :disabled="deleting" @click="deleteTarget = null">Cancelar</v-btn><v-btn color="secondary" variant="flat" :loading="deleting" @click="confirmDelete">Sí, desactivar cliente</v-btn></v-card-actions></v-card>
  </v-dialog>
  <v-dialog :model-value="vehicleTarget !== null" max-width="820" persistent scrollable aria-label="Registrar vehículo del cliente" @update:model-value="vehicleTarget = null"><VehicleRegistration v-if="vehicleTarget" :customer="vehicleTarget" @saved="vehicleSaved" @close="vehicleTarget = null" /></v-dialog>
</template>
