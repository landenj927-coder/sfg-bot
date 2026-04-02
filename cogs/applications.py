import discord
from discord.ext import commands
from discord import app_commands

from utils.config import (
    APPLICATIONS_CHANNEL_ID,
    APPLICATION_PANEL_TITLE,
    SFG_LOGO_URL,
    GUILD_ID
)

from utils.views import ApplicationBranchView


class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # /applications
    # =========================================================
    @app_commands.command(
        name="applications",
        description="Post the SFG application panel."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))  # 🔥 INSTANT SYNC
    async def applications(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send(
                "Server-only command.",
                ephemeral=True
            )

        app_channel = guild.get_channel(APPLICATIONS_CHANNEL_ID)

        if not app_channel:
            return await interaction.followup.send(
                "❌ Applications channel not found.",
                ephemeral=True
            )

        # =========================
        # REMOVE OLD PANELS
        # =========================
        try:
            bot_user = self.bot.user

            if bot_user:
                panels = []

                async for msg in app_channel.history(limit=100):
                    if msg.author.id != bot_user.id:
                        continue
                    if not msg.embeds:
                        continue
                    if (msg.embeds[0].title or "") == APPLICATION_PANEL_TITLE:
                        panels.append(msg)

                for old in panels[1:]:
                    await old.delete()

        except Exception as e:
            print("Panel cleanup error:", repr(e))

        # =========================
        # ROLE MENTION HELPER
        # =========================
        def role_mention(name: str) -> str:
            role = discord.utils.get(guild.roles, name=name)
            return role.mention if role else f"@{name}"

        # =========================
        # EMBED
        # =========================
        embed = discord.Embed(
            title=APPLICATION_PANEL_TITLE,
            color=0x3498DB
        )

        embed.add_field(
            name="Information",
            value=(
                "On this panel you can find different applications that help SFG run.\n\n"
                "Select a branch below and apply for the role you want."
            ),
            inline=False
        )

        embed.add_field(
            name="Applications",
            value=(
                f"{role_mention('Justice')}\n"
                "• Investigation Staff\n"
                "• Referee Staff\n\n"

                f"{role_mention('Community')}\n"
                "• Media Analyst\n"
                "• Media Owner\n"
                "• Streamer\n"
                "• Host\n\n"

                f"{role_mention('Franchise')}\n"
                "• Franchise Owner\n\n"

                f"{role_mention('Awards Committee')}\n"
                "• Stat Analyst"
            ),
            inline=False
        )

        embed.set_footer(
            text="SFG Bot",
            icon_url=SFG_LOGO_URL
        )

        # =========================
        # SEND PANEL
        # =========================
        await app_channel.send(
            embed=embed,
            view=ApplicationBranchView(guild)
        )

        await interaction.followup.send(
            f"✅ Application panel posted in {app_channel.mention}.",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Applications(bot))