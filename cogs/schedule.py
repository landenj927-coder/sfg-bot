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

            if t2 is None:
                t2 = available.pop()

            matchup = tuple(sorted([t1, t2]))
            matchups_played.add(matchup)
            schedule[str(week)].append([t1, t2])

    return schedule


# =========================
# BUILD WEEK EMBED
# =========================
def build_week_embed(week: str, games: list, data: dict):
    standings = load_standings() or {}
    teams_data = standings.get("teams", {})

    # Seed teams by wins, then point differential
    sorted_teams = sorted(
        teams_data.items(),
        key=lambda x: (
            -x[1].get("wins", 0),
            -((x[1].get("pf", 0)) - (x[1].get("pa", 0))),
            -x[1].get("pf", 0)
        )
    )
    seeds = {team: i + 1 for i, (team, _) in enumerate(sorted_teams)}

    # Default seed fallback for teams not yet in standings
    for team in data.get("teams", []):
        if team not in seeds:
            seeds[team] = len(seeds) + 1

    week_start_raw = data.get("week_start")
    if week_start_raw:
        week_start = datetime.fromisoformat(week_start_raw)
    else:
        week_start = datetime.utcnow()

    deadline_hours = data.get("deadline_hours", 48)
    deadline = week_start + timedelta(hours=deadline_hours)
    deadline_str = deadline.strftime("%B %d • %I:%M %p UTC")

    def get_record(team_name: str) -> str:
        stats = teams_data.get(team_name, {})
        return f"{stats.get('wins', 0)}-{stats.get('losses', 0)}"

    def get_pd(team_name: str) -> int:
        stats = teams_data.get(team_name, {})
        return stats.get("pf", 0) - stats.get("pa", 0)

    def matchup_score(a: str, b: str):
        seed_a = seeds.get(a, 999)
        seed_b = seeds.get(b, 999)
        pd_a = get_pd(a)
        pd_b = get_pd(b)

        # Bigger score = more hype
        return (
            -(seed_a + seed_b),     # better combined seeds first
            -(abs(pd_a) + abs(pd_b)),
            -min(seed_a, seed_b)
        )

    sorted_games = sorted(games, key=lambda g: matchup_score(g[0], g[1]))
    primetime_games = sorted_games[:3]

    primetime_set = {tuple(sorted(g)) for g in primetime_games}
    remaining_games = [
        g for g in games
        if tuple(sorted(g)) not in primetime_set
    ]

    primetime_lines = []
    for a, b in primetime_games:
        emoji_a = TEAM_EMOJIS.get(a, "")
        emoji_b = TEAM_EMOJIS.get(b, "")
        seed_a = seeds.get(a, "-")
        seed_b = seeds.get(b, "-")
        record_a = get_record(a)
        record_b = get_record(b)

        primetime_lines.append(
            f"{emoji_a} **#{seed_a} {a}** ({record_a}) vs {emoji_b} **#{seed_b} {b}** ({record_b})"
        )

    matchup_lines = []
    for i, (a, b) in enumerate(remaining_games, start=1):
        emoji_a = TEAM_EMOJIS.get(a, "")
        emoji_b = TEAM_EMOJIS.get(b, "")
        seed_a = seeds.get(a, "-")
        seed_b = seeds.get(b, "-")
        record_a = get_record(a)
        record_b = get_record(b)

        matchup_lines.append(
            f"`{i:>2}.` {emoji_a} **#{seed_a} {a}** ({record_a}) vs {emoji_b} **#{seed_b} {b}** ({record_b})"
        )

    embed = discord.Embed(
        title=f"📅 Week {week} Matchups",
        color=0x5865F2,
        timestamp=datetime.utcnow()
    )

    embed.add_field(
        name="🌟 Primetime Matchups",
        value="\n".join(primetime_lines) if primetime_lines else "*No primetime games selected.*",
        inline=False
    )

    embed.add_field(
        name="📋 Remaining Matchups",
        value="\n".join(matchup_lines) if matchup_lines else "*All games are featured as primetime this week.*",
        inline=False
    )

    embed.add_field(
        name="⏳ Deadline",
        value=f"Ends: **{deadline_str}**",
        inline=False
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
        description="Generate the season schedule"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.choices(
        team_count=[
            app_commands.Choice(name="16 Teams", value=16),
            app_commands.Choice(name="24 Teams", value=24),
            app_commands.Choice(name="32 Teams", value=32),
        ]
    )
    @app_commands.describe(
        team_count="How many active teams to use",
        deadline_hours="How many hours teams have to complete their games"
    )
    async def genschedule(
        self,
        interaction: discord.Interaction,
        team_count: app_commands.Choice[int],
        deadline_hours: app_commands.Range[int, 1, 336]
    ):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        user_role_names = [role.name.lower().strip() for role in user.roles]
        if "sfg" not in user_role_names:
            return await interaction.response.send_message(
                "You must have the SFG role to use this.",
                ephemeral=True
            )

        owner_role = discord.utils.get(guild.roles, name="Franchise Owner")
        if owner_role is None:
            return await interaction.response.send_message(
                "Franchise Owner role not found.",
                ephemeral=True
            )

        active_teams = []
        for team_name in NFL_TEAMS:
            role = discord.utils.get(guild.roles, name=team_name)
            if role is None:
                continue

            has_owner = any(owner_role in member.roles for member in role.members)
            if has_owner:
                active_teams.append(team_name)

        if len(active_teams) < team_count.value:
            return await interaction.response.send_message(
                f"Not enough active teams. Found {len(active_teams)}, need {team_count.value}.",
                ephemeral=True
            )

        selected_teams = random.sample(active_teams, team_count.value)
        schedule = generate_schedule(selected_teams, weeks=10)

        data = {
            "season": 1,
            "teams": selected_teams,
            "weeks": schedule,
            "messages": {},
            "current_week": 1,
            "played": [],
            "deadline_hours": int(deadline_hours),
            "week_start": datetime.utcnow().isoformat()
        }

        save_schedule(data)

        channel = guild.get_channel(SCHEDULE_CHANNEL_ID)
        if channel is None:
            return await interaction.response.send_message(
                "Schedule channel not found.",
                ephemeral=True
            )

        week = "1"
        embed = build_week_embed(week, schedule[week], data)
        msg = await channel.send(embed=embed)

        data["messages"][week] = msg.id
        save_schedule(data)

        await interaction.response.send_message(
            "✅ Schedule generated. Week 1 has been posted.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Schedule(bot))