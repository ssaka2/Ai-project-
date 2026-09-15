using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
namespace AiCareerDesk.Web.Pages.Resumes;
public class DeleteModel(ResumeService resumes) : PageModel
{
    public string Name { get; private set; } = "";
    [BindProperty, Microsoft.AspNetCore.Mvc.ModelBinding.BindRequired] public Guid ExpectedVersion { get; set; }
    [BindProperty(SupportsGet = true)] public bool Draft { get; set; }
    private string Owner => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    public async Task<IActionResult> OnGetAsync(Guid id)
    {
        if (Draft)
        {
            var record = await resumes.GetDraftAsync(Owner, id);
            if (record is null) return NotFound();
            Name = record.Name;
            ExpectedVersion = record.Version;
        }
        else
        {
            var record = await resumes.GetAsync(Owner, id);
            if (record is null) return NotFound();
            Name = record.Name;
            ExpectedVersion = record.Version;
        }
        return Page();
    }
    public async Task<IActionResult> OnPostAsync(Guid id)
    {
        var existing = Draft ? (await resumes.GetDraftAsync(Owner, id))?.Name : (await resumes.GetAsync(Owner, id))?.Name;
        if (existing is null) return NotFound();
        if (!ModelState.IsValid) return BadRequest();
        var result = Draft ? await resumes.DeleteDraftAsync(Owner, id, ExpectedVersion)
            : await resumes.DeleteAsync(Owner, id, ExpectedVersion);
        if (result == WriteResult.NotFound) return NotFound();
        if (result == WriteResult.Conflict)
        {
            var name = Draft ? (await resumes.GetDraftAsync(Owner, id))?.Name : (await resumes.GetAsync(Owner, id))?.Name;
            if (name is null) return NotFound();
            Name = name;
            Response.StatusCode = StatusCodes.Status409Conflict;
            ModelState.AddModelError("", "This record changed after you opened this page. Review the latest record before confirming deletion again.");
            return Page();
        }
        return RedirectToPage("Index");
    }
}
