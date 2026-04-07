import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

from utils.config import (
    NFL_TEAMS,
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    GUILD_ID
)

from utils.constants import ROSTER_LIMIT
from utils.standings import TEAM_EMOJIS


class Roster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="roster",
        description="Show the roster for a team role."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(team_role="Mention the team role you want to view (ex: @Tampa)")
    async def roster(self, interaction: discord.Interaction, team_role: discord.Role):

        guild = interaction.guild

        if guild is None:
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
        emoji = TEAM_EMOJIS.get(team_name, "")

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

        # 🔥 CLEAN ROSTER LIST
        if players:
            roster_lines = [f"`{i:>2}.` {m.mention}" for i, m in enumerate(players, start=1)]
            roster_text = "\n".join(roster_lines)
        else:
            roster_text = "*No players signed.*"

        embed = discord.Embed(
            title=f"{emoji} TEAM ROSTER",
            description=f"**{team_name}**",
            color=color,
            timestamp=datetime.utcnow()
        )

        # 🔥 HEADER BRANDING
        embed.set_author(
            name="SFG League",
            icon_url=SFG_LOGO_URL
        )

        # 🏈 TEAM LOGO
        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        divider = "━━━━━━━━━━━━━━━━━━"

        # 👑 MANAGEMENT SECTION
        embed.add_field(
            name="👑 Management",
            value=(
                f"**Owner:** {owners}\n"
                f"**President:** {presidents}\n"
                f"**GM:** {gms}"
            ),
            inline=False
        )

        # 🔥 DIVIDER
        embed.add_field(name=divider, value="\u200b", inline=False)

        # 📋 ROSTER SECTION
        embed.add_field(
            name=f"📋 Active Roster ({len(players)}/{ROSTER_LIMIT})",
            value=roster_text,
            inline=False
        )

        # 🔥 FOOTER
        embed.set_footer(
            text="SFG League • Official Team Roster",
            icon_url=SFG_LOGO_URL
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Roster(bot))