using System.Net;
using System.Text.RegularExpressions;
using AiCareerDesk.Web.Data;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Xunit;
namespace AiCareerDesk.Web.Tests;

public sealed class SqlServerFactAttribute : FactAttribute
{
    public SqlServerFactAttribute()
    {
        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("TEST_SQL_CONNECTION")))
            Skip = "Set TEST_SQL_CONNECTION to a disposable SQL Server database to run this test.";
    }
}

public class SqlServerWorkflowTests
{
    private static WebApplicationFactory<Program> Factory() =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Testing");
            builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["ConnectionStrings:DefaultConnection"] = Environment.GetEnvironmentVariable("TEST_SQL_CONNECTION")
                }));
        });

    private static HttpClient Client(WebApplicationFactory<Program> factory) =>
        factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false
        });

    private static async Task<HttpResponseMessage> Post(HttpClient client, string path, Dictionary<string, string> fields)
    {
        var page = await client.GetAsync(path);
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var html = await page.Content.ReadAsStringAsync();
        var input = Regex.Match(html, "<input[^>]*name=\"__RequestVerificationToken\"[^>]*>");
        Assert.True(input.Success, "Expected a real antiforgery form token.");
        var value = Regex.Match(input.Value, "value=\"([^\"]+)\"").Groups[1].Value;
        fields["__RequestVerificationToken"] = WebUtility.HtmlDecode(value);
        return await client.PostAsync(path, new FormUrlEncodedContent(fields));
    }

    private static async Task Register(HttpClient client, string email)
    {
        var response = await Post(client, "/Identity/Account/Register", new()
        {
            ["Input.Email"] = email, ["Input.Password"] = "Synthetic-Test-Password42!",
            ["Input.ConfirmPassword"] = "Synthetic-Test-Password42!"
        });
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
    }

    [SqlServerFact]
    public async Task MigrationRegistrationOwnershipAndResumeWorkflowWorkOnSqlServer()
    {
        var suffix = Guid.NewGuid().ToString("N");
        var aliceEmail = "alice-" + suffix + "@example.test";
        var bobEmail = "bob-" + suffix + "@example.test";
        Guid jobId;
        Guid resumeId;
        Guid draftId;
        await using (var factory = Factory())
        {
            using (var scope = factory.Services.CreateScope())
            {
                var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                await db.Database.MigrateAsync();
                Assert.NotEmpty(await db.Database.GetAppliedMigrationsAsync());
                Assert.False(db.Database.HasPendingModelChanges());
                await db.Database.MigrateAsync(); // Reapplying is safe.
                Assert.Empty(await db.Database.GetPendingMigrationsAsync());
            }
            using var alice = Client(factory);
            using var bob = Client(factory);
            await Register(alice, aliceEmail);
            await Register(bob, bobEmail);
            Assert.Equal(HttpStatusCode.OK, (await alice.GetAsync("/Jobs")).StatusCode);
            Assert.Equal(HttpStatusCode.OK, (await bob.GetAsync("/Jobs")).StatusCode);

            var created = await Post(alice, "/Jobs/Create", new()
            {
                ["Input.Title"] = "Private developer job", ["Input.Company"] = "Example",
                ["Input.Description"] = "Original SQL Server job", ["Input.Status"] = "0",
                ["OwnerId"] = "forged-owner"
            });
            Assert.Equal(HttpStatusCode.Redirect, created.StatusCode);
            jobId = Guid.Parse(created.Headers.Location!.ToString().Split('/').Last());

            var resumeResponse = await Post(alice, "/Resumes/Edit", new()
            {
                ["Input.Name"] = "Private resume", ["Input.Content"] = "Original SQL Server resume",
                ["OwnerId"] = "forged-owner"
            });
            Assert.Equal(HttpStatusCode.Redirect, resumeResponse.StatusCode);
            using (var scope = factory.Services.CreateScope())
            {
                var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                var owner = await db.Users.SingleAsync(x => x.Email == aliceEmail);
                Assert.Equal(owner.Id, (await db.Jobs.SingleAsync(x => x.Id == jobId)).OwnerId);
                resumeId = (await db.Resumes.SingleAsync(x => x.OwnerId == owner.Id)).Id;
            }
            var draftResponse = await Post(alice, "/Resumes/CreateDraft", new()
            {
                ["ResumeId"] = resumeId.ToString(), ["JobId"] = jobId.ToString()
            });
            Assert.Equal(HttpStatusCode.Redirect, draftResponse.StatusCode);
            draftId = Guid.Parse(draftResponse.Headers.Location!.ToString().Split('/').Last());

            // Obtain Bob's valid token from his own form, then attempt Alice's URLs.
            var bobPage = await bob.GetStringAsync("/Jobs/Create");
            var tokenInput = Regex.Match(bobPage, "<input[^>]*name=\"__RequestVerificationToken\"[^>]*>");
            var token = WebUtility.HtmlDecode(Regex.Match(tokenInput.Value, "value=\"([^\"]+)\"").Groups[1].Value);
            foreach (var path in new[] { "/Jobs/Edit/" + jobId, "/Jobs/Delete/" + jobId,
                "/Resumes/Edit/" + resumeId, "/Resumes/Delete/" + resumeId,
                "/Resumes/Draft/" + draftId, "/Resumes/Delete/" + draftId + "?draft=true" })
            {
                Assert.Equal(HttpStatusCode.NotFound, (await bob.GetAsync(path)).StatusCode);
                var attempt = await bob.PostAsync(path, new FormUrlEncodedContent(new Dictionary<string, string>
                {
                    ["__RequestVerificationToken"] = token, ["Input.Title"] = "Attack",
                    ["Input.Company"] = "Attack", ["Input.Name"] = "Attack", ["Input.Content"] = "Attack"
                }));
                Assert.Equal(HttpStatusCode.NotFound, attempt.StatusCode);
            }
            Assert.Equal(HttpStatusCode.NotFound, (await bob.GetAsync("/Resumes/Draft/" + draftId + "?handler=Download")).StatusCode);
            var download = await alice.GetStringAsync("/Resumes/Draft/" + draftId + "?handler=Download");
            Assert.Equal("Original SQL Server resume", download);
            Assert.DoesNotContain("Private developer job", await bob.GetStringAsync("/Jobs"));
            Assert.DoesNotContain("Private resume", await bob.GetStringAsync("/Resumes"));
            // A signed-in mutation without antiforgery must still fail.
            Assert.Equal(HttpStatusCode.BadRequest,
                (await alice.PostAsync("/Jobs/Delete/" + jobId, new FormUrlEncodedContent(new Dictionary<string, string>()))).StatusCode);
        }
        // A fresh host and fresh login prove persistence without reusing authentication cookies.
        await using (var factory = Factory())
        {
            using var alice = Client(factory);
            var login = await Post(alice, "/Identity/Account/Login", new()
            {
                ["Input.Email"] = aliceEmail, ["Input.Password"] = "Synthetic-Test-Password42!"
            });
            Assert.Equal(HttpStatusCode.Redirect, login.StatusCode);
            Assert.Contains("Private developer job", await alice.GetStringAsync("/Jobs"));
            Assert.Contains("Original SQL Server resume", await alice.GetStringAsync("/Resumes/Draft/" + draftId));
            var edit = await Post(alice, "/Resumes/Draft/" + draftId, new() { ["Input.Content"] = "Edited draft" });
            Assert.Equal(HttpStatusCode.Redirect, edit.StatusCode);
            Assert.Contains("Original SQL Server resume", await alice.GetStringAsync("/Resumes/Edit/" + resumeId));
            Assert.Equal(HttpStatusCode.Redirect, (await Post(alice, "/Jobs/Delete/" + jobId, new())).StatusCode);
            Assert.Equal(HttpStatusCode.Redirect, (await Post(alice, "/Resumes/Delete/" + resumeId, new())).StatusCode);
            Assert.Contains("Original SQL Server resume", await alice.GetStringAsync("/Resumes/Draft/" + draftId));
            Assert.Equal("Edited draft", await alice.GetStringAsync("/Resumes/Draft/" + draftId + "?handler=Download"));
        }
    }
}
