import discord
from datetime import datetime

from utils.config import (
    TEAM_COLORS,
    TEAM_THUMBNAILS,
    SFG_LOGO_URL,
    ROSTER_LIMIT,
    RESULTS_CHANNEL_ID
)

from utils.helpers import log_transaction
from utils.standings import TEAM_EMOJIS

# 🔥 IMPORT FROM NEW FILE (NO MORE MAIN IMPORT)
from utils.app_questions import APPLICATION_QUESTION_MAP


# =========================================================
# OFFER SYSTEM
# =========================================================
class OfferView(discord.ui.View):
    def __init__(self, team_role: discord.Role, player: discord.Member, coach: discord.Member):
        super().__init__(timeout=300)
        self.team_role = team_role
        self.player = player
        self.coach = coach

    def build_embed(self, description: str, status: str = "neutral") -> discord.Embed:
        team_name = self.team_role.name
        emoji = TEAM_EMOJIS.get(team_name, "")

        base_color = TEAM_COLORS.get(team_name, 0x2F3136)

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

        embed.set_author(name="SFG League Transactions", icon_url=SFG_LOGO_URL)

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        embed.add_field(name="🏟 Team", value=f"{emoji} **{team_name}**", inline=True)
        embed.add_field(name="🧑 Player", value=self.player.mention, inline=True)
        embed.add_field(name="🧑‍💼 Coach", value=self.coach.mention, inline=True)

        embed.set_footer(text="SFG League • Official Transaction Feed", icon_url=SFG_LOGO_URL)

        return embed

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("This offer is not for you.", ephemeral=True)

        if len(self.team_role.members) >= ROSTER_LIMIT:
            await interaction.response.edit_message(content="Roster is full.", view=None)

            embed = self.build_embed(
                f"{self.player.mention} tried to accept, but roster is full.",
                status="declined"
            )

            return await log_transaction(self.team_role.guild, embed)

        await self.player.add_roles(self.team_role)

        await interaction.response.edit_message(content="You accepted the offer.", view=None)

        embed = self.build_embed(
            f"{self.player.mention} has accepted the offer from {self.coach.mention}.",
            status="accepted"
        )

        await log_transaction(self.team_role.guild, embed)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("This offer is not for you.", ephemeral=True)

        await interaction.response.edit_message(content="You declined the offer.", view=None)

        embed = self.build_embed(
            f"{self.player.mention} has declined the offer from {self.coach.mention}.",
            status="declined"
        )

        await log_transaction(self.team_role.guild, embed)


# =========================================================
# APPLICATION SYSTEM (ELITE)
# =========================================================

from utils.app_questions import APPLICATION_QUESTION_MAP
from utils.config import APPLICATIONS_RESULTS_CHANNEL_ID


APPLICATION_BRANCHES = {
    "Justice": {"options": ["Investigation Staff", "Referee Staff"]},
    "Community": {"options": ["Media Analyst", "Media Owner", "Streamer", "Host"]},
    "Franchise": {"options": ["Franchise Owner"]},
    "Awards Committee": {"options": ["Stat Analyst"]}
}


# =========================
# STAFF REVIEW VIEW
# =========================
class ApplicationReviewView(discord.ui.View):
    def __init__(self, applicant: discord.Member, role_name: str):
        super().__init__(timeout=None)
        self.applicant = applicant
        self.role_name = role_name

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = discord.utils.get(interaction.guild.roles, name=self.role_name)

        if role:
            await self.applicant.add_roles(role)

        await interaction.response.edit_message(
            content=f"✅ Accepted by {interaction.user.mention}",
            view=None
        )

        try:
            await self.applicant.send(
                f"🎉 You have been **ACCEPTED** for **{self.role_name}**!"
            )
        except:
            pass

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(
            content=f"❌ Denied by {interaction.user.mention}",
            view=None
        )

        try:
            await self.applicant.send(
                f"❌ You have been **DENIED** for **{self.role_name}**."
            )
        except:
            pass


# =========================
# MAIN VIEWS
# =========================
class ApplicationBranchView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.add_item(ApplicationBranchSelect(guild))


class ApplicationBranchSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        self.guild = guild

        options = [
            discord.SelectOption(label=name, value=name)
            for name in APPLICATION_BRANCHES.keys()
        ]

        super().__init__(
            placeholder="Select an application branch",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        branch = self.values[0]
        data = APPLICATION_BRANCHES[branch]

        await interaction.response.send_message(
            f"**{branch} Applications**\nSelect a role:",
            ephemeral=True,
            view=ApplicationRoleView(branch, data, self.guild)
        )


class ApplicationRoleView(discord.ui.View):
    def __init__(self, branch_name: str, data: dict, guild: discord.Guild):
        super().__init__(timeout=300)
        self.guild = guild
        self.add_item(ApplicationRoleSelect(branch_name, data, guild))

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Select a branch:",
            view=ApplicationBranchView(self.guild)
        )


class ApplicationRoleSelect(discord.ui.Select):
    def __init__(self, branch_name: str, data: dict, guild: discord.Guild):
        self.guild = guild

        options = [
            discord.SelectOption(label=opt, value=opt)
            for opt in data["options"]
        ]

        super().__init__(
            placeholder=f"{branch_name} Applications",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        user = interaction.user

        questions = APPLICATION_QUESTION_MAP.get(choice)

        if not questions:
            return await interaction.response.send_message(
                "❌ No questions found.",
                ephemeral=True
            )

        await interaction.response.edit_message(
            content=f"📩 Check your DMs for **{choice}** application.",
            view=None
        )

        try:
            dm = await user.create_dm()
            answers = []

            await dm.send(f"📝 **Application Started: {choice}**")

            for q in questions:
                await dm.send(f"**{q}**")

                def check(m):
                    return m.author == user and m.channel == dm

                msg = await interaction.client.wait_for(
                    "message",
                    check=check,
                    timeout=300
                )

                answers.append(msg.content)

            await dm.send("✅ Application submitted!")

            # =========================
            # SEND TO STAFF
            # =========================
            channel = self.guild.get_channel(APPLICATIONS_RESULTS_CHANNEL_ID)

            if channel:
                embed = discord.Embed(
                    title=f"📋 {choice} Application",
                    color=0x3498DB,
                    timestamp=discord.utils.utcnow()
                )

                embed.add_field(name="Applicant", value=user.mention, inline=False)

                for i, q in enumerate(questions):
                    embed.add_field(name=q, value=answers[i], inline=False)

                embed.set_footer(text="SFG Applications")

                await channel.send(
                    embed=embed,
                    view=ApplicationReviewView(user, choice)
                )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Enable DMs and try again.",
                ephemeral=True
            )

        except Exception as e:
            print("Application Error:", e)


# =========================================================
# STREAM CLAIM SYSTEM
# =========================================================
class StreamClaimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Stream", style=discord.ButtonStyle.green, custom_id="stream_claim_button")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        for item in self.children:
            item.disabled = True

        embed = interaction.message.embeds[0]

        embed.add_field(
            name="📺 Stream Claimed",
            value=f"{user.mention} will be streaming this game.",
            inline=False
        )

        await interaction.message.edit(embed=embed, view=self)

        await interaction.response.send_message("✅ You have claimed this stream.", ephemeral=True)