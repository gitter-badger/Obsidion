from discord.ext import commands
from obsidion import constants
import discord
from datetime import datetime

from obsidion.bot import Obsidion


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if constants.Channels.new_guild_channel:
            embed = discord.Embed(name=f"{self.bot.user.name} has joined a guild")
            embed.set_footer(
                text=f"Guild: {len(self.bot.guilds):,} | Shard: {guild.shard_id}/{self.bot.shard_count-1}"
            )
            guild_text = (
                f"Name: `{guild.name}`\n"
                f"ID: `{guild.id}`\n"
                f"Owner ID: `{guild.owner.id}`\n"
            )

            embed.add_field(name="Guild", value=guild_text)
            embed.add_field(name="Region", value=guild.region)
            embed.timestamp = datetime.now()
            if guild.icon_url:
                embed.set_thumbnail(url=guild.icon_url)
            else:
                embed.set_thumbnail(url="https://i.imgur.com/AFABgjD.png")
            channel = self.bot.get_channel(constants.Channels.new_guild_channel)
            await channel.send(embed=embed)


def setup(bot: Obsidion) -> None:
    """Add `News` cog."""
    bot.add_cog(Events(bot))