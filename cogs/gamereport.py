import discord
from discord import app_commands
from discord.ext import commands
import json
from pathlib import Path

from utils.config import GUILD_ID
from utils.standings import update_game_result, post_or_update_standings

from services.stats_sheet import (
    append_qb_statline,
    append_wr_statline,
    append_db_statline,
    append_de_statline,
    commit_all_stats,
)


# =========================
# SCHEDULE FILE
# =========================
SCHEDULE_FILE = Path("schedule.json")


def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return None


def is_valid_game(team_a, team_b):
    data = load_schedule()
    if not data:
        return False

    for games in data["weeks"].values():
        for a, b in games:
            if {a, b} == {team_a, team_b}:
                return True
    return False


def already_played(team_a, team_b):
    data = load_schedule()
    if not data:
        return False

    played = data.setdefault("played", [])

    matchup = tuple(sorted([team_a, team_b]))
    return matchup in played


def mark_played(team_a, team_b):
    data = load_schedule()
    if not data:
        return

    played = data.setdefault("played", [])

    matchup = tuple(sorted([team_a, team_b]))

    if matchup not in played:
        played.append(matchup)

    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=4)


class GameReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="gamereport",
        description="Submit full game report (stats + standings)."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        team1="Select first team",
        team2="Select second team",
        score1="Score for team1",
        score2="Score for team2",
        json_file="Football Fusion export",
        qb_stats="QB stats image",
        wr_stats="WR stats image",
        cb_stats="CB stats image",
        de_stats="DE stats image",
    )
    async def gamereport(
        self,
        interaction: discord.Interaction,
        team1: discord.Role,
        team2: discord.Role,
        score1: int,
        score2: int,
        json_file: discord.Attachment,
        qb_stats: discord.Attachment,
        wr_stats: discord.Attachment,
        cb_stats: discord.Attachment,
        de_stats: discord.Attachment,
    ):
        guild = interaction.guild

        if not guild:
            return await interaction.response.send_message(
                "Server-only command.",
                ephemeral=True
            )

        await interaction.response.defer()

        team1_name = team1.name
        team2_name = team2.name

        if team1_name == team2_name:
            return await interaction.followup.send(
                "❌ A team cannot play itself.",
                ephemeral=True
            )

        # =========================
        # 🔥 SCHEDULE VALIDATION
        # =========================
        if not is_valid_game(team1_name, team2_name):
            return await interaction.followup.send(
                "❌ This matchup is not on the schedule.",
                ephemeral=True
            )

        if already_played(team1_name, team2_name):
            return await interaction.followup.send(
                "❌ This game has already been reported.",
                ephemeral=True
            )

        # =========================
        # JSON PARSE
        # =========================
        try:
            raw = await json_file.read()
            text = raw.decode("utf-8", errors="ignore")

            start = text.find("{")
            if start == -1:
                raise ValueError("No JSON found.")

            game_data = json.loads(text[start:])

        except Exception as e:
            return await interaction.followup.send(
                f"❌ Invalid JSON file.\n`{e}`",
                ephemeral=True
            )

        try:
            # =========================
            # UPDATE STANDINGS
            # =========================
            update_game_result(team1_name, team2_name, score1, score2)
            await post_or_update_standings(guild)

            # =========================
            # PROCESS STATS
            # =========================
            for player in game_data.values():

                qb = player.get("qb", {})
                wr = player.get("wr", {})
                db = player.get("db", {})
                de = player.get("def", {})
                other = player.get("other", {})

                name = (
                    other.get("display")
                    or other.get("name")
                    or "Unknown"
                )

                team_name = other.get("team", "Free Agent")

                if qb.get("yds", 0) > 0:
                    append_qb_statline(
                        name, team_name,
                        qb.get("qbr", qb.get("rtng", 0)),
                        qb.get("comp", 0),
                        qb.get("yds", 0),
                        qb.get("td", 0),
                        qb.get("int", qb.get("ints", 0))
                    )

                if wr.get("yds", 0) > 0:
                    append_wr_statline(
                        name, team_name,
                        wr.get("rec", 0),
                        wr.get("yds", 0),
                        wr.get("td", 0),
                        wr.get("fum", 0)
                    )

                if db.get("int", 0) > 0 or db.get("defl", 0) > 0:
                    append_db_statline(
                        name, team_name,
                        db.get("defl", 0),
                        db.get("int", 0),
                        db.get("rtng", 0)
                    )

                if de.get("sack", 0) > 0:
                    append_de_statline(
                        name, team_name,
                        de.get("sack", 0),
                        de.get("safe", 0),
                        de.get("ffum", 0)
                    )

            commit_all_stats()

            # =========================
            # MARK GAME AS PLAYED
            # =========================
            mark_played(team1_name, team2_name)

            # =========================
            # POST RESULT
            # =========================
            SCORES_CHANNEL_ID = 1488381961301917807
            scores_channel = guild.get_channel(SCORES_CHANNEL_ID)

            winner = team1_name if score1 > score2 else team2_name

            embed = discord.Embed(
                title="🏈 Matchup Report",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Game Result",
                value=(
                    f"{team1.mention} **{score1}**\n"
                    f"{team2.mention} **{score2}**\n\n"
                    f"🏆 Winner: **{winner}**"
                ),
                inline=False
            )

            embed.add_field(
                name="Status",
                value="✅ FINALIZED",
                inline=False
            )

            embed.set_footer(
                text=f"Submitted by {interaction.user.display_name}"
            )

            files = [
                await qb_stats.to_file(),
                await wr_stats.to_file(),
                await cb_stats.to_file(),
                await de_stats.to_file(),
            ]

            if scores_channel:
                await scores_channel.send(embed=embed, files=files)

        except Exception as e:
            return await interaction.followup.send(
                f"❌ Error:\n`{e}`",
                ephemeral=True
            )

        await interaction.followup.send(
            "✅ Game report processed successfully.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(GameReport(bot))