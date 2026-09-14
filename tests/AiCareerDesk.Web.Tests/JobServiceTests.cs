using System.ComponentModel.DataAnnotations;
using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace AiCareerDesk.Web.Tests;

public class JobServiceTests
{
    [Fact]
    public async Task JobsPersistAcrossContextsAndOtherOwnersCannotReadOrMutateThem()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlite(connection).Options;
        Guid id;
        await using (var db = new ApplicationDbContext(options))
        {
            await db.Database.EnsureCreatedAsync();
            db.Users.AddRange(
                new IdentityUser { Id = "alice", UserName = "alice" },
                new IdentityUser { Id = "bob", UserName = "bob" });
            await db.SaveChangesAsync();
            id = await new JobService(db).CreateAsync("alice", new JobInput
            {
                Title = ".NET Developer", Company = "Example",
                ApplicationUrl = "https://example.com/jobs/1"
            });
        }
        await using (var db = new ApplicationDbContext(options))
        {
            var service = new JobService(db);
            Assert.Single(await service.ListAsync("alice"));
            Assert.Empty(await service.ListAsync("bob"));
            Assert.Null(await service.GetAsync("bob", id));
            Assert.Equal(WriteResult.NotFound, await service.UpdateAsync("bob", id,
                new JobInput { Title = "Changed", Company = "Other" }));
            Assert.False(await service.DeleteAsync("bob", id));
            Assert.Equal(".NET Developer", (await service.GetAsync("alice", id))!.Title);
            Assert.Equal(WriteResult.Saved, await service.UpdateAsync("alice", id, new JobInput
            {
                Version = (await service.GetAsync("alice", id))!.Version,
                Title = ".NET Developer", Company = "Example", Status = ApplicationStatus.Applied
            }));
        }
        await using (var db = new ApplicationDbContext(options))
        {
            var service = new JobService(db);
            Assert.Single(await service.ListAsync("alice", ApplicationStatus.Applied));
            Assert.Empty(await service.ListAsync("alice", ApplicationStatus.Saved));
            Assert.True(await service.DeleteAsync("alice", id));
            Assert.Empty(await service.ListAsync("alice"));
        }
    }

    [Theory]
    [InlineData("javascript:alert(1)")]
    [InlineData("file:///etc/passwd")]
    [InlineData("/relative-url")]
    public void UnsafeOrRelativeApplicationUrlsAreRejected(string url)
    {
        var input = new JobInput { Title = "Developer", Company = "Example", ApplicationUrl = url };
        var errors = new List<ValidationResult>();
        Assert.False(Validator.TryValidateObject(input, new ValidationContext(input), errors, true));
        Assert.Contains(errors, error => error.MemberNames.Contains(nameof(JobInput.ApplicationUrl)));
    }
}
