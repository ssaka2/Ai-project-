using System.Net;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Xunit;

namespace AiCareerDesk.Web.Tests;

public class PageTests
{
    private static WebApplicationFactory<Program> Factory() =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Testing");
            builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["ConnectionStrings:DefaultConnection"] =
                        "Server=localhost;Database=UnusedPageTests;Integrated Security=true;TrustServerCertificate=true",
                    ["Identity:RequireConfirmedAccount"] = "false"
                }));
        });

    [Theory]
    [InlineData("/")]
    [InlineData("/Identity/Account/Register")]
    [InlineData("/Identity/Account/Login")]
    public async Task PublicPagesRender(string path)
    {
        await using var factory = Factory();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false
        });
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync(path)).StatusCode);
    }

    [Theory]
    [InlineData("/Account/Export")]
    [InlineData("/Account/Export?handler=Download")]
    [InlineData("/Jobs")]
    [InlineData("/Jobs/Create")]
    [InlineData("/Resumes")]
    [InlineData("/Resumes/Edit")]
    [InlineData("/Resumes/CreateDraft")]
    [InlineData("/Resumes/Tailor/00000000-0000-0000-0000-000000000001")]
    [InlineData("/Resumes/Draft/00000000-0000-0000-0000-000000000001")]
    [InlineData("/Resumes/Delete/00000000-0000-0000-0000-000000000001")]
    [InlineData("/Jobs/Edit/00000000-0000-0000-0000-000000000001")]
    [InlineData("/Jobs/Delete/00000000-0000-0000-0000-000000000001")]
    public async Task JobPagesRequireSignIn(string path)
    {
        await using var factory = Factory();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false
        });
        var response = await client.GetAsync(path);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.Contains("/Identity/Account/Login", response.Headers.Location!.ToString());
    }

    [Fact]
    public async Task RegisterPostWithoutAntiforgeryTokenIsRejected()
    {
        await using var factory = Factory();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false
        });
        var response = await client.PostAsync("/Identity/Account/Register",
            new FormUrlEncodedContent(new Dictionary<string, string>()));
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task MissingPagesReturnAReadable404WithoutLeakingRecordDetails()
    {
        await using var factory = Factory();
        using var client = factory.CreateClient();
        var response = await client.GetAsync("/missing-test-page");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Contains("This page or record is unavailable.", await response.Content.ReadAsStringAsync());
        Assert.True(response.Headers.CacheControl!.NoStore);
    }
}
