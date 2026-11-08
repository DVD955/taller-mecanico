namespace Taller.Customers;

internal static partial class SelfTests
{
    private static async Task RunVehicleManagement()
    {
        var store = new VehicleManagementMemoryStore();
        var management = new ManageVehicles(store);
        var input = new VehicleInput("WVWZZZ1JZXW000001", "ABC-123-D", "Volkswagen", "Golf", 1999, "Base", "Gris", 0);
        foreach (var role in new[] {"ADMINISTRADOR", "RECEPCIONISTA", "SECRETARIA", "MECANICO", "INVITADO"})
        {
            var actor = Admin with {Role = role};
            var read = role is "ADMINISTRADOR" or "RECEPCIONISTA" or "SECRETARIA";
            var write = role is "ADMINISTRADOR" or "RECEPCIONISTA";
            await Permission(read, () => management.List(actor, 1, 10, "", "all", default), role + " consulta vehículos");
            await Permission(read, () => management.Get(1, actor, default), role + " consulta expediente");
            await Permission(read, () => management.Image(1, 1, actor, default), role + " consulta fotos protegidas");
            await Permission(write, () => management.Update(1, new(input, 1, true), actor, default), role + " actualiza vehículos");
            await Permission(write, () => management.ChangeOwner(1, new(2, 1, true), actor, default), role + " asocia cliente");
            await Permission(role == "ADMINISTRADOR", () => management.Deactivate(1, new(1, true), actor, default), role + " desactiva vehículos");
        }
        await Expect(403, () => management.Get(1, Admin with {Status = "INACTIVO"}, default), "Vehículos: usuario inactivo bloqueado");
        await Expect(422, () => management.List(Admin, 0, 10, "", "all", default), "Vehículos: página inválida");
        await Expect(422, () => management.List(Admin, 1, 101, "", "all", default), "Vehículos: tamaño de página inválido");
        await Expect(422, () => management.List(Admin, 1, 10, "", "otro", default), "Vehículos: filtro inválido");
        await Expect(422, () => management.Update(1, new(input, 1, false), Admin, default), "Vehículos: edición requiere confirmación");
        await Expect(422, () => management.Deactivate(1, new(0, true), Admin, default), "Vehículos: baja requiere revisión");
        await Expect(422, () => management.ChangeOwner(1, new(0, 1, true), Admin, default), "Vehículos: cliente válido obligatorio");
        await Expect(422, () => management.Update(1, new(input with {Plate = "INVALIDA"}, 1, true), Admin, default), "Vehículos: edición mantiene formato de placa");
        Check(VehicleRules.BuildForUpdate(1, input with {Vin = "Q-ANTIGUO123"}).Vin == "Q-ANTIGUO123",
            "Vehículos: el VIN registrado se comprueba por identidad en persistencia");
        var png = new VehiclePhotoInput(new byte[] {137, 80, 78, 71, 13, 10, 26, 10}, "image/png");
        foreach (var (field, incomplete) in new (string, VehicleInput)[]
        {
            ("VIN", input with {Vin = ""}), ("Placa", input with {Plate = ""}),
            ("Marca", input with {Make = " "}), ("Modelo", input with {Model = ""}),
            ("Año", input with {Year = 0}), ("Versión", input with {Version = " "}),
            ("Color", input with {Color = ""}), ("Kilometraje", input with {Mileage = null})
        })
            await Expect(422, () => management.Update(1, new(incomplete, 1, true), Admin, default), "Edición: " + field + " obligatorio");
        await Expect(422, () => management.Update(1, new(input with {Color = null!}, 1, true), Admin, default), "Edición: campo nulo rechazado");
        await Expect(422, () => management.Update(1, new(input with {Mileage = -1}, 1, true), Admin, default), "Edición: kilometraje negativo rechazado");
        await Expect(422, () => management.Update(1, new(input with {Mileage = 10000001}, 1, true), Admin, default), "Edición: kilometraje fuera de límite rechazado");
        Check(VehicleRules.BuildForUpdate(1, input).Mileage == 0, "Edición: kilometraje cero es válido, no equivale a vacío");
        Check(VehicleRules.Build(1, input with {Mileage = null}).Mileage is null, "Alta: kilometraje opcional conservado");
        var withoutPhotos = new ManageVehicles(new VehicleManagementMemoryStore(0));
        await Expect(422, () => withoutPhotos.Update(1, new(input, 1, true), Admin, default), "Edición: exige una foto si no hay fotografías anteriores");
        await withoutPhotos.Update(1, new(input, 1, true, [png]), Admin, default);
        Check(true, "Edición: una foto nueva cubre el requisito");
        await management.Update(1, new(input, 1, true), Admin, default);
        Check(true, "Edición: una foto anterior evita exigir otra carga");
        await Expect(422, () => { VehiclePhotoRules.Validate(null, required: true); return Task.CompletedTask; }, "Edición: no se omite la galería obligatoria con null");
        VehiclePhotoRules.Validate([], 1, required: true);
        Check(true, "Edición: galería existente válida sin fotos nuevas");
        VehiclePhotoRules.Validate([png]);
        Check(true, "Fotos: firma PNG admitida en dominio; contenido se decodifica en FastAPI");
        await Expect(422, () => Photo([]), "Fotos: archivo vacío bloqueado");
        await Expect(422, () => Photo([1, 2, 3]), "Fotos: firma falsa bloqueada");
        await Expect(422, () => Photo(png.Content, "image/svg+xml"), "Fotos: tipo no permitido bloqueado");
        await Expect(413, () => Photo(new byte[VehiclePhotoRules.MaxBytes + 1]), "Fotos: más de 15 MB bloqueado");
        var boundary = new byte[VehiclePhotoRules.MaxBytes];
        png.Content.CopyTo(boundary, 0);
        VehiclePhotoRules.Validate([new(boundary, "image/png")]);
        Check(true, "Fotos: exactamente 15000000 bytes admitidos");
        VehiclePhotoRules.Validate(Enumerable.Repeat(png, 10).ToArray());
        Check(true, "Fotos: varias fotos hasta el límite admitidas");
        await Expect(422, () => { VehiclePhotoRules.Validate(Enumerable.Repeat(png, 11).ToArray()); return Task.CompletedTask; }, "Fotos: límite total de 10 aplicado");

        static Task Photo(byte[] content, string mime = "image/png")
        {
            VehiclePhotoRules.Validate([new(content, mime)]);
            return Task.CompletedTask;
        }
        static async Task Permission(bool allowed, Func<Task> action, string label)
        {
            if (allowed) { await action(); Check(true, label); }
            else await Expect(403, action, label + " bloqueado");
        }
    }

