using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Taller.Customers;

// Bridge implementor: persistencia reemplazable, sin SQL en el caso de uso.
public interface ICustomerStore
{
    Task<IReadOnlyList<Customer>> FindMatches(Customer candidate, CancellationToken ct);
    Task<SavedCustomer> SaveAtomically(Customer customer, Actor actor, CancellationToken ct);
}

// Bridge abstraction: operaciones de clientes delegan al implementor elegido.
public abstract class CustomerRegistry(ICustomerStore storage)
{
    protected ICustomerStore Storage { get; } = storage;
    public abstract Task<PreviewResult> Preview(CustomerInput input, Actor actor, CancellationToken ct);
    public abstract Task<SavedCustomer> Register(ConfirmRequest input, Actor actor, CancellationToken ct);
}

public sealed record PreviewResult(Customer Customer, IReadOnlyList<Customer> Matches, string? PreviewToken);
public sealed record ConfirmRequest(CustomerInput Customer, string PreviewToken, bool Confirmed);

// Firma ligada al actor y a todos los datos normalizados. Caduca en 10 minutos.
public sealed class PreviewSigner
{
    private readonly byte[] key = RandomNumberGenerator.GetBytes(32);
    private static string Digest(Customer customer) => Convert.ToHexString(SHA256.HashData(
        Encoding.UTF8.GetBytes(JsonSerializer.Serialize(customer))));

    public string Issue(Customer customer, Actor actor)
    {
        var payload = $"{actor.Id}:{DateTimeOffset.UtcNow.AddMinutes(10).ToUnixTimeSeconds()}:{Digest(customer)}";
        var encoded = Convert.ToBase64String(Encoding.UTF8.GetBytes(payload));
        return encoded + "." + Convert.ToHexString(HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(encoded)));
    }

    public void Validate(string? token, Customer customer, Actor actor)
    {
        try
        {
            var parts = token!.Split('.');
            var signature = Convert.FromHexString(parts[1]);
            var valid = CryptographicOperations.FixedTimeEquals(signature, HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(parts[0])));
            var payload = Encoding.UTF8.GetString(Convert.FromBase64String(parts[0])).Split(':');
            if (parts.Length != 2 || !valid || payload[0] != actor.Id.ToString()
                || long.Parse(payload[1]) <= DateTimeOffset.UtcNow.ToUnixTimeSeconds() || payload[2] != Digest(customer))
                throw new FormatException();
        }
        catch (Exception ex) when (ex is FormatException or IndexOutOfRangeException or NullReferenceException or OverflowException)
        {
            throw new UseCaseException(422, "La revisión cambió o expiró. Revisa los datos antes de confirmar.");
        }
    }
}

public sealed class RegisterCustomer(ICustomerStore storage, ContactNormalizer normalizer, PreviewSigner signer)
    : CustomerRegistry(storage)
{
    private Customer Build(CustomerInput? input)
    {
        if (input is null) throw new UseCaseException(422, "Los datos del cliente son obligatorios.");
        return new CustomerBuilder(normalizer).WithName(input.FullName).WithAddress(input.Address).WithContacts(input.Contacts).Build();
    }

    public override async Task<PreviewResult> Preview(CustomerInput input, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        var customer = Build(input);
        var matches = await Storage.FindMatches(customer, ct);
        return new PreviewResult(customer, matches, matches.Count == 0 ? signer.Issue(customer, actor) : null);
    }

    public override async Task<SavedCustomer> Register(ConfirmRequest input, Actor actor, CancellationToken ct)
    {
        actor.Authorize();
        if (!input.Confirmed) throw new UseCaseException(422, "Confirma los datos antes de registrar al cliente.");
        var customer = Build(input.Customer);
        signer.Validate(input.PreviewToken, customer, actor);
        if ((await Storage.FindMatches(customer, ct)).Count > 0)
            throw new UseCaseException(409, "Ya existe un cliente con ese contacto o con el mismo nombre y dirección. No se creó otro registro.");
        return await Storage.SaveAtomically(customer, actor, ct);
    }
}
