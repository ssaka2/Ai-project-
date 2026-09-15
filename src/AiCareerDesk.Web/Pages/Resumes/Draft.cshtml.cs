using System.Security.Claims;
using System.Text;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
namespace AiCareerDesk.Web.Pages.Resumes;
public class DraftModel(ResumeService resumes) : PageModel
{
    [BindProperty] public DraftInput Input { get; set; } = new();
    public ResumeDraft Draft { get; private set; } = null!;
    private string Owner => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    public async Task<IActionResult> OnGetAsync(Guid id)
    {
        var draft = await resumes.GetDraftAsync(Owner, id);
        if (draft is null) return NotFound();
        Draft = draft;
        Input = new DraftInput { Content = draft.Content, Version = draft.Version };
        return Page();
    }
    public async Task<IActionResult> OnGetDownloadAsync(Guid id)
    {
        var draft = await resumes.GetDraftAsync(Owner, id);
        if (draft is null) return NotFound();
        return File(Encoding.UTF8.GetBytes(draft.Content), "text/plain; charset=utf-8", "resume-draft.txt");
    }
    public async Task<IActionResult> OnPostAsync(Guid id)
    {
        var draft = await resumes.GetDraftAsync(Owner, id);
        if (draft is null) return NotFound();
        Draft = draft;
        if (!ModelState.IsValid) return Page();
        var result = await resumes.UpdateDraftAsync(Owner, id, Input);
        if (result == WriteResult.NotFound) return NotFound();
        if (result == WriteResult.Conflict)
        {
            Response.StatusCode = StatusCodes.Status409Conflict;
            ModelState.AddModelError("", "This draft changed in another session. Your submitted text is kept below. Open the latest saved draft in a new tab to compare before retrying.");
            return Page();
        }
        return RedirectToPage("Draft", new { id });
    }
}
