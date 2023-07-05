from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

class Sus_commands(commands.Cog, name="sus_commands"):
    def __init__(self,bot):
        self.bot=bot

    @commands.command(
        name="ownerCheck",
        description="This is a testing command that does nothing.",
    )
    # This will only allow non-blacklisted members to execute the command
    @checks.not_blacklisted()
    # This will only allow owners of the bot to execute the command -> config.json
    @checks.is_owner()
    async def ownerCheck(self, context: Context):
        """
        This is a testing command that does nothing.

        :param context: The application command context.
        """
        # Do your stuff here

        # Don't forget to remove "pass", I added this just because there's no content in the method.
        pass

async def setup(bot):
    await bot.add_cog(Sus_commands(bot))