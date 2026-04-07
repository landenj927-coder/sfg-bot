import discord
from discord.ext import commands
from discord import app_commands
import json
import random

from utils.config import NFL_TEAMS, GUILD_ID


# 🔥 SCHEDULE GENERATOR
def generate_schedule(teams, weeks=10):
    teams = teams.copy()
    random.shuffle(teams)

    schedule = {str(week): [] for week in range(1, weeks + 1)}
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


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="genschedule",
        description="Generate league schedule (SFG only)"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))  # 🔥 THIS IS WHY IT WILL SHOW
    @app_commands.describe(team_count="Number of teams for the season")
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

        # 🔒 SFG ROLE CHECK
        sfg_role = discord.utils.get(guild.roles, name="SFG")
        if not sfg_role or sfg_role not in user.roles:
            return await interaction.response.send_message(
                "You must have the SFG role to use this.",
                ephemeral=True
            )

        # 🔍 FIND ACTIVE TEAMS (WITH OWNER)
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

        # 🎯 SELECT RANDOM TEAMS
        selected_teams = random.sample(active_teams, team_count.value)

        # 🧠 GENERATE SCHEDULE
        schedule = generate_schedule(selected_teams, weeks=10)

        data = {
            "season": 1,
            "teams": selected_teams,
            "weeks": schedule
        }

        with open("schedule.json", "w") as f:
            json.dump(data, f, indent=4)

        # 📢 PUBLIC MESSAGE (NOT EPHEMERAL)
        await interaction.response.send_message(
            f"🏈 **SFG SEASON SCHEDULE GENERATED**\n"
            f"Teams: {team_count.value}\n"
            f"Weeks: 10\n"
            f"Active Teams Used: {len(selected_teams)}"
        )


async def setup(bot):
    await bot.add_cog(Schedule(bot))