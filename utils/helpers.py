import discord
import re
import unicodedata
from utils.config import TRANSACTIONS_CHANNEL

async def log_transaction(guild: discord.Guild, embed: discord.Embed):
    channel = find_text_channel_fuzzy(guild, TRANSACTIONS_CHANNEL)

    if channel:
        await channel.send(embed=embed)
    else:
        print("transactions channel not found")

def find_text_channel_fuzzy(guild: discord.Guild, target_name: str) -> discord.TextChannel | None:
    if not guild:
        return None

    target = normalize_channel_name(target_name)

    for ch in guild.text_channels:
        if normalize_channel_name(ch.name) == target:
            return ch

    return None

def normalize_channel_name(name: str) -> str:
    # Handles capitalization + unicode "fancy fonts"
    name = unicodedata.normalize("NFKD", name or "")
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-z0-9]", "", name.lower())
    return name

def get_team_role(guild, team_name: str):
    return discord.utils.get(guild.roles, name=team_name)

def find_streams_channel(guild, name: str):
    name = name.lower()

    for channel in guild.text_channels:
        if name in channel.name.lower():
            return channel

    return None