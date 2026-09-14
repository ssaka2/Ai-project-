using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
namespace AiCareerDesk.Web.Pages.Resumes;
public class EditModel(ResumeService resumes) : PageModel
{
    [BindProperty] public ResumeInput Input { get; set; } = new();
    private string Owner => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    public async Task<IActionResult> OnGetAsync(Guid? id)
    {
        if (id is null) return Page();
        var resume = await resumes.GetAsync(Owner, id.Value);
        if (resume is null) return NotFound();
        Input = new ResumeInput { Name = resume.Name, Content = resume.Content };
        return Page();
    }
    public async Task<IActionResult> OnPostAsync(Guid? id)
    {
        if (id.HasValue && await resumes.GetAsync(Owner, id.Value) is null) return NotFound();
        if (!ModelState.IsValid) return Page();
        if (id is null) await resumes.CreateAsync(Owner, Input);
        else if (!await resumes.UpdateAsync(Owner, id.Value, Input)) return NotFound();
        return RedirectToPage("Index");
    }
}
