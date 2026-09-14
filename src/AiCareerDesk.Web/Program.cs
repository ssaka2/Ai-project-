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
    // Development foundation: email delivery and confirmation are a release gate.
    options.SignIn.RequireConfirmedAccount = false;
    options.User.RequireUniqueEmail = true;
    options.Password.RequiredLength = 12;
}).AddEntityFrameworkStores<ApplicationDbContext>();
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

app.Run();

public partial class Program { }
