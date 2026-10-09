<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/services/auth'
import { assignRole, createStaff, deleteRole, getAccounts, getRoles, getStatuses, updateRole } from '@/services/administration'
import type { Account, Role, StaffInput, Status } from '@/services/administration'

type Form = { validate: () => Promise<{ valid: boolean }> }
const roles = ref<Role[]>([])
const accounts = ref<Account[]>([])
const statuses = ref<Status[]>([])
const busy = ref(false)
const error = ref('')
const message = ref('')
const dialog = ref(false)
const editing = ref<Role | null>(null)
const name = ref('')
const description = ref('')
const state = ref(1)
const form = ref<Form | null>(null)
const deletion = ref<Role | null>(null)
const staffDialog = ref(false)
const staffForm = ref<Form | null>(null)
const staff = ref<StaffInput>({ username: '', full_name: '', email: '', password: '', role_id: 0 })
const selectedAccount = ref<number | null>(null)
const selectedRole = ref<number | null>(null)
const search = ref<string | null>('')
const statusFilter = ref(0)
const activeRoles = computed(() => roles.value.filter(role => role.bin_status === 1))
const filteredRoles = computed(() => roles.value.filter(role => {
  const query = (search.value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLocaleLowerCase('es')
  const text = `${role.name} ${role.description}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es')
  return (!statusFilter.value || role.bin_status === statusFilter.value) && text.includes(query)
}))
const assignedCount = (role: Role): number => accounts.value.filter(account => account.role_id === role.id).length
const required = [(value: unknown) => !!value || 'Este campo es obligatorio.']
const nameRules = [...required, (value: string) => value.trim().length >= 3 || 'Mínimo 3 caracteres.']
const emailRules = [...required, (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) || 'Correo no válido.']
const passwordRules = [...required, (value: string) => value.length >= 8 || 'Mínimo 8 caracteres.']
const usernameRules = [...nameRules, (value: string) => /^[a-zA-Z0-9_.-]+$/.test(value) || 'Solo letras, números, punto y guion.']
function report(cause: unknown): void { error.value = cause instanceof ApiError ? cause.message : 'No se pudo conectar con el servidor.' }
async function refresh(): Promise<void> {
  ;[roles.value, accounts.value, statuses.value] = await Promise.all([getRoles(), getAccounts(), getStatuses()])
}
onMounted(async () => { busy.value = true; try { await refresh() } catch (cause) { report(cause) } finally { busy.value = false } })
function open(role: Role): void {
  editing.value = role; name.value = role.name; description.value = role.description; state.value = role.bin_status
  error.value = ''; dialog.value = true
}
async function save(): Promise<void> {
  if (!editing.value || !(await form.value?.validate())?.valid) return
  busy.value = true; error.value = ''; message.value = ''
  try {
    await updateRole({ ...editing.value, name: name.value.trim(), description: description.value.trim(), bin_status: state.value })
    dialog.value = false; message.value = 'Rol actualizado.'; await refresh()
  } catch (cause) { report(cause) } finally { busy.value = false }
}
async function remove(): Promise<void> {
  if (!deletion.value) return
  busy.value = true; error.value = ''
  try { message.value = (await deleteRole(deletion.value)).message; deletion.value = null; await refresh() }
  catch (cause) { report(cause) } finally { busy.value = false }
}
async function assign(): Promise<void> {
  if (!selectedAccount.value || !selectedRole.value) return
  busy.value = true; error.value = ''
  try { message.value = (await assignRole(selectedAccount.value, selectedRole.value)).message; await refresh() }
  catch (cause) { report(cause) } finally { busy.value = false }
}
async function createAccount(): Promise<void> {
  if (!(await staffForm.value?.validate())?.valid) return
  busy.value = true; error.value = ''
  try { await createStaff(staff.value); staffDialog.value = false; message.value = 'Cuenta de personal creada.'; staff.value = { username: '', full_name: '', email: '', password: '', role_id: 0 }; await refresh() }
  catch (cause) { report(cause) } finally { busy.value = false }
}
</script>
<template>
  <section class="customers-panel module-panel roles-management-panel">
    <div class="role-command-header">
      <div><p class="eyebrow">CONTROL DE ACCESO</p><h2>Administrar roles</h2><p>Organiza las funciones y el acceso de tu equipo.</p></div>
      <dl class="role-summary"><div><dt>En catálogo</dt><dd>{{ roles.length }}</dd></div><div><dt>Activos</dt><dd>{{ activeRoles.length }}</dd></div><div><dt>Cuentas</dt><dd>{{ accounts.length }}</dd></div></dl>
    </div>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
    <v-alert v-if="message" type="success" variant="tonal" class="mb-4">{{ message }}</v-alert>
    <section class="role-catalog" aria-labelledby="role-catalog-title">
      <div class="role-catalog-heading"><div><h3 id="role-catalog-title">Catálogo de roles</h3><p>Los registros se conservan, incluso al suspenderlos.</p></div><span class="record-kicker">{{ filteredRoles.length }} RESULTADOS</span></div>
      <div class="role-filters"><v-text-field v-model="search" label="Buscar rol" prepend-inner-icon="mdi-magnify" clearable density="compact" variant="outlined" color="secondary" /><v-select v-model="statusFilter" label="Filtrar por estatus" :items="[{ title: 'Todos', value: 0 }, { title: 'Activo', value: 1 }, { title: 'Suspendido', value: 2 }]" density="compact" variant="outlined" color="secondary" /></div>
      <v-progress-linear v-if="busy" indeterminate color="secondary" class="mb-3" />
      <ul class="role-ledger">
        <li v-for="role in filteredRoles" :key="role.id">
          <article class="role-record" data-testid="role-record" :class="{ 'role-record-suspended': role.bin_status !== 1 }">
            <div class="role-record-mark" aria-hidden="true"><v-icon :icon="role.bin_status === 1 ? 'mdi-shield-outline' : 'mdi-shield-off-outline'" /></div>
            <div class="role-record-content"><div class="role-record-title"><h4>{{ role.name }}</h4><v-chip color="secondary" :variant="role.bin_status === 1 ? 'tonal' : 'outlined'" size="small">{{ role.status }}</v-chip></div><p>{{ role.description || 'Sin descripción' }}</p><span class="role-record-accounts"><v-icon icon="mdi-account-outline" size="16" /> {{ assignedCount(role) }} cuentas asociadas</span></div>
            <div class="role-record-actions"><v-btn prepend-icon="mdi-pencil-outline" variant="text" color="secondary" size="small" :disabled="busy" :aria-label="'Actualizar ' + role.name" @click="open(role)">Actualizar</v-btn><v-btn prepend-icon="mdi-pause-circle-outline" variant="text" color="secondary" size="small" :disabled="busy || role.bin_status !== 1 || ['ADMINISTRADOR', 'INVITADO'].includes(role.code)" :aria-label="'Eliminar (suspender) ' + role.name" @click="deletion = role">Suspender</v-btn></div>
          </article>
        </li>
      </ul>
      <p v-if="!busy && !filteredRoles.length" class="role-catalog-empty">No se encontraron roles con estos filtros.</p>
      <p class="role-catalog-note"><v-icon icon="mdi-information-outline" size="18" /> Suspender aplica el estatus 2, sin borrar datos. Reactiva el rol desde Actualizar. Los roles nuevos se crean en Crear rol.</p>
    </section>
    <section class="role-assignment" aria-labelledby="role-assignment-title">
      <div class="customers-heading"><div><p class="eyebrow">EQUIPO Y ACCESOS</p><h3 id="role-assignment-title">Cuentas y asignación de roles</h3><p>Las cuentas del registro público comienzan como Invitado.</p></div><v-btn color="secondary" variant="outlined" :disabled="busy" @click="staffDialog = true">Crear cuenta de personal</v-btn></div>
      <div class="role-assignment-fields"><v-autocomplete v-model="selectedAccount" label="Cuenta" :items="accounts.map((item: Account) => ({ title: `${item.username} · ${item.role_name}`, value: item.id }))" variant="outlined" color="secondary" /><v-select v-model="selectedRole" label="Rol activo" :items="activeRoles" item-title="name" item-value="id" variant="outlined" color="secondary" /><v-btn color="secondary" :loading="busy" :disabled="!selectedAccount || !selectedRole" @click="assign">Asignar rol</v-btn></div>
    </section>
    <v-dialog v-model="dialog" max-width="540" :persistent="busy"><v-card class="customer-dialog"><v-card-text><h2>Actualizar rol</h2><v-alert v-if="error" type="error" variant="tonal" class="my-4">{{ error }}</v-alert><v-form ref="form" @submit.prevent="save"><v-text-field v-model="name" label="Nombre del rol" :rules="nameRules" :maxlength="50" class="mt-5" variant="outlined" /><v-textarea v-model="description" label="Descripción (opcional)" :maxlength="200" rows="2" variant="outlined" /><v-select v-model="state" label="Estatus" :items="statuses.filter(item => item.id !== 3)" item-title="value" item-value="id" variant="outlined" /><v-btn type="submit" color="secondary" :loading="busy">Guardar</v-btn><v-btn variant="text" :disabled="busy" @click="dialog = false">Cancelar</v-btn></v-form></v-card-text></v-card></v-dialog>
    <v-dialog :model-value="!!deletion" max-width="470" :persistent="busy" @update:model-value="!$event && (deletion = null)"><v-card class="customer-dialog"><v-card-text><h2>Eliminar rol sin borrar datos</h2><p class="my-4">¿Suspender {{ deletion?.name }}? Pasará de Activo (1) a Suspendido (2). Se conservarán sus datos y asociaciones; las cuentas con este rol no podrán acceder hasta que se reactive o se les asigne otro rol activo.</p><v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert><v-btn color="secondary" :loading="busy" @click="remove">Confirmar suspensión</v-btn><v-btn variant="text" :disabled="busy" @click="deletion = null">Cancelar</v-btn></v-card-text></v-card></v-dialog>
    <v-dialog v-model="staffDialog" max-width="540" :persistent="busy"><v-card class="customer-dialog"><v-card-text><h2>Crear cuenta de personal</h2><v-alert v-if="error" type="error" variant="tonal" class="my-4">{{ error }}</v-alert><v-form ref="staffForm" @submit.prevent="createAccount"><v-text-field v-model="staff.username" label="Usuario" :rules="usernameRules" maxlength="50" class="mt-5" variant="outlined" /><v-text-field v-model="staff.full_name" label="Nombre completo" :rules="nameRules" maxlength="120" variant="outlined" /><v-text-field v-model="staff.email" label="Correo" :rules="emailRules" type="email" variant="outlined" /><v-select v-model="staff.role_id" label="Rol" :items="activeRoles" item-title="name" item-value="id" :rules="required" variant="outlined" /><v-text-field v-model="staff.password" label="Contraseña inicial" type="password" :rules="passwordRules" maxlength="128" variant="outlined" /><v-btn type="submit" color="secondary" :loading="busy">Crear cuenta</v-btn><v-btn variant="text" :disabled="busy" @click="staffDialog = false">Cancelar</v-btn></v-form></v-card-text></v-card></v-dialog>
  </section>
</template>
