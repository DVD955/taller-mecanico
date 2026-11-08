using MySqlConnector;

namespace Taller.Customers;

public sealed partial class MySqlCustomerStore : IVehicleManagementStore
{
    private const string VehicleSource = " FROM vehicles v INNER JOIN status s ON s.id=v.bin_status "
        + "INNER JOIN customers c ON c.id=v.customer_id LEFT JOIN workshops w ON w.id=c.workshop_id ";

    private static Vehicle ReadVehicle(MySqlDataReader r) => new(r.GetInt64("id"), r.GetInt64("customer_id"),
        r.GetString("vin"), r.GetString("plate"), r.GetString("make"), r.GetString("model"), r.GetInt32("year"),
        r.GetString("version"), r.GetString("color"), r.IsDBNull(r.GetOrdinal("mileage")) ? null : r.GetInt32("mileage"),
        StatusFromCatalog(r.GetInt32("status_id")), r.GetInt32("record_version"));

    private static async Task InitializeVehicleManagement(MySqlConnection connection, CancellationToken ct)
    {
        foreach (var (table, column, definition) in new[]
        {
            ("vehicles", "record_version", "INT NOT NULL DEFAULT 1"),
            ("vehicles", "updated_at", "DATETIME(6) NULL"),
            ("vehicles", "deleted_at", "DATETIME(6) NULL"),
            ("vehicle_audit_entries", "previous_customer_id", "BIGINT NULL")
        })
        {
            await using var inspect = new MySqlCommand("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=@table AND COLUMN_NAME=@column", connection);
            inspect.Parameters.AddWithValue("@table", table);
            inspect.Parameters.AddWithValue("@column", column);
            if (Convert.ToInt32(await inspect.ExecuteScalarAsync(ct)) == 0)
            {
                // Los identificadores proceden exclusivamente de la lista constante anterior.
                await using var migrate = new MySqlCommand($"ALTER TABLE {table} ADD COLUMN {column} {definition}", connection);
                await migrate.ExecuteNonQueryAsync(ct);
            }
        }
    }

    public async Task<VehiclePage> SearchVehicles(int page, int pageSize, string search, string status, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        const string filter = """
            WHERE (@status='all' OR (@status='active' AND v.bin_status=1) OR (@status='inactive' AND v.bin_status<>1))
            AND (@empty=1 OR v.vin LIKE @search ESCAPE '!' OR v.plate LIKE @search ESCAPE '!'
              OR v.make LIKE @search ESCAPE '!' OR v.model LIKE @search ESCAPE '!'
              OR c.full_name LIKE @search ESCAPE '!')
            """;
        var pattern = "%" + search.Replace("!", "!!").Replace("%", "!%").Replace("_", "!_") + "%";
        await using var count = new MySqlCommand("SELECT COUNT(*)" + VehicleSource + filter, connection, transaction);
        Bind(count);
        var total = Convert.ToInt64(await count.ExecuteScalarAsync(ct));
        await using var command = new MySqlCommand("SELECT v.*,s.id AS status_id,c.full_name,w.name AS workshop_name,"
            + "(SELECT COUNT(*) FROM vehicle_photos p WHERE p.vehicle_id=v.id) AS photo_count" + VehicleSource + filter
            + " ORDER BY v.id DESC LIMIT @limit OFFSET @offset", connection, transaction);
        Bind(command);
        command.Parameters.AddWithValue("@limit", pageSize);
        command.Parameters.AddWithValue("@offset", (page - 1) * pageSize);
        var items = new List<VehicleListItem>();
        await using (var reader = await command.ExecuteReaderAsync(ct))
            while (await reader.ReadAsync(ct))
                items.Add(new(ReadVehicle(reader), reader.GetString("full_name"),
                    reader.IsDBNull(reader.GetOrdinal("workshop_name")) ? null : reader.GetString("workshop_name"), reader.GetInt32("photo_count")));
        await transaction.CommitAsync(ct);
        return new(items, total, page, pageSize);

        void Bind(MySqlCommand query)
        {
            query.Parameters.AddWithValue("@status", status);
            query.Parameters.AddWithValue("@empty", search.Length == 0);
            query.Parameters.AddWithValue("@search", pattern);
        }
    }

