using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc.RazorPages;
namespace AiCareerDesk.Web.Pages.Resumes;
public class IndexModel(ResumeService resumes) : PageModel
{
    public List<Resume> Items { get; private set; } = [];
    public List<ResumeDraft> Drafts { get; private set; } = [];
    public async Task OnGetAsync()
    {
        var owner = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        Items = await resumes.ListAsync(owner);
        Drafts = await resumes.ListDraftsAsync(owner);
    }
}
