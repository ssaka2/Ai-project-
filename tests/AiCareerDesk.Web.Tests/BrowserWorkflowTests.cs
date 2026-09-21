using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Data.SqlClient;
using System.Diagnostics;
using System.Net;
using AiCareerDesk.Web.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;
namespace AiCareerDesk.Web.Tests;

public sealed class BrowserTheoryAttribute : TheoryAttribute
{
    public BrowserTheoryAttribute()
    {
        if (Environment.GetEnvironmentVariable("RUN_BROWSER_TESTS") != "true" ||
            string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("TEST_SQL_CONNECTION")))
            Skip = "Set RUN_BROWSER_TESTS=true and TEST_SQL_CONNECTION, and install Playwright browsers, to run browser checks.";
    }
}

public class BrowserWorkflowTests
{
    [BrowserTheory]
    [InlineData("chromium", 0)]
    [InlineData("firefox", 0)]
    [InlineData("webkit", 0)]
    [InlineData("firefox", 1)]
    [InlineData("firefox", 2)]
    [InlineData("firefox", 3)]
    public async Task BrowsersCompletePrivateJobAndResumeWorkflowAtDesktopAndMobileWidths(string browserName, int iteration)
    {
        var connection = new SqlConnectionStringBuilder(Environment.GetEnvironmentVariable("TEST_SQL_CONNECTION"))
        {
            InitialCatalog = "CareerBrowser_" + Guid.NewGuid().ToString("N")
        }.ConnectionString;
        await using (var db = new ApplicationDbContext(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlServer(connection).Options))
            await db.Database.MigrateAsync();

        var project = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../src/AiCareerDesk.Web"));
        var start = new ProcessStartInfo("dotnet") { WorkingDirectory = project, UseShellExecute = false };
        foreach (var arg in new[] { "run", "--no-build", "--configuration", "Release", "--no-launch-profile", "--project", project })
            start.ArgumentList.Add(arg);
        start.Environment["ASPNETCORE_ENVIRONMENT"] = "Development";
        start.Environment["ASPNETCORE_URLS"] = "http://127.0.0.1:5087";
        start.Environment["ConnectionStrings__DefaultConnection"] = connection;
        start.Environment["AI__Enabled"] = "false";
        start.Environment["Email__Enabled"] = "true";
        start.Environment["Email__Host"] = "127.0.0.1";
        start.Environment["Email__Port"] = "1025";
        start.Environment["Email__Security"] = "None";
        start.Environment["Email__FromAddress"] = "career@example.test";
        start.Environment["Logging__LogLevel__Default"] = "Warning";
        start.Environment["Logging__LogLevel__Microsoft"] = "Warning";
        using var server = Process.Start(start)!;
        try
        {
            using var probe = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
            var ready = false;
            for (var i = 0; i < 60; i++)
            {
                if (server.HasExited) throw new InvalidOperationException("Browser test server exited before startup.");
                try { ready = (await probe.GetAsync("http://127.0.0.1:5087")).IsSuccessStatusCode; }
                catch (HttpRequestException) { }
                if (ready) break;
                await Task.Delay(250);
            }
            Assert.True(ready, "Kestrel should start for browser tests.");
            using var playwright = await Playwright.CreateAsync();
            await using var browser = await (browserName switch { "firefox" => playwright.Firefox, "webkit" => playwright.Webkit, _ => playwright.Chromium }).LaunchAsync(new() { Headless = true });
            await using var aliceContext = await browser.NewContextAsync(new()
            {
                BaseURL = "http://127.0.0.1:5087", ViewportSize = new() { Width = 1280, Height = 900 }
            });
            var page = await aliceContext.NewPageAsync();
            var pageErrors = new List<string>();
            page.PageError += (_, error) => pageErrors.Add(error);
            await aliceContext.Tracing.StartAsync(new() { Screenshots = true, Snapshots = true });
            try
            {
            var email = "browser-" + Guid.NewGuid().ToString("N") + "@example.test";
            await Register(page, email);
            await page.GotoAsync("/Jobs/Create");
            await page.GetByLabel("Title", new() { Exact = true }).FillAsync("Browser developer");
            await page.GetByLabel("Company", new() { Exact = true }).FillAsync("Example");
            await page.GetByLabel("Application URL").FillAsync("javascript:alert(1)");
            await page.GetByRole(AriaRole.Button, new() { Name = "Save job", Exact = true }).ClickAsync();
            await Expect(page.GetByText("Enter an absolute http or https URL.")).ToBeVisibleAsync();
            await page.GetByLabel("Application URL").FillAsync("https://example.test/jobs/1");
            await page.GetByLabel("Description", new() { Exact = true }).FillAsync("C# and SQL Server developer");
            await page.GetByRole(AriaRole.Button, new() { Name = "Save job", Exact = true }).ClickAsync();
            await page.WaitForURLAsync("**/Jobs/Edit/**");
            var jobUrl = page.Url;
            await page.GetByLabel("Status", new() { Exact = true }).SelectOptionAsync("1");
            await page.GetByRole(AriaRole.Button, new() { Name = "Save changes", Exact = true }).ClickAsync();
            await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "My job dashboard" })).ToBeVisibleAsync();
            await page.GetByRole(AriaRole.Link, new() { Name = "Browser developer", Exact = true }).ClickAsync();
            await Expect(page.GetByText("Saved → Applied", new() { Exact = false })).ToBeVisibleAsync();