    public async Task<VehicleDetails?> GetVehicle(long id, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        Vehicle vehicle;
        string customerName;
        string? workshopName;
        await using (var command = new MySqlCommand("SELECT v.*,s.id AS status_id,c.full_name,w.name AS workshop_name" + VehicleSource + "WHERE v.id=@id", connection, transaction))
        {
            command.Parameters.AddWithValue("@id", id);
            await using var reader = await command.ExecuteReaderAsync(ct);
            if (!await reader.ReadAsync(ct)) return null;
            vehicle = ReadVehicle(reader);
            customerName = reader.GetString("full_name");
            workshopName = reader.IsDBNull(reader.GetOrdinal("workshop_name")) ? null : reader.GetString("workshop_name");
        }
        var photos = new List<VehiclePhoto>();
        await using (var command = new MySqlCommand("SELECT id,content_type,size_bytes FROM vehicle_photos WHERE vehicle_id=@id ORDER BY id", connection, transaction))
        {
            command.Parameters.AddWithValue("@id", id);
            await using var reader = await command.ExecuteReaderAsync(ct);
            while (await reader.ReadAsync(ct)) photos.Add(new(reader.GetInt64(0), reader.GetString(1), reader.GetInt32(2)));
        }
        var audits = new List<VehicleAudit>();
        await using (var command = new MySqlCommand("SELECT * FROM vehicle_audit_entries WHERE vehicle_id=@id ORDER BY id DESC LIMIT 100", connection, transaction))
        {
            command.Parameters.AddWithValue("@id", id);
            await using var reader = await command.ExecuteReaderAsync(ct);
            while (await reader.ReadAsync(ct)) audits.Add(new(reader.GetInt64("id"), reader.GetInt32("actor_id"), reader.GetString("actor_username"),
                reader.GetInt64("customer_id"), id, new DateTimeOffset(DateTime.SpecifyKind(reader.GetDateTime("occurred_at"), DateTimeKind.Utc)),
                reader.GetString("action"), reader.IsDBNull(reader.GetOrdinal("previous_customer_id")) ? null : reader.GetInt64("previous_customer_id")));
        }
        await transaction.CommitAsync(ct);
        return new(vehicle, customerName, workshopName, photos, audits);
    }

    public async Task<VehicleImage?> GetVehicleImage(long vehicleId, long photoId, CancellationToken ct)
    {
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var command = new MySqlCommand("SELECT content,content_type FROM vehicle_photos WHERE id=@photo AND vehicle_id=@vehicle", connection);
        command.Parameters.AddWithValue("@photo", photoId);
        command.Parameters.AddWithValue("@vehicle", vehicleId);
        await using var reader = await command.ExecuteReaderAsync(ct);
        return await reader.ReadAsync(ct) ? new((byte[])reader[0], reader.GetString(1)) : null;
    }

    private static async Task InsertVehiclePhotos(MySqlConnection connection, MySqlTransaction transaction, long id,
        IReadOnlyList<VehiclePhotoInput>? photos, CancellationToken ct)
    {
        VehiclePhotoRules.Validate(photos);
        if (photos is null || photos.Count == 0) return;
        await using var count = new MySqlCommand("SELECT COUNT(*) FROM vehicle_photos WHERE vehicle_id=@id", connection, transaction);
        count.Parameters.AddWithValue("@id", id);
        if (Convert.ToInt32(await count.ExecuteScalarAsync(ct)) + photos.Count > VehiclePhotoRules.MaxPhotos)
            throw new UseCaseException(422, "Se permiten hasta 10 fotos por vehículo. Las fotos anteriores se conservan.");
        foreach (var photo in photos)
        {
            await using var insert = new MySqlCommand("INSERT INTO vehicle_photos (vehicle_id,content_type,size_bytes,content,created_at) VALUES (@id,@type,@size,@content,UTC_TIMESTAMP(6))", connection, transaction);
            insert.Parameters.AddWithValue("@id", id);
            insert.Parameters.AddWithValue("@type", photo.ContentType);
            insert.Parameters.AddWithValue("@size", photo.Content.Length);
            insert.Parameters.AddWithValue("@content", photo.Content);
            await insert.ExecuteNonQueryAsync(ct);
        }
    }

