using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

public class DeleteModel(JobService jobs) : PageModel
{
    public JobApplication Job { get; private set; } = null!;
    private string OwnerId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    public async Task<IActionResult> OnGetAsync(Guid id)
    {
        var job = await jobs.GetAsync(OwnerId, id);
        if (job is null) return NotFound();
        Job = job;
        return Page();
    }
    public async Task<IActionResult> OnPostAsync(Guid id)
    {
        if (!await jobs.DeleteAsync(OwnerId, id)) return NotFound();
        return RedirectToPage("Index");
    }
}
