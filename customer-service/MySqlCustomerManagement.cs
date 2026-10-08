using MySqlConnector;

namespace Taller.Customers;

public sealed partial class MySqlCustomerStore
{
    private static Customer ReadCustomer(MySqlDataReader reader) => new(
        reader.GetInt64("id"), reader.GetString("full_name"),
        new Address(reader.GetString("street"), reader.GetString("number"), reader.GetString("neighborhood"), reader.GetString("municipality"), reader.GetString("state")),
        new Contacts(reader.IsDBNull(reader.GetOrdinal("email")) ? null : reader.GetString("email"),
            reader.IsDBNull(reader.GetOrdinal("mobile")) ? null : reader.GetString("mobile"),
            reader.IsDBNull(reader.GetOrdinal("alternative")) ? null : reader.GetString("alternative")),
        reader.GetString("status"), reader.GetString("identity_fingerprint"), reader.GetInt32("version"));

    public async Task<CustomerPage> List(int page, int pageSize, string search, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        // Count y página comparten una instantánea para que la paginación sea coherente.
        await using var transaction = await connection.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        const string filter = """
            WHERE deleted_at IS NULL AND (@empty=1 OR full_name LIKE @search ESCAPE '!'
            OR email LIKE @search ESCAPE '!' OR mobile LIKE @search ESCAPE '!'
            OR alternative LIKE @search ESCAPE '!' OR municipality LIKE @search ESCAPE '!')
            """;
        var pattern = "%" + search.Replace("!", "!!").Replace("%", "!%").Replace("_", "!_") + "%";
        await using var countCommand = new MySqlCommand("SELECT COUNT(*) FROM customers " + filter, connection, transaction);
        countCommand.Parameters.AddWithValue("@empty", search.Length == 0);
        countCommand.Parameters.AddWithValue("@search", pattern);
        var total = Convert.ToInt64(await countCommand.ExecuteScalarAsync(ct));
        await using var command = new MySqlCommand("SELECT * FROM customers " + filter + " ORDER BY id DESC LIMIT @limit OFFSET @offset", connection, transaction);
        command.Parameters.AddWithValue("@empty", search.Length == 0);
        command.Parameters.AddWithValue("@search", pattern);
        command.Parameters.AddWithValue("@limit", pageSize);
        command.Parameters.AddWithValue("@offset", (page - 1) * pageSize);
        var items = new List<Customer>();
        await using (var reader = await command.ExecuteReaderAsync(ct))
            while (await reader.ReadAsync(ct)) items.Add(ReadCustomer(reader));
        await transaction.CommitAsync(ct);
        return new CustomerPage(items, total, page, pageSize);
    }

    public async Task<Customer?> Get(long id, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var command = new MySqlCommand("SELECT * FROM customers WHERE id=@id AND deleted_at IS NULL", connection);
        command.Parameters.AddWithValue("@id", id);
        await using var reader = await command.ExecuteReaderAsync(ct);
        return await reader.ReadAsync(ct) ? ReadCustomer(reader) : null;
    }

