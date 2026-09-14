using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using AiCareerDesk.Web.Services.AI;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
namespace AiCareerDesk.Web.Pages.Resumes;

public class TailorModel(ResumeService resumes, TailoringWorkflow workflow) : PageModel
{
    public ResumeDraft Draft { get; private set; } = null!;
    public List<TailoringSuggestion> Suggestions { get; private set; } = [];
    public TailoringSuggestion? Selected { get; private set; }
    [BindProperty] public bool Consent { get; set; }
    [BindProperty] public Guid ExpectedVersion { get; set; }
    [BindProperty] public Guid SuggestionId { get; set; }
    public bool IsConfigured => workflow.IsConfigured;
    private string Owner => User.FindFirstValue(ClaimTypes.NameIdentifier)!;

    private async Task<bool> LoadAsync(Guid id, Guid? suggestion = null)
    {
        var draft = await resumes.GetDraftAsync(Owner, id);
        if (draft is null) return false;
        Draft = draft;
        Suggestions = await workflow.ListAsync(Owner, id);
        Selected = suggestion.HasValue ? Suggestions.SingleOrDefault(x => x.Id == suggestion) : Suggestions.FirstOrDefault();
        return !suggestion.HasValue || Selected is not null;
    }
    public async Task<IActionResult> OnGetAsync(Guid id, Guid? suggestion)
    {
        if (!await LoadAsync(id, suggestion)) return NotFound();
        ExpectedVersion = Draft.Version;
        return Page();
    }
    public async Task<IActionResult> OnPostGenerateAsync(Guid id, CancellationToken cancellationToken)
    {
        if (!await LoadAsync(id)) return NotFound();
        try
        {
            var suggestion = await workflow.GenerateAsync(Owner, id, Consent, cancellationToken);
            if (suggestion is null) return NotFound();
            return RedirectToPage("Tailor", new { id, suggestion });
        }
        catch (TailoringException error)
        {
            ModelState.AddModelError("", error.Message);
            ExpectedVersion = Draft.Version;
            return Page();
        }
    }
    public async Task<IActionResult> OnPostApplyAsync(Guid id)
    {
        if (!await LoadAsync(id, SuggestionId)) return NotFound();
        var result = await workflow.ApplyAsync(Owner, id, SuggestionId, ExpectedVersion);
        if (result == WriteResult.NotFound) return NotFound();
        if (result == WriteResult.Conflict)
        {
            Response.StatusCode = StatusCodes.Status409Conflict;
            ModelState.AddModelError("", "Your saved draft changed. Reload this review page and compare the latest draft before applying a suggestion.");
            return Page();
        }
        return RedirectToPage("Draft", new { id });
    }
}
