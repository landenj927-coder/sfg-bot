import discord
from discord import app_commands
from discord.ext import commands
import json

from utils.config import GUILD_ID
from utils.standings import update_game_result, post_or_update_standings

from stats_sheet import (
    append_qb_statline,
    append_wr_statline,
    append_db_statline,
    append_de_statline,
    update_playerstats_top15,
)


class GameReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /gamereport
    # =========================
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

        # =========================
        # TEAM VALIDATION
        # =========================
        team1_name = team1.name
        team2_name = team2.name

        if team1_name == team2_name:
            return await interaction.followup.send(
                "❌ A team cannot play itself.",
                ephemeral=True
            )

        # =========================
        # JSON PARSE (SAFE)
        # =========================
        try:
            raw = await json_file.read()

            text = raw.decode("utf-8", errors="ignore")

            # 🔥 FIX: find first JSON object
            start = text.find("{")

            if start == -1:
                raise ValueError("No JSON object found in file.")

            clean_json = text[start:]  # remove "50 - 14 /// "

            game_data = json.loads(clean_json)

        except Exception as e:
            return await interaction.followup.send(
                f"❌ Invalid JSON file.\n`{e}`",
                ephemeral=True
            )
            # =========================
            # UPDATE STANDINGS
            # =========================
            update_game_result(team1_name, team2_name, score1, score2)
            await post_or_update_standings(guild)

            # =========================
            # PROCESS PLAYER STATS
            # =========================
            processed_players = set()

            for player in game_data.get("players", []):
                qb = player.get("qb", {})
                wr = player.get("wr", {})
                db = player.get("db", {})
                de = player.get("def", {})

                # 🔥 NAME RESOLUTION (IMPORTANT)
                name = (
                    player.get("display")
                    or player.get("name")
                    or player.get("username")
                    or str(player.get("id"))
                )

                if not name:
                    continue

                # prevent duplicates in same report
                if name in processed_players:
                    continue
                processed_players.add(name)

                # 🔥 TEAM DETECTION (basic for now)
                team_name = "Free Agent"

                # QB
                if qb.get("yds", 0) > 0:
                    append_qb_statline(name, team_name, qb)

                # WR
                if wr.get("yds", 0) > 0:
                    append_wr_statline(name, team_name, wr)

                # DB
                if db.get("int", 0) > 0 or db.get("defl", 0) > 0:
                    append_db_statline(name, team_name, db)

                # DE
                if de.get("sack", 0) > 0:
                    append_de_statline(name, team_name, de)

            # =========================
            # UPDATE LEADERBOARD
            # =========================
            update_playerstats_top15()

            # =========================
            # POST TO SCORES CHANNEL
            # =========================
            scores_channel = discord.utils.get(guild.channels, name="scores")

            winner = team1_name if score1 > score2 else team2_name

            embed = discord.Embed(
                title="🏈 Matchup Report",
                description=f"{team1.mention} **{score1}** 🏆\n{team2.mention} **{score2}**",
                color=discord.Color.green()
            )

            embed.add_field(name="Status", value="✅ FINALIZED", inline=False)

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