    public Task<SavedVehicle> UpdateVehicleAtomically(long id, VehicleUpdateRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.RegisterVehicle);
        _ = VehicleRules.BuildForUpdate(0, input.Vehicle);
        return MutateVehicle(id, input.RecordVersion, actor, ct, input.Vehicle, input.Photos);
    }

    public Task<SavedVehicle> DeactivateVehicleAtomically(long id, int recordVersion, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.Deactivate);
        return MutateVehicle(id, recordVersion, actor, ct, deactivate: true);
    }

    public Task<SavedVehicle> ChangeVehicleOwnerAtomically(long id, VehicleChangeOwnerRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.RegisterVehicle);
        return MutateVehicle(id, input.RecordVersion, actor, ct, newOwner: input.CustomerId);
    }

    private async Task<SavedVehicle> MutateVehicle(long id, int revision, Actor actor, CancellationToken ct,
        VehicleInput? input = null, IReadOnlyList<VehiclePhotoInput>? photos = null, bool deactivate = false, long? newOwner = null)
    {
        var observed = await GetVehicle(id, ct) ?? throw new UseCaseException(404, "El vehículo no existe.");
        await using var connection = new MySqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        try
        {
            // Igual que el alta/baja de clientes: primero bloquear clientes, luego vehículo.
            foreach (var customerId in new[] {observed.Vehicle.CustomerId, newOwner ?? observed.Vehicle.CustomerId}.Distinct().Order())
            {
                await using var customer = new MySqlCommand("SELECT bin_status,deleted_at FROM customers WHERE id=@id FOR UPDATE", connection, transaction);
                customer.Parameters.AddWithValue("@id", customerId);
                await using var reader = await customer.ExecuteReaderAsync(ct);
                if (!await reader.ReadAsync(ct)) throw new UseCaseException(404, "El cliente no existe.");
                if (newOwner == customerId && (reader.GetInt32(0) != 1 || !reader.IsDBNull(1)))
                    throw new UseCaseException(409, "El nuevo propietario debe ser un cliente activo.");
            }
            Vehicle current;
            await using (var command = new MySqlCommand("SELECT v.*,v.bin_status AS status_id FROM vehicles v WHERE id=@id FOR UPDATE", connection, transaction))
            {
                command.Parameters.AddWithValue("@id", id);
                await using var reader = await command.ExecuteReaderAsync(ct);
                if (!await reader.ReadAsync(ct)) throw new UseCaseException(404, "El vehículo no existe.");
                current = ReadVehicle(reader);
            }
            if (current.RecordVersion != revision || current.CustomerId != observed.Vehicle.CustomerId)
                throw new UseCaseException(409, "El vehículo cambió. Actualiza el listado antes de continuar.");
            if (current.Status != "ACTIVO") throw new UseCaseException(409, "El vehículo está inactivo. Se conserva únicamente para consulta.");
            if (newOwner == current.CustomerId) throw new UseCaseException(422, "El vehículo ya está asociado a ese cliente.");
            var candidate = current;
            if (input is not null)
            {
                var edited = VehicleRules.BuildForUpdate(current.CustomerId, input);
                var registeredVin = TextRules.Required(current.Vin, "VIN", 17);
                if (!string.Equals(edited.Vin, registeredVin, StringComparison.OrdinalIgnoreCase))
                    throw new UseCaseException(422, "El VIN registrado no se puede modificar.");
                candidate = edited with {Id = id, Vin = current.Vin};
                await using var countPhotos = new MySqlCommand("SELECT COUNT(*) FROM vehicle_photos WHERE vehicle_id=@id", connection, transaction);
                countPhotos.Parameters.AddWithValue("@id", id);
                VehiclePhotoRules.Validate(photos, Convert.ToInt32(await countPhotos.ExecuteScalarAsync(ct)), required: true);
            }
            candidate = candidate with {CustomerId = newOwner ?? current.CustomerId, Status = deactivate ? "INACTIVO" : "ACTIVO", RecordVersion = revision + 1};
            await using (var duplicate = new MySqlCommand("SELECT EXISTS(SELECT 1 FROM vehicles WHERE id<>@id AND (vin=@vin OR plate=@plate))", connection, transaction))
            {
                duplicate.Parameters.AddWithValue("@id", id);
                duplicate.Parameters.AddWithValue("@vin", candidate.Vin);
                duplicate.Parameters.AddWithValue("@plate", candidate.Plate);
                if (Convert.ToInt32(await duplicate.ExecuteScalarAsync(ct)) != 0)
                    throw new UseCaseException(409, "Otro vehículo ya tiene ese VIN o placa, incluso si está inactivo.");
            }
            var now = DateTimeOffset.UtcNow;
            await using (var update = new MySqlCommand("""
                UPDATE vehicles SET customer_id=@customer,plate=@plate,make=@make,model=@model,year=@year,
                  version=@trim,color=@color,mileage=@mileage,bin_status=@status,record_version=@revision,updated_at=@now,deleted_at=@deleted
                WHERE id=@id
                """, connection, transaction))
            {
                update.Parameters.AddWithValue("@id", id);
                update.Parameters.AddWithValue("@customer", candidate.CustomerId);
                update.Parameters.AddWithValue("@plate", candidate.Plate);
                update.Parameters.AddWithValue("@make", candidate.Make);
                update.Parameters.AddWithValue("@model", candidate.Model);
                update.Parameters.AddWithValue("@year", candidate.Year);
                update.Parameters.AddWithValue("@trim", candidate.Version);
                update.Parameters.AddWithValue("@color", candidate.Color);
                update.Parameters.AddWithValue("@mileage", candidate.Mileage);
                update.Parameters.AddWithValue("@status", deactivate ? 2 : 1);
                update.Parameters.AddWithValue("@revision", candidate.RecordVersion);
                update.Parameters.AddWithValue("@now", now.UtcDateTime);
                update.Parameters.AddWithValue("@deleted", deactivate ? now.UtcDateTime : null);
                await update.ExecuteNonQueryAsync(ct);
            }
            await InsertVehiclePhotos(connection, transaction, id, photos, ct);
            var action = deactivate ? "UC-CV-09 DesactivarVehiculo" : newOwner.HasValue ? "UC-CV-12 CambiarPropietario" : "UC-CV-08 ActualizarVehiculo";
            await using var audit = new MySqlCommand("""
                INSERT INTO vehicle_audit_entries (actor_id,actor_username,customer_id,vehicle_id,action,previous_customer_id,occurred_at)
                VALUES (@actor,@username,@customer,@vehicle,@action,@previous,@now)
                """, connection, transaction);
            audit.Parameters.AddWithValue("@actor", actor.Id);
            audit.Parameters.AddWithValue("@username", actor.Username);
            audit.Parameters.AddWithValue("@customer", candidate.CustomerId);
            audit.Parameters.AddWithValue("@vehicle", id);
            audit.Parameters.AddWithValue("@action", action);
            audit.Parameters.AddWithValue("@previous", newOwner.HasValue ? current.CustomerId : null);
            audit.Parameters.AddWithValue("@now", now.UtcDateTime);
            await audit.ExecuteNonQueryAsync(ct);
            var entry = new VehicleAudit(audit.LastInsertedId, actor.Id, actor.Username, candidate.CustomerId, id, now, action,
                newOwner.HasValue ? current.CustomerId : null);
            await transaction.CommitAsync(ct);
            return new(candidate, entry);
        }
        catch (MySqlException ex) when (ex.Number == 1062)
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw new UseCaseException(409, "Otro vehículo ya tiene ese VIN o placa. No se guardaron cambios.");
        }
        catch
        {
            await transaction.RollbackAsync(CancellationToken.None);
            throw;
        }
    }
}
