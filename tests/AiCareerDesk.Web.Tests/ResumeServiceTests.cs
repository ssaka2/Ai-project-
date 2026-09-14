using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;
namespace AiCareerDesk.Web.Tests;

public class ResumeServiceTests
{
    [Fact]
    public async Task DraftSnapshotsSurviveSourceEditsAndDeletionAndEnforceOwnership()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlite(connection).Options;
        Guid draftId;
        await using (var db = new ApplicationDbContext(options))
        {
            await db.Database.EnsureCreatedAsync();
            db.Users.AddRange(new IdentityUser { Id = "alice" }, new IdentityUser { Id = "bob" });
            await db.SaveChangesAsync();
            var resumes = new ResumeService(db);
            var jobs = new JobService(db);
            var resumeId = await resumes.CreateAsync("alice", new ResumeInput { Name = "Base", Content = "Original C# experience" });
            var jobId = await jobs.CreateAsync("alice", new JobInput { Title = "Developer", Company = "Example", Description = "Original job" });
            Assert.Null(await resumes.CreateDraftAsync("bob", resumeId, jobId));
            var bobsResume = await resumes.CreateAsync("bob", new ResumeInput { Name = "Bob", Content = "Bob resume" });
            Assert.Null(await resumes.CreateDraftAsync("bob", bobsResume, jobId));
            Assert.Null(await resumes.CreateDraftAsync("alice", bobsResume, jobId));
            draftId = (await resumes.CreateDraftAsync("alice", resumeId, jobId))!.Value;
            Assert.Null(await resumes.GetDraftAsync("bob", draftId));
            Assert.Empty(await resumes.ListDraftsAsync("bob"));
            Assert.False(await resumes.UpdateDraftAsync("bob", draftId, new DraftInput { Content = "Attack" }));
            Assert.False(await resumes.DeleteDraftAsync("bob", draftId));
            Assert.False(await resumes.UpdateAsync("bob", resumeId, new ResumeInput { Name = "Attack", Content = "Attack" }));
            Assert.False(await resumes.DeleteAsync("bob", resumeId));
            Assert.True(await resumes.UpdateDraftAsync("alice", draftId, new DraftInput { Content = "Edited draft" }));
            Assert.Equal("Original C# experience", (await resumes.GetAsync("alice", resumeId))!.Content);
            await resumes.UpdateAsync("alice", resumeId, new ResumeInput { Name = "New", Content = "Changed resume" });
            await jobs.UpdateAsync("alice", jobId, new JobInput { Title = "New", Company = "Example", Description = "Changed job" });
            await resumes.DeleteAsync("alice", resumeId);
            await jobs.DeleteAsync("alice", jobId);
        }
        await using (var db = new ApplicationDbContext(options))
        {
            var resumes = new ResumeService(db);
            var draft = await resumes.GetDraftAsync("alice", draftId);
            Assert.NotNull(draft);
            Assert.Equal("Original C# experience", draft.ResumeSnapshot);
            Assert.Equal("Original job", draft.JobDescriptionSnapshot);
            Assert.Equal("Edited draft", draft.Content);
            Assert.True(await resumes.DeleteDraftAsync("alice", draftId));
            Assert.Null(await resumes.GetDraftAsync("alice", draftId));
        }
    }

    [Fact]
    public async Task StatusHistoryRecordsOnlyChangesAndRequiresOwnership()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using var db = new ApplicationDbContext(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();
        db.Users.Add(new IdentityUser { Id = "alice" });
        await db.SaveChangesAsync();
        var jobs = new JobService(db);
        var input = new JobInput { Title = "Developer", Company = "Example" };
        var id = await jobs.CreateAsync("alice", input);
        Assert.Empty(await jobs.HistoryAsync("alice", id));
        input.Status = ApplicationStatus.Applied;
        await jobs.UpdateAsync("alice", id, input);
        await jobs.UpdateAsync("alice", id, input);
        var entry = Assert.Single(await jobs.HistoryAsync("alice", id));
        Assert.Equal(ApplicationStatus.Saved, entry.FromStatus);
        Assert.Equal(ApplicationStatus.Applied, entry.ToStatus);
        Assert.Empty(await jobs.HistoryAsync("bob", id));
    }
}
