# IMPORTS
import asyncio
import discord
from discord.ext import commands
from guild_events import Guild_Events
import mysql.connector as mysql
import dbconnection as db
from time import time

class Client_Commands(commands.Cog):
    def  __init__(self, client):
        self.client = client

    # HELP CMD
    @commands.command()
    async def help(self, ctx, bot):
        # check if bot has nickname
        if '!' in bot:
            bot_id = int(bot[3:-1])
        else:
            bot_id = int(bot[2:-1])

        # check to make sure @user is the bot
        if bot_id != self.client.user.id:
            return

        # send our help message
        await ctx.send(f'```Help for {self.client.user}\n\nClient Commands:\n'
            '\t.marry <@proposee> - marry another user\n\t.divorce - divorce '
            'your partner\n\t.couples - view a large list of the top couples '
            '\nAdmin Commands (Administrator Permissions):\n\t.startleaderboard'
            ' - auto-updating couples leaderboard\n\t.stopleaderboard - stops '
            'the leaderboard from updating```')

    # MARRY CMD
    @commands.command()
    async def marry(self, ctx, proposee):
        message_id = ctx.message.id
        # check if proposee has nickname
        if '!' in proposee:
            proposee_id = int(proposee[3:-1])
        else:
            proposee_id = int(proposee[2:-1])

        # check to make sure suitor is not trying to marry themselves
        if ctx.message.author.id == proposee_id:
            await ctx.send(f"You can't marry yourself {ctx.author.mention},"
                " you silly goose.")
            return

        # check to make sure suitor is not trying to marry the bot
        if proposee_id == self.client.user.id:
            await ctx.send(f'{ctx.author.mention}, I am married to the machine'
            ' I run on.')
            return
        # check to make sure the suitor is not married already
        db.c.execute("SELECT player_id, spouse_id FROM marriage \
            WHERE (player_id=%s OR spouse_id = %s) AND guild_id=%s", 
            (ctx.author.id, ctx.author.id, ctx.author.guild.id))
        married_to = db.c.fetchone()
        if married_to != None:
            if ctx.author.id == married_to[0]:
                married_to = married_to[1]
            else:
                married_to = married_to[0]
            await ctx.send(f'{ctx.author.mention}, you are already married to'
                f' {self.client.get_user(married_to).mention}. If you wish to'
                ' leave them, type **.divorce.**')
            return
        # check to make sure the proposee is in database
        db.c.execute("SELECT player_id FROM xp WHERE player_id=%s AND guild_id=%s", 
            (proposee_id, ctx.author.guild.id))
        proposee_married_to = db.c.fetchone()

        if proposee_married_to == None:
            await ctx.send(f'Sorry {ctx.author.mention}, '
                f'{self.client.get_user(proposee_id).mention} is not'
                ' eligible for marriage yet - they are considered inactive'
                ' since they have not sent a message after I\'ve been'
                ' here.')
            return
        # check to make sure the proposee is not married already
        db.c.execute("SELECT spouse_id FROM marriage WHERE player_id=%s AND \
                guild_id=%s",
            (proposee_id, ctx.guild.id))
        proposee_status = db.c.fetchone()
        
        if proposee_status != None: 
            await ctx.send(f'Sorry {ctx.author.mention}, '
                f'{self.client.get_user(proposee_id).mention} is already'
                f' married to'
                f' {self.client.get_user(proposee_status[0]).mention}')
            return

        # create reactions to allow user easily access to react
        await ctx.message.add_reaction('✅')
        await ctx.message.add_reaction('❌')


        # alert proposee to confirm or deny
        confirmation = await ctx.send(f'{self.client.get_user(proposee_id).mention},'
            f'react to accept or deny {ctx.author.mention}\'s proposal.')

        def check(reaction, user):
            return (user.id == proposee_id and str(reaction.emoji) == '✅' 
            and reaction.message.id == message_id or user.id == proposee_id and 
            str(reaction) == '❌' and reaction.message.id == message_id)

        # check to make sure proposee reacted with one of the two
        # options
        try:
            reaction, user = await self.client.wait_for('reaction_add', 
                timeout=60.0, check=check)

            if str(reaction) == '✅':
                db.c.execute("INSERT INTO marriage \
                    (player_id, spouse_id, guild_id, marriage_date, marriage_score) \
                    VALUES (%s, %s, %s, %s, 0)",
                    (ctx.author.id, proposee_id, ctx.author.guild.id, time()))

                # update combined marriage score
                update_marriage_score = Guild_Events(self.client)
                await update_marriage_score.update_marriage_score(ctx)
                db.conn.commit()
                await confirmation.edit(content=f'Congratulations! '
                    f'{ctx.author.mention} and '
                    f'{self.client.get_user(proposee_id).mention} are now '
                    'married!')
            else:
                await confirmation.edit(content=f'Sorry {ctx.author.mention},'
                    f' {self.client.get_user(proposee_id).mention}'
                    f' has said no to marrying you.')
            return
        except asyncio.TimeoutError:
            await confirmation.edit(
                content=f'{self.client.get_user(proposee_id).mention} did not '
                'react in time.')
            return

    # DIVORCE CMD
    @commands.command()
    async def divorce(self, ctx):
        message_id = ctx.message.id

        # check to make sure user is married
        db.c.execute("SELECT player_id, spouse_id FROM marriage WHERE \
            (player_id=%s OR spouse_id = %s) AND guild_id = %s", 
            (ctx.author.id, ctx.author.id, ctx.guild.id))
        married_to = db.c.fetchone()
        if married_to == None:
            await ctx.send(f'{ctx.author.mention}, you can\'t use that command'
                ' until you are married.')
            return
        elif ctx.author.id == married_to[0]:
            married_to = married_to[1]
        else:
            married_to = married_to[0]

        # create reactions to allow user easily access to react
        await ctx.message.add_reaction('✅')

        # send message to confirm divorce
        confirm = await ctx.send(f'{ctx.author.mention}, react to confirm your'
            f' divorce with {self.client.get_user(married_to).mention}.')

        # reaction confirmation
        def check(reaction, user):
            return (user.id == ctx.author.id and str(reaction.emoji) == '✅'
                and reaction.message.id == message_id)
        try:
            reaction, user = await self.client.wait_for('reaction_add', 
                timeout=60.0, check=check)

            db.c.execute("DELETE FROM marriage WHERE (player_id=%s OR spouse_id = %s) \
                AND guild_id = %s", 
                (ctx.author.id, ctx.author.id, ctx.guild.id))
            db.conn.commit()

            # edit message confirming divorce
            await confirm.edit(content=f'{ctx.message.author.mention} and '
                f'{self.client.get_user(married_to).mention} are now divorced.')
            return
        except asyncio.TimeoutError:
            await confirm.edit(content=f'{ctx.message.author.mention} did not '
                'react in time.')
            return

    # COUPLES CMD
    @commands.command()
    async def couples(self, ctx):
        embed = discord.Embed(
            colour = discord.Colour.magenta()
            )

        # using this as title of embed since it looks nicer
        embed.set_author(name='Cupid Couples Board', 
            icon_url='https://i.imgur.com/vImzBiU.jpg')

        # get the couples
        sql_statement = (
            'SELECT '
                'player_id, '
                '('
                    'select name '
                    'from player '
                    'where m.player_id = player_id '
                '), '
                'spouse_id, '
                '('
                    'select name '
                    'from player '
                    'where m.spouse_id = player_id '
                '), '
                'marriage_date, '
                'marriage_score '
                'from marriage m '
            'WHERE guild_id = %s '
            'ORDER BY marriage_score DESC'
        )
        db.c.execute(sql_statement, (ctx.guild.id,))

        couples = db.c.fetchmany(21)

        i = 0
        # looping every other couple in the couples list
        for couple in couples:
            if i > 20:
                # if more couples exist, add footer
                embed.set_footer(text='+ more!')
                return

            # if time is less than 1 day, send < 1 day
            if round((time() - couple[4]) / 86400, 1) < 1.0:
                married_time = '< 1 day'
            else:
                married_time = f'{round((time() - couple[4]) / 86400, 1)} days'

            # append the field for the couple
            embed.add_field(
                name=f'{couple[1]}  &  {couple[3]}',
                value=f'{couple[5]} points - {married_time}',
                inline=True
                )
            i += 1

        # send the couple board
        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(Client_Commands(client))
    
