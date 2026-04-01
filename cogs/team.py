import time
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from utils.config import GUILD_ID
from utils.constants import (
    NFL_TEAMS,
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    ROSTER_LIMIT,
)
from utils.helpers import log_transaction


DEMAND_COOLDOWNS: dict[int, float] = {}
DEMAND_COOLDOWN_SECONDS = 48 * 60 * 60

MANAGEMENT_ROLE_NAMES = [
    "Franchise Owner",
    "Team President",
    "General Manager",
]

PROMOTABLE_ROLE_NAMES = [
    "Team President",
    "General Manager",
]


class PromoteRoleChoice(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> str:
        value = value.strip()
        if value not in PROMOTABLE_ROLE_NAMES:
            raise app_commands.AppCommandError("Invalid management role.")
        return value


async def promotable_role_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    current = (current or "").lower()
    return [
        app_commands.Choice(name=role_name, value=role_name)
        for role_name in PROMOTABLE_ROLE_NAMES
        if current in role_name.lower()
    ][:25]


class Team(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =========================
    # HELPERS
    # =========================
    def get_member_team_role(self, member: discord.Member) -> discord.Role | None:
        return next((r for r in member.roles if r.name in NFL_TEAMS), None)

    def get_member_team_name(self, member: discord.Member) -> str:
        role = self.get_member_team_role(member)
        return role.name if role else ""

    def has_management_role(self, member: discord.Member) -> bool:
        return any(r.name in MANAGEMENT_ROLE_NAMES for r in member.roles)

    def get_highest_management_name(self, member: discord.Member) -> str | None:
        # hierarchy by power
        if any(r.name == "Franchise Owner" for r in member.roles):
            return "Franchise Owner"
        if any(r.name == "Team President" for r in member.roles):
            return "Team President"
        if any(r.name == "General Manager" for r in member.roles):
            return "General Manager"
        return None

    def can_manage_role(self, actor: discord.Member, target_role_name: str) -> bool:
        actor_rank = self.get_highest_management_name(actor)

        if actor_rank == "Franchise Owner":
            return target_role_name in {"Team President", "General Manager"}

        if actor_rank == "Team President":
            return target_role_name == "General Manager"

        return False

    def build_team_embed(
        self,
        team_name: str,
        title: str,
        description: str
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=TEAM_COLORS.get(team_name, 0x2F3136),
            timestamp=datetime.utcnow()
        )

        thumb_url = TEAM_THUMBNAILS.get(team_name)
        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        embed.set_footer(text="SFG Bot", icon_url=SFG_LOGO_URL)
        return embed

    # =========================
    # /release
    # =========================
    @app_commands.command(
        name="release",
        description="Release a player from your team."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="The player you want to release")
    async def release(self, interaction: discord.Interaction, user: discord.Member):
        guild = interaction.guild
        author = interaction.user

        if guild is None or not isinstance(author, discord.Member):
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        coach_team = self.get_member_team_role(author)
        if not coach_team or not self.has_management_role(author):
            return await interaction.response.send_message(
                "You do not have a coach role.",
                ephemeral=True
            )

        if coach_team not in user.roles:
            return await interaction.response.send_message(
                f"{user.mention} is NOT on your team ({coach_team.name}).",
                ephemeral=True
            )

        await user.remove_roles(coach_team)

        embed = self.build_team_embed(
            coach_team.name,
            "Player Released",
            f"{user.mention} has been released from **{coach_team.name}** by {author.mention}."
        )

        await interaction.response.send_message(
            f"{user.mention} has been released from **{coach_team.name}**.",
            ephemeral=True
        )
        await log_transaction(guild, embed)

    # =========================
    # /promote
    # =========================
    @app_commands.command(
        name="promote",
        description="Promote someone on your team to a management role."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The player you want to promote",
        role_name="The management role to give"
    )
    @app_commands.autocomplete(role_name=promotable_role_autocomplete)
    async def promote(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        role_name: str,
    ):
        guild = interaction.guild
        author = interaction.user

        if guild is None or not isinstance(author, discord.Member):
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        role_name = role_name.strip()

        if role_name not in PROMOTABLE_ROLE_NAMES:
            return await interaction.response.send_message(
                "Invalid management role.",
                ephemeral=True
            )

        author_team = self.get_member_team_role(author)
        if not author_team or not self.has_management_role(author):
            return await interaction.response.send_message(
                "You do not have a coach role.",
                ephemeral=True
            )

        if not self.can_manage_role(author, role_name):
            return await interaction.response.send_message(
                "You do not have permission to give that role.",
                ephemeral=True
            )

        if author_team not in user.roles:
            return await interaction.response.send_message(
                "That player is not on your team.",
                ephemeral=True
            )

        target_role = discord.utils.get(guild.roles, name=role_name)
        if not target_role:
            return await interaction.response.send_message(
                f"Role not found: {role_name}",
                ephemeral=True
            )

        if target_role in user.roles:
            return await interaction.response.send_message(
                f"{user.mention} already has **{role_name}**.",
                ephemeral=True
            )

        await user.add_roles(target_role)

        embed = self.build_team_embed(
            author_team.name,
            "Player Promoted",
            f"{user.mention} has been promoted to **{role_name}** on **{author_team.name}** by {author.mention}."
        )

        await interaction.response.send_message(
            f"{user.mention} has been promoted to **{role_name}**.",
            ephemeral=True
        )
        await log_transaction(guild, embed)

    # =========================
    # /demote
    # =========================
    @app_commands.command(
        name="demote",
        description="Demote someone on your team from a management role."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The staff member you want to demote",
        role_name="The management role to remove"
    )
    @app_commands.autocomplete(role_name=promotable_role_autocomplete)
    async def demote(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        role_name: str,
    ):
        guild = interaction.guild
        author = interaction.user

        if guild is None or not isinstance(author, discord.Member):
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        role_name = role_name.strip()

        if role_name not in PROMOTABLE_ROLE_NAMES:
            return await interaction.response.send_message(
                "Invalid management role.",
                ephemeral=True
            )

        author_team = self.get_member_team_role(author)
        if not author_team or not self.has_management_role(author):
            return await interaction.response.send_message(
                "You do not have a coach role.",
                ephemeral=True
            )

        if not self.can_manage_role(author, role_name):
            return await interaction.response.send_message(
                "You do not have permission to remove that role.",
                ephemeral=True
            )

        if author_team not in user.roles:
            return await interaction.response.send_message(
                "That staff member is not on your team.",
                ephemeral=True
            )

        target_role = discord.utils.get(guild.roles, name=role_name)
        if not target_role:
            return await interaction.response.send_message(
                f"Role not found: {role_name}",
                ephemeral=True
            )

        if target_role not in user.roles:
            return await interaction.response.send_message(
                f"{user.mention} does not have **{role_name}**.",
                ephemeral=True
            )

        await user.remove_roles(target_role)

        embed = self.build_team_embed(
            author_team.name,
            "Player Demoted",
            f"{user.mention} has been demoted from **{role_name}** on **{author_team.name}** by {author.mention}."
        )

        await interaction.response.send_message(
            f"{user.mention} has been demoted from **{role_name}**.",
            ephemeral=True
        )
        await log_transaction(guild, embed)

    # =========================
    # /demand
    # =========================
    @app_commands.command(
        name="demand",
        description="Demand a release from your current team (players only)."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def demand(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        if guild is None or not isinstance(user, discord.Member):
            return await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )

        if self.has_management_role(user):
            return await interaction.response.send_message(
                "You cannot demand a release while holding a management role.",
                ephemeral=True
            )

        now = time.time()
        last_used = DEMAND_COOLDOWNS.get(user.id, 0)

        if now - last_used < DEMAND_COOLDOWN_SECONDS:
            remaining = int(DEMAND_COOLDOWN_SECONDS - (now - last_used))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return await interaction.response.send_message(
                f"⏳ You must wait **{hours}h {minutes}m** before using `/demand` again.",
                ephemeral=True
            )

        team_role = self.get_member_team_role(user)
        if not team_role:
            return await interaction.response.send_message(
                "You are not signed to a team.",
                ephemeral=True
            )

        team_name = team_role.name
        roster_before = len(team_role.members)
        roster_after = max(0, roster_before - 1)

        DEMAND_COOLDOWNS[user.id] = now
        await user.remove_roles(team_role)

        embed = self.build_team_embed(
            team_name,
            "Player Demanded Release",
            (
                f"{user.mention} has demanded from **{team_name}**.\n"
                f"**New roster count:** {roster_after} / {ROSTER_LIMIT}"
            )
        )

        await interaction.response.send_message(
            f"You have been released from **{team_name}**. You may demand again in **48 hours**.",
            ephemeral=True
        )
        await log_transaction(guild, embed)


async def setup(bot):
    await bot.add_cog(Team(bot))