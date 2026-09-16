using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public class IndexModel(JobService jobs) : PageModel
{
    [BindProperty(SupportsGet = true)] public ApplicationStatus? Status { get; set; }
    [BindProperty(SupportsGet = true)] public string? Search { get; set; }
    public int DueCount { get; private set; }
    public List<JobApplication> Items { get; private set; } = [];
    public Dictionary<ApplicationStatus, int> Counts { get; private set; } = [];
    public async Task<IActionResult> OnGetAsync()
    {
        if (!ModelState.IsValid || (Status.HasValue && !Enum.IsDefined(Status.Value)))
            return BadRequest();
        var all = await jobs.ListAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        Counts = Enum.GetValues<ApplicationStatus>().ToDictionary(s => s, s => all.Count(x => x.Status == s));
        DueCount = ApplicationAutomation.Due(all, DateTime.UtcNow).Count;
        Items = Status.HasValue ? all.Where(x => x.Status == Status).ToList() : all;
        if (!string.IsNullOrWhiteSpace(Search))
        {
            var query = Search.Trim();
            Items = Items.Where(j => j.Title.Contains(query, StringComparison.OrdinalIgnoreCase)
                || j.Company.Contains(query, StringComparison.OrdinalIgnoreCase)
                || j.Location.Contains(query, StringComparison.OrdinalIgnoreCase)).ToList();
        }
        return Page();
    }
    public async Task<IActionResult> OnGetExportAsync()
    {
        var result = await OnGetAsync();
        if (result is not PageResult) return result;
        return File(ApplicationAutomation.Csv(Items), "text/csv; charset=utf-8", "careerdesk-applications.csv");
    }
}
