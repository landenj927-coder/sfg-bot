from discord import app_commands
from utils.config import NFL_TEAMS

async def nfl_team_autocomplete(
    interaction,
    current: str
):
    return [
        app_commands.Choice(name=team, value=team)
        for team in NFL_TEAMS
        if current.lower() in team.lower()
    ][:25]