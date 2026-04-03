import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.config import (
    NFL_TEAMS,
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    GUILD_ID
)

from utils.helpers import find_text_channel_fuzzy


class Appoint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /APPOINT
    # =========================
    @app_commands.command(
        name="appoint",
        description="SFG only: appoint a user as Franchise Owner of a team."
    )
    @app_commands.describe(
        user="User to appoint",
        team_role="Select the team role"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def appoint(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        team_role: discord.Role
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

        # ✅ Only SFG role
        if not any(r.name == "SFG" for r in issuer.roles):
            return await interaction.followup.send(
                "❌ Only users with the **SFG** role can use this command.",
                ephemeral=True
            )

        # ✅ Ensure valid team role
        if team_role.name not in NFL_TEAMS:
            return await interaction.followup.send(
                "❌ That role is not a valid team.",
                ephemeral=True
            )

        # 🔒 Role hierarchy check
        me = guild.me or guild.get_member(self.bot.user.id)
        if me and (team_role >= me.top_role):
            return await interaction.followup.send(
                "❌ I can’t assign that team role (move my bot role above it).",
                ephemeral=True
            )

        fo_role = discord.utils.get(guild.roles, name="Franchise Owner")
        if not fo_role:
            return await interaction.followup.send(
                "❌ Role not found: **Franchise Owner**",
                ephemeral=True
            )

        # 🔒 Check FO role hierarchy too
        if me and fo_role >= me.top_role:
            return await interaction.followup.send(
                "❌ I can’t assign the Franchise Owner role.",
                ephemeral=True
            )

        # =========================
        # ASSIGN ROLES
        # =========================
        try:
            await user.add_roles(
                fo_role,
                team_role,
                reason=f"Appointed by {issuer} as FO of {team_role.name}"
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ I can’t assign roles (check hierarchy).",
                ephemeral=True
            )

        # =========================
        # DM USER
        # =========================
        team_logo = TEAM_THUMBNAILS.get(team_role.name)

        dm_embed = discord.Embed(
            title="SFG Appointment",
            description=f"You have been appointed as **Franchise Owner** of **{team_role.name}**.",
            color=TEAM_COLORS.get(team_role.name, 0x2F3136),
            timestamp=datetime.utcnow()
        )

        if team_logo:
            dm_embed.set_thumbnail(url=team_logo)

        dm_embed.add_field(
            name="Appointed By",
            value=issuer.mention,
            inline=False
        )

        dm_embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        try:
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # =========================
        # LOG
        # =========================
        logs_channel = find_text_channel_fuzzy(guild, "logs")
        if logs_channel:
            await logs_channel.send(
                f"📋 **Franchise Owner Appointed**\n"
                f"• **User:** {user.mention}\n"
                f"• **Team:** {team_role.mention}\n"
                f"• **Appointed By:** {issuer.mention}"
            )

        # =========================
        # FINAL RESPONSE
        # =========================
        await interaction.followup.send(
            f"✅ Appointed {user.mention} as **Franchise Owner** of {team_role.mention}.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Appoint(bot))