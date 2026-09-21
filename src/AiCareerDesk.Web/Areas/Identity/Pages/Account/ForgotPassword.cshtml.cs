using System.ComponentModel.DataAnnotations;
using System.Text;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.UI.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.WebUtilities;

namespace AiCareerDesk.Web.Areas.Identity.Pages.Account;

[AllowAnonymous]
public class ForgotPasswordModel(UserManager<IdentityUser> users, IEmailSender sender) : PageModel
{
    [BindProperty]
    public RecoveryInput Input { get; set; } = new();

    public class RecoveryInput
    {
        [Required, EmailAddress]
        public string Email { get; set; } = "";
    }

    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) return Page();
        var user = await users.FindByEmailAsync(Input.Email);
        // Keep the response identical for absent and unconfirmed accounts.
        if (user is not null && await users.IsEmailConfirmedAsync(user))
        {
            var token = await users.GeneratePasswordResetTokenAsync(user);
            var code = WebEncoders.Base64UrlEncode(Encoding.UTF8.GetBytes(token));
            var callback = Url.Page("/Account/ResetPassword", pageHandler: null,
                values: new { area = "Identity", code }, protocol: Request.Scheme)
                ?? throw new InvalidOperationException("Password reset route is unavailable.");
            await sender.SendEmailAsync(Input.Email, "Reset Password",
                $"Reset your password by <a href='{HtmlEncoder.Default.Encode(callback)}'>following this link</a>.");
        }
        return RedirectToPage("./ForgotPasswordConfirmation");
    }
}
