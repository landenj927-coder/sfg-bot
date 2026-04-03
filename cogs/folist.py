import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.config import (
    NFL_TEAMS,
    SFG_LOGO_URL,
    GUILD_ID
)

from utils.helpers import get_team_role
from utils.standings import TEAM_EMOJIS


class FOList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /FOLIST
    # =========================
    @app_commands.command(
        name="folist",
        description="Show each NFL team and its Franchise Owner (or N/A)."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def folist(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send(
                "Server-only command.",
                ephemeral=True
            )

        fo_role = discord.utils.get(guild.roles, name="Franchise Owner")
        if not fo_role:
            return await interaction.followup.send(
                "❌ Role not found: **Franchise Owner**",
                ephemeral=True
            )

        lines = []

        for team in NFL_TEAMS:
            team_role = get_team_role(guild, team)

            emoji_str = TEAM_EMOJIS.get(team, "")
            team_label = f"{emoji_str} **{team}**" if emoji_str else f"**{team}**"

            owner_text = "N/A"

            if team_role:
                owners = [
                    m.mention for m in fo_role.members
                    if team_role in m.roles
                ]
                if owners:
                    owner_text = ", ".join(owners)

            lines.append(f"{team_label} — {owner_text}")

        # =========================
        # SPLIT INTO PAGES
        # =========================
        chunks = []
        current = ""

        for line in lines:
            if len(current) + len(line) + 1 > 3800:
                chunks.append(current)
                current = ""
            current += line + "\n"

        if current:
            chunks.append(current)

        embeds = []

        for i, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title="Franchise Owner List" + (
                    f" (Page {i}/{len(chunks)})" if len(chunks) > 1 else ""
                ),
                description=chunk,
                color=0x2F3136,
                timestamp=datetime.utcnow()
            )

            embed.set_thumbnail(url=SFG_LOGO_URL)
            embed.set_footer(text="SFG Bot")

            embeds.append(embed)

        # =========================
        # SEND
        # =========================
        await interaction.followup.send(
            embeds=embeds,
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(FOList(bot))