    private static async Task<Customer> LockCurrent(MySqlConnection connection, MySqlTransaction transaction, long id, int version, CancellationToken ct)
    {
        await using var command = new MySqlCommand("SELECT * FROM customers WHERE id=@id AND deleted_at IS NULL FOR UPDATE", connection, transaction);
        command.Parameters.AddWithValue("@id", id);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) throw new UseCaseException(404, "El cliente no existe o ya fue eliminado del listado.");
        var current = ReadCustomer(reader);
        if (current.Version != version) throw new UseCaseException(409, "Otro usuario modificó este cliente. Actualiza el listado y revisa nuevamente.");
        return current;
    }

    private static async Task<AuditEntry> WriteAudit(MySqlConnection connection, MySqlTransaction transaction, Actor actor, long id, string action, DateTimeOffset now, CancellationToken ct)
    {
        await using var command = new MySqlCommand("INSERT INTO audit_entries (actor_id,actor_username,customer_id,action,occurred_at) VALUES (@actor,@username,@id,@action,@now)", connection, transaction);
        command.Parameters.AddWithValue("@actor", actor.Id);
        command.Parameters.AddWithValue("@username", actor.Username);
        command.Parameters.AddWithValue("@id", id);
        command.Parameters.AddWithValue("@action", action);
        command.Parameters.AddWithValue("@now", now.UtcDateTime);
        await command.ExecuteNonQueryAsync(ct);
        return new AuditEntry(command.LastInsertedId, actor.Id, actor.Username, id, now, action);
    }

    public async Task<SavedCustomer> UpdateAtomically(Customer customer, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        try
        {
            await LockCurrent(connection, transaction, customer.Id, customer.Version, ct);
            await using var command = new MySqlCommand("""
                UPDATE customers SET full_name=@name,street=@street,number=@number,neighborhood=@neighborhood,
                municipality=@municipality,state=@state,email=@email,mobile=@mobile,alternative=@alternative,
                identity_fingerprint=@identity,version=version+1 WHERE id=@id
                """, connection, transaction);
            command.Parameters.AddWithValue("@id", customer.Id);
            command.Parameters.AddWithValue("@name", customer.FullName);
            command.Parameters.AddWithValue("@street", customer.Address.Street);
            command.Parameters.AddWithValue("@number", customer.Address.Number);
            command.Parameters.AddWithValue("@neighborhood", customer.Address.Neighborhood);
            command.Parameters.AddWithValue("@municipality", customer.Address.Municipality);
            command.Parameters.AddWithValue("@state", customer.Address.State);
            command.Parameters.AddWithValue("@email", customer.Contacts.Email);
            command.Parameters.AddWithValue("@mobile", customer.Contacts.Mobile);
            command.Parameters.AddWithValue("@alternative", customer.Contacts.Alternative);
            command.Parameters.AddWithValue("@identity", customer.Fingerprint);
            await command.ExecuteNonQueryAsync(ct);
            await using var removeKeys = new MySqlCommand("DELETE FROM customer_contact_keys WHERE customer_id=@id", connection, transaction);
            removeKeys.Parameters.AddWithValue("@id", customer.Id);
            await removeKeys.ExecuteNonQueryAsync(ct);
            foreach (var (kind, value) in ContactKeys(customer.Contacts))
            {
                await using var contact = new MySqlCommand("INSERT INTO customer_contact_keys (kind,value,customer_id) VALUES (@kind,@value,@id)", connection, transaction);
                contact.Parameters.AddWithValue("@kind", kind);
                contact.Parameters.AddWithValue("@value", value);
                contact.Parameters.AddWithValue("@id", customer.Id);
                await contact.ExecuteNonQueryAsync(ct);
            }
            var audit = await WriteAudit(connection, transaction, actor, customer.Id, "UC-CV-02 ActualizarCliente", DateTimeOffset.UtcNow, ct);
            await transaction.CommitAsync(ct);
            return new SavedCustomer(customer with {Version = customer.Version + 1}, audit);
        }
        catch (MySqlException ex) when (ex.Number == 1062)
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw new UseCaseException(409, "Los datos coinciden con otro cliente. No se guardaron los cambios.");
        }
        catch
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw;
        }
    }

    public async Task<SavedCustomer> DeleteAtomically(long id, int version, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        try
        {
            var current = await LockCurrent(connection, transaction, id, version, ct);
            var now = DateTimeOffset.UtcNow;
            await using var command = new MySqlCommand("UPDATE customers SET status='INACTIVO',deleted_at=@now,version=version+1 WHERE id=@id", connection, transaction);
            command.Parameters.AddWithValue("@id", id);
            command.Parameters.AddWithValue("@now", now.UtcDateTime);
            await command.ExecuteNonQueryAsync(ct);
            var audit = await WriteAudit(connection, transaction, actor, id, "UC-CV-03 EliminarCliente", now, ct);
            await transaction.CommitAsync(ct);
            // No se borran el cliente, sus contactos únicos ni las auditorías históricas.
            return new SavedCustomer(current with {Status = "INACTIVO", Version = version + 1}, audit);
        }
        catch
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw;
        }
    }
}
