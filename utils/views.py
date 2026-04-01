import discord
from datetime import datetime

from utils.config import (
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    ROSTER_LIMIT
)

from utils.helpers import log_transaction

class OfferView(discord.ui.View):
    def __init__(self, team_role: discord.Role, player: discord.Member, coach: discord.Member):
        super().__init__(timeout=None)
        self.team_role = team_role
        self.player = player
        self.coach = coach

    def build_embed(self, title: str, description: str) -> discord.Embed:
        team_name = self.team_role.name
        color = TEAM_COLORS.get(team_name, 0x2F3136)
        thumb_url = TEAM_THUMBNAILS.get(team_name)

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        embed.set_footer(text="SFG Bot", icon_url=SFG_LOGO_URL)
        embed.add_field(name="Team", value=team_name, inline=True)
        embed.add_field(name="Coach", value=self.coach.mention, inline=True)
        embed.add_field(name="Player", value=self.player.mention, inline=True)
        return embed

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("This offer is not for you.", ephemeral=True)

        if len(self.team_role.members) >= ROSTER_LIMIT:
            await interaction.response.edit_message(content="Roster is full.", view=None)
            embed = self.build_embed("Offer Declined", f"{self.player.mention} tried to accept, but **{self.team_role.name}** is full.")
            return await log_transaction(self.team_role.guild, embed)

        await self.player.add_roles(self.team_role)
        await interaction.response.edit_message(content="You have accepted the offer.", view=None)

        embed = self.build_embed("Offer Accepted", f"{self.player.mention} has **accepted** the offer from {self.coach.mention}.")
        await log_transaction(self.team_role.guild, embed)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("This offer is not for you.", ephemeral=True)

        await interaction.response.edit_message(content="You declined the offer.", view=None)

        embed = self.build_embed("Offer Declined", f"{self.player.mention} has **declined** the offer from {self.coach.mention}.")
        await log_transaction(self.team_role.guild, embed)