    private sealed class VehicleManagementMemoryStore(int photoCount = 1) : IVehicleManagementStore
    {
        private static readonly Vehicle Vehicle = new(1, 1, "WVWZZZ1JZXW000001", "ABC123D", "Volkswagen", "Golf", 1999, "Base", "Gris", null, "ACTIVO");
        public Task<VehiclePage> SearchVehicles(int page, int pageSize, string search, string status, CancellationToken ct) => Task.FromResult(new VehiclePage([], 0, page, pageSize));
        public Task<VehicleDetails?> GetVehicle(long id, CancellationToken ct) => Task.FromResult<VehicleDetails?>(new(Vehicle, "Cliente", "Taller",
            Enumerable.Range(1, photoCount).Select(index => new VehiclePhoto(index, "image/png", 100)).ToArray(), []));
        public Task<VehicleImage?> GetVehicleImage(long vehicleId, long photoId, CancellationToken ct) => Task.FromResult<VehicleImage?>(new([], "image/png"));
        public Task<SavedVehicle> UpdateVehicleAtomically(long id, VehicleUpdateRequest input, Actor actor, CancellationToken ct) => Saved(actor);
        public Task<SavedVehicle> DeactivateVehicleAtomically(long id, int recordVersion, Actor actor, CancellationToken ct) => Saved(actor);
        public Task<SavedVehicle> ChangeVehicleOwnerAtomically(long id, VehicleChangeOwnerRequest input, Actor actor, CancellationToken ct) => Saved(actor);
        private static Task<SavedVehicle> Saved(Actor actor) => Task.FromResult(new SavedVehicle(Vehicle, new(1, actor.Id, actor.Username, 1, 1, DateTimeOffset.UtcNow)));
    }
}
