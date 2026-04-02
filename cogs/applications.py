import discord
from discord import app_commands
from discord.ext import commands

from utils.config import (
    APPLICATIONS_CHANNEL_ID,
    APPLICATION_PANEL_TITLE,
    SFG_LOGO_URL
)

from utils.views import ApplicationBranchView


class ApplicationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =========================================================
    # /applications command (single panel only)
    # =========================================================
    @app_commands.command(
        name="applications",
        description="Post the SFG application panel."
    )
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

        # ✅ Remove old panels (keep newest)
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

                for old_panel in panels[1:]:
                    await old_panel.delete()

        except Exception as e:
            print("Panel cleanup error:", repr(e))

        # helper
        def role_mention(name: str) -> str:
            r = discord.utils.get(guild.roles, name=name)
            return r.mention if r else f"@{name}"

        # embed
        embed = discord.Embed(
            title=APPLICATION_PANEL_TITLE,
            color=0x3498DB
        )

        embed.add_field(
            name="Information",
            value=(
                "On this panel you can find numerous amounts of different applications "
                "that help SFG run. If you'd like to be a part of our team, decide which "
                "branch you'd like to apply to and read the questions carefully."
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

        embed.set_footer(text="SFG Bot", icon_url=SFG_LOGO_URL)

        await app_channel.send(
            embed=embed,
            view=ApplicationBranchView(guild)
        )

        await interaction.followup.send(
            f"✅ Application panel posted in {app_channel.mention}.",
            ephemeral=True
        )


# REQUIRED SETUP FUNCTION
async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationsCog(bot))