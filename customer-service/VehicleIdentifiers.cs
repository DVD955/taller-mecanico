using System.Text.Json;
using System.Text.RegularExpressions;

namespace Taller.Customers;

// Un mismo catálogo de formatos se comparte con el formulario, sin reglas genéricas de 5–10 caracteres.
public static class VehicleIdentifiers
{
    private sealed record PlateFormat(string Id, string Pattern, string Example, string Canonical);
    private sealed record Specification(string VinPattern, int[] VinWeights, string[] CheckDigitPrefixes,
        string PlateLetters, Dictionary<string, string> Messages, PlateFormat[] PlateFormats);
    private static readonly Specification Rules = JsonSerializer.Deserialize<Specification>(
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "vehicle-identifiers.json")),
        new JsonSerializerOptions {PropertyNameCaseInsensitive = true})
        ?? throw new InvalidOperationException("No se pudo cargar el catálogo de identificación de automóviles.");
    private static readonly Regex[] PlatePatterns = Rules.PlateFormats.Select(format =>
        new Regex("\\A" + format.Pattern.Replace("{L}", Rules.PlateLetters) + "\\z", RegexOptions.CultureInvariant)).ToArray();

    public static string Vin(string? input)
    {
        var text = TextRules.Required(input, "VIN", 17, 17);
        if (!Regex.IsMatch(input?.Trim() ?? "", @"\A[a-zA-Z0-9]{17}\z"))
            throw new UseCaseException(422, Rules.Messages["vin"]);
        var vin = text.ToUpperInvariant();
        if (!Regex.IsMatch(vin, Rules.VinPattern, RegexOptions.CultureInvariant))
            throw new UseCaseException(422, Rules.Messages["vin"]);
        if (vin.All(character => character == vin[0]))
            throw new UseCaseException(422, Rules.Messages["repeatedVin"]);
        if (Rules.CheckDigitPrefixes.Contains(vin[..1]))
        {
            var sum = vin.Select((character, index) => Value(character) * Rules.VinWeights[index]).Sum();
            var digit = sum % 11 == 10 ? 'X' : (char)('0' + sum % 11);
            if (vin[8] != digit) throw new UseCaseException(422, Rules.Messages["checkDigit"]);
        }
        return vin;
    }

    public static string MexicanPlate(string? input)
    {
        var plate = TextRules.Required(input, "Placa", 20).ToUpperInvariant();
        if (!Regex.IsMatch(input?.Trim() ?? "", @"\A[a-zA-Z0-9 -]+\z")
            || !PlatePatterns.Any(pattern => pattern.IsMatch(plate)))
            throw new UseCaseException(422, Rules.Messages["plate"]);
        if (!plate.Any(character => character is >= '1' and <= '9'))
            throw new UseCaseException(422, Rules.Messages["zeroPlate"]);
        return Regex.Replace(plate, "[ -]", "");
    }

    public static IReadOnlyList<(string Example, string Canonical)> PlateExamples() =>
        Rules.PlateFormats.Select(format => (format.Example, format.Canonical)).ToArray();

    private static int Value(char character) => character switch
    {
        >= '0' and <= '9' => character - '0',
        'A' or 'J' => 1,
        'B' or 'K' or 'S' => 2,
        'C' or 'L' or 'T' => 3,
        'D' or 'M' or 'U' => 4,
        'E' or 'N' or 'V' => 5,
        'F' or 'W' => 6,
        'G' or 'P' or 'X' => 7,
        'H' or 'Y' => 8,
        'R' or 'Z' => 9,
        _ => throw new InvalidOperationException("Carácter de VIN no validado."),
    };
}
