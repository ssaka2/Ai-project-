using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AiCareerDesk.Web.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddTailoringSuggestions : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<Guid>(
                name: "Version",
                table: "ResumeDrafts",
                type: "uniqueidentifier",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"));

            migrationBuilder.CreateTable(
                name: "TailoringSuggestions",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ResumeDraftId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    Content = table.Column<string>(type: "nvarchar(max)", maxLength: 30000, nullable: false),
                    SkillGaps = table.Column<string>(type: "nvarchar(max)", maxLength: 11000, nullable: false),
                    Provider = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    Model = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    ResponseId = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    PromptVersion = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    CreatedUtc = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_TailoringSuggestions", x => x.Id);
                    table.ForeignKey(
                        name: "FK_TailoringSuggestions_ResumeDrafts_ResumeDraftId",
                        column: x => x.ResumeDraftId,
                        principalTable: "ResumeDrafts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_TailoringSuggestions_ResumeDraftId_CreatedUtc",
                table: "TailoringSuggestions",
                columns: new[] { "ResumeDraftId", "CreatedUtc" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "TailoringSuggestions");

            migrationBuilder.DropColumn(
                name: "Version",
                table: "ResumeDrafts");
        }
    }
}
