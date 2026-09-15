using System.Security.Claims;
using System.Text.Json;
using AiCareerDesk.Web.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
namespace AiCareerDesk.Web.Pages.Account;

[Authorize]
[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public class ExportModel(ApplicationDbContext db) : PageModel
{
    public void OnGet() { }
    // Read-only GET supports explicit browser download links; POST remains antiforgery protected.
    public Task<IActionResult> OnGetDownloadAsync(CancellationToken cancellationToken) => DownloadAsync(cancellationToken);
    public Task<IActionResult> OnPostAsync(CancellationToken cancellationToken) => DownloadAsync(cancellationToken);
    private async Task<IActionResult> DownloadAsync(CancellationToken cancellationToken)
    {
        var owner = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        // Explicitly select account fields: never serialize an IdentityUser.
        var account = await db.Users.AsNoTracking().Where(x => x.Id == owner)
            .Select(x => new { x.Email, x.UserName, x.EmailConfirmed, x.PhoneNumber, x.PhoneNumberConfirmed })
            .SingleOrDefaultAsync(cancellationToken);
        if (account is null) return NotFound();
        var jobs = await db.Jobs.AsNoTracking().Where(x => x.OwnerId == owner).OrderBy(x => x.Id).ToListAsync(cancellationToken);
        var history = await db.StatusHistory.AsNoTracking()
            .Where(x => db.Jobs.Any(j => j.Id == x.JobApplicationId && j.OwnerId == owner))
            .OrderBy(x => x.ChangedUtc).ToListAsync(cancellationToken);
        var resumes = await db.Resumes.AsNoTracking().Where(x => x.OwnerId == owner).OrderBy(x => x.Id).ToListAsync(cancellationToken);
        var drafts = await db.ResumeDrafts.AsNoTracking().Where(x => x.OwnerId == owner).OrderBy(x => x.Id).ToListAsync(cancellationToken);
        var suggestions = await db.TailoringSuggestions.AsNoTracking()
            .Where(x => db.ResumeDrafts.Any(d => d.Id == x.ResumeDraftId && d.OwnerId == owner))
            .OrderBy(x => x.CreatedUtc).ToListAsync(cancellationToken);
        var data = new { FormatVersion = 1, ExportedUtc = DateTime.UtcNow, Account = account,
            Jobs = jobs, StatusHistory = history, Resumes = resumes, Drafts = drafts, Suggestions = suggestions };
        Response.Headers.CacheControl = "no-store";
        Response.Headers.Pragma = "no-cache";
        Response.Headers["X-Content-Type-Options"] = "nosniff";
        return File(JsonSerializer.SerializeToUtf8Bytes(data, new JsonSerializerOptions { WriteIndented = true }),
            "application/json", "ai-career-desk-export.json");
    }
}
