import discord
from discord import app_commands
from discord.ext import commands

# =========================
# CONFIG (EDIT THESE)
# =========================
RULES_CHANNEL_ID = 123456789012345678
SUPPORT_SERVER_LINK = "https://discord.gg/YOURSERVER"
ROBLOX_GROUP_LINK = "https://www.roblox.com/groups/YOURGROUP"
SPREADSHEET_LINK = "https://docs.google.com/spreadsheets/d/YOUR_SHEET"


class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /panel
    # =========================
    @app_commands.command(
        name="panel",
        description="Post the SFG info panel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):

        guild = interaction.guild

        if not guild:
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        rules_channel = guild.get_channel(RULES_CHANNEL_ID)

        # =========================
        # EMBED
        # =========================
        embed = discord.Embed(
            title="🏈 SFG Football League",
            description=(
                "**Welcome to SFG — a competitive Roblox Football Fusion league.**\n\n"
                "• Join a team\n"
                "• Compete in scheduled games\n"
                "• Track stats live\n\n"
                "Everything is automated — contracts, standings, and player stats."
            ),
            color=discord.Color.dark_gold()
        )

        embed.add_field(
            name="📜 Rules",
            value=(
                f"Make sure to read the rules before playing.\n"
                f"{rules_channel.mention if rules_channel else 'Rules channel not set'}"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Stats & Standings",
            value=(
                "View all player stats, leaderboards, and team standings live.\n"
                f"[Open Spreadsheet]({SPREADSHEET_LINK})"
            ),
            inline=False
        )

        embed.add_field(
            name="🤝 Support",
            value=f"[Join Support Server]({SUPPORT_SERVER_LINK})",
            inline=False
        )

        embed.add_field(
            name="🎮 Roblox Group",
            value=f"[Join Group]({ROBLOX_GROUP_LINK})",
            inline=False
        )

        embed.set_footer(text="SFG League • Powered by SFG Bot")

        # =========================
        # BUTTONS
        # =========================
        view = discord.ui.View()

        view.add_item(discord.ui.Button(
            label="📜 Rules",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{guild.id}/{RULES_CHANNEL_ID}"
        ))

        view.add_item(discord.ui.Button(
            label="📊 Stats",
            style=discord.ButtonStyle.link,
            url=SPREADSHEET_LINK
        ))

        view.add_item(discord.ui.Button(
            label="🤝 Support",
            style=discord.ButtonStyle.link,
            url=SUPPORT_SERVER_LINK
        ))

        view.add_item(discord.ui.Button(
            label="🎮 Roblox Group",
            style=discord.ButtonStyle.link,
            url=ROBLOX_GROUP_LINK
        ))

        # =========================
        # SEND PANEL
        # =========================
        await interaction.response.send_message(
            "✅ Panel posted.",
            ephemeral=True
        )

        await interaction.channel.send(embed=embed, view=view)


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Panel(bot))