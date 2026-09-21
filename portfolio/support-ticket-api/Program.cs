using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
// Local demonstration: explicit loopback default, no public hosting or login.
if (string.IsNullOrWhiteSpace(builder.Configuration["urls"]))
    builder.WebHost.UseUrls("http://127.0.0.1:5081");
builder.Services.AddProblemDetails();
builder.Services.AddSingleton(new TicketStore(
    builder.Configuration["TICKET_DATA_PATH"] ?? Path.Combine("data", "tickets.json")));
var app = builder.Build();
app.UseExceptionHandler();

app.MapGet("/health", () => Results.Ok(new { status = "ready" }));
app.MapGet("/", () => Results.Ok(new
{
    name = "Support Ticket API", version = "1.0",
    endpoints = new[] { "GET /tickets", "GET /tickets/{id}", "POST /tickets", "PATCH /tickets/{id}/status" }
}));
app.MapGet("/tickets", (string? status, int? offset, int? limit, TicketStore store) =>
{
    var skip = offset ?? 0;
    var take = limit ?? 20;
    if (skip < 0 || take is < 1 or > 100 || (status is not null && !TicketStore.ValidStatus(status)))
        return Results.BadRequest(new { error = "Use a valid status, offset >= 0, and limit between 1 and 100." });
    var tickets = store.List(status);
    return Results.Ok(new { total = tickets.Length, offset = skip, limit = take, items = tickets.Skip(skip).Take(take) });
});
app.MapGet("/tickets/{id:guid}", (Guid id, TicketStore store) =>
    store.Find(id) is { } ticket ? Results.Ok(ticket) : Results.NotFound());
app.MapPost("/tickets", (CreateTicket request, TicketStore store) =>
{
    if (string.IsNullOrWhiteSpace(request.Title) || request.Title.Trim().Length > 120 ||
        request.Description is null || request.Description.Length > 2000)
        return Results.BadRequest(new { error = "Title is required (max 120 characters); description is required (max 2000)." });
    var ticket = store.Create(request.Title.Trim(), request.Description.Trim());
    return Results.Created($"/tickets/{ticket.Id}", ticket);
});
app.MapPatch("/tickets/{id:guid}/status", (Guid id, ChangeStatus request, TicketStore store) =>
{
    if (!TicketStore.ValidStatus(request.Status) || request.ExpectedVersion < 1)
        return Results.BadRequest(new { error = "Valid status and positive expectedVersion are required." });
    var result = store.ChangeStatus(id, request.Status!, request.ExpectedVersion);
    return result.Outcome switch
    {
        "missing" => Results.NotFound(),
        "conflict" => Results.Conflict(new { error = "Ticket changed. Reload before saving.", current = result.Ticket }),
        "invalid" => Results.BadRequest(new { error = "Reopen a closed ticket before marking it InProgress." }),
        _ => Results.Ok(result.Ticket)
    };
});
app.Run();

record CreateTicket(string? Title, string? Description);
record ChangeStatus(string? Status, int ExpectedVersion);
record StatusEvent(string From, string To, DateTimeOffset At);
record Ticket(Guid Id, string Title, string Description, string Status, int Version,
    DateTimeOffset CreatedAt, DateTimeOffset UpdatedAt, StatusEvent[] History);

sealed class TicketStore
{
    private readonly object gate = new();
    private readonly string path;
    private Dictionary<Guid, Ticket> tickets;
    public TicketStore(string filename)
    {
        path = Path.GetFullPath(filename);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var stored = File.Exists(path)
            ? JsonSerializer.Deserialize<Ticket[]>(File.ReadAllText(path)) ?? throw new InvalidDataException("Invalid ticket snapshot")
            : [];
        if (stored.Any(t => !ValidStatus(t.Status) || t.Version < 1 || t.History is null))
            throw new InvalidDataException("Invalid ticket snapshot");
        tickets = stored.ToDictionary(t => t.Id);
    }
    public static bool ValidStatus(string? status) => status is "Open" or "InProgress" or "Closed";
    public Ticket[] List(string? status)
    {
        lock (gate)
            return tickets.Values.Where(t => status is null || t.Status == status)
                .OrderByDescending(t => t.CreatedAt).ThenBy(t => t.Id).ToArray();
    }
    public Ticket? Find(Guid id)
    {
        lock (gate) return tickets.GetValueOrDefault(id);
    }
    public Ticket Create(string title, string description)
    {
        lock (gate)
        {
            var now = DateTimeOffset.UtcNow;
            var ticket = new Ticket(Guid.NewGuid(), title, description, "Open", 1, now, now, []);
            var next = new Dictionary<Guid, Ticket>(tickets) { [ticket.Id] = ticket };
            Save(next);
            return ticket;
        }
    }
    public (string Outcome, Ticket? Ticket) ChangeStatus(Guid id, string status, int expectedVersion)
    {
        lock (gate)
        {
            if (!tickets.TryGetValue(id, out var ticket)) return ("missing", null);
            if (ticket.Version != expectedVersion) return ("conflict", ticket);
            if (ticket.Status == status) return ("ok", ticket);
            if (ticket.Status == "Closed" && status == "InProgress") return ("invalid", ticket);
            var now = DateTimeOffset.UtcNow;
            var updated = ticket with
            {
                Status = status, Version = checked(ticket.Version + 1), UpdatedAt = now,
                History = [.. ticket.History, new StatusEvent(ticket.Status, status, now)]
            };
            var next = new Dictionary<Guid, Ticket>(tickets) { [id] = updated };
            Save(next);
            return ("ok", updated);
        }
    }
    private void Save(Dictionary<Guid, Ticket> next)
    {
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write))
            {
                JsonSerializer.Serialize(stream, next.Values.ToArray());
                stream.Flush(flushToDisk: true);
            }
            File.Move(temporary, path, overwrite: true);
            tickets = next;
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }
}
