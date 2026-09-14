using AiCareerDesk.Web.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace AiCareerDesk.Web.Data;

public class ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
    : IdentityDbContext<IdentityUser>(options)
{
    public DbSet<JobApplication> Jobs => Set<JobApplication>();

    public DbSet<TailoringSuggestion> TailoringSuggestions => Set<TailoringSuggestion>();
    public DbSet<Resume> Resumes => Set<Resume>();
    public DbSet<ResumeDraft> ResumeDrafts => Set<ResumeDraft>();
    public DbSet<ApplicationStatusHistory> StatusHistory => Set<ApplicationStatusHistory>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);
        builder.Entity<TailoringSuggestion>().HasOne<ResumeDraft>().WithMany()
            .HasForeignKey(x => x.ResumeDraftId).OnDelete(DeleteBehavior.Cascade);
        builder.Entity<TailoringSuggestion>().HasIndex(x => new { x.ResumeDraftId, x.CreatedUtc });
        builder.Entity<Resume>().HasIndex(x => x.OwnerId);
        builder.Entity<Resume>().HasOne<IdentityUser>().WithMany()
            .HasForeignKey(x => x.OwnerId).OnDelete(DeleteBehavior.Cascade);
        builder.Entity<ResumeDraft>().HasIndex(x => x.OwnerId);
        builder.Entity<ResumeDraft>().HasOne<IdentityUser>().WithMany()
            .HasForeignKey(x => x.OwnerId).OnDelete(DeleteBehavior.Cascade);
        builder.Entity<ApplicationStatusHistory>().HasOne<JobApplication>().WithMany()
            .HasForeignKey(x => x.JobApplicationId).OnDelete(DeleteBehavior.Cascade);
        builder.Entity<ApplicationStatusHistory>().HasIndex(x => new { x.JobApplicationId, x.ChangedUtc });
        builder.Entity<JobApplication>().HasIndex(x => new { x.OwnerId, x.Status });
        builder.Entity<JobApplication>().HasOne<IdentityUser>().WithMany()
            .HasForeignKey(x => x.OwnerId).OnDelete(DeleteBehavior.Cascade);
    }
}
