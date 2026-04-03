import discord
from discord.ext import commands
from discord import app_commands
import time
import re

from utils.config import (
    NFL_TEAMS,
    GUILD_ID,
    STREAMER_ROLE_NAME,
    STREAMS_CHANNEL_NAME,
    STREAM_COOLDOWN_SECONDS,
    YOUTUBE_COLOR,
    TWITCH_COLOR,
    YOUTUBE_LOGO_URL,
    TWITCH_LOGO_URL
)

from utils.helpers import get_team_role
from utils.config import STREAMS_CHANNEL_ID
from utils.standings import TEAM_EMOJIS
from utils.autocomplete import nfl_team_autocomplete


# =========================
# GLOBALS
# =========================
URL_REGEX = re.compile(r"^https?://")
stream_cooldowns = {}


class Stream(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /STREAM
    # =========================
    @app_commands.command(
        name="stream",
        description="Streamer-only: post a stream link + matchup."
    )
    @app_commands.describe(
        team1="First NFL team",
        team2="Second NFL team",
        platform="Streaming platform",
        link="Stream URL"
    )
    @app_commands.autocomplete(team1=nfl_team_autocomplete, team2=nfl_team_autocomplete)
    @app_commands.choices(
        platform=[
            app_commands.Choice(name="YouTube", value="YouTube"),
            app_commands.Choice(name="Twitch", value="Twitch"),
        ]
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def stream(
        self,
        interaction: discord.Interaction,
        team1: str,
        team2: str,
        platform: app_commands.Choice[str],
        link: str
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("Server-only command.", ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            return await interaction.followup.send("Couldn’t verify roles.", ephemeral=True)

        # =========================
        # ROLE CHECK
        # =========================
        if not any(r.name == STREAMER_ROLE_NAME for r in member.roles):
            return await interaction.followup.send(
                f"❌ You need the **{STREAMER_ROLE_NAME}** role to use `/stream`.",
                ephemeral=True
            )

        # =========================
        # COOLDOWN
        # =========================
        now = time.time()
        last = stream_cooldowns.get(member.id, 0)

        if now - last < STREAM_COOLDOWN_SECONDS:
            remaining = int(STREAM_COOLDOWN_SECONDS - (now - last))
            h, m = divmod(remaining // 60, 60)

            return await interaction.followup.send(
                f"⏳ You must wait **{h}h {m}m** before using `/stream` again.",
                ephemeral=True
            )

        # =========================
        # VALIDATION
        # =========================
        if team1 not in NFL_TEAMS or team2 not in NFL_TEAMS or team1 == team2:
            return await interaction.followup.send("❌ Invalid team selection.", ephemeral=True)

        if not URL_REGEX.match(link.strip()):
            return await interaction.followup.send(
                "❌ Link must start with **http://** or **https://**.",
                ephemeral=True
            )

        streams_ch = guild.get_channel(STREAMS_CHANNEL_ID)
        if not streams_ch:
            return await interaction.followup.send(
                "❌ Streams channel not found (invalid ID).",
                ephemeral=True
            )

        role1 = get_team_role(guild, team1)
        role2 = get_team_role(guild, team2)

        if not role1 or not role2:
            return await interaction.followup.send(
                "❌ Team roles missing.",
                ephemeral=True
            )

        # =========================
        # EMOJIS
        # =========================
        e1 = TEAM_EMOJIS.get(team1, "")
        e2 = TEAM_EMOJIS.get(team2, "")

        left = f"{e1} {role1.mention}".strip()
        right = f"{e2} {role2.mention}".strip()

        # =========================
        # PLATFORM STYLE
        # =========================
        if platform.value == "YouTube":
            color = YOUTUBE_COLOR
            logo = YOUTUBE_LOGO_URL
        else:
            color = TWITCH_COLOR
            logo = TWITCH_LOGO_URL

        embed = discord.Embed(
            title="📺 Live Stream",
            description=(
                f"**Matchup:** {left} vs {right}\n"
                f"**Platform:** {platform.value}\n"
                f"**Link:** {link}"
            ),
            color=color
        )

        embed.set_thumbnail(url=logo)
        embed.set_footer(text=f"Posted by {member.display_name}")

        # =========================
        # SEND MESSAGE
        # =========================
        msg = await streams_ch.send(
            content=f"@here\n{left} {right}",
            embed=embed
        )

        # Optional: reactions (only if emojis exist as real emojis)
        for emoji in guild.emojis:
            if emoji.name.lower() == team1.lower():
                await msg.add_reaction(emoji)
            if emoji.name.lower() == team2.lower():
                await msg.add_reaction(emoji)

        # =========================
        # SET COOLDOWN
        # =========================
        stream_cooldowns[member.id] = now

        # =========================
        # RESPONSE
        # =========================
        await interaction.followup.send(
            f"✅ Stream posted in {streams_ch.mention}.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Stream(bot))