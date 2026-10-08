using System.Net.Http.Headers;
using Microsoft.AspNetCore.Mvc;
using MySqlConnector;
using Taller.Customers;

if (args.Contains("--self-test"))
{
    await SelfTests.Run();
    return;
}
if (args.Contains("--integration-test"))
{
    await SelfTests.Integration();
    return;
}

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://127.0.0.1:8003");
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 16_384);
builder.Services.AddHttpClient("auth", client =>
{
    client.BaseAddress = new Uri(Environment.GetEnvironmentVariable("AUTH_API_URL") ?? "http://127.0.0.1:8002");
    client.Timeout = TimeSpan.FromSeconds(5);
});
builder.Services.AddSingleton(new ContactNormalizer(new EmailStrategy(), new PhoneStrategy("Celular"), new PhoneStrategy("Alternativo")));
builder.Services.AddSingleton<PreviewSigner>();
builder.Services.AddSingleton(new MySqlCustomerStore(DatabaseConfig.ConnectionString()));
builder.Services.AddSingleton<ICustomerStore>(services => services.GetRequiredService<MySqlCustomerStore>());
builder.Services.AddSingleton<ICustomerManagementStore>(services => services.GetRequiredService<MySqlCustomerStore>());
builder.Services.AddTransient<CustomerRegistry, RegisterCustomer>();
builder.Services.AddTransient<CustomerManagement, ManageCustomers>();
var app = builder.Build();
await app.Services.GetRequiredService<MySqlCustomerStore>().Initialize(CancellationToken.None);

app.Use(async (context, next) =>
{
    try { await next(context); }
    catch (UseCaseException ex) { await Reply(context, ex.Status, ex.Message); }
    catch (BadHttpRequestException) { await Reply(context, 422, "El cuerpo de la solicitud no tiene un formato válido."); }
    catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
    {
        if (!context.RequestAborted.IsCancellationRequested)
            await Reply(context, 503, "No se pudo validar la sesión. Intenta nuevamente.");
    }
    catch (MySqlException ex)
    {
        app.Logger.LogError("MySQL: código {Code}", ex.Number);
        await Reply(context, 503, "No se pudo completar la operación del cliente. Actualiza el listado antes de reintentar.");
    }
});

app.MapGet("/health", () => Results.Ok(new {status = "ok", module = "UC-CV-01/02/03"}));
app.MapGet("/customers", async (int? page, int? pageSize, string? search, HttpContext context, IHttpClientFactory factory,
    CustomerManagement management, CancellationToken ct) =>
    Results.Ok(await management.List(await Authenticate(context, factory, ct), page ?? 1, pageSize ?? 10, search ?? "", ct)));
app.MapGet("/customers/{id:long}", async (long id, HttpContext context, IHttpClientFactory factory,
    CustomerManagement management, CancellationToken ct) =>
    Results.Ok(await management.Get(id, await Authenticate(context, factory, ct), ct)));
app.MapPost("/customers/{id:long}/preview", async (long id, UpdateDraft input, HttpContext context, IHttpClientFactory factory,
    CustomerManagement management, CancellationToken ct) =>
    Results.Ok(await management.PreviewUpdate(id, input, await Authenticate(context, factory, ct), ct)));
app.MapPut("/customers/{id:long}", async (long id, UpdateRequest input, HttpContext context, IHttpClientFactory factory,
    CustomerManagement management, CancellationToken ct) =>
    Results.Ok(await management.Update(id, input, await Authenticate(context, factory, ct), ct)));
app.MapDelete("/customers/{id:long}", async (long id, [FromBody] DeleteRequest input, HttpContext context, IHttpClientFactory factory,
    CustomerManagement management, CancellationToken ct) =>
    Results.Ok(await management.Delete(id, input, await Authenticate(context, factory, ct), ct)));
app.MapPost("/customers/preview", async (CustomerInput input, HttpContext context, IHttpClientFactory factory,
    CustomerRegistry registry, CancellationToken ct) =>
    Results.Ok(await registry.Preview(input, await Authenticate(context, factory, ct), ct)));
app.MapPost("/customers", async (ConfirmRequest input, HttpContext context, IHttpClientFactory factory,
    CustomerRegistry registry, CancellationToken ct) =>
{
    var result = await registry.Register(input, await Authenticate(context, factory, ct), ct);
    return Results.Json(result, statusCode: 201);
});
await app.RunAsync();

static async Task Reply(HttpContext context, int status, string detail)
{
    context.Response.StatusCode = status;
    await context.Response.WriteAsJsonAsync(new {detail});
}

static async Task<Actor> Authenticate(HttpContext context, IHttpClientFactory factory, CancellationToken ct)
{
    if (!AuthenticationHeaderValue.TryParse(context.Request.Headers.Authorization, out var authorization)
        || authorization.Scheme != "Bearer" || string.IsNullOrWhiteSpace(authorization.Parameter))
        throw new UseCaseException(401, "Inicia sesión para gestionar clientes.");
    using var request = new HttpRequestMessage(HttpMethod.Get, "/api/auth/me");
    request.Headers.Authorization = authorization;
    using var response = await factory.CreateClient("auth").SendAsync(request, ct);
    if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
        throw new UseCaseException(401, "Tu sesión expiró o fue cerrada. Inicia sesión nuevamente.");
    if (!response.IsSuccessStatusCode) throw new UseCaseException(503, "El servicio de sesión no está disponible.");
    var user = await response.Content.ReadFromJsonAsync<AuthUser>(cancellationToken: ct)
        ?? throw new UseCaseException(401, "Sesión no válida.");
    var actor = new Actor(user.Id, user.Username, user.Role, user.Status);
    actor.Authorize();
    return actor;
}

internal sealed record AuthUser(int Id, string Username, string Role, string Status);

internal static class DatabaseConfig
{
    public static string ConnectionString()
    {
        var configured = Environment.GetEnvironmentVariable("CUSTOMERS_MYSQL");
        if (!string.IsNullOrWhiteSpace(configured)) return configured;
        var envPath = Path.GetFullPath(Environment.GetEnvironmentVariable("BACKEND_ENV") ?? "../backend/.env");
        var line = File.ReadLines(envPath).First(x => x.TrimStart().StartsWith("DATABASE_URL="));
        var uri = new Uri(line[(line.IndexOf('=') + 1)..].Trim().Trim('"', '\''));
        var credentials = uri.UserInfo.Split(':', 2);
        var settings = new MySqlConnectionStringBuilder
        {
            Server = uri.Host, Port = uri.Port > 0 ? (uint)uri.Port : 3306,
            UserID = Uri.UnescapeDataString(credentials[0]), Password = Uri.UnescapeDataString(credentials[1]),
            Database = Uri.UnescapeDataString(uri.AbsolutePath.TrimStart('/')),
            ConnectionTimeout = 5, DefaultCommandTimeout = 10, DateTimeKind = MySqlDateTimeKind.Utc
        };
        return settings.ConnectionString;
    }
}
