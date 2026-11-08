namespace Taller.Customers;

public sealed record VehiclePhoto(long Id, string ContentType, int SizeBytes);
public sealed record VehicleImage(byte[] Content, string ContentType);
public sealed record VehicleListItem(Vehicle Vehicle, string CustomerName, string? WorkshopName, int PhotoCount);
public sealed record VehiclePage(IReadOnlyList<VehicleListItem> Items, long Total, int Page, int PageSize);
public sealed record VehicleDetails(Vehicle Vehicle, string CustomerName, string? WorkshopName,
    IReadOnlyList<VehiclePhoto> Photos, IReadOnlyList<VehicleAudit> AuditEntries);
public sealed record VehicleUpdateRequest(VehicleInput Vehicle, int RecordVersion, bool Confirmed,
    IReadOnlyList<VehiclePhotoInput>? Photos = null);
public sealed record VehicleChangeOwnerRequest(long CustomerId, int RecordVersion, bool Confirmed);
public sealed record VehicleDeactivateRequest(int RecordVersion, bool Confirmed);

public static class VehiclePhotoRules
{
    public const int MaxBytes = 15_000_000;
    public const int MaxPhotos = 10;

    public static void Validate(IReadOnlyList<VehiclePhotoInput>? photos, int existingCount = 0, bool required = false)
    {
        var total = existingCount + (photos?.Count ?? 0);
        if (required && total < 1) throw new UseCaseException(422, "Agrega al menos una fotografía para modificar el vehículo.");
        if (total > MaxPhotos) throw new UseCaseException(422, "Se permiten hasta 10 fotos por vehículo.");
        if (photos is null) return;
        foreach (var photo in photos)
        {
            if (photo is null || photo.Content is null || photo.Content.Length == 0)
                throw new UseCaseException(422, "La foto está vacía.");
            if (photo.Content.Length > MaxBytes) throw new UseCaseException(413, "Cada foto debe pesar como máximo 15 MB.");
            var data = photo.Content.AsSpan();
            var valid = photo.ContentType switch
            {
                "image/jpeg" => data.Length >= 4 && data[0] == 0xff && data[1] == 0xd8 && data[2] == 0xff,
                "image/png" => data.StartsWith(new byte[] {137, 80, 78, 71, 13, 10, 26, 10}),
                "image/webp" => data.Length >= 12 && data[..4].SequenceEqual("RIFF"u8) && data.Slice(8, 4).SequenceEqual("WEBP"u8),
                _ => false
            };
            if (!valid) throw new UseCaseException(422, "Adjunta fotos JPG, PNG o WebP válidas.");
        }
    }
}

// Bridge: la administración no depende de consultas SQL ni del transporte de fotos.
public interface IVehicleManagementStore
{
    Task<VehiclePage> SearchVehicles(int page, int pageSize, string search, string status, CancellationToken ct);
    Task<VehicleDetails?> GetVehicle(long id, CancellationToken ct);
    Task<VehicleImage?> GetVehicleImage(long vehicleId, long photoId, CancellationToken ct);
    Task<SavedVehicle> UpdateVehicleAtomically(long id, VehicleUpdateRequest input, Actor actor, CancellationToken ct);
    Task<SavedVehicle> DeactivateVehicleAtomically(long id, int recordVersion, Actor actor, CancellationToken ct);
    Task<SavedVehicle> ChangeVehicleOwnerAtomically(long id, VehicleChangeOwnerRequest input, Actor actor, CancellationToken ct);
}

public sealed class ManageVehicles(IVehicleManagementStore storage)
{
    public Task<VehiclePage> List(Actor actor, int page, int pageSize, string search, string status, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.Read);
        if (page < 1 || page > 100_000 || pageSize < 1 || pageSize > 100 || search.Length > 120
            || search.Any(char.IsControl) || status is not ("all" or "active" or "inactive"))
            throw new UseCaseException(422, "La búsqueda o el filtro de vehículos no son válidos.");
        return storage.SearchVehicles(page, pageSize, search.Trim(), status, ct);
    }

    public async Task<VehicleDetails> Get(long id, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.Read);
        return await storage.GetVehicle(id, ct) ?? throw new UseCaseException(404, "El vehículo no existe.");
    }

    public async Task<VehicleImage> Image(long id, long photoId, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.Read);
        return await storage.GetVehicleImage(id, photoId, ct) ?? throw new UseCaseException(404, "La foto no existe para ese vehículo.");
    }

    public async Task<SavedVehicle> Update(long id, VehicleUpdateRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.RegisterVehicle);
        Confirm(input.Confirmed, input.RecordVersion);
        _ = VehicleRules.BuildForUpdate(0, input.Vehicle);
        var current = await storage.GetVehicle(id, ct) ?? throw new UseCaseException(404, "El vehículo no existe.");
        VehiclePhotoRules.Validate(input.Photos, current.Photos.Count, required: true);
        return await storage.UpdateVehicleAtomically(id, input, actor, ct);
    }

    public Task<SavedVehicle> Deactivate(long id, VehicleDeactivateRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.Deactivate);
        Confirm(input.Confirmed, input.RecordVersion);
        return storage.DeactivateVehicleAtomically(id, input.RecordVersion, actor, ct);
    }

    public Task<SavedVehicle> ChangeOwner(long id, VehicleChangeOwnerRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.RegisterVehicle);
        Confirm(input.Confirmed, input.RecordVersion);
        if (input.CustomerId < 1) throw new UseCaseException(422, "Selecciona un cliente activo.");
        return storage.ChangeVehicleOwnerAtomically(id, input, actor, ct);
    }

    private static void Confirm(bool confirmed, int version)
    {
        if (!confirmed || version < 1) throw new UseCaseException(422, "Confirma la operación con la revisión vigente del vehículo.");
    }
}
