import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
import json
from datetime import datetime, timedelta

from utils.config import GUILD_ID, SFG_LOGO_URL

SCHEDULE_FILE = Path("schedule.json")

LOGS_CHANNEL_ID = 1488388876262314194
SUPPORT_SERVER = "https://discord.gg/YOURINVITE"


def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return None


class ScheduleView(discord.ui.View):
    def __init__(self, bot, owner, team, matchup, week):
        super().__init__(timeout=86400)
        self.bot = bot
        self.owner = owner
        self.team = team
        self.matchup = matchup
        self.week = week
        self.clicked = False

    async def log_status(self, status, color):
        channel = self.bot.get_channel(LOGS_CHANNEL_ID)
        if channel is None:
            return

        embed = discord.Embed(
            title="📋 Scheduling Status Update",
            color=color,
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="Franchise Owner", value=self.owner.mention, inline=True)
        embed.add_field(name="Team", value=self.team, inline=True)
        embed.add_field(name="Week", value=self.week, inline=True)
        embed.add_field(name="Matchup", value=self.matchup, inline=False)
        embed.add_field(name="Status", value=status, inline=False)
        embed.set_footer(text="SFG Bot", icon_url=SFG_LOGO_URL)

        await channel.send(embed=embed)

    @discord.ui.button(label="Scheduled", emoji="✅", style=discord.ButtonStyle.success)
    async def scheduled(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.clicked = True
        await self.log_status("✅ Scheduled", 0x2ECC71)

        await interaction.response.send_message(
            "✅ Status updated: Scheduled. League staff has been notified.",
            ephemeral=True
        )

        self.stop()

    @discord.ui.button(label="Scheduling", emoji="🕒", style=discord.ButtonStyle.primary)
    async def scheduling(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.clicked = True
        await self.log_status("🕒 Scheduling", 0x3498DB)

        await interaction.response.send_message(
            "🕒 Status updated: Scheduling. League staff has been notified.",
            ephemeral=True
        )

        self.stop()

    @discord.ui.button(label="Difficulties", emoji="⚠️", style=discord.ButtonStyle.danger)
    async def difficulties(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.clicked = True
        await self.log_status("⚠️ Difficulties", 0xE74C3C)

        await interaction.response.send_message(
            f"⚠️ League staff has been notified.\n\nSupport Server:\n{SUPPORT_SERVER}",
            ephemeral=True
        )

        self.stop()

    async def on_timeout(self):
        if self.clicked:
            return

        channel = self.bot.get_channel(LOGS_CHANNEL_ID)
        if channel is None:
            return

        await channel.send(
            f"⚠️ {self.owner.mention} ghosted the scheduling reminder message.\n"
            f"**Team:** {self.team}\n"
            f"**Week:** {self.week}\n"
            f"**Matchup:** {self.matchup}"
        )


class ScheduleReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="schedreminders",
        description="DM all franchise owners their weekly scheduling reminders."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def schedreminders(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        data = load_schedule()

        if not data:
            return await interaction.followup.send("No schedule found.", ephemeral=True)

        guild = interaction.guild

        if guild is None:
            return await interaction.followup.send("Server only command.", ephemeral=True)

        current_week = str(data.get("current_week", 1))
        games = data["weeks"].get(current_week)

        if not games:
            return await interaction.followup.send(
                "No games found for current week.",
                ephemeral=True
            )

        week_start = datetime.fromisoformat(data["week_start"])
        deadline = week_start + timedelta(hours=data.get("deadline_hours", 48))
        deadline_text = deadline.strftime("%B %d, %Y • %I:%M %p UTC")

        sent_count = 0
        failed = []

        for team_a, team_b in games:
            role_a = discord.utils.get(guild.roles, name=team_a)
            role_b = discord.utils.get(guild.roles, name=team_b)

            if not role_a or not role_b:
                continue

            owner_a = next(
                (
                    m for m in role_a.members
                    if any(r.name == "Franchise Owner" for r in m.roles)
                ),
                None
            )

            owner_b = next(
                (
                    m for m in role_b.members
                    if any(r.name == "Franchise Owner" for r in m.roles)
                ),
                None
            )

            matchup = f"{team_a} vs {team_b}"

            for owner, team in [(owner_a, team_a), (owner_b, team_b)]:
                if owner is None:
                    failed.append(f"{team} has no Franchise Owner.")
                    continue

                embed = discord.Embed(
                    title=f"📅 Week {current_week} Scheduling Reminder",
                    description=(
                        f"Hello {owner.mention},\n\n"
                        "Please schedule your game as soon as possible.\n\n"
                        f"🏈 **Matchup**\n{matchup}\n\n"
                        f"⏳ **Scheduling Deadline**\n{deadline_text}\n\n"
                        "Use the buttons below to update your scheduling status."
                    ),
                    color=0xF1C40F,
                    timestamp=datetime.utcnow()
                )

                embed.add_field(
                    name="✅ Scheduled",
                    value="Game time has been agreed on.",
                    inline=True
                )

                embed.add_field(
                    name="🕒 Scheduling",
                    value="Currently working on a time.",
                    inline=True
                )

                embed.add_field(
                    name="⚠️ Difficulties",
                    value="Need staff assistance.",
                    inline=True
                )

                embed.set_footer(
                    text="SFG League Scheduling System",
                    icon_url=SFG_LOGO_URL
                )

                view = ScheduleView(
                    self.bot,
                    owner,
                    team,
                    matchup,
                    current_week
                )

                try:
                    await owner.send(embed=embed, view=view)
                    sent_count += 1
                except discord.Forbidden:
                    failed.append(f"Could not DM {owner.mention} for {team}.")

        response = f"✅ Sent {sent_count} scheduling reminders."

        if failed:
            response += "\n\n⚠️ Issues:\n" + "\n".join(failed)

        await interaction.followup.send(response, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ScheduleReminder(bot))