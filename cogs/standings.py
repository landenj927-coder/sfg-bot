import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from utils.config import GUILD_ID

from utils.standings import (
    load_standings,
    save_standings,
    post_or_update_standings,
    reset_standings,
    STANDINGS_LOCK,
)


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

        # ✅ DO NOT FILTER HERE — utils handles it
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

        # 🔒 PERMISSIONS
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

            # preserve standings message
            msg_id = data.get("standings_message_id")

            # determine new season
            if season and season > 0:
                new_season = season
            else:
                new_season = int(data.get("season", 1)) + 1

            # reset standings
            reset_standings()

            data = load_standings()
            data["season"] = new_season
            data["standings_message_id"] = msg_id

            save_standings(data)

        # update message
        await post_or_update_standings(guild)

        await interaction.followup.send(
            f"✅ Standings reset. Now starting **Season {new_season}**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Standings(bot))