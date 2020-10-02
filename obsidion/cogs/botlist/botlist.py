"""Botlist info."""

import logging

import dbl
from discord.ext import commands, tasks

from obsidion import constants
from obsidion.bot import Obsidion

log = logging.getLogger(__name__)


class botlist(commands.Cog):
    """commands that are bot related."""

    def __init__(self, bot: Obsidion) -> None:
        """Init."""
        self.bot = bot
        self.session = bot.http_session

        # bot lists
        self.dblpy = dbl.DBLClient(
            self.bot,
            constants.Discord_bot_list.dbl_token,
            autopost=True,
        )

        self.botsfordiscord.start()
        self.discord_boats.start()
        self.discord_bot_list.start()
        self.discord_labs.start()
        # self.bots_on_discord.start()

    @tasks.loop(minutes=30.0)
    async def botsfordiscord(self) -> None:
        """Bots for discord."""
        await self.bot.wait_until_ready()
        headers = {
            "Content-Type": "application/json",
            "Authorization": constants.Discord_bot_list.bots4discord_token,
        }
        json = {"server_count": len(self.bot.guilds)}

        await self.session.post(
            f"https://botsfordiscord.com/api/bot/{constants.Bot.clientid}",
            headers=headers,
            json=json,
        )

    @tasks.loop(minutes=30.0)
    async def discord_boats(self) -> None:
        """Discord boats."""
        await self.bot.wait_until_ready()
        headers = {
            "Authorization": constants.Discord_bot_list.discordboats_token,
        }
        json = {"server_count": len(self.bot.guilds)}

        await self.session.post(
            f"https://discord.boats/api/bot/{constants.Bot.clientid}",
            headers=headers,
            json=json,
        )

    @tasks.loop(minutes=30.0)
    async def discord_bot_list(self) -> None:
        """Discord bot list."""
        await self.bot.wait_until_ready()
        headers = {
            "Content-Type": "application/json",
            "Authorization": constants.Discord_bot_list.discordbotlist_token,
        }
        json = {"guilds": len(self.bot.guilds)}

        await self.session.post(
            f"https://discordbotlist.com/api/v1/bots/{constants.Bot.clientid}/stats",
            headers=headers,
            json=json,
        )

    @tasks.loop(minutes=30.0)
    async def discord_labs(self) -> None:
        """Discord labs."""
        await self.bot.wait_until_ready()
        headers = {
            "token": constants.Discord_bot_list.discodlabs_token,
        }
        json = {"server_count": len(self.bot.guilds)}

        await self.session.post(
            f"https://bots.discordlabs.org/v2/bot/{constants.Bot.clientid}/stats",
            headers=headers,
            json=json,
        )

    @tasks.loop(minutes=30.0)
    async def bots_on_discord(self) -> None:
        """Bots on discord."""
        await self.bot.wait_until_ready()
        headers = {
            "Content-Type": "application/json",
            "Authorization": constants.Discord_bot_list.botsondiscord_token,
        }
        json = {"guildCount": len(self.bot.guilds)}

        await self.session.post(
            f"https://bots.ondiscord.xyz/bot-api/bots/{constants.Bot.clientid}",
            headers=headers,
            json=json,
        )
