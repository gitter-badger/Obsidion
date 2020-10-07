"""Info cogs."""

import base64
from datetime import datetime
import io
import json
import logging
from typing import Optional, Tuple

import discord
from discord.ext import commands

from obsidion import constants
from obsidion.bot import Obsidion
from obsidion.utils.utils import (
    ApiError,
    get,
    get_username,
    player_info,
    usernameToUUID,
)

log = logging.getLogger(__name__)


class Info(commands.Cog):
    """Commands that are bot related."""

    def __init__(self, bot: Obsidion) -> None:
        """Initialise the bot."""
        self.bot = bot

    @commands.command(
        aliases=["whois", "p", "names", "namehistory", "pastnames", "namehis"]
    )
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def profile(self, ctx: commands.Context, username: str = None) -> None:
        """View a players Minecraft UUID, Username history and skin."""
        await ctx.channel.trigger_typing()
        username = await get_username(self.bot, username, ctx.author.id)
        if not username:
            await ctx.send("Please provide a username or link one using account link.")
            await ctx.send_help(ctx.command)
            return
        try:
            uuid = await usernameToUUID(username, self.bot)
        except ApiError:
            await ctx.send(f"The username `{username}` is not currently in use.")
            return

        long_uuid = f"{uuid[0:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

        names = await player_info(uuid, self.bot)

        name_list = ""
        for name in names[::-1][:-1]:
            name1 = name["name"]
            date = datetime.utcfromtimestamp(
                int(str(name["changedToAt"])[:-3])
            ).strftime("%b %d, %Y")
            name_list += (
                f"**{names.index(name)+1}."  # pytype: disable=attribute-error
                + f"** `{name1}` - {date} "
                + "\n"
            )
        original = names[0]["name"]
        name_list += f"**1.** `{original}` - First Username"

        uuids = "Short UUID: `" + uuid + "\n" + "`Long UUID: `" + long_uuid + "`"
        information = ""
        information += f"Username Changes: `{len(names)-1}`\n"

        embed = discord.Embed(title=f"Minecraft profile for {username}", color=0x00FF00)

        embed.add_field(name="UUID's", inline=False, value=uuids)
        embed.add_field(
            name="Textures",
            inline=True,
            value=f"Skin: [Open Skin](https://visage.surgeplay.com/bust/{uuid})",
        )
        embed.add_field(name="Information", inline=True, value=information)
        embed.add_field(name="Name History", inline=False, value=name_list)
        embed.set_thumbnail(url=(f"https://visage.surgeplay.com/bust/{uuid}"))

        await ctx.send(embed=embed)

    @staticmethod
    def get_server(ip: str, port: int) -> Tuple[str, Optional[int]]:
        """Returns the server icon."""
        if ":" in ip:  # deal with them providing port in string instead of seperate
            ip, port = ip.split(":")
            return (ip, int(port))
        if port:
            return (ip, port)
        return (ip, None)

    @commands.command()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def server(
        self, ctx: commands.Context, server_ip: str = None, port: int = None
    ) -> None:
        """Get info on a minecraft server."""
        await ctx.channel.trigger_typing()
        _server_ip = await self.bot.db_pool.fetchval(
            "SELECT server FROM guild WHERE id = $1", ctx.guild.id
        )
        if not _server_ip and not _server_ip:
            await ctx.send("Please provide a server or link one using serverlink.")
            await ctx.send_help(ctx.command)
            return
        server_ip = _server_ip if _server_ip else server_ip
        url = f"{constants.Bot.api}/server/java"
        server_ip, _port = self.get_server(server_ip, port)
        port = _port if _port else port
        payload = {"server": server_ip}
        key = f"server_{server_ip}"
        if port:
            payload["port"] = port
            key += f":{port}"

        if await self.bot.redis_session.exists(key):
            data = json.loads(await self.bot.redis_session.get(key))
        else:
            try:
                data = await get(ctx.bot.http_session, url, payload)
            except ApiError:
                await ctx.send(
                    f"{ctx.author}, :x: The Java edition Minecraft server `{server_ip}`"
                    " is currently not online or cannot be requested"
                )
                return
            await self.bot.redis_session.set(key, json.dumps(data), expire=300)
        embed = discord.Embed(title=f"Java Server: {server_ip}", color=0x00FF00)
        embed.add_field(name="Description", value=data["description"])

        embed.add_field(
            name="Players",
            value=(
                f"Online: `{data['players']['online']:,}` \n "
                f"Maximum: `{data['players']['max']:,}`"
            ),
        )
        if data["players"]["sample"]:
            names = ""
            for player in data["players"]["sample"]:
                names += f"{player['name']}\n"
            embed.add_field(name="Information", value=names, inline=False)
        embed.add_field(
            name="Version",
            value=(
                f"Java Edition \n Running: `{data['version']['name']}` \n "
                f"Protocol: `{data['version']['protocol']}`"
            ),
            inline=False,
        )
        if data["favicon"]:
            encoded = base64.decodebytes(data["favicon"][22:].encode("utf-8"))
            image_bytesio = io.BytesIO(encoded)
            favicon = discord.File(image_bytesio, "favicon.png")
            embed.set_thumbnail(url="attachment://favicon.png")
            await ctx.send(embed=embed, file=favicon)
        else:
            embed.set_thumbnail(
                url=(
                    "https://media.discordapp.net/attachments/493764139290984459"
                    "/602058959284863051/unknown.png"
                )
            )
            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def serverpe(
        self, ctx: commands.Context, server_ip: str = None, port: int = None
    ) -> None:
        """Get info on a minecraft PE server."""
        await ctx.channel.trigger_typing()
        _server_ip = await self.bot.db_pool.fetchval(
            "SELECT server FROM guild WHERE id = $1", ctx.guild.id
        )
        if not _server_ip and not _server_ip:
            await ctx.send("Please provide a server or link one using serverlink.")
            await ctx.send_help(ctx.command)
            return
        server_ip = _server_ip if _server_ip else server_ip
        url = f"{constants.Bot.api}/server/bedrock"
        server_ip, _port = self.get_server(server_ip, port)
        if _port:
            port = _port

        payload = {"server": server_ip}

        key = f"bserver_{server_ip}"
        if port:
            payload["port"] = port
            key += f":{port}"

        if await self.bot.redis_session.exists(key):
            data = json.loads(await self.bot.redis_session.get(key))
        else:
            try:
                data = await get(ctx.bot.http_session, url, payload)
            except ApiError:
                await ctx.send(
                    f"{ctx.author}, :x: The Bedrock edition Minecraft "
                    f"server `{server_ip}`"
                    " is currently not online or cannot be requested"
                )
                return
            self.bot.redis_session.set(key, json.dumps(data), expire=300)
        embed = discord.Embed(title=f"Bedrock Server: {server_ip}", color=0x00FF00)
        embed.add_field(name="Description", value=data["motd"])

        embed.add_field(
            name="Players",
            value=(
                f"Online: `{data['players']['online']:,}` \n Maximum: "
                f"`{data['players']['max']:,}`"
            ),
        )
        embed.add_field(
            name="Version",
            value=(
                f"Bedrock Edition \n Running: `{data['software']['version']}` "
                f"\n Map: `{data['map']}`"
            ),
            inline=True,
        )
        if data["players"]["names"]:
            names = ""
            for player in data["players"]["names"][:10]:
                names += f"{player}\n"
            embed.add_field(name="Players Online", value=names, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["sales"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def status(self, ctx: commands.Context) -> None:
        """Check the status of all the Mojang services."""
        await ctx.channel.trigger_typing()
        data = await get(ctx.bot.http_session, f"{constants.Bot.api}/mojang/check")
        sales_mapping = {
            "item_sold_minecraft": True,
            "prepaid_card_redeemed_minecraft": True,
            "item_sold_cobalt": False,
            "item_sold_scrolls": False,
        }
        payload = {"metricKeys": [k for (k, v) in sales_mapping.items() if v]}

        if await self.bot.redis_session.exists("status"):
            sales_data = json.loads(await self.bot.redis_session.get("status"))
        else:
            url = "https://api.mojang.com/orders/statistics"
            async with ctx.bot.http_session.post(url, json=payload) as resp:
                if resp.status == 200:
                    sales_data = await resp.json()
            await self.bot.redis_session.set("status", json.dumps(sales_data))

        services = ""
        for service in data:
            if data[service] == "green":
                services += (
                    f":green_heart: - {service}: **This service is healthy.** \n"
                )
            else:
                services += f":heart: - {service}: **This service is offline.** \n"
        embed = discord.Embed(title="Minecraft Service Status", color=0x00FF00)
        embed.add_field(
            name="Minecraft Game Sales",
            value=(
                f"Total Sales: **{sales_data['total']:,}** Last 24 Hours: "
                f"**{sales_data['last24h']:,}**"
            ),
        )
        embed.add_field(name="Minecraft Services:", value=services, inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=1.0, type=commands.BucketType.user)
    async def mcbug(self, ctx: commands.Context, bug: str = None) -> None:
        """Gets info on a bug from bugs.mojang.com."""
        if not bug:
            await ctx.send(f"{ctx.message.author.mention},  :x: Please provide a bug.")
            return
        await ctx.channel.trigger_typing()
        data = await get(
            ctx.bot.http_session, f"https://bugs.mojang.com/rest/api/latest/issue/{bug}"
        )
        if not data:
            await ctx.send(
                f"{ctx.message.author.mention},  :x: The bug {bug} was not found."
            )
            return
        embed = discord.Embed(
            description=data["fields"]["description"],
            color=0x00FF00,
        )

        embed.set_author(
            name=f"{data['fields']['project']['name']} - {data['fields']['summary']}",
            url=f"https://bugs.mojang.com/browse/{bug}",
        )

        info = (
            f"Version: {data['fields']['project']['name']}\n"
            f"Reporter: {data['fields']['creator']['displayName']}\n"
            f"Created: {data['fields']['created']}\n"
            f"Votes: {data['fields']['votes']['votes']}\n"
            f"Updates: {data['fields']['updated']}\n"
            f"Watchers: {data['fields']['watches']['watchCount']}"
        )

        details = (
            f"Type: {data['fields']['issuetype']['name']}\n"
            f"Status: {data['fields']['status']['name']}\n"
        )
        if data["fields"]["resolution"]["name"]:
            details += f"Resolution: {data['fields']['resolution']['name']}\n"
        if "version" in data["fields"]:
            details += (
                "Affected: "
                f"{', '.join(s['name'] for s in data['fields']['versions'])}\n"
            )
        if "fixVersions" in data["fields"]:
            if len(data["fields"]["fixVersions"]) >= 1:
                details += (
                    f"Fixed Version: {data['fields']['fixVersions'][0]} + "
                    f"{len(data['fields']['fixVersions'])}\n"
                )

        embed.add_field(name="Information", value=info)
        embed.add_field(name="Details", value=details)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=1.0, type=commands.BucketType.user)
    async def wiki(self, ctx: commands.Context, *, query: str) -> None:
        """Get an article from the minecraft wiki."""
        await ctx.channel.trigger_typing()

        def generate_payload(query: str) -> dict:
            """Generate the payload for Gamepedia based on a query string."""
            payload = {
                "action": "query",
                "titles": query.replace(" ", "_"),
                "format": "json",
                "formatversion": "2",  # Cleaner json results
                "prop": "extracts",  # Include extract in returned results
                "exintro": "1",  # Only return summary paragraph(s) before main content
                "redirects": "1",  # Follow redirects
                "explaintext": "1",  # Make sure it's plaintext (not HTML)
            }
            return payload

        base_url = "https://minecraft.gamepedia.com/api.php"
        footer_icon = (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53"
            "/Wikimedia-logo.png/600px-Wikimedia-logo.png"
        )

        payload = generate_payload(query)

        result = await get(ctx.bot.http_session, base_url, params=payload)

        try:
            # Get the last page. Usually this is the only page.
            page = result["query"]["pages"][-1]
            title = page["title"]
            description = page["extract"].strip().replace("\n", "\n\n")
            url = f"https://minecraft.gamepedia.com/{title.replace(' ', '_')}"

            if len(description) > 1500:
                description = description[:1500].strip()
                description += f"... [(read more)]({url})"

            embed = discord.Embed(
                title=f"Minecraft Gamepedia: {title}",
                description=f"\u2063\n{description}\n\u2063",
                color=0x00FF00,
                url=url,
            )
            embed.set_footer(
                text="Information provided by Wikimedia", icon_url=footer_icon
            )
            await ctx.send(embed=embed)

        except KeyError:
            await ctx.send(f"I'm sorry, I couldn't find \"{query}\" on Gamepedia")
