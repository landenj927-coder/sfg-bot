import discord
from discord.ext import commands
from discord import app_commands


class RulebookView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Open Full Rulebook",
                url="https://docs.google.com/document/d/1em9c6CFmBzwcVgyREU8kq8pXzRd0xac6zhqx5GBUIW0/edit?usp=sharing",
                style=discord.ButtonStyle.link
            )
        )


class Rulebook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="rulebook",
        description="View the SFG rulebook and league agreement."
    )
    async def rulebook(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📘 SFG League Rulebook",
            description=(
                "**League Agreement**\n\n"
                "By accepting an offer in this league, you agree to a **mild, unharmful device search** "
                "if sufficient evidence is found against you.\n\n"
                "We are **not required to publicly disclose this evidence**, however, a minimum of **three "
                "unbiased staff members** must agree there is enough evidence to conduct a check."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="⚖️ Fair Play Commitment",
            value="All enforcement decisions are made to maintain league integrity and fairness.",
            inline=False
        )

        embed.add_field(
            name="📢 Transparency",
            value="Staff decisions are reviewed internally to ensure unbiased and consistent rulings.",
            inline=False
        )

        embed.add_field(
            name="📄 Full Rulebook",
            value="Use the button below to view the complete SFG rulebook.",
            inline=False
        )

        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1488380244237750413/PUT_YOURS_HERE.png"
        )

        embed.set_footer(text="SFG Bot")

        await interaction.response.send_message(
            embed=embed,
            view=RulebookView()
        )


async def setup(bot):
    await bot.add_cog(Rulebook(bot))