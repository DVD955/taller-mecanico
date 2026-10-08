<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CustomerRegistration from '@/components/CustomerRegistration.vue'
import { ApiError } from '@/services/auth'
import { deleteCustomer, getCustomer, listCustomers } from '@/services/customers'
import type { Customer } from '@/services/customers'

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
function create(): void { editTarget.value = undefined; editorOpen.value = true }
async function inspect(customer: Customer, edit: boolean): Promise<void> {
  fetching.value = customer.id; errorMessage.value = ''
  try {
    const current = await getCustomer(customer.id)
    if (edit) { editTarget.value = current; editorOpen.value = true }
    else detail.value = current
  } catch (error) { errorMessage.value = message(error) }
  finally { fetching.value = null }
}
function saved(customer: Customer): void {
  notice.value = `Cliente #${customer.id} ${customer.fullName} ${editTarget.value ? 'actualizado' : 'registrado'} correctamente.`
  editorOpen.value = false
  void load()
}
function askDelete(customer: Customer): void { deleteTarget.value = customer; deleteError.value = '' }
async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value || deleting.value) return
  const target = deleteTarget.value
  deleting.value = true; deleteError.value = ''
  try {
    await deleteCustomer(target.id, target.version)
    notice.value = `Cliente #${target.id} ${target.fullName} eliminado del listado. Su historial se conserva.`
    deleteTarget.value = null
    await load()
  } catch (error) { deleteError.value = message(error) }
  finally { deleting.value = false }
}
onMounted(() => { void load() })
</script>

