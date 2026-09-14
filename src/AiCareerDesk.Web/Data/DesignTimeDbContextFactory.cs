using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
namespace AiCareerDesk.Web.Data;

public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<ApplicationDbContext>
{
    public ApplicationDbContext CreateDbContext(string[] args)
    {
        var config = new ConfigurationBuilder().SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: true)
            .AddUserSecrets<ApplicationDbContext>(optional: true)
            .AddEnvironmentVariables().Build();
        var connection = config.GetConnectionString("DefaultConnection")
            ?? "Server=localhost;Database=AiCareerDesk;Integrated Security=true;TrustServerCertificate=true";
        return new ApplicationDbContext(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlServer(connection).Options);
    }
}
