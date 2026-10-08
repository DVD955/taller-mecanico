namespace Taller.Customers;

public sealed record CustomerPage(IReadOnlyList<Customer> Items, long Total, int Page, int PageSize);
public sealed record UpdateDraft(CustomerInput Customer, int Version);
public sealed record UpdateRequest(CustomerInput Customer, string PreviewToken, bool Confirmed, int Version);
public sealed record DeleteRequest(int Version, bool Confirmed);

// Bridge: extiende las capacidades del implementor sin acoplar el caso de uso a SQL.
public interface ICustomerManagementStore : ICustomerStore
{
    Task<CustomerPage> List(int page, int pageSize, string search, CancellationToken ct);
    Task<Customer?> Get(long id, CancellationToken ct);
    Task<SavedCustomer> UpdateAtomically(Customer customer, Actor actor, CancellationToken ct);
    Task<SavedCustomer> DeleteAtomically(long id, int version, Actor actor, CancellationToken ct);
}

public abstract class CustomerManagement(ICustomerManagementStore storage)
{
    protected ICustomerManagementStore Storage { get; } = storage;
    public abstract Task<CustomerPage> List(Actor actor, int page, int pageSize, string search, CancellationToken ct);
    public abstract Task<Customer> Get(long id, Actor actor, CancellationToken ct);
    public abstract Task<PreviewResult> PreviewUpdate(long id, UpdateDraft input, Actor actor, CancellationToken ct);
    public abstract Task<SavedCustomer> Update(long id, UpdateRequest input, Actor actor, CancellationToken ct);
    public abstract Task<SavedCustomer> Delete(long id, DeleteRequest input, Actor actor, CancellationToken ct);
}

public sealed class ManageCustomers(ICustomerManagementStore storage, ContactNormalizer normalizer, PreviewSigner signer)
    : CustomerManagement(storage)
{
    public override Task<CustomerPage> List(Actor actor, int page, int pageSize, string search, CancellationToken ct)
    {
        actor.Authorize();
        if (page < 1 || page > 100_000 || pageSize < 1 || pageSize > 100 || search.Length > 120 || search.Any(char.IsControl))
            throw new UseCaseException(422, "La búsqueda o la paginación no son válidas.");
        return Storage.List(page, pageSize, search.Trim(), ct);
    }

    public override async Task<Customer> Get(long id, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        return await Storage.Get(id, ct) ?? throw new UseCaseException(404, "El cliente no existe o fue eliminado del listado.");
    }

    private async Task<Customer> BuildUpdate(long id, CustomerInput? input, int version, Actor actor, CancellationToken ct)
    {
        var current = await Get(id, actor, ct);
        if (version < 1) throw new UseCaseException(422, "La versión del cliente es obligatoria.");
        if (version != current.Version) throw new UseCaseException(409, "Otro usuario modificó este cliente. Actualiza el listado y revisa nuevamente.");
        if (input is null) throw new UseCaseException(422, "Los datos del cliente son obligatorios.");
        return new CustomerBuilder(normalizer).WithName(input.FullName).WithAddress(input.Address).WithContacts(input.Contacts).Build()
            with {Id = id, Version = version, Status = current.Status};
    }

    public override async Task<PreviewResult> PreviewUpdate(long id, UpdateDraft input, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        var candidate = await BuildUpdate(id, input.Customer, input.Version, actor, ct);
        var matches = await Storage.FindMatches(candidate, ct);
        return new PreviewResult(candidate, matches, matches.Count == 0 ? signer.Issue(candidate, actor) : null);
    }

    public override async Task<SavedCustomer> Update(long id, UpdateRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        if (!input.Confirmed) throw new UseCaseException(422, "Confirma los cambios antes de actualizar.");
        var candidate = await BuildUpdate(id, input.Customer, input.Version, actor, ct);
        signer.Validate(input.PreviewToken, candidate, actor);
        if ((await Storage.FindMatches(candidate, ct)).Count > 0)
            throw new UseCaseException(409, "Otro cliente ya tiene ese contacto o el mismo nombre y dirección. No se guardaron los cambios.");
        return await Storage.UpdateAtomically(candidate, actor, ct);
    }

    public override async Task<SavedCustomer> Delete(long id, DeleteRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        if (!input.Confirmed || input.Version < 1)
            throw new UseCaseException(422, "Confirma la eliminación del cliente e indica su versión vigente.");
        return await Storage.DeleteAtomically(id, input.Version, actor, ct);
    }
}
