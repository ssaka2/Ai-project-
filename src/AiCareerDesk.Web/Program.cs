using AiCareerDesk.Web.Services.Email;
using Microsoft.AspNetCore.Identity.UI.Services;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Extensions.Options;
using AiCareerDesk.Web.Services.AI;
using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddDbContext<ApplicationDbContext>((services, options) =>
{
    var connectionString = services.GetRequiredService<IConfiguration>()
        .GetConnectionString("DefaultConnection")
        ?? throw new InvalidOperationException("Set ConnectionStrings:DefaultConnection with user secrets or environment variables.");
    options.UseSqlServer(connectionString);
});
builder.Services.AddDefaultIdentity<IdentityUser>(options =>
{
    options.SignIn.RequireConfirmedAccount = builder.Configuration.GetValue("Identity:RequireConfirmedAccount", true);
    options.Lockout.MaxFailedAccessAttempts = 5;
    options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
    options.User.RequireUniqueEmail = true;
    options.Password.RequiredLength = 12;
}).AddEntityFrameworkStores<ApplicationDbContext>();
builder.Services.Configure<EmailOptions>(builder.Configuration.GetSection("Email"));
builder.Services.AddTransient<IEmailSender, SmtpEmailSender>();
builder.Services.Configure<DataProtectionTokenProviderOptions>(options => options.TokenLifespan = TimeSpan.FromHours(1));
var protection = builder.Services.AddDataProtection().SetApplicationName("AiCareerDesk");
var keyPath = builder.Configuration["DataProtection:KeyPath"];
if (!string.IsNullOrWhiteSpace(keyPath))
{
    Directory.CreateDirectory(keyPath);
    protection.PersistKeysToFileSystem(new DirectoryInfo(keyPath));
}
builder.Services.AddScoped<JobService>();
builder.Services.AddScoped<ResumeService>();
builder.Services.Configure<AiOptions>(builder.Configuration.GetSection("AI"));
builder.Services.AddHttpClient<IResumeTailoringService, OpenAiResumeTailoringService>(client =>
{
    client.Timeout = TimeSpan.FromSeconds(65);
}).ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler { AllowAutoRedirect = false });
builder.Services.AddSingleton<GenerationGate>();
builder.Services.AddScoped<TailoringWorkflow>();
builder.Services.AddRazorPages(options =>
{
    options.Conventions.AuthorizeFolder("/Jobs");
    options.Conventions.AuthorizeFolder("/Resumes");
});

var app = builder.Build();
// Validate after the host has applied all configuration sources.
if (string.IsNullOrWhiteSpace(app.Configuration.GetConnectionString("DefaultConnection")))
    throw new InvalidOperationException("Set ConnectionStrings:DefaultConnection with user secrets or environment variables.");
var email = app.Services.GetRequiredService<IOptions<EmailOptions>>().Value;
if (app.Configuration.GetValue("Identity:RequireConfirmedAccount", true) && !email.IsConfigured)
    throw new InvalidOperationException("Confirmed accounts require configured SMTP delivery. See docs/full-stack-setup.md.");
if (email.Enabled && email.SocketOptions == MailKit.Security.SecureSocketOptions.None &&
    !app.Environment.IsDevelopment() && !app.Environment.IsEnvironment("Testing"))
    throw new InvalidOperationException("SMTP encryption is required outside development and tests.");
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}
app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.MapRazorPages();
app.MapGet("/health/live", () => Results.Ok(new { status = "ok" }));
app.MapGet("/health/ready", async (ApplicationDbContext db, CancellationToken token) =>
{
    try
    {
        return await db.Database.CanConnectAsync(token) && !(await db.Database.GetPendingMigrationsAsync(token)).Any()
            ? Results.Ok(new { status = "ready" }) : Results.StatusCode(503);
    }
    catch { return Results.StatusCode(503); }
});

app.Run();

public partial class Program { }
