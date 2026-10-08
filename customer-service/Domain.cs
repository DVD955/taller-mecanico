using System.Globalization;
using System.Net.Mail;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace Taller.Customers;

public sealed class UseCaseException(int status, string message) : Exception(message)
{
    public int Status { get; } = status;
}

public sealed record Actor(int Id, string Username, string Role, string Status)
{
    public void Authorize()
    {
        if (Status != "ACTIVO" || Role is not ("ADMINISTRADOR" or "RECEPCIONISTA"))
            throw new UseCaseException(403, "Solo administradores y recepcionistas activos pueden gestionar clientes.");
    }
}

public sealed record Address(string Street, string Number, string Neighborhood, string Municipality, string State);
public sealed record Contacts(string? Email, string? Mobile, string? Alternative);
public sealed record CustomerInput(string FullName, Address Address, Contacts Contacts);
public sealed record Customer(long Id, string FullName, Address Address, Contacts Contacts, string Status, string Fingerprint, int Version = 1);
public sealed record AuditEntry(long Id, int ActorId, string ActorUsername, long CustomerId, DateTimeOffset OccurredAt, string Action = "UC-CV-01 RegistrarCliente");
public sealed record SavedCustomer(Customer Customer, AuditEntry AuditEntry);

public static class TextRules
{
    public static string Required(string? value, string label, int max, int min = 1)
    {
        if (value is null || value.Any(char.IsControl))
            throw new UseCaseException(422, $"{label}: valor obligatorio o formato no válido.");
        var clean = Regex.Replace(value.Trim().Normalize(), @"\s+", " ");
        if (clean.Length < min || clean.Length > max)
            throw new UseCaseException(422, $"{label}: utiliza entre {min} y {max} caracteres.");
        return clean;
    }

    public static string Identity(string value)
    {
        var decomposed = value.Normalize(NormalizationForm.FormD);
        return new string(decomposed.Where(c => CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
            .ToArray()).ToUpperInvariant();
    }
}

// Strategy: cada tipo de contacto valida y produce su representación canónica.
public interface IContactStrategy
{
    string? NormalizeAndValidate(string? value);
}

public sealed class EmailStrategy : IContactStrategy
{
    public string? NormalizeAndValidate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        var clean = value.Trim().ToLowerInvariant();
        if (clean.Length > 254 || !MailAddress.TryCreate(clean, out var address) || address.Address != clean
            || !Regex.IsMatch(clean, @"^[^@\s]+@[^@\s]+\.[^@\s]+$"))
            throw new UseCaseException(422, "Correo: formato no válido.");
        return clean;
    }
}

public sealed class PhoneStrategy(string label) : IContactStrategy
{
    public string? NormalizeAndValidate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        var clean = value.Trim();
        if (clean.Length > 40 || !Regex.IsMatch(clean, @"^\+?[0-9() .-]+$"))
            throw new UseCaseException(422, $"{label}: usa un teléfono de 10 dígitos o formato internacional +país.");
        var digits = Regex.Replace(clean, @"[() .-]", "");
        if (!digits.StartsWith('+') && Regex.IsMatch(digits, @"^[0-9]{10}$")) digits = "+52" + digits;
        if (!Regex.IsMatch(digits, @"^\+[1-9][0-9]{7,14}$"))
            throw new UseCaseException(422, $"{label}: teléfono no válido.");
        return digits;
    }
}

public sealed class ContactNormalizer(IContactStrategy email, IContactStrategy mobile, IContactStrategy alternative)
{
    public Contacts Normalize(Contacts? input)
    {
        if (input is null) throw new UseCaseException(422, "Captura al menos un contacto.");
        var result = new Contacts(email.NormalizeAndValidate(input.Email), mobile.NormalizeAndValidate(input.Mobile),
            alternative.NormalizeAndValidate(input.Alternative));
        if (result.Email is null && result.Mobile is null && result.Alternative is null)
            throw new UseCaseException(422, "Captura al menos un correo, celular o teléfono alternativo.");
        return result;
    }
}

// Builder: solo construye un cliente completo, validado y activo.
public sealed class CustomerBuilder(ContactNormalizer normalizer)
{
    private string? name;
    private Address? address;
    private Contacts? contacts;

    public CustomerBuilder WithName(string? value)
    {
        name = TextRules.Required(value, "Nombre completo", 120, 3);
        if (!Regex.IsMatch(name, @"^[\p{L}\p{M} .'-]+$"))
            throw new UseCaseException(422, "Nombre completo: utiliza letras, espacios, apóstrofos o guiones.");
        return this;
    }

    public CustomerBuilder WithAddress(Address? value)
    {
        if (value is null) throw new UseCaseException(422, "La dirección es obligatoria.");
        address = new Address(TextRules.Required(value.Street, "Calle", 150), TextRules.Required(value.Number, "Número", 20),
            TextRules.Required(value.Neighborhood, "Colonia", 100), TextRules.Required(value.Municipality, "Municipio", 100),
            TextRules.Required(value.State, "Estado", 100));
        return this;
    }

    public CustomerBuilder WithContacts(Contacts? value)
    {
        contacts = normalizer.Normalize(value);
        return this;
    }

    public Customer Build()
    {
        if (name is null || address is null || contacts is null)
            throw new UseCaseException(422, "El cliente requiere nombre, dirección completa y contacto.");
        var key = System.Text.Json.JsonSerializer.Serialize(new[] {name, address.Street, address.Number,
            address.Neighborhood, address.Municipality, address.State}.Select(TextRules.Identity));
        var fingerprint = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(key))).ToLowerInvariant();
        return new Customer(0, name, address, contacts, "ACTIVO", fingerprint);
    }
}
