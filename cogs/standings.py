import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from pathlib import Path
import json

from utils.config import GUILD_ID

from utils.standings import (
    load_standings,
    save_standings,
    post_or_update_standings,
    reset_standings,
    STANDINGS_LOCK,
)


# =========================
# 🔥 NEW: SCHEDULE INTEGRATION
# =========================
SCHEDULE_FILE = Path("schedule.json")


def get_active_teams():
    if not SCHEDULE_FILE.exists():
        return None

    try:
        with open(SCHEDULE_FILE, "r") as f:
            data = json.load(f)
            return data.get("teams", None)
    except:
        return None


class Standings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /standings
    # =========================
    @app_commands.command(
        name="standings",
        description="Post or refresh the current SFG standings."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def standings_cmd(self, interaction: discord.Interaction):

        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "Server-only command.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # =========================
        # 🔥 FILTER TO ACTIVE TEAMS
        # =========================
        active_teams = get_active_teams()

        if active_teams:
            data = load_standings()

            # keep only teams in current season
            data["teams"] = {
                k: v for k, v in data["teams"].items()
                if k in active_teams
            }

            save_standings(data)

        # post/update normally
        await post_or_update_standings(guild)

        await interaction.followup.send(
            "✅ Standings updated successfully.",
            ephemeral=True
        )

    # =========================
    # /resetstandings
    # =========================
    @app_commands.command(
        name="resetstandings",
        description="Reset standings for a new season (SFG/Admin only)."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(season="Optional: set season number manually")
    async def resetstandings(
        self,
        interaction: discord.Interaction,
        season: Optional[int] = None,
    ):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "Server-only command.",
                ephemeral=True
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Permission check failed.",
                ephemeral=True
            )

        # =========================
        # 🔒 PERMISSIONS
        # =========================
        is_sfg = any(r.name.lower() == "sfg" for r in interaction.user.roles)
        perms = interaction.user.guild_permissions

        if not (is_sfg or perms.administrator or perms.manage_guild):
            return await interaction.response.send_message(
                "❌ Only **SFG** or server admins can use `/resetstandings`.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        async with STANDINGS_LOCK:
            data = load_standings()

            # preserve message ID
            msg_id = data.get("standings_message_id")

            # determine new season
            if season and season > 0:
                new_season = season
            else:
                new_season = int(data.get("season", 1)) + 1

            # reset everything
            reset_standings()

            data = load_standings()
            data["season"] = new_season
            data["standings_message_id"] = msg_id

            save_standings(data)

        await post_or_update_standings(guild)

        await interaction.followup.send(
            f"✅ Standings reset. Now starting **Season {new_season}**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Standings(bot))