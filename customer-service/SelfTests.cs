using MySqlConnector;
using System.Text.Json;

namespace Taller.Customers;

internal static partial class SelfTests
{
    private static ContactNormalizer Normalizer() => new(new EmailStrategy(), new PhoneStrategy("Celular"), new PhoneStrategy("Alternativo"));
    private static CustomerInput Input(string? email = " ana@example.com ", string? mobile = "55 1234 5678", string? alternative = null) =>
        new("  Ana   Pérez  ", new Address(" Calle Uno ", "12", "Centro", "Puebla", "Puebla"), new Contacts(email, mobile, alternative), 1);
    private static readonly Actor Admin = new(1, "prueba", "ADMINISTRADOR", "ACTIVO");
    private static int count;

    private static void Check(bool condition, string name)
    {
        if (!condition) throw new InvalidOperationException("FALLÓ: " + name);
        count++;
        Console.WriteLine("OK: " + name);
    }

    private static async Task Expect(int status, Func<Task> action, string name)
    {
        try { await action(); }
        catch (UseCaseException ex) when (ex.Status == status) { Check(true, name); return; }
        throw new InvalidOperationException("FALLÓ: " + name);
    }

    public static async Task Run()
    {
        using (var cases = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(AppContext.BaseDirectory, "vehicle-identifiers.cases.json"))))
        {
            foreach (var (example, canonical) in VehicleIdentifiers.PlateExamples())
                Check(VehicleIdentifiers.MexicanPlate(example) == canonical, "Formato mexicano: " + example);
            foreach (var kind in new[] {"vins", "plates"})
            foreach (var entry in cases.RootElement.GetProperty(kind).EnumerateArray())
            {
                var raw = entry.GetProperty("raw").GetString()!;
                var expected = entry.GetProperty("canonical").GetString();
                if (expected is not null)
                    Check((kind == "vins" ? VehicleIdentifiers.Vin(raw) : VehicleIdentifiers.MexicanPlate(raw)) == expected,
                        "Identificador válido y normalizado: " + expected);
                else
                    await Expect(422, () =>
                    {
                        _ = kind == "vins" ? VehicleIdentifiers.Vin(raw) : VehicleIdentifiers.MexicanPlate(raw);
                        return Task.CompletedTask;
                    }, "Identificador inválido rechazado: " + JsonSerializer.Serialize(raw));
            }
        }
        Check(MySqlCustomerStore.StatusFromCatalog(1) == "ACTIVO"
            && MySqlCustomerStore.StatusFromCatalog(2) == "INACTIVO"
            && MySqlCustomerStore.StatusFromCatalog(3) == "INACTIVO",
            "Contrato HTTP de estatus derivado del catálogo sin texto persistido");
        var store = new MemoryStore();
        var useCase = new RegisterCustomer(store, Normalizer(), new PreviewSigner());
        var input = Input();
        var preview = await useCase.Preview(input, Admin, default);
        Check(preview.Customer.FullName == "Ana Pérez" && preview.Customer.Contacts.Email == "ana@example.com"
            && preview.Customer.Contacts.Mobile == "+525512345678", "Normalización de nombre, correo y teléfono");
        await Expect(422, async () => { await useCase.Preview(Input(null, null), Admin, default); }, "Contacto mínimo obligatorio");
        await Expect(422, async () => { await useCase.Preview(Input("malcorreo"), Admin, default); }, "Correo inválido");
        await Expect(422, async () => { await useCase.Preview(Input(null, "123"), Admin, default); }, "Teléfono inválido");
        await Expect(422, async () => { await useCase.Preview(input with {Address = input.Address with {State = ""}}, Admin, default); }, "Dirección completa obligatoria");
        await Expect(403, async () => { await useCase.Preview(input, Admin with {Role = "MECANICO"}, default); }, "Mecánico bloqueado");
        await Expect(403, () => { (Admin with {Role = "CLIENTE"}).Authorize(); return Task.CompletedTask; }, "Cliente sin permiso para gestionar clientes");
        await Expect(403, async () => { await useCase.Register(new(input, preview.PreviewToken!, true), Admin with {Status = "INACTIVO"}, default); }, "Usuario inactivo bloqueado");
        await Expect(422, async () => { await useCase.Register(new(input, preview.PreviewToken!, false), Admin, default); }, "Confirmación obligatoria");
        await Expect(422, async () => { await useCase.Register(new(input with {FullName = "Otro Nombre"}, preview.PreviewToken!, true), Admin, default); }, "Cambio posterior a revisión bloqueado");
        await Expect(422, async () => { await useCase.Register(new(input, preview.PreviewToken!, true), Admin with {Id = 2}, default); }, "Revisión ligada al actor");
        var saved = await useCase.Register(new(input, preview.PreviewToken!, true), Admin, default);
        Check(saved.Customer.Status == "ACTIVO" && saved.Customer.Id > 0 && saved.AuditEntry.ActorId == Admin.Id
            && saved.AuditEntry.CustomerId == saved.Customer.Id && saved.AuditEntry.OccurredAt.Offset == TimeSpan.Zero, "Customer activo y auditoría del actor en UTC");
        await Expect(409, async () => { await useCase.Register(new(input, preview.PreviewToken!, true), Admin, default); }, "Reintento sin duplicado");
        var match = await useCase.Preview(Input("otro@example.com", null, "+52 55 1234 5678") with {FullName = "Otra Persona"}, Admin, default);
        Check(match.Matches.Count == 1 && match.PreviewToken is null, "Duplicado celular contra alternativo");
        var identity = await useCase.Preview(Input("nuevo@example.com", "+525587654321") with {FullName = "Ana Perez"}, Admin, default);
        Check(identity.Matches.Count == 1, "Duplicado por nombre y dirección sin acentos");
        var receptionist = await useCase.Preview(Input("recepcion@example.com", null) with {FullName = "Cliente Nuevo"}, Admin with {Role = "RECEPCIONISTA"}, default);
        Check(receptionist.PreviewToken is not null, "Recepcionista autorizado");
        await Expect(422, async () => { await useCase.Preview(input with {WorkshopId = null}, Admin, default); }, "Taller obligatorio en alta nueva");
        await Expect(422, async () => { await useCase.Preview(input with {WorkshopId = 2}, Admin, default); }, "Taller inexistente o suspendido rechazado");
        var management = new ManageCustomers(store, Normalizer(), new PreviewSigner());
        var secretary = Admin with {Role = "SECRETARIA"};
        var update = new UpdateDraft(input with {FullName = "Ana Actualizada"}, 1);
        await Expect(403, async () => { await management.PreviewUpdate(saved.Customer.Id, update, Admin with {Role = "RECEPCIONISTA"}, default); }, "Recepcionista no edita según indicación escrita");
        await Expect(422, async () => { await management.PreviewUpdate(saved.Customer.Id, update with {Customer = update.Customer with {WorkshopId = 2}}, secretary, default); }, "Taller inmutable al editar");
        var updatePreview = await management.PreviewUpdate(saved.Customer.Id, update, secretary, default);
        var updated = await management.Update(saved.Customer.Id, new(update.Customer, updatePreview.PreviewToken!, true, 1), secretary, default);
        Check(updated.Customer.WorkshopId == 1 && updated.Customer.FullName == "Ana Actualizada", "Secretaria activa edita y conserva taller");
        await Expect(403, async () => { await management.Delete(saved.Customer.Id, new(2, true), secretary, default); }, "Solo administrador desactiva");
        var vehicles = new RegisterVehicle(store, store);
        Check(typeof(VehicleInput).GetProperties().Select(property => property.Name).ToHashSet()
            .SetEquals(["Vin", "Plate", "Make", "Model", "Year", "Version", "Color", "Mileage"]),
            "Registro de vehículo solo recibe datos solicitados, sin ID técnico independiente");
        var vehicleInput = new VehicleInput("1hgcm82633a004352", "abc-123-d", "Honda", "Accord", 2003, "EX", "Gris");
        Check(VehicleRules.Build(saved.Customer.Id, vehicleInput) is {Vin: "1HGCM82633A004352", Plate: "ABC123D", Mileage: null}, "VIN y placa normalizados; kilometraje opcional");
        await Expect(422, () => { VehicleRules.Build(1, vehicleInput with {Vin = "1IGCM82633A004352"}); return Task.CompletedTask; }, "VIN no admite I, O, Q");
        await Expect(422, () => { VehicleRules.Build(1, vehicleInput with {Plate = "??"}); return Task.CompletedTask; }, "Placa inválida bloqueada");
        await Expect(422, () => { VehicleRules.Build(1, vehicleInput with {Year = DateTime.UtcNow.Year + 2}); return Task.CompletedTask; }, "Año futuro fuera de rango bloqueado");
        await Expect(422, () => { VehicleRules.Build(1, vehicleInput with {Mileage = -1}); return Task.CompletedTask; }, "Kilometraje negativo bloqueado");
        await Expect(403, async () => { await vehicles.Register(saved.Customer.Id, new(vehicleInput, true), secretary, default); }, "Secretaria no registra vehículos");
        var vehicle = await vehicles.Register(saved.Customer.Id, new(vehicleInput, true), Admin with {Role = "RECEPCIONISTA"}, default);
        Check(vehicle.Vehicle.CustomerId == saved.Customer.Id && vehicle.Vehicle.Status == "ACTIVO", "Recepcionista registra vehículo asociado y activo");
        await management.Delete(saved.Customer.Id, new(2, true), Admin, default);
        await Expect(404, async () => { await vehicles.Register(saved.Customer.Id, new(vehicleInput, true), Admin, default); }, "Baja del cliente impide nuevas asociaciones");
        await RunVehicleManagement();
        Console.WriteLine($"RESULTADO: {count} comprobaciones aprobadas.");
    }

    public static async Task Integration()
    {
        var connectionString = DatabaseConfig.ConnectionString();
        var store = new MySqlCustomerStore(connectionString);
        await store.Initialize(default);
        await store.Initialize(default);
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync();
        await using var normalized = new MySqlCommand("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='customers' AND COLUMN_NAME='status'
            """, connection);
        Check(Convert.ToInt32(await normalized.ExecuteScalarAsync()) == 0,
            "MySQL: arranque repetible conserva solo bin_status en clientes");
        await using var userCommand = new MySqlCommand("""
            SELECT u.id,u.username FROM users u
            INNER JOIN status s ON s.id=u.bin_status
            INNER JOIN roles r ON r.code=u.role
            WHERE r.code='ADMINISTRADOR' AND s.id=1 AND r.bin_status=1 LIMIT 1
            """, connection);
        Actor actor;
        await using (var reader = await userCommand.ExecuteReaderAsync())
        {
            if (!await reader.ReadAsync()) throw new InvalidOperationException("Se requiere un administrador existente para la prueba.");
            actor = new(reader.GetInt32(0), reader.GetString(1), "ADMINISTRADOR", "ACTIVO");
        }
        var marker = Guid.NewGuid().ToString("N");
        await using var workshopCommand = new MySqlCommand("SELECT id FROM workshops WHERE bin_status=1 LIMIT 1", connection);
        var workshopId = Convert.ToInt32(await workshopCommand.ExecuteScalarAsync() ?? throw new InvalidOperationException("Se requiere un taller activo para la prueba."));
        var customer = new CustomerBuilder(Normalizer()).WithName("Prueba Integracion")
            .WithAddress(new Address("TEST " + marker, "1", "Test", "Test", "Test"))
            .WithContacts(new Contacts(marker + "@example.com", null, null)).WithWorkshop(workshopId).Build();
        var failed = customer with {Fingerprint = new string('f', 64), Contacts = new Contacts(marker + "rollback@example.com", null, null)};
        try
        {
            var attempts = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ =>
            {
                try { await store.SaveAtomically(customer, actor, default); return true; }
                catch (UseCaseException ex) when (ex.Status == 409) { return false; }
            }));
            Check(attempts.Count(x => x) == 1, "MySQL: ocho altas concurrentes crean exactamente un cliente");
            await using var audit = new MySqlCommand("SELECT COUNT(*) FROM audit_entries a JOIN customers c ON c.id=a.customer_id WHERE c.identity_fingerprint=@fp AND a.actor_id=@actor", connection);
            audit.Parameters.AddWithValue("@fp", customer.Fingerprint);
            audit.Parameters.AddWithValue("@actor", actor.Id);
            Check(Convert.ToInt32(await audit.ExecuteScalarAsync()) == 1, "MySQL: exactamente una auditoría del actor correcto");
            try
            {
                await store.SaveAtomically(failed, actor with {Username = new string('x', 51)}, default);
                throw new InvalidOperationException("No se provocó el fallo de auditoría esperado.");
            }
            catch (MySqlException ex) when (ex.Number == 1406) { }
            await using var rollback = new MySqlCommand("SELECT COUNT(*) FROM customers WHERE email=@email", connection);
            rollback.Parameters.AddWithValue("@email", failed.Contacts.Email);
            Check(Convert.ToInt32(await rollback.ExecuteScalarAsync()) == 0, "MySQL: fallo de auditoría revierte también al cliente y contactos");
            var current = (await store.FindMatches(customer, default)).Single();
            await using var suspend = new MySqlCommand("UPDATE customers SET bin_status=2 WHERE id=@id", connection);
            suspend.Parameters.AddWithValue("@id", current.Id);
            await suspend.ExecuteNonQueryAsync();
            Check((await store.Get(current.Id, default))?.Status == "INACTIVO"
                && (await store.List(1, 10, marker, default)).Items.Single().Status == "INACTIVO",
                "MySQL: INNER JOIN obtiene cliente suspendido sin columna textual");
            suspend.CommandText = "UPDATE customers SET bin_status=1 WHERE id=@id";
            await suspend.ExecuteNonQueryAsync();
            var changed = current with {FullName = "Prueba Actualizada"};
            var updates = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ =>
            {
                try { await store.UpdateAtomically(changed, actor, default); return true; }
                catch (UseCaseException ex) when (ex.Status == 409) { return false; }
            }));
            Check(updates.Count(x => x) == 1 && (await store.Get(current.Id, default))?.Version == 2,
                "MySQL: ocho ediciones concurrentes permiten una sola versión nueva");
            var afterUpdate = (await store.Get(current.Id, default))!;
            try
            {
                await store.UpdateAtomically(afterUpdate with {Contacts = failed.Contacts}, actor with {Username = new string('x', 51)}, default);
                throw new InvalidOperationException("No falló la auditoría de actualización.");
            }
            catch (MySqlException ex) when (ex.Number == 1406) { }
            var retained = (await store.Get(current.Id, default))!;
            Check(retained.Version == 2 && retained.Contacts == customer.Contacts
                && (await store.FindMatches(customer, default)).Count == 1,
                "MySQL: auditoría fallida revierte edición, versión y claves de contacto");
            try
            {
                await store.DeleteAtomically(current.Id, 2, actor with {Username = new string('x', 51)}, default);
                throw new InvalidOperationException("No falló la auditoría de eliminación.");
            }
            catch (MySqlException ex) when (ex.Number == 1406) { }
            Check((await store.Get(current.Id, default)) is {Status: "ACTIVO", Version: 2},
                "MySQL: auditoría fallida revierte la baja lógica");
            var seed = Convert.ToInt64(marker[..8], 16);
            var serial = seed % 999_997 + 1;
            var plateNumber = seed % 9_997 + 1;
            const string plateAlphabet = "ABCDEFGHJKLMNPRSTUVWXYZ";
            var prefix = string.Concat(marker[..3].Select(character => plateAlphabet[Convert.ToInt32(character.ToString(), 16)]));
            var vehicleCandidate = VehicleRules.Build(current.Id, new($"WVWZZZ1JZXW{serial:D6}", $"{prefix}{plateNumber:D4}", "Prueba", "Modelo", 1999, "Base", "Gris"));
            var vehicles = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ =>
            {
                try { await store.SaveVehicleAtomically(vehicleCandidate, actor, default); return true; }
                catch (UseCaseException ex) when (ex.Status == 409) { return false; }
            }));
            Check(vehicles.Count(x => x) == 1 && (await store.ListVehicles(current.Id, default)).Count == 1,
                "MySQL: ocho altas de vehículo simultáneas guardan solo uno");
            await Expect(409, async () =>
            {
                await store.SaveVehicleAtomically(vehicleCandidate with {Plate = $"{prefix}{plateNumber + 1:D4}"}, actor, default);
            }, "MySQL: VIN duplicado con otra placa rechazado antes de guardar");
            await Expect(409, async () =>
            {
                await store.SaveVehicleAtomically(vehicleCandidate with {Vin = $"WVWZZZ1JZXW{serial + 1:D6}"}, actor, default);
            }, "MySQL: placa duplicada con otro VIN rechazada antes de guardar");
            await using var vehicleAudit = new MySqlCommand("SELECT COUNT(*) FROM vehicle_audit_entries WHERE customer_id=@id", connection);
            vehicleAudit.Parameters.AddWithValue("@id", current.Id);
            Check(Convert.ToInt32(await vehicleAudit.ExecuteScalarAsync()) == 1,
                "MySQL: rechazar duplicados no crea auditorías de alta adicionales");
            var failedVehicle = vehicleCandidate with {Vin = $"WVWZZZ1JZXW{serial + 2:D6}", Plate = $"{prefix}{plateNumber + 2:D4}"};
            try
            {
                await store.SaveVehicleAtomically(failedVehicle, actor with {Username = new string('x', 51)}, default,
                    [new(new byte[] {137, 80, 78, 71, 13, 10, 26, 10}, "image/png")]);
                throw new InvalidOperationException("No falló la auditoría del vehículo.");
            }
            catch (MySqlException ex) when (ex.Number == 1406) { }
            Check((await store.ListVehicles(current.Id, default)).Count == 1, "MySQL: fallo de auditoría revierte vehículo y asociación");
            await using var photoCount = new MySqlCommand("SELECT COUNT(*) FROM vehicle_photos p INNER JOIN vehicles v ON v.id=p.vehicle_id WHERE v.customer_id=@id", connection);
            photoCount.Parameters.AddWithValue("@id", current.Id);
            Check(Convert.ToInt32(await photoCount.ExecuteScalarAsync()) == 0, "MySQL: fallo de auditoría también revierte las fotografías");
            var deletions = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ =>
            {
                try { await store.DeleteAtomically(current.Id, 2, actor, default); return true; }
                catch (UseCaseException ex) when (ex.Status == 404) { return false; }
            }));
            Check(deletions.Count(x => x) == 1 && await store.Get(current.Id, default) is null,
                "MySQL: ocho eliminaciones concurrentes generan una sola baja");
            await Expect(409, async () => { await store.SaveVehicleAtomically(failedVehicle, actor, default); }, "MySQL: cliente desactivado rechaza asociación");
            Check((await store.ListVehicles(current.Id, default)).Count == 1, "MySQL: baja lógica conserva vehículos");
            await using var retainedAudit = new MySqlCommand("SELECT COUNT(*) FROM audit_entries WHERE customer_id=@id", connection);
            retainedAudit.Parameters.AddWithValue("@id", current.Id);
            Check(Convert.ToInt32(await retainedAudit.ExecuteScalarAsync()) == 3
                && (await store.FindMatches(customer, default)).Single() is {Status: "INACTIVO", Version: 3},
                "MySQL: baja conserva el cliente, contacto único y las tres auditorías");
            Console.WriteLine($"RESULTADO: {count} comprobaciones de MySQL aprobadas.");
        }
        finally
        {
            // Solo elimina los registros con correos únicos generados por esta prueba.
            await using var cleanup = new MySqlCommand("""
                DELETE p FROM vehicle_photos p JOIN vehicles v ON v.id=p.vehicle_id JOIN customers c ON c.id=v.customer_id WHERE c.email IN (@email,@failed);
                DELETE a FROM vehicle_audit_entries a JOIN customers c ON c.id=a.customer_id WHERE c.email IN (@email,@failed);
                DELETE v FROM vehicles v JOIN customers c ON c.id=v.customer_id WHERE c.email IN (@email,@failed);
                DELETE a FROM audit_entries a JOIN customers c ON c.id=a.customer_id WHERE c.email IN (@email,@failed);
                DELETE FROM customers WHERE email IN (@email,@failed);
                """, connection);
            cleanup.Parameters.AddWithValue("@email", customer.Contacts.Email);
            cleanup.Parameters.AddWithValue("@failed", failed.Contacts.Email);
            await cleanup.ExecuteNonQueryAsync();
        }
    }

    private sealed class MemoryStore : ICustomerManagementStore, IVehicleStore
    {
        private readonly List<SavedCustomer> saved = [];
        private readonly List<SavedVehicle> vehicles = [];
        public Task<WorkshopInfo?> GetWorkshop(int id, CancellationToken ct) => Task.FromResult<WorkshopInfo?>(id == 1 ? new(1, "Taller de prueba", true) : null);
        public Task<IReadOnlyList<Customer>> FindMatches(Customer candidate, CancellationToken ct)
        {
            var keys = MySqlCustomerStore.ContactKeys(candidate.Contacts).ToHashSet();
            IReadOnlyList<Customer> matches = saved.Select(x => x.Customer).Where(x => x.Id != candidate.Id && (x.Fingerprint == candidate.Fingerprint
                || MySqlCustomerStore.ContactKeys(x.Contacts).Any(keys.Contains))).ToList();
            return Task.FromResult(matches);
        }
        public Task<SavedCustomer> SaveAtomically(Customer customer, Actor actor, CancellationToken ct)
        {
            var id = saved.Count + 1;
            var result = new SavedCustomer(customer with {Id = id}, new(id, actor.Id, actor.Username, id, DateTimeOffset.UtcNow));
            saved.Add(result);
            return Task.FromResult(result);
        }
        public Task<CustomerPage> List(int page, int pageSize, string search, CancellationToken ct) => Task.FromResult(new CustomerPage(saved.Select(x => x.Customer).ToList(), saved.Count, page, pageSize));
        public Task<Customer?> Get(long id, CancellationToken ct) => Task.FromResult(saved.FirstOrDefault(x => x.Customer.Id == id && x.Customer.Status == "ACTIVO")?.Customer);
        public Task<SavedCustomer> UpdateAtomically(Customer customer, Actor actor, CancellationToken ct)
        {
            var index = saved.FindIndex(x => x.Customer.Id == customer.Id);
            var result = new SavedCustomer(customer with {Version = customer.Version + 1}, new(index + 1, actor.Id, actor.Username, customer.Id, DateTimeOffset.UtcNow));
            saved[index] = result;
            return Task.FromResult(result);
        }
        public Task<SavedCustomer> DeleteAtomically(long id, int version, Actor actor, CancellationToken ct)
        {
            var index = saved.FindIndex(x => x.Customer.Id == id);
            var result = saved[index] with {Customer = saved[index].Customer with {Status = "INACTIVO", Version = version + 1}};
            saved[index] = result;
            return Task.FromResult(result);
        }
        public Task<IReadOnlyList<Vehicle>> ListVehicles(long customerId, CancellationToken ct) => Task.FromResult<IReadOnlyList<Vehicle>>(vehicles.Select(x => x.Vehicle).Where(x => x.CustomerId == customerId).ToList());
        public Task<SavedVehicle> SaveVehicleAtomically(Vehicle vehicle, Actor actor, CancellationToken ct, IReadOnlyList<VehiclePhotoInput>? photos = null)
        {
            var result = new SavedVehicle(vehicle with {Id = vehicles.Count + 1}, new(vehicles.Count + 1, actor.Id, actor.Username, vehicle.CustomerId, vehicles.Count + 1, DateTimeOffset.UtcNow));
            vehicles.Add(result);
            return Task.FromResult(result);
        }
    }
}
