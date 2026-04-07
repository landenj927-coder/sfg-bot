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

            if not t2:
                t2 = available.pop()

            matchup = tuple(sorted([t1, t2]))
            matchups_played.add(matchup)

            schedule[str(week)].append([t1, t2])

    return schedule


# =========================
# EMBED BUILDER
# =========================
def build_week_embed(week: str, games: list, data: dict):
    standings = load_standings()
    teams_data = standings.get("teams", {})

    # 🏆 SEEDS
    sorted_teams = sorted(
        teams_data.items(),
        key=lambda x: (
            -x[1].get("wins", 0),
            -(x[1].get("pf", 0) - x[1].get("pa", 0))
        )
    )

    seeds = {team: i + 1 for i, (team, _) in enumerate(sorted_teams)}

    # ⏳ DEADLINE
    week_start = datetime.fromisoformat(data.get("week_start"))
    deadline = week_start + timedelta(hours=data.get("deadline_hours", 48))
    deadline_str = deadline.strftime("%B %d • %I:%M %p UTC")

    # 🔥 MATCHUP SCORING
    def matchup_score(a, b):
        seed_a = seeds.get(a, 99)
        seed_b = seeds.get(b, 99)

        rec_a = teams_data.get(a, {})
        rec_b = teams_data.get(b, {})

        pd_a = rec_a.get("pf", 0) - rec_a.get("pa", 0)
        pd_b = rec_b.get("pf", 0) - rec_b.get("pa", 0)

        return (-min(seed_a, seed_b), -(pd_a + pd_b))

    sorted_games = sorted(games, key=lambda g: matchup_score(g[0], g[1]))
    primetime_games = sorted_games[:3]

    # 🌟 PRIMETIME
    primetime_lines = []
    for a, b in primetime_games:
        emoji_a = TEAM_EMOJIS.get(a, "")
        emoji_b = TEAM_EMOJIS.get(b, "")

        seed_a = seeds.get(a, "-")
        seed_b = seeds.get(b, "-")

        rec_a = teams_data.get(a, {})
        rec_b = teams_data.get(b, {})

        record_a = f"{rec_a.get('wins',0)}-{rec_a.get('losses',0)}"
        record_b = f"{rec_b.get('wins',0)}-{rec_b.get('losses',0)}"

        primetime_lines.append(
            f"🌟 {emoji_a} **#{seed_a} {a}** ({record_a}) vs {emoji_b} **#{seed_b} {b}** ({record_b})"
        )

    # 📋 ALL GAMES
    lines = []
    for i, (a, b) in enumerate(games, start=1):
        emoji_a = TEAM_EMOJIS.get(a, "")
        emoji_b = TEAM_EMOJIS.get(b, "")

        seed_a = seeds.get(a, "-")
        seed_b = seeds.get(b, "-")

        rec_a = teams_data.get(a, {})
        rec_b = teams_data.get(b, {})

        record_a = f"{rec_a.get('wins',0)}-{rec_a.get('losses',0)}"
        record_b = f"{rec_b.get('wins',0)}-{rec_b.get('losses',0)}"

        lines.append(
            f"`{i:>2}.` {emoji_a} **#{seed_a} {a}** ({record_a}) vs {emoji_b} **#{seed_b} {b}** ({record_b})"
        )

    embed = discord.Embed(
        title=f"📅 Week {week} Matchups",
        description="\n".join(lines),
        color=0x5865F2
    )

    embed.add_field(
        name="🌟 Primetime Matchups",
        value="\n".join(primetime_lines),
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

    @app_commands.command(name="genschedule", description="Generate league schedule")
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
        deadline_hours="Hours to complete games"
    )
    async def genschedule(
        self,
        interaction: discord.Interaction,
        team_count: app_commands.Choice[int],
        deadline_hours: int
    ):
        guild = interaction.guild
        user = interaction.user

        if "sfg" not in [r.name.lower() for r in user.roles]:
            return await interaction.response.send_message(
                "No permission.",
                ephemeral=True
            )

        owner_role = discord.utils.get(guild.roles, name="Franchise Owner")

        active = []
        for team in NFL_TEAMS:
            role = discord.utils.get(guild.roles, name=team)
            if role and any(owner_role in m.roles for m in role.members):
                active.append(team)

        if len(active) < team_count.value:
            return await interaction.response.send_message(
                "Not enough active teams.",
                ephemeral=True
            )

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

        embed = build_week_embed("1", schedule["1"], data)
        msg = await channel.send(embed=embed)

        data["messages"]["1"] = msg.id
        save_schedule(data)

        await interaction.response.send_message(
            "✅ Schedule generated. Week 1 posted.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Schedule(bot))