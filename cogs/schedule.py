import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from pathlib import Path

from utils.config import NFL_TEAMS, GUILD_ID
from utils.constants import SCHEDULE_CHANNEL_ID


SCHEDULE_FILE = Path("schedule.json")


# =========================
# LOAD / SAVE
# =========================
def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return {"season": 1, "teams": [], "weeks": {}, "messages": {}}


def save_schedule(data):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# GENERATOR
# =========================
def generate_schedule(teams, weeks=10):
    teams = teams.copy()
    random.shuffle(teams)

    schedule = {str(w): [] for w in range(1, weeks + 1)}
    matchups_played = set()

    for week in range(1, weeks + 1):
        available = teams.copy()
        random.shuffle(available)

        while len(available) >= 2:
            t1 = available.pop()
            t2 = None

            for i, opp in enumerate(available):
                matchup = tuple(sorted([t1, opp]))
                if matchup not in matchups_played:
                    t2 = opp
                    available.pop(i)
                    break

            if not t2:
                t2 = available.pop()

            matchup = tuple(sorted([t1, t2]))
            matchups_played.add(matchup)

            schedule[str(week)].append([t1, t2])

    return schedule


# =========================
# EMBED BUILDER (CLEAN AF)
# =========================
def build_week_embed(week: str, games: list):
    lines = []
    for i, (a, b) in enumerate(games, start=1):
        lines.append(f"`{i:>2}.` **{a}** vs **{b}**")

    return discord.Embed(
        title=f"📅 Week {week} Matchups",
        description="\n".join(lines),
        color=0x5865F2
    ).set_footer(text="SFG League • Official Schedule")


# =========================
# COG
# =========================
class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="genschedule", description="Generate league schedule")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.choices(
        team_count=[
            app_commands.Choice(name="16 Teams", value=16),
            app_commands.Choice(name="24 Teams", value=24),
            app_commands.Choice(name="32 Teams", value=32),
        ]
    )
    async def genschedule(self, interaction: discord.Interaction, team_count: app_commands.Choice[int]):

        guild = interaction.guild
        user = interaction.user

        # 🔒 ROLE CHECK
        if "sfg" not in [r.name.lower() for r in user.roles]:
            return await interaction.response.send_message("No permission.", ephemeral=True)

        owner_role = discord.utils.get(guild.roles, name="Franchise Owner")

        active = []
        for team in NFL_TEAMS:
            role = discord.utils.get(guild.roles, name=team)
            if role and any(owner_role in m.roles for m in role.members):
                active.append(team)

        if len(active) < team_count.value:
            return await interaction.response.send_message(
                f"Need {team_count.value} teams, only found {len(active)}",
                ephemeral=True
            )

        selected = random.sample(active, team_count.value)
        schedule = generate_schedule(selected)

        data = load_schedule()
        data["teams"] = selected
        data["weeks"] = schedule
        data.setdefault("messages", {})
        save_schedule(data)

        channel = guild.get_channel(SCHEDULE_CHANNEL_ID)

        if not channel:
            return await interaction.response.send_message(
                "Schedule channel not found.",
                ephemeral=True
            )

        # =========================
        # UPDATE / CREATE MESSAGES
        # =========================
        for week, games in schedule.items():
            embed = build_week_embed(week, games)

            msg_id = data["messages"].get(week)

            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                except:
                    msg = await channel.send(embed=embed)
                    data["messages"][week] = msg.id
            else:
                msg = await channel.send(embed=embed)
                data["messages"][week] = msg.id

        save_schedule(data)

        await interaction.response.send_message(
            "✅ Schedule updated successfully.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Schedule(bot))