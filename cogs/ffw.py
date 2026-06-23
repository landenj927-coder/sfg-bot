import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.config import (
    GUILD_ID,
    NFL_TEAMS,
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    SCORES_CHANNEL_ID,
)

from utils.standings import (
    STANDINGS_LOCK,
    load_standings,
    save_standings,
    post_or_update_standings,
)


class FFW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ffw",
        description="SFG only: record a forfeit win as 14-0."
    )
    @app_commands.describe(
        winning_team="Team receiving the forfeit win",
        losing_team="Team taking the forfeit loss"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ffw(
        self,
        interaction: discord.Interaction,
        winning_team: discord.Role,
        losing_team: discord.Role
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send(
                "Server-only command.",
                ephemeral=True
            )

        issuer = interaction.user
        if not isinstance(issuer, discord.Member):
            return await interaction.followup.send(
                "Couldn’t verify roles.",
                ephemeral=True
            )

        if not any(r.name == "SFG" for r in issuer.roles):
            return await interaction.followup.send(
                "❌ Only users with the **SFG** role can use this command.",
                ephemeral=True
            )

        if winning_team.name not in NFL_TEAMS:
            return await interaction.followup.send(
                "❌ The winning team role is not a valid team.",
                ephemeral=True
            )

        if losing_team.name not in NFL_TEAMS:
            return await interaction.followup.send(
                "❌ The losing team role is not a valid team.",
                ephemeral=True
            )

        if winning_team.id == losing_team.id:
            return await interaction.followup.send(
                "❌ Winning team and losing team cannot be the same.",
                ephemeral=True
            )

        winner = winning_team.name
        loser = losing_team.name

        async with STANDINGS_LOCK:
            standings = load_standings()

            if "teams" not in standings:
                standings["teams"] = {}

            for team in (winner, loser):
                if team not in standings["teams"]:
                    standings["teams"][team] = {
                        "wins": 0,
                        "losses": 0,
                        "pf": 0,
                        "pa": 0,
                    }

            standings["teams"][winner]["wins"] += 1
            standings["teams"][winner]["pf"] += 14
            standings["teams"][winner]["pa"] += 0

            standings["teams"][loser]["losses"] += 1
            standings["teams"][loser]["pf"] += 0
            standings["teams"][loser]["pa"] += 14

            save_standings(standings)

        try:
            await post_or_update_standings(guild)
        except Exception as e:
            print(f"Standings update failed after /ffw: {type(e).__name__}: {e}")

        scores_channel = guild.get_channel(SCORES_CHANNEL_ID)

        team_logo = TEAM_THUMBNAILS.get(winner)

        embed = discord.Embed(
            title="Forfeit Win Recorded",
            description=(
                f"{winning_team.mention} defeats {losing_team.mention}\n\n"
                f"**Final Score:** `{winner} 14 - 0 {loser}`\n"
                f"**Reason:** Forfeit Loss"
            ),
            color=TEAM_COLORS.get(winner, 0x2F3136),
            timestamp=datetime.utcnow()
        )

        if team_logo:
            embed.set_thumbnail(url=team_logo)
        elif SFG_LOGO_URL:
            embed.set_thumbnail(url=SFG_LOGO_URL)

        embed.add_field(
            name="Recorded By",
            value=issuer.mention,
            inline=False
        )

        embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        if isinstance(scores_channel, discord.TextChannel):
            await scores_channel.send(embed=embed)

        await interaction.followup.send(
            f"✅ Forfeit win recorded: **{winner} 14 - 0 {loser}**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(FFW(bot))