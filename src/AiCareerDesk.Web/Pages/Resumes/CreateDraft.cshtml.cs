using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.Mvc.Rendering;
namespace AiCareerDesk.Web.Pages.Resumes;
public class CreateDraftModel(ResumeService resumes, JobService jobs) : PageModel
{
    [BindProperty] public Guid ResumeId { get; set; }
    [BindProperty] public Guid JobId { get; set; }
    public List<SelectListItem> ResumeOptions { get; private set; } = [];
    public List<SelectListItem> JobOptions { get; private set; } = [];
    private string Owner => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    private async Task LoadAsync()
    {
        ResumeOptions = (await resumes.ListAsync(Owner)).Select(x => new SelectListItem(x.Name, x.Id.ToString())).ToList();
        JobOptions = (await jobs.ListAsync(Owner)).Select(x => new SelectListItem(x.Title + " — " + x.Company, x.Id.ToString())).ToList();
    }
    public Task OnGetAsync() => LoadAsync();
    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) { await LoadAsync(); return Page(); }
        var id = await resumes.CreateDraftAsync(Owner, ResumeId, JobId);
        if (id is null)
        {
            ModelState.AddModelError("", "Choose one of your saved resumes and jobs.");
            await LoadAsync();
            return Page();
        }
        return RedirectToPage("Draft", new { id });
    }
}
