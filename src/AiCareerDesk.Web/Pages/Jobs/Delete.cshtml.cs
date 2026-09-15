using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

public class DeleteModel(JobService jobs) : PageModel
{
    [BindProperty, Microsoft.AspNetCore.Mvc.ModelBinding.BindRequired] public Guid ExpectedVersion { get; set; }
    public JobApplication Job { get; private set; } = null!;
    private string OwnerId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    public async Task<IActionResult> OnGetAsync(Guid id)
    {
        var job = await jobs.GetAsync(OwnerId, id);
        if (job is null) return NotFound();
        Job = job;
        ExpectedVersion = job.Version;
        return Page();
    }
    public async Task<IActionResult> OnPostAsync(Guid id)
    {
        if (await jobs.GetAsync(OwnerId, id) is null) return NotFound();
        if (!ModelState.IsValid) return BadRequest();
        var result = await jobs.DeleteAsync(OwnerId, id, ExpectedVersion);
        if (result == WriteResult.NotFound) return NotFound();
        if (result == WriteResult.Conflict)
        {
            var current = await jobs.GetAsync(OwnerId, id);
            if (current is null) return NotFound();
            Job = current;
            Response.StatusCode = StatusCodes.Status409Conflict;
            ModelState.AddModelError("", "This job changed after you opened this page. Review the latest job before confirming deletion again.");
            return Page();
        }
        return RedirectToPage("Index");
    }
}
