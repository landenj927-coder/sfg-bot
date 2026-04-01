import discord
from datetime import datetime

from utils.config import (
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    ROSTER_LIMIT
)

from utils.helpers import log_transaction
from utils.standings import TEAM_EMOJIS


class OfferView(discord.ui.View):
    def __init__(self, team_role: discord.Role, player: discord.Member, coach: discord.Member):
        super().__init__(timeout=None)
        self.team_role = team_role
        self.player = player
        self.coach = coach

    # 🔥 ELITE EMBED BUILDER
    def build_embed(self, description: str, status: str = "neutral") -> discord.Embed:
        team_name = self.team_role.name
        emoji = TEAM_EMOJIS.get(team_name, "")

        base_color = TEAM_COLORS.get(team_name, 0x2F3136)

        # 🎯 STATUS SYSTEM
        if status == "accepted":
            color = 0x57F287
            header = "🟢 SIGNING CONFIRMED"
        elif status == "declined":
            color = 0xED4245
            header = "🔴 OFFER DECLINED"
        else:
            color = base_color
            header = f"{emoji} OFFER RECEIVED"

        thumb_url = TEAM_THUMBNAILS.get(team_name)

        embed = discord.Embed(
            title=header,
            description=f"**{description}**",
            color=color,
            timestamp=datetime.utcnow()
        )

        # 🔥 SFG HEADER
        embed.set_author(
            name="SFG League Transactions",
            icon_url=SFG_LOGO_URL
        )

        # 🏈 TEAM LOGO
        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        divider = "━━━━━━━━━━━━━━━━━━"

        # 📊 CORE INFO
        embed.add_field(
            name="🏟 Team",
            value=f"{emoji} **{team_name}**",
            inline=True
        )

        embed.add_field(
            name="🧑 Player",
            value=self.player.mention,
            inline=True
        )

        embed.add_field(
            name="🧑‍💼 Coach",
            value=self.coach.mention,
            inline=True
        )

        # 🔥 VISUAL BREAK
        embed.add_field(name=divider, value="\u200b", inline=False)

        # 📢 DETAILS
        embed.add_field(
            name="📢 Details",
            value=description,
            inline=False
        )

        # 🏁 FOOTER
        embed.set_footer(
            text="SFG League • Official Transaction Feed",
            icon_url=SFG_LOGO_URL
        )

        return embed

    # =========================
    # ACCEPT
    # =========================
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.player.id:
            return await interaction.response.send_message(
                "This offer is not for you.",
                ephemeral=True
            )

        # 🔥 ROSTER FULL
        if len(self.team_role.members) >= ROSTER_LIMIT:
            await interaction.response.edit_message(
                content="Roster is full.",
                view=None
            )

            embed = self.build_embed(
                f"{self.player.mention} tried to accept, but **{self.team_role.name}** is full.",
                status="declined"
            )

            return await log_transaction(self.team_role.guild, embed)

        # ✅ ACCEPT
        await self.player.add_roles(self.team_role)

        await interaction.response.edit_message(
            content="You have accepted the offer.",
            view=None
        )

        embed = self.build_embed(
            f"{self.player.mention} has **accepted** the offer from {self.coach.mention}.",
            status="accepted"
        )

        await log_transaction(self.team_role.guild, embed)

    # =========================
    # DECLINE
    # =========================
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.player.id:
            return await interaction.response.send_message(
                "This offer is not for you.",
                ephemeral=True
            )

        await interaction.response.edit_message(
            content="You declined the offer.",
            view=None
        )

        embed = self.build_embed(
            f"{self.player.mention} has **declined** the offer from {self.coach.mention}.",
            status="declined"
        )

        await log_transaction(self.team_role.guild, embed)