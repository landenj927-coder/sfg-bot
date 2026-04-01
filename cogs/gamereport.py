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
)

SCORES_CHANNEL_ID = 123456789012345678  # 🔥 PUT YOUR CHANNEL ID HERE

NFL_TEAMS = [
    "Arizona","Atlanta","Baltimore","Buffalo","Carolina","Chicago","Cincinnati","Cleveland",
    "Dallas","Denver","Detroit","GreenBay","Houston","Indianapolis","Jacksonville","Chiefs",
    "LasVegas","Rams","Chargers","Miami","Minnesota","Patriots","Saints","Giants","Jets",
    "Philadelphia","Pittsburgh","49ers","Seattle","Tampa","Tennessee","Washington"
]


class GameReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="gamereport",
        description="Submit full game report (stats + standings)."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
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

        if team1_name not in NFL_TEAMS or team2_name not in NFL_TEAMS:
            return await interaction.followup.send(
                "❌ Invalid team roles.",
                ephemeral=True
            )

        if team1_name == team2_name:
            return await interaction.followup.send(
                "❌ A team cannot play itself.",
                ephemeral=True
            )

        try:
            # =========================
            # UPDATE STANDINGS
            # =========================
            update_game_result(team1_name, team2_name, score1, score2)
            await post_or_update_standings(guild)

            # =========================
            # PARSE JSON (FIXED)
            # =========================
            raw = await json_file.read()
            text = raw.decode("utf-8")

            try:
                game_data = json.loads(text)
            except:
                start = text.find("{")
                end = text.rfind("}") + 1
                game_data = json.loads(text[start:end])

            # =========================
            # 🔥 STAT LOOP (NEW)
            # =========================
            for player in game_data.get("players", []):
                rid = player.get("roblox_id")

                qb = player.get("qb", {})
                wr = player.get("wr", {})
                db = player.get("db", {})
                de = player.get("def", {})

                name = player.get("display", "Unknown")

                # TEMP TEAM (we upgrade with bloxlink next)
                team = "Free Agent"

                if qb.get("yds", 0) > 0:
                    append_qb_statline(name, team, qb)

                if wr.get("yds", 0) > 0:
                    append_wr_statline(name, team, wr)

                if db.get("int", 0) > 0:
                    append_db_statline(name, team, db)

                if de.get("sack", 0) > 0:
                    append_de_statline(name, team, de)
                
            update_playerstats_top15()

            # =========================
            # POST TO SCORES
            # =========================
            scores_channel = guild.get_channel(SCORES_CHANNEL_ID)
            if scores_channel is None:
                scores_channel = await guild.fetch_channel(SCORES_CHANNEL_ID)

            winner1 = score1 > score2
            winner2 = score2 > score1

            embed = discord.Embed(
                title="🏈 SFG Matchup Report",
                description=(
                    f"{team1.mention} **{score1}** {'🏆' if winner1 else ''}\n"
                    f"{team2.mention} **{score2}** {'🏆' if winner2 else ''}"
                ),
                color=discord.Color.green()
            )

            embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━", value=" ", inline=False)

            embed.add_field(
                name="📊 Game Info",
                value=f"Winner: {(team1 if winner1 else team2).mention}\nMargin: {abs(score1-score2)} pts",
                inline=False
            )

            embed.add_field(name="Status", value="🟢 FINAL", inline=True)

            embed.set_footer(
                text=f"Submitted by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

            embed.timestamp = discord.utils.utcnow()

            files = [
                await qb_stats.to_file(),
                await wr_stats.to_file(),
                await cb_stats.to_file(),
                await de_stats.to_file(),
            ]

            await scores_channel.send(embed=embed, files=files)

        except Exception as e:
            return await interaction.followup.send(
                f"❌ Error:\n{e}",
                ephemeral=True
            )

        await interaction.followup.send(
            "✅ Game report processed.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(GameReport(bot))

from stats_sheet import update_playerstats_top15