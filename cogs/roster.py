import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

from utils.constants import NFL_TEAMS, TEAM_COLORS, TEAM_THUMBNAILS, ROSTER_LIMIT, SFG_LOGO_URL

class Roster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(self.roster)

    # =========================
    # /roster
    # =========================
    @app_commands.command(name="roster", description="Show the roster for a team role.")
    @app_commands.describe(team_role="Mention the team role you want to view (ex: @Tampa)")
    async def roster(self, interaction: discord.Interaction, team_role: discord.Role):
        guild = interaction.guild

        if not guild:
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        if team_role.name not in NFL_TEAMS:
            return await interaction.response.send_message(
                "Invalid team role.",
                ephemeral=True
            )

        team_name = team_role.name
        players = team_role.members

        color = TEAM_COLORS.get(team_name, 0x2F3136)
        thumb_url = TEAM_THUMBNAILS.get(team_name)

        owner_role = discord.utils.get(guild.roles, name="Franchise Owner")
        president_role = discord.utils.get(guild.roles, name="Team President")
        gm_role = discord.utils.get(guild.roles, name="General Manager")

        def staff_for_team(role: Optional[discord.Role]) -> str:
            if not role:
                return "N/A"
            matched = [m.mention for m in role.members if team_role in m.roles]
            return ", ".join(matched) if matched else "N/A"

        owners = staff_for_team(owner_role)
        presidents = staff_for_team(president_role)
        gms = staff_for_team(gm_role)

        roster_text = (
            "\n".join(f"{i}. {m.mention}" for i, m in enumerate(players, start=1))
            if players else "No players."
        )

        description = (
            f"{owner_role.mention if owner_role else 'Franchise Owner'}: {owners}\n"
            f"{president_role.mention if president_role else 'Team President'}: {presidents}\n"
            f"{gm_role.mention if gm_role else 'General Manager'}: {gms}\n\n"
            f"**Roster:**\n{roster_text}"
        )

        embed = discord.Embed(
            title=f"{team_name} Roster",
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        embed.add_field(
            name="Roster Size",
            value=f"{len(players)} / {ROSTER_LIMIT}",
            inline=False
        )

        embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        await interaction.response.send_message(embed=embed)

# REQUIRED FOR COG LOADING
async def setup(bot):
    await bot.add_cog(Roster(bot))