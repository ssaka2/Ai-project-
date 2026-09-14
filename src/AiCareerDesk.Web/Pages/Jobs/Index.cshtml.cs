using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

public class IndexModel(JobService jobs) : PageModel
{
    [BindProperty(SupportsGet = true)] public ApplicationStatus? Status { get; set; }
    public List<JobApplication> Items { get; private set; } = [];
    public Dictionary<ApplicationStatus, int> Counts { get; private set; } = [];
    public async Task<IActionResult> OnGetAsync()
    {
        if (!ModelState.IsValid || (Status.HasValue && !Enum.IsDefined(Status.Value)))
            return BadRequest();
        var all = await jobs.ListAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        Counts = Enum.GetValues<ApplicationStatus>().ToDictionary(s => s, s => all.Count(x => x.Status == s));
        Items = Status.HasValue ? all.Where(x => x.Status == Status).ToList() : all;
        return Page();
    }
}
