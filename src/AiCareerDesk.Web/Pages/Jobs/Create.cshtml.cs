using System.Security.Claims;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AiCareerDesk.Web.Pages.Jobs;

public class CreateModel(JobService jobs) : PageModel
{
    [BindProperty] public JobInput Input { get; set; } = new();
    public void OnGet() { }
    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) return Page();
        var id = await jobs.CreateAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!, Input);
        return RedirectToPage("Edit", new { id });
    }
}
