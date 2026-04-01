import discord
from discord.ext import commands

MEMBERS_CHANNEL_ID = 123456789012345678  # replace with your real channel ID


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"[MEMBERS COG] on_member_join fired for: {member} ({member.id})")

        channel = member.guild.get_channel(MEMBERS_CHANNEL_ID)
        print(f"[MEMBERS COG] join channel found: {channel}")

        if not isinstance(channel, discord.TextChannel):
            print("[MEMBERS COG] join channel invalid or not found")
            return

        count = member.guild.member_count or len(member.guild.members)

        message = (
            f"Welcome to Storcity's Football Gridiron {member.mention} ({member.name}). "
            f"We now have **{count}** in the community."
        )

        try:
            await channel.send(message)
            print("[MEMBERS COG] join message sent")
        except Exception as e:
            print(f"[MEMBERS COG] failed to send join message: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        print(f"[MEMBERS COG] on_member_remove fired for: {member} ({member.id})")

        channel = member.guild.get_channel(MEMBERS_CHANNEL_ID)
        print(f"[MEMBERS COG] leave channel found: {channel}")

        if not isinstance(channel, discord.TextChannel):
            print("[MEMBERS COG] leave channel invalid or not found")
            return

        count = member.guild.member_count or len(member.guild.members)

        message = (
            f"({member.name}) has left Storcity's Football Gridiron. "
            f"We now have **{count}** in the community."
        )

        try:
            await channel.send(message)
            print("[MEMBERS COG] leave message sent")
        except Exception as e:
            print(f"[MEMBERS COG] failed to send leave message: {e}")


async def setup(bot):
    await bot.add_cog(Members(bot))