<template>
  <section class="customers-panel" aria-labelledby="customers-title">
    <div class="customers-heading">
      <div><p class="eyebrow">DIRECTORIO DEL TALLER</p><h2 id="customers-title">Clientes <span class="customer-count">{{ total }}</span></h2><p>Consulta sus datos y mantén su información al día.</p></div>
      <v-btn color="secondary" prepend-icon="mdi-account-plus-outline" @click="create">Nuevo cliente</v-btn>
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
      <v-btn color="secondary" variant="outlined" @click="appliedSearch ? clearSearch() : create()">{{ appliedSearch ? 'Ver todos los clientes' : 'Registrar cliente' }}</v-btn>
    </div>
    <template v-else-if="customers.length">
      <div class="customer-table-wrap">
        <table class="customer-table"><caption class="sr-only">Listado de clientes del taller</caption>
          <thead><tr><th scope="col">Cliente</th><th scope="col">Contacto</th><th scope="col">Dirección</th><th scope="col">Acciones</th></tr></thead>
          <tbody><tr v-for="customer in customers" :key="customer.id">
            <td><div class="customer-person"><span class="customer-avatar" aria-hidden="true">{{ initials(customer.fullName) }}</span><div><strong>{{ customer.fullName }}</strong><small>#{{ customer.id }} · {{ customer.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</small></div></div></td>
            <td><div class="customer-contact"><span v-if="customer.contacts.email"><v-icon size="15">mdi-email-outline</v-icon>{{ customer.contacts.email }}</span><span v-if="customer.contacts.mobile"><v-icon size="15">mdi-cellphone</v-icon>{{ customer.contacts.mobile }}</span><span v-if="customer.contacts.alternative"><v-icon size="15">mdi-phone-outline</v-icon>{{ customer.contacts.alternative }} <small>Alternativo</small></span></div></td>
            <td><div class="customer-address">{{ customer.address.street }} {{ customer.address.number }}<small>{{ customer.address.neighborhood }}</small><small>{{ customer.address.municipality }}, {{ customer.address.state }}</small></div></td>
            <td><div class="customer-actions">
              <v-btn icon="mdi-eye-outline" size="small" variant="text" color="secondary" :aria-label="`Ver datos de ${customer.fullName}`" title="Ver datos" :disabled="fetching !== null" @click="inspect(customer, false)" />
              <v-btn icon="mdi-pencil-outline" size="small" variant="text" color="secondary" :aria-label="`Actualizar ${customer.fullName}`" title="Actualizar" :disabled="fetching !== null" @click="inspect(customer, true)" />
              <v-btn icon="mdi-trash-can-outline" size="small" variant="text" color="secondary" :aria-label="`Eliminar ${customer.fullName}`" title="Eliminar" @click="askDelete(customer)" />
            </div></td>
          </tr></tbody>
        </table>
      </div>
      <div class="customer-mobile-list">
        <article v-for="customer in customers" :key="customer.id" class="customer-mobile-card">
          <div class="customer-person"><span class="customer-avatar" aria-hidden="true">{{ initials(customer.fullName) }}</span><div><h3>{{ customer.fullName }}</h3><small>#{{ customer.id }} · {{ customer.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</small></div></div>
          <div class="customer-contact"><span v-if="customer.contacts.email"><v-icon size="16">mdi-email-outline</v-icon>{{ customer.contacts.email }}</span><span v-if="customer.contacts.mobile"><v-icon size="16">mdi-cellphone</v-icon>{{ customer.contacts.mobile }}</span><span v-if="customer.contacts.alternative"><v-icon size="16">mdi-phone-outline</v-icon>{{ customer.contacts.alternative }} (alternativo)</span></div>
          <p class="customer-address">{{ customer.address.street }} {{ customer.address.number }}, {{ customer.address.neighborhood }}<small>{{ customer.address.municipality }}, {{ customer.address.state }}</small></p>
          <div class="customer-mobile-actions"><v-btn size="small" variant="text" color="secondary" :disabled="fetching !== null" @click="inspect(customer, false)">Ver datos</v-btn><v-btn size="small" variant="text" color="secondary" :disabled="fetching !== null" @click="inspect(customer, true)">Actualizar</v-btn><v-btn size="small" variant="text" color="secondary" @click="askDelete(customer)">Eliminar</v-btn></div>
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
      <p class="eyebrow">CLIENTE #{{ detail.id }}</p><h2>{{ detail.fullName }}</h2><v-chip class="my-3" color="secondary" variant="tonal">{{ detail.status === 'ACTIVO' ? 'Activo' : 'Inactivo' }}</v-chip>
      <h3 class="mt-4 mb-2">Dirección</h3><dl class="customer-detail"><dt>Calle y número</dt><dd>{{ detail.address.street }} {{ detail.address.number }}</dd><dt>Colonia</dt><dd>{{ detail.address.neighborhood }}</dd><dt>Municipio</dt><dd>{{ detail.address.municipality }}</dd><dt>Estado</dt><dd>{{ detail.address.state }}</dd></dl>
      <h3 class="mt-5 mb-2">Contacto</h3><dl class="customer-detail"><dt>Correo</dt><dd>{{ detail.contacts.email || 'No registrado' }}</dd><dt>Celular</dt><dd>{{ detail.contacts.mobile || 'No registrado' }}</dd><dt>Alternativo</dt><dd>{{ detail.contacts.alternative || 'No registrado' }}</dd></dl>
    </v-card-text><v-card-actions><v-btn color="secondary" variant="text" @click="detail = null">Cerrar</v-btn></v-card-actions></v-card>
  </v-dialog>
  <v-dialog :model-value="deleteTarget !== null" max-width="500" persistent aria-label="Confirmar eliminación de cliente">
    <v-card v-if="deleteTarget" class="customer-dialog"><v-card-text>
      <v-icon color="secondary" size="38" class="mb-3">mdi-account-remove-outline</v-icon><h2>¿Eliminar este cliente?</h2>
      <p class="mt-4"><strong>{{ deleteTarget.fullName }}</strong> · #{{ deleteTarget.id }}</p><p class="mt-3">Se retirará del listado y quedará inactivo. Su historial y la auditoría se conservarán. No se eliminará ninguna cuenta de acceso.</p>
      <v-alert v-if="deleteError" variant="tonal" color="secondary" class="mt-4" role="alert">{{ deleteError }}</v-alert>
    </v-card-text><v-card-actions class="flex-wrap"><v-btn color="secondary" variant="text" :disabled="deleting" @click="deleteTarget = null">Cancelar</v-btn><v-btn color="secondary" variant="flat" :loading="deleting" @click="confirmDelete">Sí, eliminar cliente</v-btn></v-card-actions></v-card>
  </v-dialog>
</template>
