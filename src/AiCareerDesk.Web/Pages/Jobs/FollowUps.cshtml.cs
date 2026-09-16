using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public class FollowUpsModel(JobService jobs) : PageModel
{
    public List<JobApplication> Due { get; private set; } = [];
    public List<JobApplication> Upcoming { get; private set; } = [];
    public async Task OnGetAsync()
    {
        var all = await jobs.ListAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        var today = DateTime.UtcNow.Date;
        Due = ApplicationAutomation.Due(all, today);
        Upcoming = all.Where(j => ApplicationAutomation.FollowUpDate(j) > today)
            .OrderBy(j => ApplicationAutomation.FollowUpDate(j)).ToList();
    }
}
