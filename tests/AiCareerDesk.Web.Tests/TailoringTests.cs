using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using AiCareerDesk.Web.Services.AI;
using Microsoft.AspNetCore.Identity;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;
namespace AiCareerDesk.Web.Tests;

public class TestTailoringProvider : IResumeTailoringService
{
    public bool IsConfigured { get; set; } = true;
    public string ProviderName => "Test";
    public int Calls { get; private set; }
    public TailoringRequest? LastRequest { get; private set; }
    public Func<CancellationToken, Task>? BeforeReturn { get; set; }
    public async Task<TailoringResult> GenerateAsync(TailoringRequest request, CancellationToken cancellationToken)
    {
        Calls++;
        LastRequest = request;
        if (BeforeReturn is not null) await BeforeReturn(cancellationToken);
        return new("Suggested C# resume", ["Cloud certification not evidenced"], "fake-model", "fake-response");
    }
}

public class TailoringTests
{
    private sealed class Fixture : IAsyncDisposable
    {
        private readonly SqliteConnection connection = new("Data Source=:memory:");
        public ApplicationDbContext Db { get; private set; } = null!;
        public Guid DraftId { get; private set; }
        public Guid ResumeId { get; private set; }
        public readonly TestTailoringProvider Provider = new();
        public readonly GenerationGate Gate = new();
        public TailoringWorkflow Workflow => new(Db, Provider, Gate);
        public ApplicationDbContext NewContext() => new(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlite(connection).Options);
        public async Task StartAsync()
        {
            await connection.OpenAsync();
            Db = NewContext();
            await Db.Database.EnsureCreatedAsync();
            Db.Users.AddRange(new IdentityUser { Id = "alice" }, new IdentityUser { Id = "bob" });
            await Db.SaveChangesAsync();
            ResumeId = await new ResumeService(Db).CreateAsync("alice", new ResumeInput { Name = "Base", Content = "Original C# experience" });
            var job = await new JobService(Db).CreateAsync("alice", new JobInput { Title = "Developer", Company = "Example", Description = "C# and cloud certification" });
            DraftId = (await new ResumeService(Db).CreateDraftAsync("alice", ResumeId, job))!.Value;
            Db.ChangeTracker.Clear();
        }
        public async ValueTask DisposeAsync() { Gate.Dispose(); await Db.DisposeAsync(); await connection.DisposeAsync(); }
    }

    [Fact]
    public async Task SuggestionsRequireConsentAndOwnershipAndDoNotReplaceCurrentEdits()
    {
        await using var f = new Fixture(); await f.StartAsync();
        Assert.Null(await f.Workflow.GenerateAsync("bob", f.DraftId, true, default));
        await Assert.ThrowsAsync<TailoringException>(() => f.Workflow.GenerateAsync("alice", f.DraftId, false, default));
        Assert.Equal(0, f.Provider.Calls);
        var originalVersion = (await new ResumeService(f.Db).GetDraftAsync("alice", f.DraftId))!.Version;
        f.Provider.BeforeReturn = async _ =>
        {
            await using var other = f.NewContext();
            var service = new ResumeService(other);
            Assert.Equal(WriteResult.Saved, await service.UpdateDraftAsync("alice", f.DraftId,
                new DraftInput { Content = "My concurrent edit", Version = originalVersion }));
        };
        var suggestionId = (await f.Workflow.GenerateAsync("alice", f.DraftId, true, default))!.Value;
        var current = (await new ResumeService(f.Db).GetDraftAsync("alice", f.DraftId))!;
        Assert.Equal("My concurrent edit", current.Content);
        Assert.Equal("Original C# experience", f.Provider.LastRequest!.ResumeSource);
        Assert.Empty(await f.Workflow.ListAsync("bob", f.DraftId));
        var suggestion = Assert.Single(await f.Workflow.ListAsync("alice", f.DraftId));
        Assert.Equal("fake-model", suggestion.Model);
        Assert.Equal("Cloud certification not evidenced", suggestion.SkillGaps);
        Assert.Equal(WriteResult.NotFound, await f.Workflow.ApplyAsync("bob", f.DraftId, suggestionId, current.Version));
        Assert.Equal(WriteResult.Conflict, await f.Workflow.ApplyAsync("alice", f.DraftId, suggestionId, originalVersion));
        Assert.Equal(WriteResult.Saved, await f.Workflow.ApplyAsync("alice", f.DraftId, suggestionId, current.Version));
        Assert.Equal("Suggested C# resume", (await new ResumeService(f.Db).GetDraftAsync("alice", f.DraftId))!.Content);
        Assert.Equal("Original C# experience", (await new ResumeService(f.Db).GetAsync("alice", f.ResumeId))!.Content);
        Assert.Single(await f.Workflow.ListAsync("alice", f.DraftId));
    }

