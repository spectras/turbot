import asyncio
import discord
import logging

logger = logging.getLogger(__name__)


class Reply(object):
    """ Abstract out the way commands generate output """

    def __init__(self, client, message):
        self.client = client
        self.message = message
        self.guild = message.guild
        self.channel = message.channel
        self.user = message.author

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    async def notify(self):
        pass

    async def send(self, *args, **kwargs):
        raise NotImplementedError

    async def error(self, text):
        return await self.send(text)

    async def delete_message(self, message):
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.HTTPException as exc:
            logger.warning('could not delete message in channel %s: %s' % (message.channel.name, exc))


class DirectReply(Reply):
    """ Reply object that send answers back through a direct message """

    async def notify(self):
        await self.user.trigger_typing()

    async def send(self, *args, **kwargs):
        if isinstance(self.channel, discord.abc.GuildChannel):
            asyncio.ensure_future(self.delete_message(self.message), loop=self.client.loop)
        return await self.user.send(*args, **kwargs)


class MentionReply(Reply):
    """ Reply object that send answers back through originating channel """

    async def notify(self):
        await self.channel.trigger_typing()

    async def send(self, text, *args, **kwargs):
        if isinstance(self.channel, discord.abc.GuildChannel):
            text = '%s: %s' % (self.user.mention, text)
        return await self.channel.send(text, *args, **kwargs)

class DeleteAndMentionReply(MentionReply):
    """ Reply object that send answers back through originating channel """

    async def __aexit__(self, exc_type, exc_value, traceback):
        if isinstance(self.channel, discord.abc.GuildChannel):
            await self.delete_message(self.message)

    async def error(self, text):
        message = await self.send(text)
        if isinstance(self.channel, discord.abc.GuildChannel):
            asyncio.ensure_future(self.delete_after(message, 10), loop=self.client.loop)
        return message

    async def delete_after(self, message, delay):
        await asyncio.sleep(delay, loop=self.client.loop)
        await self.delete_message(message)
