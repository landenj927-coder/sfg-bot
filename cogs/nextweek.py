import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path

from utils.config import GUILD_ID
from utils.constants import SCHEDULE_CHANNEL_ID
from utils.standings import TEAM_EMOJIS


SCHEDULE_FILE = Path("schedule.json")


# =========================
# LOAD / SAVE
# =========================
def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return None


def save_schedule(data):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# EMBED BUILDER (same as schedule)
# =========================
def build_week_embed(week: str, games: list):
    lines = []

    for i, (a, b) in enumerate(games, start=1):
        emoji_a = TEAM_EMOJIS.get(a, "")
        emoji_b = TEAM_EMOJIS.get(b, "")

        lines.append(
            f"`{i:>2}.` {emoji_a} **{a}** vs {emoji_b} **{b}**"
        )

    embed = discord.Embed(
        title=f"📅 Week {week} Matchups",
        description="\n".join(lines),
        color=0x5865F2
    )

    embed.set_footer(text="SFG League • Official Schedule")

    return embed


# =========================
# COG
# =========================
class NextWeek(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="nextweek",
        description="Advance to the next week (SFG only)"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def nextweek(self, interaction: discord.Interaction):

        guild = interaction.guild
        user = interaction.user

        if not guild:
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        # 🔒 ROLE CHECK
        if "sfg" not in [r.name.lower().strip() for r in user.roles]:
            return await interaction.response.send_message(
                "You must have the SFG role to use this.",
                ephemeral=True
            )

        data = load_schedule()

        if not data:
            return await interaction.response.send_message(
                "No schedule found. Run /genschedule first.",
                ephemeral=True
            )

        current_week = data.get("current_week", 1)
        next_week = current_week + 1

        if str(next_week) not in data["weeks"]:
            return await interaction.response.send_message(
                "Season is already finished.",
                ephemeral=True
            )

        # =========================
        # UPDATE WEEK
        # =========================
        data["current_week"] = next_week
        save_schedule(data)

        # =========================
        # POST NEXT WEEK
        # =========================
        channel = guild.get_channel(SCHEDULE_CHANNEL_ID)

        if not channel:
            return await interaction.response.send_message(
                "Schedule channel not found.",
                ephemeral=True
            )

        games = data["weeks"][str(next_week)]
        embed = build_week_embed(str(next_week), games)

        msg = await channel.send(embed=embed)

        data["messages"][str(next_week)] = msg.id
        save_schedule(data)

        # =========================
        # RESPONSE
        # =========================
        await interaction.response.send_message(
            f"📅 Week {next_week} has been posted.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(NextWeek(bot))