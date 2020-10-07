"""Main bot file."""

import asyncio
import datetime
import logging
import socket
from typing import Optional

import aiohttp
import aioredis
import asyncpg
import discord
from discord.ext import commands

from . import constants
from .async_stats import AsyncStatsClient
from .core.global_checks import init_global_checks
from .utils.utils import create_db

log = logging.getLogger(__name__)

__all__ = ["Obsidion"]


class Obsidion(commands.AutoShardedBot):
    """Main bot autosharded class."""

    def __init__(self, *args: str, **kwargs: str) -> None:
        """Initialise bot and start conections to services."""
        super().__init__(*args, **kwargs)

        self.http_session: Optional[aiohttp.ClientSession] = None
        self.redis_session: Optional[aioredis.Redis] = None
        self.redis_ready = asyncio.Event()
        self.redis_closed = False
        self.db_pool: asyncpg.Pool = None
        self.db_ready = asyncio.Event()

        self._connector = None
        self._resolver = None

        self.uptime: datetime.datetime

        statsd_url = constants.Stats.statsd_host

        if not constants.Stats.enabled:
            # Since statsd is UDP, there are no errors for sending to a down port.
            # For this reason, setting the statsd host to 127.0.0.1 for development
            # will effectively disable stats.
            statsd_url = "127.0.0.1"

        self.stats = AsyncStatsClient(self.loop, statsd_url, 8125, prefix="obsidion")
        # Do basic checks on every command
        init_global_checks(self)

    async def _create_db_pool(self) -> None:
        """Create the postgres connection pool."""
        self.db_pool = await asyncpg.create_pool(
            database=constants.Database.database,
            user=constants.Database.username,
            password=constants.Database.password,
            host=constants.Database.host,
            port=constants.Database.port,
        )

        # Check wether the database has to be created.
        if not await self.db_pool.fetchval("SELECT to_regclass('public.discord_user')"):
            await create_db(self.db_pool)

        self.db_ready.set()

    async def _create_redis_session(self) -> None:
        """Create the Redis connection pool.

        If constants.Redis.use_fakeredis is True, we'll set up a fake redis pool instead
        of attempting to communicate with a real Redis server. This is useful because it
        means contributors don't necessarily need to get Redis running locally just
        to run the bot. The fakeredis cache won't have persistence across restarts,
        but that usually won't matter for local bot testing.
        """
        if not constants.Redis.enabled:
            # Only use in dev as dev dependancy
            import fakeredis.aioredis

            log.info(
                "Using fakeredis instead of communicating with a real Redis server."
            )
            self.redis_session = await fakeredis.aioredis.create_redis_pool()
        else:
            self.redis_session = await aioredis.create_redis_pool(
                address=(constants.Redis.host, constants.Redis.port),
            )

        self.redis_closed = False
        self.redis_ready.set()

    async def login(self, *args: str, **kwargs: str) -> None:
        """Re-create the connector and set up sessions before logging into Discord."""
        self._recreate()
        await self.stats.create_socket()
        await super().login(*args, **kwargs)
        self.uptime = datetime.datetime.now()

    async def close(self) -> None:
        """Close the Discord connection and aiohttp."""
        await super().close()

        if self.http_session:
            await self.http_session.close()

        if self._connector:
            await self._connector.close()

        if self._resolver:
            await self._resolver.close()

        if self.stats._transport:
            self.stats._transport.close()

        if self.redis_session:
            self.redis_closed = True
            self.redis_session.close()
            self.redis_ready.clear()
            await self.redis_session.wait_closed()

    def _recreate(self) -> None:
        """Re-create the connector, aiohttp session.

        the APIClient and the Redis session. Use asyncio for DNS resolution
        instead of threads so threads aren't spammed.
        """
        self._resolver = aiohttp.AsyncResolver()

        # Its __del__ does send a warning but it doesn't always show up for some reason.
        if self._connector and not self._connector._closed:
            log.warning(
                (
                    "The previous connector was not closed; it will remain ",
                    "open and be overwritten",
                )
            )

        if self.redis_session and not self.redis_session.closed:
            log.warning(
                (
                    "The previous redis pool was not closed; it will ",
                    "remain open and be overwritten",
                )
            )

        # Create the redis session
        self.loop.create_task(self._create_redis_session())

        # Create the postgres pool
        self.loop.create_task(self._create_db_pool())

        # Use AF_INET as its socket family to prevent HTTPS related
        # problems both locally and in production.
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            family=socket.AF_INET,
        )

        # Client.login() will call HTTPClient.static_login()
        # which will create a session using this connector attribute.
        self.http.connector = self._connector

        # Its __del__ does send a warning but it doesn't always show up for some reason.
        if self.http_session and not self.http_session.closed:
            log.warning(
                (
                    "The previous session was not closed; it will ",
                    "remain open and be overwritten",
                )
            )

        self.http_session = aiohttp.ClientSession(connector=self._connector)

    async def get_context(self, message: discord.Message) -> None:
        """Get context."""
        return await super().get_context(message)

    async def process_commands(self, message: discord.Message) -> None:
        """Ignore messages from bots."""
        if not message.author.bot:
            ctx = await self.get_context(message)
            await self.invoke(ctx)
        else:
            ctx = None

    async def logout(self) -> None:
        """Logs out of Discord and closes all connections."""
        await super().logout()