            await page.GotoAsync("/Resumes/Edit");
            await page.GetByLabel("Resume name").FillAsync("Browser base");
            await page.GetByLabel("Resume text").FillAsync("C# developer\n<script>window.resumeInjected=true</script>");
            await page.GetByRole(AriaRole.Button, new() { Name = "Save resume", Exact = true }).ClickAsync();
            await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "My resumes", Exact = true })).ToBeVisibleAsync();
            await Expect(page.GetByRole(AriaRole.Link, new() { Name = "Browser base", Exact = true })).ToBeVisibleAsync();
            await page.GotoAsync("/Resumes/CreateDraft");
            await page.GetByLabel("Base resume").SelectOptionAsync(new SelectOptionValue { Label = "Browser base" });
            await page.GetByLabel("Job", new() { Exact = true }).SelectOptionAsync(new SelectOptionValue { Label = "Browser developer — Example" });
            await page.GetByRole(AriaRole.Button, new() { Name = "Create editable draft" }).ClickAsync();
            // The editor is our readiness signal; unrelated load events can stall Firefox.
            await page.WaitForURLAsync("**/Resumes/Draft/**", new() { WaitUntil = WaitUntilState.Commit });
            await Expect(page.GetByLabel("Draft text")).ToBeVisibleAsync();
            await Expect(page.GetByLabel("Draft text")).ToHaveValueAsync("C# developer\n<script>window.resumeInjected=true</script>");
            var draftUrl = page.Url;
            var staleTab = await aliceContext.NewPageAsync();
            await staleTab.GotoAsync(draftUrl);
            await page.GetByLabel("Draft text").FillAsync("Saved browser draft");
            await page.GetByRole(AriaRole.Button, new() { Name = "Save changes", Exact = true }).ClickAsync();
            await Expect(page.GetByLabel("Draft text")).ToHaveValueAsync("Saved browser draft");
            await staleTab.GetByLabel("Draft text").FillAsync("My stale unsaved text");
            await staleTab.GetByRole(AriaRole.Button, new() { Name = "Save changes", Exact = true }).ClickAsync();
            await Expect(staleTab.GetByText("This draft changed in another session.", new() { Exact = false })).ToBeVisibleAsync();
            await Expect(staleTab.GetByLabel("Draft text")).ToHaveValueAsync("My stale unsaved text");
            await staleTab.CloseAsync();
            await page.BringToFrontAsync();

            page.Response += (_, response) =>
            {
                if (response.Url.Contains("handler=Download", StringComparison.Ordinal))
                    System.Console.WriteLine($"Draft download HTTP {response.Status} on {browserName}");
            };
            var download = await page.RunAndWaitForDownloadAsync(() =>
                page.GetByRole(AriaRole.Link, new() { Name = "Download saved draft (.txt)" }).ClickAsync());
            await using (var stream = await download.CreateReadStreamAsync())
            using (var reader = new StreamReader(stream!))
                Assert.Equal("Saved browser draft", await reader.ReadToEndAsync());

            await page.GetByRole(AriaRole.Link, new() { Name = "AI suggestions", Exact = true }).ClickAsync();
            await Expect(page.GetByText("AI tailoring is not enabled", new() { Exact = false })).ToBeVisibleAsync();
            await page.GetByText("Source documents sent for generation", new() { Exact = true }).ClickAsync();
            Assert.True(await page.EvaluateAsync<bool>("() => window.resumeInjected === undefined"));
            await page.SetViewportSizeAsync(390, 844);
            Assert.True(await page.EvaluateAsync<bool>("() => document.documentElement.scrollWidth <= window.innerWidth"));
            await page.GotoAsync("/Jobs");
            await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "My job dashboard" })).ToBeVisibleAsync();
            Assert.True(await page.EvaluateAsync<bool>("() => document.documentElement.scrollWidth <= window.innerWidth"));
            await page.GetByRole(AriaRole.Link, new() { Name = "My resumes", Exact = true }).ClickAsync();
            await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "My resumes", Exact = true })).ToBeVisibleAsync();

            await page.GetByRole(AriaRole.Link, new() { Name = "Export my data", Exact = true }).ClickAsync();
            var export = await page.RunAndWaitForDownloadAsync(() =>
                page.GetByRole(AriaRole.Link, new() { Name = "Download my data (.json)" }).ClickAsync());
            await using (var stream = await export.CreateReadStreamAsync())
            using (var exported = await JsonDocument.ParseAsync(stream!))
            {
                Assert.Equal(email, exported.RootElement.GetProperty("Account").GetProperty("Email").GetString());
                Assert.Equal(1, exported.RootElement.GetProperty("Drafts").GetArrayLength());
            }
            await using var bobContext = await browser.NewContextAsync(new() { BaseURL = "http://127.0.0.1:5087" });
            var bob = await bobContext.NewPageAsync();
            await Register(bob, "bob-browser-" + Guid.NewGuid().ToString("N") + "@example.test");
            Assert.Equal(404, (await bob.GotoAsync(jobUrl))!.Status);
            Assert.Equal(404, (await bob.GotoAsync(draftUrl))!.Status);
            await page.BringToFrontAsync();
            await page.GetByRole(AriaRole.Button, new() { Name = "Sign out", Exact = true }).ClickAsync();
            await Expect(page.GetByRole(AriaRole.Link, new() { Name = "Sign in", Exact = true })).ToBeVisibleAsync();
            await page.GotoAsync("/Identity/Account/ForgotPassword");
            await page.GetByLabel("Email", new() { Exact = true }).FillAsync(email);
            await page.Locator("main form button[type=submit]").ClickAsync();
            await Expect(page).ToHaveURLAsync(new Regex(@"/Identity/Account/ForgotPasswordConfirmation$"), new() { Timeout = 30000 });
            await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "Forgot password confirmation", Exact = true })).ToBeVisibleAsync();
            await page.GotoAsync(await EmailLink(email, "Reset"));
            await page.GetByLabel("Email", new() { Exact = true }).FillAsync(email);
            await page.GetByLabel("Password", new() { Exact = true }).FillAsync("Browser-Replacement42!");
            await page.GetByLabel(new Regex("^Confirm password$", RegexOptions.IgnoreCase)).FillAsync("Browser-Replacement42!");
            await page.Locator("main form button[type=submit]").ClickAsync();
            await Expect(page).ToHaveURLAsync(new Regex(@"/Identity/Account/ResetPasswordConfirmation$"), new() { Timeout = 30000 });
            await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "Reset password confirmation", Exact = true })).ToBeVisibleAsync();
            await page.GotoAsync("/Identity/Account/Login");
            await page.GetByLabel("Email", new() { Exact = true }).FillAsync(email);
            await page.GetByLabel("Password", new() { Exact = true }).FillAsync("Browser-Replacement42!");
            await page.GetByRole(AriaRole.Button, new() { Name = "Log in", Exact = true }).ClickAsync();
            await Expect(page.GetByRole(AriaRole.Button, new() { Name = "Sign out", Exact = true })).ToBeVisibleAsync();
            await page.GotoAsync(draftUrl);
            await Expect(page.GetByLabel("Draft text")).ToHaveValueAsync("Saved browser draft");
            Assert.Empty(pageErrors);
            }
            catch
            {
                var artifacts = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../TestResults"));
                Directory.CreateDirectory(artifacts);
                Console.WriteLine($"Browser failure on {browserName}: {page.Url}");
                await File.WriteAllTextAsync(Path.Combine(artifacts, $"{browserName}-{iteration}-failure.html"), await page.ContentAsync());
                await page.ScreenshotAsync(new() { Path = Path.Combine(artifacts, $"{browserName}-failure.png"), FullPage = true });
                await aliceContext.Tracing.StopAsync(new() { Path = Path.Combine(artifacts, $"{browserName}-{iteration}-trace.zip") });
                throw;
            }
        }
        finally
        {
            if (!server.HasExited) server.Kill(entireProcessTree: true);
            await server.WaitForExitAsync();
            await using var cleanup = new ApplicationDbContext(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlServer(connection).Options);
            await cleanup.Database.EnsureDeletedAsync();
        }
    }

    private static async Task Register(IPage page, string email)
    {
        await page.GotoAsync("/Identity/Account/Register");
        await page.GetByLabel("Email", new() { Exact = true }).FillAsync(email);
        await page.GetByLabel("Password", new() { Exact = true }).FillAsync("Synthetic-Test-Password42!");
        await page.GetByLabel(new Regex("^Confirm password$", RegexOptions.IgnoreCase)).FillAsync("Synthetic-Test-Password42!");
        await page.GetByRole(AriaRole.Button, new() { Name = "Register", Exact = true }).ClickAsync();
        await Expect(page.GetByRole(AriaRole.Heading, new() { Name = "Check your email" })).ToBeVisibleAsync();
        await page.GotoAsync(await EmailLink(email, "Confirm"));
        await page.GotoAsync("/Identity/Account/Login");
        await page.GetByLabel("Email", new() { Exact = true }).FillAsync(email);
        await page.GetByLabel("Password", new() { Exact = true }).FillAsync("Synthetic-Test-Password42!");
        await page.GetByRole(AriaRole.Button, new() { Name = "Log in", Exact = true }).ClickAsync();
        await Expect(page.GetByRole(AriaRole.Button, new() { Name = "Sign out", Exact = true })).ToBeVisibleAsync();
    }

    private static async Task<string> EmailLink(string email, string subject)
    {
        using var http = new HttpClient { BaseAddress = new Uri("http://127.0.0.1:8025") };
        for (var attempt = 0; attempt < 30; attempt++)
        {
            using var messages = JsonDocument.Parse(await http.GetStringAsync("/api/v1/messages?limit=100"));
            foreach (var message in messages.RootElement.GetProperty("messages").EnumerateArray())
            {
                if (!message.GetProperty("Subject").GetString()!.Contains(subject, StringComparison.OrdinalIgnoreCase) ||
                    !message.GetProperty("To").EnumerateArray().Any(to => to.GetProperty("Address").GetString() == email)) continue;
                using var full = JsonDocument.Parse(await http.GetStringAsync("/api/v1/message/" + message.GetProperty("ID").GetString()));
                var html = full.RootElement.GetProperty("HTML").GetString()!;
                return WebUtility.HtmlDecode(Regex.Match(html, """href=['"]([^'"]+)""").Groups[1].Value);
            }
            await Task.Delay(100);
        }
        throw new InvalidOperationException("Expected account email was not captured by the test inbox.");
    }
}
