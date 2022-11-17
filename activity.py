from discord.ext import commands, tasks
import discord.utils
from pd.pd import pd
import asyncio
from datetime import datetime as dt


def setup(bot):
    l = activity_cog(bot)
    bot.add_cog(l)
    print('activity cog loaded')

class activity_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pd = pd('activity.json')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot == False:
            return
            g = str(message.guild)
            self._ensure(g, 'last message')
            seld.pd[g]['last message'][str(message.author.id)] = datetime.now()

    @commands.command()
    async def activity(self, ctx, *args):
        if len(args) == 0:
            if not self._can_execute(ctx): 
                return
            roles = self._get_roles(ctx.guild.id)
            if len(roles) == 0:
                await self.bot.send(ctx, 'no roles set to tack. use `.activity -r <role> <role> ...`')
            def foo(r):
                r = discord.utils.get(ctx.guild.roles, id = r)
                r = self._role_pipeline(r)
                return self._pretty_print(r)
            msg = '\n'.join([foo(role) for role in roles])
            await self.bot.send(ctx, msg)
        elif args[0] == '-r':
            msg = self._set_roles(ctx.guild.id, [int(x) for x in args[1:]])
            await self.bot.send(ctx, msg)
        elif args[0] == '-s':
            await self._scan(ctx)
        elif args[0] == 'report':
            await self.pprint(ctx)

    def member_is_tracked(self, m, r):
        for i in m.roles:
            if i.id in r:
                return True
        return False

    async def _scan(self, ctx):
        mf = '%Y%m%d %H:%M'
        msg = await self.bot._send(ctx, 'hold my beer, that may take a while')
        roles_to_track = self._get_roles(ctx.guild.id)
        await self.edit_msg(msg, f'\nroles to track: {[str(r) for r in roles_to_track]}')
        cl = ctx.guild.channels
        cn = len(cl)
        guid = str(ctx.guild.id)
        if not guid in self.pd:
            self.pd[guid] = {}
            self.pd.sync()
        if not 'last messages' in self.pd[guid]:
            self.pd[guid]['last messages'] = {}
            self.pd.sync()
        d = self.pd[guid]['last messages']
        for i in d:
            d[i] = dt.strptime(d[i], mf)
        await self.edit_msg(msg, f'\nneed to scan {cn} channels')
        for i in range(cn):
            if isinstance(cl[i], discord.TextChannel):
                await self.edit_msg(msg, f'\nchannel {i+1}/{cn}: {cl[i].name}')
                n = 0
                last = 0
                async for m in cl[i].history(limit = None):
                    n += 1
                    if n > (last + 1000):
                        await self.edit_msg(msg, ' ... ' + str(n))
                        last = n
                    mm = ctx.guild.get_member(m.author.id)
                    if mm:
                        if self.member_is_tracked(mm, roles_to_track):
                            key = str(m.author.id)
                            if key in d:
                                if d[key] < m.created_at:
                                    d[key] = m.created_at
                            else:
                                d[key] = m.created_at
            else:
                await self.edit_msg(msg, f'\nchannel {i+1}/{n}: {cl[i].name}: not a text channel')
        for i in d:
            d[i] = d[i].strftime(mf)
        await self.edit_msg(msg, f'\ndone')
        self.pd.sync()
        await self.pprint(ctx)

    async def edit_msg(self, msg, txt):
        if len(msg.content) + len(txt) < 1900:
            await msg.edit(content = msg.content + txt)
        else:
            msg = await self.bot.send(msg.channel, txt)
        return msg

    async def pprint(self, ctx):
        mf = '%Y%m%d %H:%M'
        guid = str(ctx.guild.id)
        d = self.pd[guid]['last messages']
        sd = {k: {'last': v, 'diff': (dt.now() - dt.strptime(v, mf)).seconds} for k, v in d.items()}
        nsd = sorted(sd.items(), key = lambda x: x[1]['diff'])
        ar = [f'{ctx.guild.get_member(int(k)).name}: {v["last"]}, {v["diff"]//60//24} days' for k, v in nsd]
        msg = ''
        for i in ar:
            if len(msg) + len(i) < 1900:
                msg += '\n' + i
            else:
                await self.bot.send(ctx, '```\n' + msg + '```')
                msg = ''
        if len(msg) > 0:
            await self.bot.send(ctx, '```\n' + msg + '```')

    def _can_execute(self, ctx):
        return ctx.message.author.id == ctx.guild.owner.id

    def _get_roles(self, id):
        id = str(id)
        if id in self.pd:
            return self.pd[id]['roles']
        else:
            return []

    def _set_roles(self, id, roles):
        id = str(id)
        if not id in self.pd:
            self.pd[id] = {}
        self.pd[id]['roles'] = roles
        self.pd.sync()
        return 'ok'

    def _member_pipeline(self, m):
        return {str(m): None}

    def _role_pipeline(self, role):
        return {str(role): [self._member_pipeline(m) for m in role.members]}
        return {str(role): {str(m): self._member_pipeline(m) for m in role.members}}

    def _pretty_print(self, d):
        return str(d)

