using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 16_384);
builder.Services.AddSingleton(new BookingStore(
    Environment.GetEnvironmentVariable("BOOKING_DATA") ?? Path.Combine(builder.Environment.ContentRootPath, "data", "bookings.json")));
var app = builder.Build();
app.UseDefaultFiles();
app.UseStaticFiles();
app.MapGet("/health", () => Results.Ok(new { status = "ready" }));
app.MapGet("/api/services", () => Results.Ok(BookingStore.Services));
app.MapGet("/api/bookings", (BookingStore store) => Results.Ok(store.List()));
app.MapGet("/api/bookings/{id:guid}", (Guid id, BookingStore store) =>
    store.List().FirstOrDefault(x => x.Id == id) is { } item ? Results.Ok(item) : Results.NotFound());
app.MapPost("/api/bookings", (BookingRequest request, BookingStore store) =>
{
    var error = BookingStore.Validate(request);
    if (error is not null) return Results.Problem(error, statusCode: 400);
    try
    {
        var booking = store.Create(request);
        return booking is null
            ? Results.Problem("This service already has a booking during that time.", statusCode: 409)
            : Results.Created($"/api/bookings/{booking.Id}", booking);
    }
    catch (IOException) { return Results.Problem("Could not persist the booking.", statusCode: 503); }
    catch (UnauthorizedAccessException) { return Results.Problem("Booking storage is not writable.", statusCode: 503); }
});
app.MapDelete("/api/bookings/{id:guid}", (Guid id, BookingStore store) =>
{
    try { return store.Cancel(id) ? Results.NoContent() : Results.NotFound(); }
    catch (IOException) { return Results.Problem("Could not persist cancellation.", statusCode: 503); }
    catch (UnauthorizedAccessException) { return Results.Problem("Booking storage is not writable.", statusCode: 503); }
});
app.Run();

record BookingRequest(string? Service, string? Customer, DateTimeOffset Start, int Minutes);
record Booking(Guid Id, string Service, string Customer, DateTimeOffset Start, int Minutes);
sealed class BookingStore
{
    public static readonly string[] Services = ["consultation", "code-review", "career-coaching"];
    private readonly object gate = new();
    private readonly string path;
    private List<Booking> bookings;

    public BookingStore(string path)
    {
        this.path = Path.GetFullPath(path);
        Directory.CreateDirectory(Path.GetDirectoryName(this.path)!);
        bookings = File.Exists(this.path)
            ? JsonSerializer.Deserialize<List<Booking>>(File.ReadAllText(this.path))
                ?? throw new InvalidDataException("Invalid booking store.")
            : [];
        // Corrupt persisted data must fail startup instead of being silently discarded.
        if (bookings.Any(b => b.Id == Guid.Empty || !Services.Contains(b.Service) ||
            string.IsNullOrWhiteSpace(b.Customer) || b.Customer.Length > 100 ||
            b.Minutes < 15 || b.Minutes > 240 || b.Start.Offset != TimeSpan.Zero ||
            b.Start > DateTimeOffset.MaxValue.AddMinutes(-240)) ||
            bookings.Select(b => b.Id).Distinct().Count() != bookings.Count)
            throw new InvalidDataException("Invalid booking records.");
    }

    public static string? Validate(BookingRequest r)
    {
        if (r.Service is null || !Services.Contains(r.Service)) return "Choose a listed service.";
        if (string.IsNullOrWhiteSpace(r.Customer) || r.Customer.Length > 100) return "Customer must be 1–100 characters.";
        if (r.Minutes < 15 || r.Minutes > 240) return "Duration must be 15–240 minutes.";
        var now = DateTimeOffset.UtcNow;
        if (r.Start.Offset != TimeSpan.Zero || r.Start <= now || r.Start > now.AddDays(365))
            return "Start must be in UTC, in the future, and within 365 days.";
        return null;
    }

    public Booking[] List() { lock (gate) return bookings.OrderBy(b => b.Start).ToArray(); }

    public Booking? Create(BookingRequest r)
    {
        lock (gate)
        {
            var end = r.Start.AddMinutes(r.Minutes);
            if (bookings.Any(b => b.Service == r.Service && b.Start < end && r.Start < b.Start.AddMinutes(b.Minutes))) return null;
            var booking = new Booking(Guid.NewGuid(), r.Service!, r.Customer!.Trim(), r.Start, r.Minutes);
            List<Booking> next = [.. bookings, booking];
            Save(next); // Memory changes only after durable file replacement succeeds.
            bookings = next;
            return booking;
        }
    }

    public bool Cancel(Guid id)
    {
        lock (gate)
        {
            if (!bookings.Any(b => b.Id == id)) return false;
            var next = bookings.Where(b => b.Id != id).ToList();
            Save(next);
            bookings = next;
            return true;
        }
    }

    private void Save(List<Booking> next)
    {
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                JsonSerializer.Serialize(stream, next);
                stream.Flush(flushToDisk: true);
            }
            File.Move(temporary, path, overwrite: true);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
}
