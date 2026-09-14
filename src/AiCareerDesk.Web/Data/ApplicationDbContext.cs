using AiCareerDesk.Web.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace AiCareerDesk.Web.Data;

public class ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
    : IdentityDbContext<IdentityUser>(options)
{
    public DbSet<JobApplication> Jobs => Set<JobApplication>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);
        builder.Entity<JobApplication>().HasIndex(x => new { x.OwnerId, x.Status });
        builder.Entity<JobApplication>().HasOne<IdentityUser>().WithMany()
            .HasForeignKey(x => x.OwnerId).OnDelete(DeleteBehavior.Cascade);
    }
}
