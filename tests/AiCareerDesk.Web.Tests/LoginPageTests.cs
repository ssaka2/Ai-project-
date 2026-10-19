using AiCareerDesk.Web.Areas.Identity.Pages.Account;
using AiCareerDesk.Web.Data;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.Mvc.RazorPages.Infrastructure;
using Microsoft.AspNetCore.Mvc.Routing;
using Microsoft.AspNetCore.Routing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Xunit;
using SignInResult = Microsoft.AspNetCore.Identity.SignInResult;

namespace AiCareerDesk.Web.Tests;

public class LoginPageTests
{
    private sealed class FakeSignIn(
        UserManager<IdentityUser> users, IHttpContextAccessor accessor, IUserClaimsPrincipalFactory<IdentityUser> claims,
        IOptions<IdentityOptions> options, ILogger<SignInManager<IdentityUser>> logger,
        IAuthenticationSchemeProvider schemes, IUserConfirmation<IdentityUser> confirmation)
        : SignInManager<IdentityUser>(users, accessor, claims, options, logger, schemes, confirmation)
    {
        public SignInResult Result { get; set; } = SignInResult.Success;
        public int Calls { get; private set; }
        public bool? LockoutOnFailure { get; private set; }
        public override Task<SignInResult> PasswordSignInAsync(string userName, string password, bool isPersistent, bool lockoutOnFailure)
        {
            Calls++;
            LockoutOnFailure = lockoutOnFailure;
            return Task.FromResult(Result);
        }
    }

    private static (LoginModel Page, FakeSignIn SignIn) Create(string? returnUrl, SignInResult result)
    {
        var services = new ServiceCollection();
        services.AddLogging();
        services.AddHttpContextAccessor();
        services.AddAuthenticationCore();
        services.AddDbContext<ApplicationDbContext>(o => o.UseSqlite("Data Source=:memory:"));
        services.AddIdentityCore<IdentityUser>().AddEntityFrameworkStores<ApplicationDbContext>().AddSignInManager<FakeSignIn>();
        var provider = services.BuildServiceProvider();
        var signIn = (FakeSignIn)provider.CreateScope().ServiceProvider.GetRequiredService<SignInManager<IdentityUser>>();
        signIn.Result = result;
        var context = new PageContext(new ActionContext(
            new DefaultHttpContext { RequestServices = provider }, new RouteData(), new PageActionDescriptor()));
        var page = new LoginModel(signIn)
        {
            PageContext = context,
            Url = new UrlHelper(context),
            ReturnUrl = returnUrl,
            Input = new LoginModel.LoginInput { Email = "alice@example.test", Password = "correct horse battery" }
        };
        return (page, signIn);
    }

    [Theory]
    [InlineData("/Jobs?status=Applied", "/Jobs?status=Applied")]
    [InlineData("~/Resumes", "~/Resumes")]
    [InlineData(null, "/")]
    [InlineData("", "/")]
    [InlineData("https://evil.example/phish", "/")]
    [InlineData("//evil.example/phish", "/")]
    [InlineData("/\\evil.example/phish", "/")]
    [InlineData("javascript:alert(1)", "/")]
    public async Task SuccessfulSignInOnlyRedirectsToLocalUrls(string? returnUrl, string expected)
    {
        var (page, signIn) = Create(returnUrl, SignInResult.Success);
        var redirect = Assert.IsType<LocalRedirectResult>(await page.OnPostAsync());
        Assert.Equal(expected, redirect.Url);
        Assert.True(signIn.LockoutOnFailure);
    }

    [Fact]
    public async Task TwoFactorRedirectCarriesOnlyALocalReturnUrl()
    {
        var (page, _) = Create("https://evil.example/phish", SignInResult.TwoFactorRequired);
        var redirect = Assert.IsType<RedirectToPageResult>(await page.OnPostAsync());
        Assert.Equal("./LoginWith2fa", redirect.PageName);
        Assert.Equal("/", redirect.RouteValues!["ReturnUrl"]);
    }

    [Fact]
    public async Task FailedSignInShowsAGenericMessageThatDoesNotRevealWhetherTheAccountExists()
    {
        var (page, signIn) = Create("/Jobs", SignInResult.Failed);
        Assert.IsType<PageResult>(await page.OnPostAsync());
        var error = Assert.Single(page.ModelState[""]!.Errors);
        Assert.Equal("Unable to sign in. Check your credentials and confirm your email.", error.ErrorMessage);
        Assert.True(signIn.LockoutOnFailure);
    }

    [Fact]
    public async Task LockedOutSignInExplainsTheWait()
    {
        var (page, _) = Create("/Jobs", SignInResult.LockedOut);
        Assert.IsType<PageResult>(await page.OnPostAsync());
        Assert.Equal("Too many failed attempts. Try again in fifteen minutes.",
            Assert.Single(page.ModelState[""]!.Errors).ErrorMessage);
    }

    [Fact]
    public async Task InvalidFormDoesNotAttemptSignIn()
    {
        var (page, signIn) = Create("/Jobs", SignInResult.Success);
        page.ModelState.AddModelError("Input.Email", "Required");
        Assert.IsType<PageResult>(await page.OnPostAsync());
        Assert.Equal(0, signIn.Calls);
    }
}
