import discord
from discord.ext import commands

# 🔧 PUT YOUR CHANNEL ID HERE
MEMBERS_CHANNEL_ID = 123456789012345678


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # MEMBER JOIN
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        channel = member.guild.get_channel(MEMBERS_CHANNEL_ID)
        if not channel:
            return

        count = member.guild.member_count

        message = (
            f"Welcome to Storcit'y Football Gridiron {member.mention} ({member.name}). "
            f"We now have **{count}** in the community."
        )

        await channel.send(message)

    # =========================
    # MEMBER LEAVE
    # =========================
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):

        channel = member.guild.get_channel(MEMBERS_CHANNEL_ID)
        if not channel:
            return

        count = member.guild.member_count

        message = (
            f"({member.name}) has left Storcit'y Football Gridiron. "
            f"We now have **{count}** in the community."
        )

        await channel.send(message)


# =========================
# SETUP
# =========================
async def setup(bot):
    await bot.add_cog(Members(bot))