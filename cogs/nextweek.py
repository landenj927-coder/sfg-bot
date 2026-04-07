import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path
from datetime import datetime

from utils.config import GUILD_ID
from utils.constants import SCHEDULE_CHANNEL_ID
from utils.standings import TEAM_EMOJIS, load_standings

from cogs.schedule import load_schedule, save_schedule, build_week_embed


class NextWeek(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nextweek", description="Advance to next week")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def nextweek(self, interaction: discord.Interaction):

        if "sfg" not in [r.name.lower() for r in interaction.user.roles]:
            return await interaction.response.send_message("No permission.", ephemeral=True)

        data = load_schedule()

        current = data.get("current_week", 1)
        next_week = current + 1

        if str(next_week) not in data["weeks"]:
            return await interaction.response.send_message("Season finished.", ephemeral=True)

        data["current_week"] = next_week
        data["week_start"] = datetime.utcnow().isoformat()

        save_schedule(data)

        channel = interaction.guild.get_channel(SCHEDULE_CHANNEL_ID)

        games = data["weeks"][str(next_week)]
        embed = build_week_embed(str(next_week), games, data)

        msg = await channel.send(embed=embed)
        data["messages"][str(next_week)] = msg.id

        save_schedule(data)

        await interaction.response.send_message(
            f"📅 Week {next_week} posted.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(NextWeek(bot))