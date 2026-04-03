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

from utils.helpers import (
    get_team_role,
    find_text_channel_fuzzy
)


class Disband(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /DISBAND
    # =========================
    @app_commands.command(
        name="disband",
        description="SFG only: disband a team (remove roles from everyone)."
    )
    @app_commands.describe(
        team="Which NFL team to disband",
        reason="Why is this team being disbanded?"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def disband(
        self,
        interaction: discord.Interaction,
        team: str,
        reason: str
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

        if team not in NFL_TEAMS:
            return await interaction.followup.send(
                "❌ Invalid NFL team.",
                ephemeral=True
            )

        team_role = get_team_role(guild, team)
        if not team_role:
            return await interaction.followup.send(
                f"❌ Team role not found: **{team}**",
                ephemeral=True
            )

        # 🔒 Role hierarchy check
        me = guild.me or guild.get_member(self.bot.user.id)
        if me and team_role >= me.top_role:
            return await interaction.followup.send(
                "❌ I can’t manage that team role (move my bot role above it).",
                ephemeral=True
            )

        removed_team = 0
        removed_mgmt = 0

        # 🔥 Management roles
        mgmt_role_names = ("Franchise Owner", "Team President", "General Manager")
        mgmt_roles = [
            r for r in guild.roles if r.name in mgmt_role_names
        ]

        members_to_update = list(team_role.members)

        for member in members_to_update:
            roles_to_remove = []

            if team_role in member.roles:
                roles_to_remove.append(team_role)

            for r in mgmt_roles:
                if r in member.roles:
                    roles_to_remove.append(r)

            if not roles_to_remove:
                continue

            try:
                await member.remove_roles(
                    *roles_to_remove,
                    reason=f"Disbanded {team_role.name} by {issuer} | {reason}"
                )

                if team_role in roles_to_remove:
                    removed_team += 1

                removed_mgmt += sum(
                    1 for r in roles_to_remove if r is not team_role
                )

            except discord.Forbidden:
                continue
            except Exception:
                continue

        # =========================
        # EMBED
        # =========================
        team_logo = TEAM_THUMBNAILS.get(team_role.name)

        embed = discord.Embed(
            title=f"{team_role.name} is Disbanded!",
            color=TEAM_COLORS.get(team_role.name, 0xED4245),
            timestamp=datetime.utcnow()
        )

        if team_logo:
            embed.set_thumbnail(url=team_logo)

        embed.add_field(
            name="Reason",
            value=reason.strip()[:1024] or "N/A",
            inline=False
        )

        embed.add_field(
            name="Disbanded By",
            value=issuer.mention,
            inline=False
        )

        embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        # =========================
        # LOG CHANNEL
        # =========================
        logs_ch = find_text_channel_fuzzy(guild, "logs")
        if logs_ch:
            await logs_ch.send(embed=embed)

        # =========================
        # FINAL RESPONSE
        # =========================
        await interaction.followup.send(
            content=(
                f"✅ Disbanded **{team_role.name}**.\n"
                f"• Removed team role from **{removed_team}** member(s)\n"
                f"• Removed FO/TP/GM roles from **{removed_mgmt}** assignments\n"
                f"• Logged in **logs**."
            ),
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Disband(bot))