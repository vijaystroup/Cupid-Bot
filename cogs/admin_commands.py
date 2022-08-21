# IMPORTS
import asyncio
import discord
from discord.ext import commands
import mysql.connector as mysql
import dbconnection as db
from PIL import Image, ImageDraw, ImageFont
from time import time

class Admin_Commands(commands.Cog):
    def  __init__(self, client):
        self.client = client

    # START_LEADERBOARD CMD
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def startleaderboard(self, ctx):
        # make sure leaderboard has not already been set
        db.c.execute("SELECT is_leaderboard_set FROM guild WHERE \
            guild_id=%s", (ctx.guild.id,))
        has_leaderboard_set = db.c.fetchone()[0]

        if has_leaderboard_set:
            lboard_start_msg = await ctx.send('You can not use that '
                'command if you already have a leaderboard started. Try '
                'typing **.stopleaderboard** first.')
            # delete the message after 10 seconds
            await lboard_start_msg.delete(delay=10.0)
            return

        # check to make sure there are at least three couples
        db.c.execute("SELECT player_id FROM marriage WHERE guild_id=%s",
            (ctx.guild.id,))
        
        rows = db.c.fetchmany(3)
        if len(rows) != 3:
            await ctx.send('You can not use that command till there are '
                'three couples.')
            return

        # if all passed, set leaderboard_set to 1(True)
        db.c.execute("UPDATE guild set is_leaderboard_set=1 \
            WHERE guild_id=%s", (ctx.guild.id,))
        db.conn.commit()

        await self.update_leaderboard(ctx)

    # STOP_LEADERBOARD CMD
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def stopleaderboard(self, ctx):
        # check to make sure set_leaderboard is not 0(False)
        db.c.execute("SELECT is_leaderboard_set FROM guild WHERE \
            guild_id=%s", (ctx.guild.id,))
        has_leaderboard_set = db.c.fetchone()[0]
        if not has_leaderboard_set:
            lboard_stop_msg = await ctx.send('You can not use that command'
            ' if you do not have a leaderboard started. Try typing'
            ' **.startleaderboard** first.')
            # delete the message after 10 seconds
            await lboard_stop_msg.delete(delay=10.0)
            return

        # update set_leaderboard to 0(False)
        db.c.execute("UPDATE guild set is_leaderboard_set=0 \
            WHERE guild_id=%s", (ctx.guild.id,))
        db.conn.commit()

    # UPDATE LEADERBOARD
    async def update_leaderboard(self, ctx):
        # loop image and send to chat
        while True:
            # check to make sure set_leaderboard is not 0(False). if 
            # yes, break
            db.c.execute("SELECT is_leaderboard_set FROM guild WHERE \
            guild_id=%s", (ctx.guild.id,))
            is_leaderboard_set = db.c.fetchone()[0]
            if not is_leaderboard_set:
                break

            # send leaderboard
            await self.draw_leaderboard(ctx.guild.id)
            board = await ctx.send(file=discord.File(f'leaderboards/leaderboard_{ctx.guild.id}.png'))
            await asyncio.sleep(60)
            await board.delete()
        # return from function after loop is broken
        return

    # LEADERBOARD PICTURE
    async def draw_leaderboard(self, guild_id):
        # select info needed for drawing
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
        db.c.execute(sql_statement, (guild_id,))
        board = db.c.fetchmany(3)

        # setting up image
        image = Image.open('background.png')
        font_names = ImageFont.truetype('Lato-RegularItalic.ttf', size=35)
        font_score = ImageFont.truetype('Lato-RegularItalic.ttf', size=25)
        draw = ImageDraw.Draw(image)

        # -1st Place-
        # couples names
        names_first = f'{board[0][1]}  &  {board[0][3]}'

        # getting marriage time
        married_for_first = round((time() - board[0][4]) / 86400, 1)

        # if couples married less than 1 day, marraige time < 1d
        if married_for_first < 1.0:
            score_first = f'{board[0][5]} points  -  < 1 day'
        else:
            score_first = f'{board[0][5]} points  -  {married_for_first} days'

        # draw onto image
        draw.text((200, 95), names_first, fill=(255,190,0), font=font_names)
        draw.text((200, 135), score_first, fill=(0,0,0), font=font_score)

        # -2nd Place-
        # couples names
        names_second = f'{board[1][1]}  &  {board[1][3]}'

        # getting marriage time
        married_for_second = round((time() - board[1][4]) / 86400, 1)

        # if couples married less than 1 day, marraige time < 1d
        if married_for_second < 1.0:
            score_second = f'{board[1][5]} points  -  < 1 day'
        else:
            score_second = f'{board[1][5]} points  -  {married_for_second} days'

        # draw onto image
        draw.text((200, 220), names_second, fill=(112,112,112), font=font_names)
        draw.text((200, 260), score_second, fill=(0,0,0), font=font_score)

        # -3rd Place-
        # couples names
        names_third = f'{board[2][1]}  &  {board[2][3]}'

        # getting marriage time
        married_for_third = round((time() - board[2][4]) / 86400, 1)

        # if couples married less than 1 day, marraige time < 1d
        if married_for_third < 1.0:
            score_third = f'{board[2][5]} points  -  < 1 day'
        else:
            score_third = f'{board[2][5]} points  -  {married_for_third} days'

        # draw onto image
        draw.text((200, 355), names_third, fill=(179,94,27), font=font_names)
        draw.text((200, 395), score_third, fill=(0,0,0), font=font_score)

        # save the image
        image.save(f'leaderboards/leaderboard_{guild_id}.png')

def setup(client):
    client.add_cog(Admin_Commands(client))
