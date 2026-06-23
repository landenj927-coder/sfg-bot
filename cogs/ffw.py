import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.config import (
    GUILD_ID,
    NFL_TEAMS,
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    TEAM_EMOJI_NAME,
    SFG_LOGO_URL,
    SCORES_CHANNEL_ID,
)

from utils.standings import (
    update_game_result,
    post_or_update_standings,
)


def normalize_team_name(name: str) -> str:
    return (
        name.replace(" ", "")
            .replace(".", "")
            .replace("-", "")
            .lower()
    )


def get_team_emoji(guild: discord.Guild, team_name: str) -> str:
    if not guild:
        return ""

    emoji_name = TEAM_EMOJI_NAME.get(team_name)
    if not emoji_name:
        return ""

    normalized_lookup = normalize_team_name(emoji_name)

    for emoji in guild.emojis:
        if normalize_team_name(emoji.name) == normalized_lookup:
            return str(emoji)

    return ""


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
            return await interaction.followup.send("Server-only command.", ephemeral=True)

        issuer = interaction.user
        if not isinstance(issuer, discord.Member):
            return await interaction.followup.send("Couldn’t verify roles.", ephemeral=True)

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

        try:
            update_game_result(winner, loser, 14, 0)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Failed to update standings.\n```{type(e).__name__}: {e}```",
                ephemeral=True
            )

        try:
            await post_or_update_standings(guild)
        except Exception as e:
            print(f"Standings update failed after /ffw: {type(e).__name__}: {e}")

        scores_channel = guild.get_channel(SCORES_CHANNEL_ID)

        winner_emoji = get_team_emoji(guild, winner)
        loser_emoji = get_team_emoji(guild, loser)

        team_logo = TEAM_THUMBNAILS.get(winner)

        embed = discord.Embed(
            title="🏳️ Official Forfeit Ruling",
            description=(
                f"### {winner_emoji} {winning_team.mention}\n"
                f"**Wins by Forfeit**\n\n"
                f"### {loser_emoji} {losing_team.mention}\n"
                f"**Receives a Forfeit Loss**"
            ),
            color=TEAM_COLORS.get(winner, 0x2F3136),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Final Score",
            value=f"🏈 **{winner} 14 - 0 {loser}**",
            inline=False
        )

        embed.add_field(
            name="Result",
            value=(
                f"{winner_emoji} {winning_team.mention} awarded a win.\n"
                f"{loser_emoji} {losing_team.mention} recorded a forfeit loss."
            ),
            inline=False
        )

        embed.add_field(
            name="Recorded By",
            value=issuer.mention,
            inline=False
        )

        if team_logo:
            embed.set_thumbnail(url=team_logo)
        elif SFG_LOGO_URL:
            embed.set_thumbnail(url=SFG_LOGO_URL)

        embed.set_footer(
            text="SFG League Operations",
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