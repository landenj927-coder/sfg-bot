import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

from utils.config import GUILD_ID
from utils.constants import SCHEDULE_CHANNEL_ID
from utils.standings import TEAM_EMOJIS, load_standings
from cogs.schedule import load_schedule, save_schedule


def get_schedule_teams(schedule_data: dict) -> list[str]:
    teams = []

    for games in schedule_data.get("weeks", {}).values():
        for a, b in games:
            if a not in teams:
                teams.append(a)
            if b not in teams:
                teams.append(b)

    return teams


def get_stats(team: str, standings: dict) -> dict:
    return standings.get("teams", {}).get(team, {
        "wins": 0,
        "losses": 0,
        "pf": 0,
        "pa": 0,
        "streak": 0
    })


def win_pct(stats: dict) -> float:
    wins = int(stats.get("wins", 0))
    losses = int(stats.get("losses", 0))
    games = wins + losses
    return wins / games if games > 0 else 0.0


def point_diff(stats: dict) -> int:
    return int(stats.get("pf", 0)) - int(stats.get("pa", 0))


def get_seed_map(schedule_data: dict) -> dict[str, int]:
    standings = load_standings()
    season_teams = get_schedule_teams(schedule_data)

    ranked = sorted(
        season_teams,
        key=lambda team: (
            win_pct(get_stats(team, standings)),
            point_diff(get_stats(team, standings)),
            int(get_stats(team, standings).get("wins", 0)),
        ),
        reverse=True
    )

    return {team: i + 1 for i, team in enumerate(ranked)}


def get_record(team: str) -> str:
    standings = load_standings()
    stats = get_stats(team, standings)

    wins = int(stats.get("wins", 0))
    losses = int(stats.get("losses", 0))

    return f"{wins}-{losses}"


def team_display(team: str, seed_map: dict[str, int]) -> str:
    emoji = TEAM_EMOJIS.get(team, "🏈")
    seed = seed_map.get(team, "?")
    record = get_record(team)

    return f"{emoji} **#{seed} {team}** ({record})"


def build_nextweek_embed(week: str, games: list, data: dict) -> discord.Embed:
    seed_map = get_seed_map(data)

    embed = discord.Embed(
        title=f"📅 Week {week} Matchups",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="☀️ Primetime Matchups",
        value="\n".join(
            f"{team_display(a, seed_map)} vs {team_display(b, seed_map)}"
            for a, b in games[:3]
        ) or "No primetime matchups.",
        inline=False
    )

    remaining_lines = []
    for i, (a, b) in enumerate(games[3:], start=1):
        remaining_lines.append(
            f"`{i}.` {team_display(a, seed_map)} vs {team_display(b, seed_map)}"
        )

    embed.add_field(
        name="📋 Remaining Matchups",
        value="\n".join(remaining_lines) or "No remaining matchups.",
        inline=False
    )

    deadline_hours = int(data.get("deadline_hours", 48))
    week_start = datetime.fromisoformat(data["week_start"])
    deadline = week_start + timedelta(hours=deadline_hours)

    embed.add_field(
        name="🏆 Deadline",
        value=f"Ends: <t:{int(deadline.timestamp())}:F>",
        inline=False
    )

    embed.set_footer(
        text=f"SFG League • Official Schedule • Week {week}"
    )

    return embed


class NextWeek(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nextweek", description="Advance to next week")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def nextweek(self, interaction: discord.Interaction):

        if "sfg" not in [r.name.lower() for r in interaction.user.roles]:
            return await interaction.response.send_message("No permission.", ephemeral=True)

        data = load_schedule()

        current = int(data.get("current_week", 1))
        next_week = current + 1

        if str(next_week) not in data["weeks"]:
            return await interaction.response.send_message("Season finished.", ephemeral=True)

        data["current_week"] = next_week
        data["week_start"] = datetime.utcnow().isoformat()

        save_schedule(data)

        channel = interaction.guild.get_channel(SCHEDULE_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Schedule channel not found.",
                ephemeral=True
            )

        games = data["weeks"][str(next_week)]
        embed = build_nextweek_embed(str(next_week), games, data)

        msg = await channel.send(embed=embed)

        data.setdefault("messages", {})
        data["messages"][str(next_week)] = msg.id

        save_schedule(data)

        await interaction.response.send_message(
            f"📅 Week {next_week} posted.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(NextWeek(bot))