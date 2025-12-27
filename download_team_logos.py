import os
import requests

TEAM_EMOJI_IMAGES = {
    "Dallas": "https://cdn.discordapp.com/emojis/1448881516422758565.webp?size=96&quality=lossless",
    "Detroit": "https://cdn.discordapp.com/emojis/1448881504754204817.webp?size=96&quality=lossless",
    "Tampa": "https://cdn.discordapp.com/emojis/1448881513985736776.webp?size=96&quality=lossless",
    "Atlanta": "https://cdn.discordapp.com/emojis/1448881506905751653.webp?size=96&quality=lossless",
    "Arizona": "https://cdn.discordapp.com/emojis/1448881457106915509.webp?size=96&quality=lossless",
    "Rams": "https://cdn.discordapp.com/emojis/1448881461057814658.webp?size=96&quality=lossless",
    "Miami": "https://cdn.discordapp.com/emojis/1448881448982679678.webp?size=96&quality=lossless",
    "Jets": "https://cdn.discordapp.com/emojis/1448881451989995661.webp?size=96&quality=lossless",
    "Cincinnati": "https://cdn.discordapp.com/emojis/1448881436592570369.webp?size=96&quality=lossless",
    "Pittsburgh": "https://cdn.discordapp.com/emojis/1448881441516687511.webp?size=96&quality=lossless",
    "Patriots": "https://cdn.discordapp.com/emojis/1448881447272533812.webp?size=96&quality=lossless",
    "Baltimore": "https://cdn.discordapp.com/emojis/1448881443856322562.webp?size=96&quality=lossless",
    "Cleveland": "https://cdn.discordapp.com/emojis/1448881438591322346.webp?size=96&quality=lossless",
    "Houston": "https://cdn.discordapp.com/emojis/1448881477729410067.webp?size=96&quality=lossless",
    "Indianapolis": "https://cdn.discordapp.com/emojis/1448881486471364679.webp?size=96&quality=lossless",
    "Jacksonville": "https://cdn.discordapp.com/emojis/1448881484021895170.webp?size=96&quality=lossless",
    "Tennessee": "https://cdn.discordapp.com/emojis/1448881481064644679.webp?size=96&quality=lossless",
    "Denver": "https://cdn.discordapp.com/emojis/1448881475821768785.webp?size=96&quality=lossless",
    "Chiefs": "https://cdn.discordapp.com/emojis/1448881473536004106.webp?size=96&quality=lossless",
    "LasVegas": "https://cdn.discordapp.com/emojis/1448881471220617402.webp?size=96&quality=lossless",
    "Chargers": "https://cdn.discordapp.com/emojis/1448881467492012032.webp?size=96&quality=lossless",
    "Giants": "https://cdn.discordapp.com/emojis/1448881491022053492.webp?size=96&quality=lossless",
    "Philadelphia": "https://cdn.discordapp.com/emojis/1448881488912187513.webp?size=96&quality=lossless",
    "Washington": "https://cdn.discordapp.com/emojis/1448881493509144760.webp?size=96&quality=lossless",
    "Chicago": "https://cdn.discordapp.com/emojis/1448881495694381218.webp?size=96&quality=lossless",
    "GreenBay": "https://cdn.discordapp.com/emojis/1448881501574926368.webp?size=96&quality=lossless",
    "Minnesota": "https://cdn.discordapp.com/emojis/1448881499213664498.webp?size=96&quality=lossless",
    "Carolina": "https://cdn.discordapp.com/emojis/14488815171570438923.webp?size=96&quality=lossless",
    "Saints": "https://cdn.discordapp.com/emojis/1448881509577658379.webp?size=96&quality=lossless",
    "49ers": "https://cdn.discordapp.com/emojis/1448881473102702791.webp?size=96&quality=lossless",
    "Seattle": "https://cdn.discordapp.com/emojis/14488814846950128843.webp?size=96&quality=lossless",
    "Buffalo": "https://cdn.discordapp.com/emojis/1448881454604533504.webp?size=96&quality=lossless"
}


for team, url in TEAM_EMOJI_IMAGES.items():
    filename = f"team_logos/{team}.png"
    print(f"Downloading {team} logo...")

    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)

print("All logos downloaded!")