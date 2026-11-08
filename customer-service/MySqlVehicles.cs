using MySqlConnector;

namespace Taller.Customers;

public sealed partial class MySqlCustomerStore : IVehicleStore
{
    public async Task<IReadOnlyList<Vehicle>> ListVehicles(long customerId, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var command = new MySqlCommand("""
            SELECT v.*, s.id AS status_id FROM vehicles v INNER JOIN status s ON s.id=v.bin_status
            WHERE v.customer_id=@customer ORDER BY v.created_at DESC, v.id DESC
            """, connection);
        command.Parameters.AddWithValue("@customer", customerId);
        var items = new List<Vehicle>();
        await using var reader = await command.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
            items.Add(new(reader.GetInt64("id"), reader.GetInt64("customer_id"), reader.GetString("vin"),
                reader.GetString("plate"), reader.GetString("make"), reader.GetString("model"), reader.GetInt32("year"),
                reader.GetString("version"), reader.GetString("color"),
                reader.IsDBNull(reader.GetOrdinal("mileage")) ? null : reader.GetInt32("mileage"),
                StatusFromCatalog(reader.GetInt32("status_id")), reader.GetInt32("record_version")));
        return items;
    }

    public async Task<SavedVehicle> SaveVehicleAtomically(Vehicle vehicle, Actor actor, CancellationToken ct, IReadOnlyList<VehiclePhotoInput>? photos = null)
    {
        actor.Authorize(CustomerOperation.RegisterVehicle);
        VehiclePhotoRules.Validate(photos);
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        try
        {
            // El mismo bloqueo que usa la baja evita asociar después de desactivar.
            await using var customer = new MySqlCommand("SELECT bin_status FROM customers WHERE id=@id FOR UPDATE", connection, transaction);
            customer.Parameters.AddWithValue("@id", vehicle.CustomerId);
            var status = await customer.ExecuteScalarAsync(ct);
            if (status is null) throw new UseCaseException(404, "El cliente no existe.");
            if (Convert.ToInt32(status) != 1) throw new UseCaseException(409, "Solo se pueden asociar vehículos a clientes activos.");
            // Buscar antes de guardar. Los índices UNIQUE siguen siendo la
            // protección definitiva frente a altas simultáneas de otros clientes.
            await using var duplicate = new MySqlCommand("""
                SELECT EXISTS(SELECT 1 FROM vehicles WHERE vin=@vin OR plate=@plate)
                """, connection, transaction);
            duplicate.Parameters.AddWithValue("@vin", vehicle.Vin);
            duplicate.Parameters.AddWithValue("@plate", vehicle.Plate);
            if (Convert.ToInt32(await duplicate.ExecuteScalarAsync(ct)) != 0)
                throw new UseCaseException(409, "Ya existe un vehículo con ese VIN o placa. No se creó otro registro ni se cambió su cliente.");
            var now = DateTimeOffset.UtcNow;
            await using var insert = new MySqlCommand("""
                INSERT INTO vehicles (customer_id,vin,plate,make,model,year,version,color,mileage,bin_status,created_at)
                VALUES (@customer,@vin,@plate,@make,@model,@year,@version,@color,@mileage,1,@now)
                """, connection, transaction);
            insert.Parameters.AddWithValue("@customer", vehicle.CustomerId);
            insert.Parameters.AddWithValue("@vin", vehicle.Vin);
            insert.Parameters.AddWithValue("@plate", vehicle.Plate);
            insert.Parameters.AddWithValue("@make", vehicle.Make);
            insert.Parameters.AddWithValue("@model", vehicle.Model);
            insert.Parameters.AddWithValue("@year", vehicle.Year);
            insert.Parameters.AddWithValue("@version", vehicle.Version);
            insert.Parameters.AddWithValue("@color", vehicle.Color);
            insert.Parameters.AddWithValue("@mileage", vehicle.Mileage);
            insert.Parameters.AddWithValue("@now", now.UtcDateTime);
            await insert.ExecuteNonQueryAsync(ct);
            var id = insert.LastInsertedId;
            await InsertVehiclePhotos(connection, transaction, id, photos, ct);
            await using var audit = new MySqlCommand("""
                INSERT INTO vehicle_audit_entries (actor_id,actor_username,customer_id,vehicle_id,action,occurred_at)
                VALUES (@actor,@username,@customer,@vehicle,'UC-CV-06 RegistrarVehiculo',@now)
                """, connection, transaction);
            audit.Parameters.AddWithValue("@actor", actor.Id);
            audit.Parameters.AddWithValue("@username", actor.Username);
            audit.Parameters.AddWithValue("@customer", vehicle.CustomerId);
            audit.Parameters.AddWithValue("@vehicle", id);
            audit.Parameters.AddWithValue("@now", now.UtcDateTime);
            await audit.ExecuteNonQueryAsync(ct);
            var result = new SavedVehicle(vehicle with {Id = id}, new(audit.LastInsertedId, actor.Id, actor.Username, vehicle.CustomerId, id, now));
            await transaction.CommitAsync(ct);
            return result;
        }
        catch (MySqlException ex) when (ex.Number == 1062)
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw new UseCaseException(409, "Ya existe un vehículo con ese VIN o placa. No se creó otro registro ni se cambió su cliente.");
        }
        catch
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw;
        }
    }
}
