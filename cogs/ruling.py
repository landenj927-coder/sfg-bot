import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.config import (
    GUILD_ID,
    SFG_LOGO_URL,
    RULINGS_CHANNEL_ID,
    SUSPENDED_ROLE_NAME,
    BLACKLIST_ROLE_NAME
)


class Ruling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /RULING
    # =========================
    @app_commands.command(
        name="ruling",
        description="Admin: punish a player (Suspension / Blacklist / Ban)"
    )
    @app_commands.describe(
        user="User being punished",
        punishment="Type of punishment",
        bail_price="Bail price",
        description="What happened"
    )
    @app_commands.choices(
        punishment=[
            app_commands.Choice(name="Suspension", value="Suspension"),
            app_commands.Choice(name="Blacklist", value="Blacklist"),
            app_commands.Choice(name="Ban", value="Ban"),
        ]
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ruling(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        punishment: app_commands.Choice[str],
        bail_price: app_commands.Range[int, 0, 1_000_000],
        description: str
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        issuer = interaction.user

        if not guild:
            return await interaction.followup.send("Server only command.", ephemeral=True)

        if not isinstance(issuer, discord.Member):
            return await interaction.followup.send("Couldn’t verify roles.", ephemeral=True)

        # =========================
        # PERMISSIONS
        # =========================
        perms = issuer.guild_permissions
        if not (perms.administrator or perms.ban_members or perms.manage_guild):
            return await interaction.followup.send(
                "❌ No permission.",
                ephemeral=True
            )

        if user.id == issuer.id:
            return await interaction.followup.send(
                "❌ You can't punish yourself.",
                ephemeral=True
            )

        # =========================
        # EMBED
        # =========================
        embed = discord.Embed(
            title="SFG – Judgement",
            description=f"**Punishment:** {punishment.value}",
            color=0xED4245,
            timestamp=datetime.utcnow()
        )

        embed.set_thumbnail(url=SFG_LOGO_URL)

        embed.add_field(name="Offender", value=user.mention, inline=True)
        embed.add_field(name="Issued By", value=issuer.mention, inline=True)
        embed.add_field(name="Bail Price", value=f"${bail_price:,}", inline=True)
        embed.add_field(name="Details", value=description[:1024], inline=False)

        action_taken = ""

        # =========================
        # DM USER FIRST
        # =========================
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass

        # =========================
        # APPLY PUNISHMENT
        # =========================
        try:

            if punishment.value == "Suspension":
                role = discord.utils.get(guild.roles, name=SUSPENDED_ROLE_NAME)

                if not role:
                    return await interaction.followup.send(
                        "❌ Suspended role missing.",
                        ephemeral=True
                    )

                await user.add_roles(role)
                action_taken = f"{user.mention} Suspended"


            elif punishment.value == "Blacklist":
                role = discord.utils.get(guild.roles, name=BLACKLIST_ROLE_NAME)

                if not role:
                    return await interaction.followup.send(
                        "❌ Blacklisted role missing.",
                        ephemeral=True
                    )

                await user.add_roles(role)
                action_taken = f"{user.mention} Blacklisted"


            elif punishment.value == "Ban":
                await guild.ban(
                    user,
                    reason=f"Ruling | {description}",
                    delete_message_days=0
                )

                action_taken = f"{user.mention} Banned"

        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Permission error.",
                ephemeral=True
            )

        except Exception as e:
            return await interaction.followup.send(
                f"❌ Error: {e}",
                ephemeral=True
            )

        # =========================
        # SEND TO CHANNEL (ID BASED 🔥)
        # =========================
        judgements_ch = guild.get_channel(RULINGS_CHANNEL_ID)

        if judgements_ch:
            await judgements_ch.send(embed=embed)

        # =========================
        # FINAL RESPONSE
        # =========================
        await interaction.followup.send(
            f"✅ {action_taken}",
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Ruling(bot))