    [Fact]
    public async Task FailureAndCancellationPreserveDraftAndExistingSuggestion()
    {
        await using var f = new Fixture(); await f.StartAsync();
        await f.Workflow.GenerateAsync("alice", f.DraftId, true, default);
        f.Provider.BeforeReturn = _ => throw new TailoringException("Provider unavailable");
        await Assert.ThrowsAsync<TailoringException>(() => f.Workflow.GenerateAsync("alice", f.DraftId, true, default));
        f.Provider.BeforeReturn = _ => throw new OperationCanceledException();
        await Assert.ThrowsAsync<OperationCanceledException>(() => f.Workflow.GenerateAsync("alice", f.DraftId, true, default));
        Assert.Single(await f.Workflow.ListAsync("alice", f.DraftId));
        Assert.Equal("Original C# experience", (await new ResumeService(f.Db).GetDraftAsync("alice", f.DraftId))!.Content);
    }

    [Fact]
    public async Task MissingConfigurationAndEmptyDescriptionDoNotCallProvider()
    {
        await using var f = new Fixture(); await f.StartAsync();
        f.Provider.IsConfigured = false;
        await Assert.ThrowsAsync<TailoringException>(() => f.Workflow.GenerateAsync("alice", f.DraftId, true, default));
        f.Provider.IsConfigured = true;
        var draft = await f.Db.ResumeDrafts.SingleAsync();
        draft.JobDescriptionSnapshot = "";
        await f.Db.SaveChangesAsync();
        await Assert.ThrowsAsync<TailoringException>(() => f.Workflow.GenerateAsync("alice", f.DraftId, true, default));
        Assert.Equal(0, f.Provider.Calls);
    }

    [Fact]
    public async Task DeletedDraftDuringGenerationDoesNotReappear()
    {
        await using var f = new Fixture(); await f.StartAsync();
        f.Provider.BeforeReturn = async _ =>
        {
            await using var other = f.NewContext();
            await new ResumeService(other).DeleteDraftAsync("alice", f.DraftId,
                (await new ResumeService(other).GetDraftAsync("alice", f.DraftId))!.Version);
        };
        Assert.Null(await f.Workflow.GenerateAsync("alice", f.DraftId, true, default));
        Assert.Empty(await f.Db.TailoringSuggestions.ToListAsync());
    }

    [Fact]
    public async Task StaleManualDraftEditIsRejectedWithoutDiscardingSavedText()
    {
        await using var f = new Fixture(); await f.StartAsync();
        var service = new ResumeService(f.Db);
        var version = (await service.GetDraftAsync("alice", f.DraftId))!.Version;
        Assert.Equal(WriteResult.Saved, await service.UpdateDraftAsync("alice", f.DraftId,
            new DraftInput { Content = "First edit", Version = version }));
        f.Db.ChangeTracker.Clear();
        Assert.Equal(WriteResult.Conflict, await service.UpdateDraftAsync("alice", f.DraftId,
            new DraftInput { Content = "Stale edit", Version = version }));
        Assert.Equal("First edit", (await service.GetDraftAsync("alice", f.DraftId))!.Content);
    }

    [Fact]
    public void GateLimitsRequestsPerAccountAndConcurrentGenerations()
    {
        using var gate = new GenerationGate();
        using (gate.Enter("alice")) { }
        using (gate.Enter("alice")) { }
        using (gate.Enter("alice")) { }
        Assert.Throws<TailoringException>(() => gate.Enter("alice"));
        using var bob = gate.Enter("bob");
        using var carol = gate.Enter("carol");
        Assert.Throws<TailoringException>(() => gate.Enter("dave"));
    }

