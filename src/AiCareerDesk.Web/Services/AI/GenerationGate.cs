using System.Threading.RateLimiting;
namespace AiCareerDesk.Web.Services.AI;

// Limits apply to this application instance. Use a shared limiter before scaling out.
public sealed class GenerationGate : IDisposable
{
    private readonly ConcurrencyLimiter concurrency = new(new ConcurrencyLimiterOptions
    {
        PermitLimit = 2, QueueLimit = 0
    });
    private readonly PartitionedRateLimiter<string> users = PartitionedRateLimiter.Create<string, string>(owner =>
        RateLimitPartition.GetFixedWindowLimiter(owner, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 3, Window = TimeSpan.FromMinutes(10), QueueLimit = 0, AutoReplenishment = true
        }));

    public IDisposable Enter(string owner)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        var global = concurrency.AttemptAcquire();
        if (!global.IsAcquired) { global.Dispose(); throw new TailoringException("AI tailoring is busy. Try again shortly."); }
        var user = users.AttemptAcquire(owner);
        if (!user.IsAcquired)
        {
            global.Dispose(); user.Dispose();
            throw new TailoringException("You have reached the generation limit. Try again in ten minutes.");
        }
        return new Lease(global, user);
    }
    private sealed class Lease(RateLimitLease global, RateLimitLease user) : IDisposable
    {
        public void Dispose() { user.Dispose(); global.Dispose(); }
    }
    public void Dispose() { users.Dispose(); concurrency.Dispose(); }
}
