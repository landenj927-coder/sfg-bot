import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from pathlib import Path

from utils.config import NFL_TEAMS, GUILD_ID
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
    return {
        "season": 1,
        "teams": [],
        "weeks": {},
        "messages": {},
        "current_week": 1
    }


def save_schedule(data):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# GENERATE SCHEDULE
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
# EMBED BUILDER
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
class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="genschedule",
        description="Generate league schedule (SFG only)"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.choices(
        team_count=[
            app_commands.Choice(name="16 Teams", value=16),
            app_commands.Choice(name="24 Teams", value=24),
            app_commands.Choice(name="32 Teams", value=32),
        ]
    )
    async def genschedule(
        self,
        interaction: discord.Interaction,
        team_count: app_commands.Choice[int]
    ):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
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

        # 🔍 FIND ACTIVE TEAMS
        owner_role = discord.utils.get(guild.roles, name="Franchise Owner")

        active_teams = []
        for team_name in NFL_TEAMS:
            role = discord.utils.get(guild.roles, name=team_name)
            if not role:
                continue

            has_owner = any(owner_role in m.roles for m in role.members)
            if has_owner:
                active_teams.append(team_name)

        if len(active_teams) < team_count.value:
            return await interaction.response.send_message(
                f"Not enough active teams. Found {len(active_teams)}, need {team_count.value}.",
                ephemeral=True
            )

        # 🎯 SELECT TEAMS
        selected_teams = random.sample(active_teams, team_count.value)

        # 🧠 GENERATE SCHEDULE
        schedule = generate_schedule(selected_teams, weeks=10)

        # =========================
        # SAVE DATA
        # =========================
        data = {
            "season": 1,
            "teams": selected_teams,
            "weeks": schedule,
            "messages": {},
            "current_week": 1,
            "played": []
        }

        save_schedule(data)

        # =========================
        # POST ONLY WEEK 1
        # =========================
        channel = guild.get_channel(SCHEDULE_CHANNEL_ID)

        if not channel:
            return await interaction.response.send_message(
                "Schedule channel not found.",
                ephemeral=True
            )

        week = "1"
        games = schedule[week]

        embed = build_week_embed(week, games)

        msg = await channel.send(embed=embed)

        data["messages"][week] = msg.id
        save_schedule(data)

        # =========================
        # RESPONSE
        # =========================
        await interaction.response.send_message(
            "✅ Schedule generated. Week 1 has been posted.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Schedule(bot))