using MySqlConnector;

namespace Taller.Customers;

internal static class SelfTests
{
    private static ContactNormalizer Normalizer() => new(new EmailStrategy(), new PhoneStrategy("Celular"), new PhoneStrategy("Alternativo"));
    private static CustomerInput Input(string? email = " ana@example.com ", string? mobile = "55 1234 5678", string? alternative = null) =>
        new("  Ana   Pérez  ", new Address(" Calle Uno ", "12", "Centro", "Puebla", "Puebla"), new Contacts(email, mobile, alternative));
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
        Console.WriteLine($"RESULTADO: {count} comprobaciones aprobadas.");
    }

    public static async Task Integration()
    {
        var connectionString = DatabaseConfig.ConnectionString();
        var store = new MySqlCustomerStore(connectionString);
        await store.Initialize(default);
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync();
        await using var userCommand = new MySqlCommand("SELECT id,username FROM users WHERE role='ADMINISTRADOR' AND status='ACTIVO' LIMIT 1", connection);
        Actor actor;
        await using (var reader = await userCommand.ExecuteReaderAsync())
        {
            if (!await reader.ReadAsync()) throw new InvalidOperationException("Se requiere un administrador existente para la prueba.");
            actor = new(reader.GetInt32(0), reader.GetString(1), "ADMINISTRADOR", "ACTIVO");
        }
        var marker = Guid.NewGuid().ToString("N");
        var customer = new CustomerBuilder(Normalizer()).WithName("Prueba Integracion")
            .WithAddress(new Address("TEST " + marker, "1", "Test", "Test", "Test"))
            .WithContacts(new Contacts(marker + "@example.com", null, null)).Build();
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
            var deletions = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ =>
            {
                try { await store.DeleteAtomically(current.Id, 2, actor, default); return true; }
                catch (UseCaseException ex) when (ex.Status == 404) { return false; }
            }));
            Check(deletions.Count(x => x) == 1 && await store.Get(current.Id, default) is null,
                "MySQL: ocho eliminaciones concurrentes generan una sola baja");
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
                DELETE a FROM audit_entries a JOIN customers c ON c.id=a.customer_id WHERE c.email IN (@email,@failed);
                DELETE FROM customers WHERE email IN (@email,@failed);
                """, connection);
            cleanup.Parameters.AddWithValue("@email", customer.Contacts.Email);
            cleanup.Parameters.AddWithValue("@failed", failed.Contacts.Email);
            await cleanup.ExecuteNonQueryAsync();
        }
    }

    private sealed class MemoryStore : ICustomerStore
    {
        private readonly List<SavedCustomer> saved = [];
        public Task<IReadOnlyList<Customer>> FindMatches(Customer candidate, CancellationToken ct)
        {
            var keys = MySqlCustomerStore.ContactKeys(candidate.Contacts).ToHashSet();
            IReadOnlyList<Customer> matches = saved.Select(x => x.Customer).Where(x => x.Fingerprint == candidate.Fingerprint
                || MySqlCustomerStore.ContactKeys(x.Contacts).Any(keys.Contains)).ToList();
            return Task.FromResult(matches);
        }
        public Task<SavedCustomer> SaveAtomically(Customer customer, Actor actor, CancellationToken ct)
        {
            var id = saved.Count + 1;
            var result = new SavedCustomer(customer with {Id = id}, new(id, actor.Id, actor.Username, id, DateTimeOffset.UtcNow));
            saved.Add(result);
            return Task.FromResult(result);
        }
    }
}
