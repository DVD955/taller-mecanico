using MySqlConnector;

namespace Taller.Customers;

public sealed partial class MySqlCustomerStore(string connectionString) : ICustomerManagementStore
{
    public async Task Initialize(CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        var sql = await File.ReadAllTextAsync(Path.Combine(AppContext.BaseDirectory, "customers.sql"), ct);
        await using var command = new MySqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync(ct);
        var columns = new HashSet<string>();
        await using (var inspect = new MySqlCommand("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='customers'", connection))
        await using (var reader = await inspect.ExecuteReaderAsync(ct))
            while (await reader.ReadAsync(ct)) columns.Add(reader.GetString(0));
        if (!columns.Contains("version"))
        {
            await using var migrate = new MySqlCommand("ALTER TABLE customers ADD COLUMN version INT NOT NULL DEFAULT 1", connection);
            await migrate.ExecuteNonQueryAsync(ct);
        }
        if (!columns.Contains("deleted_at"))
        {
            await using var migrate = new MySqlCommand("ALTER TABLE customers ADD COLUMN deleted_at DATETIME(6) NULL", connection);
            await migrate.ExecuteNonQueryAsync(ct);
        }
        if (!columns.Contains("bin_status"))
        {
            var inactiveCondition = columns.Contains("status") ? "WHEN status='INACTIVO' THEN 2 " : "";
            await using var migrate = new MySqlCommand("ALTER TABLE customers ADD COLUMN bin_status INT NOT NULL DEFAULT 1; "
                + "UPDATE customers SET bin_status=CASE WHEN deleted_at IS NOT NULL THEN 3 " + inactiveCondition + "ELSE 1 END", connection);
            await migrate.ExecuteNonQueryAsync(ct);
        }
        // Si bin_status ya existe, se conserva: es la única fuente del estatus real.
        await using (var inspect = new MySqlCommand("""
            SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='customers' AND COLUMN_NAME='bin_status'
              AND REFERENCED_TABLE_NAME='status' AND REFERENCED_COLUMN_NAME='id'
            """, connection))
        {
            if (Convert.ToInt32(await inspect.ExecuteScalarAsync(ct)) == 0)
            {
                await using var migrate = new MySqlCommand("ALTER TABLE customers ADD CONSTRAINT fk_customers_bin_status FOREIGN KEY (bin_status) REFERENCES status(id)", connection);
                await migrate.ExecuteNonQueryAsync(ct);
            }
        }
        if (columns.Contains("status"))
        {
            await using var migrate = new MySqlCommand("ALTER TABLE customers DROP COLUMN status", connection);
            await migrate.ExecuteNonQueryAsync(ct);
        }
    }

    public static IEnumerable<(string Kind, string Value)> ContactKeys(Contacts contacts)
    {
        if (contacts.Email is not null) yield return ("EMAIL", contacts.Email);
        foreach (var phone in new[] {contacts.Mobile, contacts.Alternative}.Where(x => x is not null).Distinct())
            yield return ("PHONE", phone!);
    }

    public async Task<IReadOnlyList<Customer>> FindMatches(Customer candidate, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var command = new MySqlCommand("""
            SELECT DISTINCT c.*, s.id AS status_id FROM customers c
            INNER JOIN status s ON s.id=c.bin_status
            LEFT JOIN customer_contact_keys k ON k.customer_id=c.id
            WHERE c.id<>@id AND (c.identity_fingerprint=@identity
              OR (k.kind='EMAIL' AND k.value=@email)
              OR (k.kind='PHONE' AND (k.value=@mobile OR k.value=@alternative)))
            ORDER BY c.id LIMIT 10
            """, connection);
        command.Parameters.AddWithValue("@identity", candidate.Fingerprint);
        command.Parameters.AddWithValue("@id", candidate.Id);
        command.Parameters.AddWithValue("@email", candidate.Contacts.Email);
        command.Parameters.AddWithValue("@mobile", candidate.Contacts.Mobile);
        command.Parameters.AddWithValue("@alternative", candidate.Contacts.Alternative);
        var matches = new List<Customer>();
        await using var reader = await command.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
        {
            matches.Add(ReadCustomer(reader));
        }
        return matches;
    }

    public async Task<SavedCustomer> SaveAtomically(Customer customer, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        var now = DateTimeOffset.UtcNow;
        try
        {
            await using var insert = new MySqlCommand("""
                INSERT INTO customers (full_name,street,number,neighborhood,municipality,state,email,mobile,alternative,bin_status,identity_fingerprint,created_at)
                VALUES (@name,@street,@number,@neighborhood,@municipality,@state,@email,@mobile,@alternative,1,@identity,@now)
                """, connection, transaction);
            insert.Parameters.AddWithValue("@name", customer.FullName);
            insert.Parameters.AddWithValue("@street", customer.Address.Street);
            insert.Parameters.AddWithValue("@number", customer.Address.Number);
            insert.Parameters.AddWithValue("@neighborhood", customer.Address.Neighborhood);
            insert.Parameters.AddWithValue("@municipality", customer.Address.Municipality);
            insert.Parameters.AddWithValue("@state", customer.Address.State);
            insert.Parameters.AddWithValue("@email", customer.Contacts.Email);
            insert.Parameters.AddWithValue("@mobile", customer.Contacts.Mobile);
            insert.Parameters.AddWithValue("@alternative", customer.Contacts.Alternative);
            insert.Parameters.AddWithValue("@identity", customer.Fingerprint);
            insert.Parameters.AddWithValue("@now", now.UtcDateTime);
            await insert.ExecuteNonQueryAsync(ct);
            var id = insert.LastInsertedId;
            foreach (var (kind, value) in ContactKeys(customer.Contacts))
            {
                await using var contact = new MySqlCommand("INSERT INTO customer_contact_keys (kind,value,customer_id) VALUES (@kind,@value,@id)", connection, transaction);
                contact.Parameters.AddWithValue("@kind", kind);
                contact.Parameters.AddWithValue("@value", value);
                contact.Parameters.AddWithValue("@id", id);
                await contact.ExecuteNonQueryAsync(ct);
            }
            await using var audit = new MySqlCommand("""
                INSERT INTO audit_entries (actor_id,actor_username,customer_id,action,occurred_at)
                VALUES (@actor,@username,@customer,'UC-CV-01 RegistrarCliente',@now)
                """, connection, transaction);
            audit.Parameters.AddWithValue("@actor", actor.Id);
            audit.Parameters.AddWithValue("@username", actor.Username);
            audit.Parameters.AddWithValue("@customer", id);
            audit.Parameters.AddWithValue("@now", now.UtcDateTime);
            await audit.ExecuteNonQueryAsync(ct);
            var result = new SavedCustomer(customer with {Id = id}, new AuditEntry(audit.LastInsertedId, actor.Id, actor.Username, id, now));
            await transaction.CommitAsync(ct);
            return result;
        }
        catch (MySqlException ex) when (ex.Number == 1062)
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw new UseCaseException(409, "Ya existe un cliente con ese contacto o con el mismo nombre y dirección. No se creó otro registro.");
        }
        catch
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw;
        }
    }
}