    [Fact]
    public async Task DatabaseConcurrencyTokenRejectsTwoAlreadyTrackedWriters()
    {
        await using var f = new Fixture(); await f.StartAsync();
        await using var first = f.NewContext();
        await using var second = f.NewContext();
        var a = await first.ResumeDrafts.SingleAsync(x => x.Id == f.DraftId);
        var b = await second.ResumeDrafts.SingleAsync(x => x.Id == f.DraftId);
        Assert.Equal(a.Version, b.Version);
        var oldVersion = a.Version;
        Assert.Equal(WriteResult.Saved, await new ResumeService(first).UpdateDraftAsync("alice", f.DraftId,
            new DraftInput { Version = oldVersion, Content = "First writer" }));
        Assert.Equal(WriteResult.Conflict, await new ResumeService(second).UpdateDraftAsync("alice", f.DraftId,
            new DraftInput { Version = oldVersion, Content = "Second writer" }));
        Assert.Equal("First writer", (await new ResumeService(f.Db).GetDraftAsync("alice", f.DraftId))!.Content);
    }

    [Fact]
    public async Task DatabaseConflictsPreserveJobsResumesAndAtomicStatusHistory()
    {
        await using var f = new Fixture(); await f.StartAsync();
        await using var first = f.NewContext();
        await using var second = f.NewContext();
        var jobA = await first.Jobs.SingleAsync();
        var jobB = await second.Jobs.SingleAsync();
        var resumeA = await first.Resumes.SingleAsync();
        var resumeB = await second.Resumes.SingleAsync();
        Assert.Equal(WriteResult.Saved, await new JobService(first).UpdateAsync("alice", jobA.Id,
            new JobInput { Title = "First", Company = "Example", Status = ApplicationStatus.Applied, Version = jobA.Version }));
        Assert.Equal(WriteResult.Conflict, await new JobService(second).UpdateAsync("alice", jobB.Id,
            new JobInput { Title = "Stale", Company = "Example", Status = ApplicationStatus.Offer, Version = jobB.Version }));
        Assert.Equal(WriteResult.Saved, await new ResumeService(first).UpdateAsync("alice", resumeA.Id,
            new ResumeInput { Name = "Base", Content = "First resume", Version = resumeA.Version }));
        Assert.Equal(WriteResult.Conflict, await new ResumeService(second).UpdateAsync("alice", resumeB.Id,
            new ResumeInput { Name = "Base", Content = "Stale resume", Version = resumeB.Version }));
        // A subsequent save must not leak the rejected writer's status-history entry.
        await second.SaveChangesAsync();
        Assert.Equal("First", (await new JobService(f.Db).GetAsync("alice", jobA.Id))!.Title);
        Assert.Equal(ApplicationStatus.Applied, Assert.Single(await new JobService(f.Db).HistoryAsync("alice", jobA.Id)).ToStatus);
        Assert.Equal("First resume", (await new ResumeService(f.Db).GetAsync("alice", resumeA.Id))!.Content);
    }

    [Fact]
    public async Task ConcurrentDeletesRejectChangesCommittedAfterRecordsWereLoaded()
    {
        await using var f = new Fixture(); await f.StartAsync();
        await using var deleting = f.NewContext();
        await using var editing = f.NewContext();
        var job = await deleting.Jobs.SingleAsync();
        var resume = await deleting.Resumes.SingleAsync();
        var draft = await deleting.ResumeDrafts.SingleAsync();
        await new JobService(editing).UpdateAsync("alice", job.Id,
            new JobInput { Title = "Keep job", Company = "Example", Version = job.Version });
        await new ResumeService(editing).UpdateAsync("alice", resume.Id,
            new ResumeInput { Name = "Keep resume", Content = "Keep content", Version = resume.Version });
        await new ResumeService(editing).UpdateDraftAsync("alice", draft.Id,
            new DraftInput { Content = "Keep draft", Version = draft.Version });
        Assert.Equal(WriteResult.Conflict, await new JobService(deleting).DeleteAsync("alice", job.Id, job.Version));
        Assert.Equal(WriteResult.Conflict, await new ResumeService(deleting).DeleteAsync("alice", resume.Id, resume.Version));
        Assert.Equal(WriteResult.Conflict, await new ResumeService(deleting).DeleteDraftAsync("alice", draft.Id, draft.Version));
        await deleting.SaveChangesAsync();
        Assert.NotNull(await new JobService(f.Db).GetAsync("alice", job.Id));
        Assert.NotNull(await new ResumeService(f.Db).GetAsync("alice", resume.Id));
        Assert.NotNull(await new ResumeService(f.Db).GetDraftAsync("alice", draft.Id));
    }
}
