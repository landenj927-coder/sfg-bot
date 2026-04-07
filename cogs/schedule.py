import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

from utils.config import NFL_TEAMS, GUILD_ID
from utils.constants import SCHEDULE_CHANNEL_ID
from utils.standings import TEAM_EMOJIS, load_standings


SCHEDULE_FILE = Path("schedule.json")


def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return None


def save_schedule(data):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=4)


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


def build_week_embed(week: str, games: list, data: dict):
    standings = load_standings()
    team_stats = standings.get("teams", {})

    week_start = datetime.fromisoformat(data.get("week_start"))
    deadline_hours = data.get("deadline_hours", 48)
    deadline = week_start + timedelta(hours=deadline_hours)

    deadline_str = deadline.strftime("%B %d • %I:%M %p UTC")

    lines = []

    for i, (a, b) in enumerate(games, start=1):
        emoji_a = TEAM_EMOJIS.get(a, "")
        emoji_b = TEAM_EMOJIS.get(b, "")

        rec_a = team_stats.get(a, {})
        rec_b = team_stats.get(b, {})

        record_a = f"{rec_a.get('wins',0)}-{rec_a.get('losses',0)}"
        record_b = f"{rec_b.get('wins',0)}-{rec_b.get('losses',0)}"

        lines.append(
            f"`{i:>2}.` {emoji_a} **{a}** ({record_a}) vs {emoji_b} **{b}** ({record_b})"
        )

    embed = discord.Embed(
        title=f"📅 Week {week} Matchups",
        description="\n".join(lines),
        color=0x5865F2
    )

    embed.add_field(
        name="⏳ Deadline",
        value=f"Ends: **{deadline_str}**",
        inline=False
    )

    embed.set_footer(text="SFG League • Official Schedule")

    return embed


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="genschedule", description="Generate schedule")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.choices(
        team_count=[
            app_commands.Choice(name="16 Teams", value=16),
            app_commands.Choice(name="24 Teams", value=24),
            app_commands.Choice(name="32 Teams", value=32),
        ]
    )
    @app_commands.describe(
        team_count="Number of teams",
        deadline_hours="Hours teams have to play games"
    )
    async def genschedule(self, interaction: discord.Interaction, team_count: app_commands.Choice[int], deadline_hours: int):

        guild = interaction.guild
        user = interaction.user

        if "sfg" not in [r.name.lower() for r in user.roles]:
            return await interaction.response.send_message("No permission.", ephemeral=True)

        owner_role = discord.utils.get(guild.roles, name="Franchise Owner")

        active = []
        for team in NFL_TEAMS:
            role = discord.utils.get(guild.roles, name=team)
            if role and any(owner_role in m.roles for m in role.members):
                active.append(team)

        selected = random.sample(active, team_count.value)
        schedule = generate_schedule(selected)

        data = {
            "season": 1,
            "teams": selected,
            "weeks": schedule,
            "messages": {},
            "current_week": 1,
            "played": [],
            "deadline_hours": deadline_hours,
            "week_start": datetime.utcnow().isoformat()
        }

        save_schedule(data)

        channel = guild.get_channel(SCHEDULE_CHANNEL_ID)

        games = schedule["1"]
        embed = build_week_embed("1", games, data)

        msg = await channel.send(embed=embed)
        data["messages"]["1"] = msg.id
        save_schedule(data)

        await interaction.response.send_message("✅ Week 1 posted.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Schedule(bot))