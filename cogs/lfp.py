import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.config import GUILD_ID
from utils.helpers import find_text_channel_fuzzy

from utils.constants import NFL_TEAMS, TEAM_COLORS, TEAM_THUMBNAILS, SFG_LOGO_URL


class LFP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /lfp
    # =========================
    @app_commands.command(
        name="lfp",
        description="Post a looking for players message"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        info="Message players should see"
    )
    async def lfp(
        self,
        interaction: discord.Interaction,
        info: str,
    ):

        # 🔥 FIX: prevent timeout
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user

        if not guild:
            return await interaction.followup.send(
                "Server only command.",
                ephemeral=True
            )

        # 🔥 FIX: flexible team role detection
        team_role = next(
            (r for r in member.roles if any(team in r.name for team in NFL_TEAMS)),
            None
        )

        if not team_role:
            return await interaction.followup.send(
                "You must have a team role.",
                ephemeral=True
            )

        team_name = team_role.name

        # =========================
        # FIND FREE AGENCY CHANNEL
        # =========================
        channel = find_text_channel_fuzzy(guild, "free agency")

        if not channel:
            return await interaction.followup.send(
                "Free Agency channel not found.",
                ephemeral=True
            )

        # =========================
        # BUILD EMBED
        # =========================
        color = TEAM_COLORS.get(team_name, 0x2F3136)
        thumb = TEAM_THUMBNAILS.get(team_name)

        embed = discord.Embed(
            title="Free Agency",
            description=f"{team_role.mention} is looking for players!",
            color=color,
            timestamp=datetime.utcnow()
        )

        if thumb:
            embed.set_thumbnail(url=thumb)

        embed.add_field(
            name="Information",
            value=f"```\n{info}\n```",
            inline=False
        )

        embed.add_field(
            name="Coach",
            value=member.mention,
            inline=False
        )

        embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        # =========================
        # SEND
        # =========================
        await channel.send(embed=embed)

        await interaction.followup.send(
            "✅ Free Agency post sent.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(LFP(bot))