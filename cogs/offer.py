import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.config import (
    NFL_TEAMS,
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    GUILD_ID
)
from utils.views import OfferView


class Offer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="offer",
        description="Offer a player to join your team."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))  # 🔥 instant register
    @app_commands.describe(user="The player you are offering a spot to")
    async def offer(self, interaction: discord.Interaction, user: discord.Member):

        # 🔥 prevents "application did not respond"
        await interaction.response.defer(ephemeral=True)

        author = interaction.user
        guild = interaction.guild

        if guild is None:
            return await interaction.followup.send(
                "Server only command.",
                ephemeral=True
            )

        # 🔒 Check coach role
        coach_team = next(
            (r.name for r in author.roles if r.name in NFL_TEAMS),
            None
        )

        if not coach_team:
            return await interaction.followup.send(
                "You do not have a coach role.",
                ephemeral=True
            )

        # 🔒 Get team role
        team_role = discord.utils.get(guild.roles, name=coach_team)

        if not team_role:
            return await interaction.followup.send(
                "Team role not found on server.",
                ephemeral=True
            )

        # 🔒 Check if player already signed
        for t in NFL_TEAMS:
            role = discord.utils.get(guild.roles, name=t)
            if role and role in user.roles:
                return await interaction.followup.send(
                    "Cant send offer, player is already signed.",
                    ephemeral=True
                )

        # 🎨 Embed
        color = TEAM_COLORS.get(coach_team, 0x2F3136)
        thumb_url = TEAM_THUMBNAILS.get(coach_team)

        embed = discord.Embed(
            title="Offer Received",
            description=(
                f"{user.mention}, you have received an offer from {author.mention} "
                f"to join **{coach_team}**.\n\n"
                "Use the buttons below to accept or decline."
            ),
            color=color,
            timestamp=datetime.utcnow()
        )

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        # 🧠 Buttons
        view = OfferView(team_role, user, author)

        # 📩 Send DM
        try:
            await user.send(embed=embed, view=view)

            await interaction.followup.send(
                f"Offer has been sent to {user.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                f"Could not DM {user.mention}. They may have DMs disabled.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Offer(bot))