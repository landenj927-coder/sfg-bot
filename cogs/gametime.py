import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.config import (
    NFL_TEAMS,
    TEAM_COLORS,
    SFG_LOGO_URL,
    GUILD_ID,
    GAMETIME_TIME_CHOICES,
    GAMETIMES_CHANNEL_ID
)

from utils.helpers import (
    get_team_role,
    get_member_team_name
)

from utils.standings import TEAM_EMOJIS
from utils.autocomplete import nfl_team_autocomplete
from utils.views import StreamClaimView
from utils.time_parser import _parse_when_to_dt  # assuming you have this


class Gametime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /GAMETIME
    # =========================
    @app_commands.command(
        name="gametime",
        description="Post a scheduled game time between two NFL teams."
    )
    @app_commands.describe(
        team1="First NFL team",
        team2="Second NFL team",
        when="Start time"
    )
    @app_commands.autocomplete(team1=nfl_team_autocomplete, team2=nfl_team_autocomplete)
    @app_commands.choices(when=GAMETIME_TIME_CHOICES)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def gametime(
        self,
        interaction: discord.Interaction,
        team1: str,
        team2: str,
        when: app_commands.Choice[str],
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("Server-only command.", ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            return await interaction.followup.send("Couldn’t verify roles.", ephemeral=True)

        # =========================
        # VALIDATION
        # =========================
        if team1 not in NFL_TEAMS or team2 not in NFL_TEAMS:
            return await interaction.followup.send("❌ Invalid NFL teams.", ephemeral=True)

        if team1 == team2:
            return await interaction.followup.send("❌ Teams can’t be the same.", ephemeral=True)

        role1 = get_team_role(guild, team1)
        role2 = get_team_role(guild, team2)

        if not role1 or not role2:
            return await interaction.followup.send(
                "❌ Team roles missing in server.",
                ephemeral=True
            )

        # =========================
        # TEAM CHECK
        # =========================
        user_team = get_member_team_name(member)

        if user_team not in (team1, team2):
            return await interaction.followup.send(
                f"❌ You must be on {role1.mention} or {role2.mention} to post this.",
                ephemeral=True
            )

        # =========================
        # MANAGEMENT CHECK
        # =========================
        allowed_roles = {"Franchise Owner", "Team President", "General Manager"}

        if not any(r.name in allowed_roles for r in member.roles):
            return await interaction.followup.send(
                "❌ Only **Franchise Owners**, **Team Presidents**, or **General Managers** can post game times.",
                ephemeral=True
            )

        # =========================
        # CHANNEL (ID BASED 🔥)
        # =========================
        gametimes_ch = guild.get_channel(GAMETIMES_CHANNEL_ID)

        if not gametimes_ch:
            return await interaction.followup.send(
                "❌ Gametimes channel not found (invalid ID).",
                ephemeral=True
            )

        # =========================
        # TIME PARSING
        # =========================
        try:
            dt = _parse_when_to_dt(when.value)
        except Exception as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)

        unix = int(dt.timestamp())
        time_full = f"<t:{unix}:t>"
        time_relative = f"<t:{unix}:R>"

        # =========================
        # EMBED BUILD
        # =========================
        color = TEAM_COLORS.get(user_team, 0x2F3136)

        e1 = TEAM_EMOJIS.get(team1, "")
        e2 = TEAM_EMOJIS.get(team2, "")

        left = f"{e1} {role1.mention}".strip()
        right = f"{e2} {role2.mention}".strip()

        embed = discord.Embed(
            title="SFG Scheduling",
            description=f"**Scheduled @ {time_full}**",
            color=color
        )

        embed.set_thumbnail(url=SFG_LOGO_URL)

        embed.add_field(
            name="\u200b",
            value=f"{left} vs {right}",
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value=(
                f"⏰ **Start:** {time_relative}\n"
                f"**Coach:** {member.mention} ({user_team})"
            ),
            inline=False
        )

        embed.set_footer(
            text=member.display_name,
            icon_url=member.display_avatar.url
        )

        # =========================
        # SEND
        # =========================
        view = StreamClaimView()
        await gametimes_ch.send(embed=embed, view=view)

        await interaction.followup.send(
            f"✅ Posted in {gametimes_ch.mention}.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Gametime(bot))