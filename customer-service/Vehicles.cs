namespace Taller.Customers;

public sealed record VehicleInput(string Vin, string Plate, string Make, string Model, int Year,
    string Version, string Color, int? Mileage = null);
public sealed record Vehicle(long Id, long CustomerId, string Vin, string Plate, string Make, string Model,
    int Year, string Version, string Color, int? Mileage, string Status, int RecordVersion = 1);
public sealed record VehiclePhotoInput(byte[] Content, string ContentType);
public sealed record VehicleRequest(VehicleInput Vehicle, bool Confirmed, IReadOnlyList<VehiclePhotoInput>? Photos = null);
public sealed record VehicleAudit(long Id, int ActorId, string ActorUsername, long CustomerId,
    long VehicleId, DateTimeOffset OccurredAt, string Action = "UC-CV-06 RegistrarVehiculo", long? PreviousCustomerId = null);
public sealed record SavedVehicle(Vehicle Vehicle, VehicleAudit AuditEntry);

public static class VehicleRules
{
    public static Vehicle BuildForUpdate(long customerId, VehicleInput? input) => Build(customerId, input, editing: true);

    public static Vehicle Build(long customerId, VehicleInput? input) => Build(customerId, input, editing: false);

    private static Vehicle Build(long customerId, VehicleInput? input, bool editing)
    {
        if (input is null) throw new UseCaseException(422, "Captura los datos del vehículo.");
        var vin = editing ? TextRules.Required(input.Vin, "VIN", 17) : VehicleIdentifiers.Vin(input.Vin);
        var plate = VehicleIdentifiers.MexicanPlate(input.Plate);
        if (input.Year < 1900 || input.Year > DateTime.UtcNow.Year + 1)
            throw new UseCaseException(422, $"Año: utiliza un año entre 1900 y {DateTime.UtcNow.Year + 1}.");
        if (editing && input.Mileage is null)
            throw new UseCaseException(422, "Kilometraje: obligatorio para modificar el vehículo.");
        if (input.Mileage is < 0 or > 10_000_000)
            throw new UseCaseException(422, "Kilometraje: utiliza un número entero entre 0 y 10000000.");
        return new(0, customerId, vin, plate, TextRules.Required(input.Make, "Marca", 60),
            TextRules.Required(input.Model, "Modelo", 60), input.Year, TextRules.Required(input.Version, "Versión", 60),
            TextRules.Required(input.Color, "Color", 40), input.Mileage, "ACTIVO");
    }
}

// Bridge: el caso de uso delega la relación, unicidad y auditoría al adaptador.
public interface IVehicleStore
{
    Task<IReadOnlyList<Vehicle>> ListVehicles(long customerId, CancellationToken ct);
    Task<SavedVehicle> SaveVehicleAtomically(Vehicle vehicle, Actor actor, CancellationToken ct, IReadOnlyList<VehiclePhotoInput>? photos = null);
}

public sealed class RegisterVehicle(IVehicleStore storage, ICustomerManagementStore customers)
{
    public async Task<IReadOnlyList<Vehicle>> List(long customerId, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.Read);
        _ = await customers.Get(customerId, ct) ?? throw new UseCaseException(404, "El cliente no está disponible.");
        return await storage.ListVehicles(customerId, ct);
    }

    public async Task<SavedVehicle> Register(long customerId, VehicleRequest request, Actor actor, CancellationToken ct)
    {
        actor.Authorize(CustomerOperation.RegisterVehicle);
        if (!request.Confirmed) throw new UseCaseException(422, "Confirma el registro del vehículo.");
        var customer = await customers.Get(customerId, ct) ?? throw new UseCaseException(404, "El cliente no está disponible.");
        if (customer.Status != "ACTIVO") throw new UseCaseException(409, "Solo se pueden asociar vehículos a clientes activos.");
        VehiclePhotoRules.Validate(request.Photos);
        return await storage.SaveVehicleAtomically(VehicleRules.Build(customerId, request.Vehicle), actor, ct, request.Photos);
    }
}
