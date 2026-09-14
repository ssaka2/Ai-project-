using System.Security.Claims;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
namespace AiCareerDesk.Web.Pages.Resumes;
public class DeleteModel(ResumeService resumes) : PageModel
{
    public string Name { get; private set; } = "";
    [BindProperty(SupportsGet = true)] public bool Draft { get; set; }
    private string Owner => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    public async Task<IActionResult> OnGetAsync(Guid id)
    {
        var name = Draft ? (await resumes.GetDraftAsync(Owner, id))?.Name : (await resumes.GetAsync(Owner, id))?.Name;
        if (name is null) return NotFound();
        Name = name;
        return Page();
    }
    public async Task<IActionResult> OnPostAsync(Guid id)
    {
        var deleted = Draft ? await resumes.DeleteDraftAsync(Owner, id) : await resumes.DeleteAsync(Owner, id);
        return deleted ? RedirectToPage("Index") : NotFound();
    }
}
