using System.Security.Claims;
using System.Text.Json;
using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Pages.Account;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace AiCareerDesk.Web.Tests;

public class AccountExportTests : IAsyncLifetime
{
    private readonly SqliteConnection connection = new("Data Source=:memory:");
    private ApplicationDbContext db = null!;

    public async Task InitializeAsync()
    {
        await connection.OpenAsync();
        db = new ApplicationDbContext(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();
        db.Users.AddRange(
            new IdentityUser
            {
                Id = "alice", UserName = "alice@example.test", Email = "alice@example.test", EmailConfirmed = true,
                PasswordHash = "alice-password-hash", SecurityStamp = "alice-security-stamp"
            },
            new IdentityUser { Id = "bob", UserName = "bob@example.test", Email = "bob@example.test" });
        await db.SaveChangesAsync();
        await SeedAsync("alice", "Alice");
        await SeedAsync("bob", "Bob");
    }

    public async Task DisposeAsync()
    {
        await db.DisposeAsync();
        await connection.DisposeAsync();
    }

    private async Task SeedAsync(string owner, string marker)
    {
        var jobs = new JobService(db);
        var jobId = await jobs.CreateAsync(owner, new JobInput { Title = $"{marker} Developer", Company = $"{marker} Co" });
        var job = (await jobs.GetAsync(owner, jobId))!;
        Assert.Equal(WriteResult.Saved, await jobs.UpdateAsync(owner, jobId, new JobInput
        {
            Version = job.Version, Title = job.Title, Company = job.Company, Status = ApplicationStatus.Applied
        }));
        var resumes = new ResumeService(db);
        var resumeId = await resumes.CreateAsync(owner, new ResumeInput { Name = $"{marker} Resume", Content = $"{marker} experience" });
        var draftId = (await resumes.CreateDraftAsync(owner, resumeId, jobId))!.Value;
        db.TailoringSuggestions.Add(new TailoringSuggestion
        {
            ResumeDraftId = draftId, Content = $"{marker} suggestion", Provider = "test", Model = "test-model"
        });
        await db.SaveChangesAsync();
    }

    private ExportModel Page(string owner) => new(db)
    {
        PageContext = new PageContext
        {
            HttpContext = new DefaultHttpContext
            {
                User = new ClaimsPrincipal(new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier, owner)], "Test"))
            }
        }
    };

    private static JsonElement Parse(IActionResult result)
    {
        var file = Assert.IsType<FileContentResult>(result);
        Assert.Equal("application/json", file.ContentType);
        Assert.Equal("ai-career-desk-export.json", file.FileDownloadName);
        return JsonDocument.Parse(file.FileContents).RootElement.Clone();
    }

    [Fact]
    public async Task ExportContainsEveryOwnedRecordAndNothingFromOtherAccounts()
    {
        var export = Parse(await Page("alice").OnPostAsync(CancellationToken.None));

        Assert.Equal(1, export.GetProperty("FormatVersion").GetInt32());
        Assert.Equal("alice@example.test", export.GetProperty("Account").GetProperty("Email").GetString());
        Assert.Equal("Alice Developer", Assert.Single(export.GetProperty("Jobs").EnumerateArray()).GetProperty("Title").GetString());
        var history = Assert.Single(export.GetProperty("StatusHistory").EnumerateArray());
        Assert.Equal((int)ApplicationStatus.Applied, history.GetProperty("ToStatus").GetInt32());
        Assert.Equal("Alice Resume", Assert.Single(export.GetProperty("Resumes").EnumerateArray()).GetProperty("Name").GetString());
        Assert.Equal("alice", Assert.Single(export.GetProperty("Drafts").EnumerateArray()).GetProperty("OwnerId").GetString());
        Assert.Equal("Alice suggestion", Assert.Single(export.GetProperty("Suggestions").EnumerateArray()).GetProperty("Content").GetString());
        Assert.DoesNotContain("Bob", export.GetRawText());
        Assert.DoesNotContain("bob@example.test", export.GetRawText());
    }

    [Fact]
    public async Task ExportOmitsIdentitySecrets()
    {
        var export = Parse(await Page("alice").OnGetDownloadAsync(CancellationToken.None));

        var account = export.GetProperty("Account");
        Assert.Equal(
            ["Email", "UserName", "EmailConfirmed", "PhoneNumber", "PhoneNumberConfirmed"],
            account.EnumerateObject().Select(x => x.Name));
        Assert.DoesNotContain("alice-password-hash", export.GetRawText());
        Assert.DoesNotContain("alice-security-stamp", export.GetRawText());
    }

    [Fact]
    public async Task ExportResponseIsNotCacheable()
    {
        var page = Page("alice");
        await page.OnPostAsync(CancellationToken.None);

        var headers = page.HttpContext.Response.Headers;
        Assert.Equal("no-store", headers.CacheControl.ToString());
        Assert.Equal("no-cache", headers.Pragma.ToString());
        Assert.Equal("nosniff", headers.XContentTypeOptions.ToString());
    }

    [Fact]
    public async Task ExportForDeletedAccountReturnsNotFound()
    {
        Assert.IsType<NotFoundResult>(await Page("deleted-user").OnPostAsync(CancellationToken.None));
    }
}
