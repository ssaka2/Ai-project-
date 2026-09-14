using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

public class EditModel(JobService jobs) : PageModel
{
    [BindProperty] public JobInput Input { get; set; } = new();
    private string OwnerId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;

    public async Task<IActionResult> OnGetAsync(Guid id)
    {
        var job = await jobs.GetAsync(OwnerId, id);
        if (job is null) return NotFound();
        Input = new JobInput
        {
            Title = job.Title, Company = job.Company, Location = job.Location,
            ApplicationUrl = job.ApplicationUrl, Description = job.Description,
            Notes = job.Notes, Status = job.Status
        };
        return Page();
    }

    public async Task<IActionResult> OnPostAsync(Guid id)
    {
        if (await jobs.GetAsync(OwnerId, id) is null) return NotFound();
        if (!ModelState.IsValid) return Page();
        if (!await jobs.UpdateAsync(OwnerId, id, Input)) return NotFound();
        return RedirectToPage("Index");
    }
}
