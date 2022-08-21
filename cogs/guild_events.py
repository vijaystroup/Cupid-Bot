# IMPORTS
import discord
from discord.ext import commands
import logging
from logging import debug, info, warning, error, critical
import mysql.connector as mysql
import dbconnection as db

# logging
log = logging.getLogger('discord')

class Guild_Events(commands.Cog):
    def  __init__(self, client):
        self.client = client

    # ON_GUILD_JOIN
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            db.c.execute("INSERT INTO guild (guild_id, name, is_leaderboard_set) \
                VALUES (%s, %s, 0)", (guild.id, str(guild.name)))
            db.conn.commit()
        except mysql.Error as e:
            log.error('on_guild_join() row already exists in table. This should not happen.')
            return

    # ON_GUILD_REMOVE
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        # delete players in guild from marriage table
        try:
            db.c.execute("DELETE FROM marriage WHERE guild_id=%s", (guild.id,))
            db.conn.commit()
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")

        # delete players xp for that guild
        try:
            db.c.execute("DELETE FROM xp WHERE guild_id=%s", (guild.id,))
            db.conn.commit()
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")

        # delete row from guild table
        try:
            db.c.execute("DELETE FROM guild WHERE guild_id=%s", (guild.id,))
            db.conn.commit()
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")


    # ON_MEMBER_JOIN
    @commands.Cog.listener()
    async def on_member_join(self, member):
        member_name = str(member)

        # make sure user is not already in player table. if not, add them
        db.c.execute("SELECT 1 FROM player WHERE player_id=%s", 
            (member.id,))
        if db.c.fetchone() == None:
            db.c.execute("INSERT INTO player (player_id, name) VALUES (%s, %s)", 
                (member.id, member_name))
            db.c.execute("INSERT INTO xp (player_id, guild_id, xp) \
                VALUES (%s, %s, 0)", (member.id, member.guild.id))
            db.conn.commit()

    # ON_MEMBER_REMOVE
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.id == self.client.user.id:
            return

        try:
            # delete marriage
            db.c.execute("DELETE FROM marriage WHERE (player_id = %s OR \
                spouse_id = %s) AND guild_id = %s", 
                (member.id, member.id, member.guild.id))

            db.conn.commit()
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")
            return

        try:
            # delete xp for that guild
            db.c.execute("DELETE FROM xp WHERE player_id = %s \
                AND guild_id =  %s", (member.id, member.guild.id))
            db.conn.commit()
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")
            return



    # ON_MESSAGE
    @commands.Cog.listener()
    async def on_message(self, messsage):
        # ignore messages bot sends
        if messsage.author == self.client.user:
            return

        # check to make sure bot wasn't invited when offline
        db.c.execute("SELECT guild_id FROM guild WHERE guild_id=%s",
                (messsage.guild.id,))
        if db.c.fetchone() == None:
            db.c.execute("INSERT INTO guild (guild_id, name, is_leaderboard_set) \
            VALUES (%s, %s, 0)", (messsage.guild.id, str(messsage.guild.name)))
        db.conn.commit()

        # when someone sends a message, give them xp
        await self.add_xp(messsage.author.id, messsage)

    async def add_xp(self, discord_id, messsage):
        member_name = str(messsage.author)

        # check to make sure user is in player table: if not, add them
        db.c.execute("SELECT 1 FROM player WHERE player_id=%s", 
            (discord_id,))
        if db.c.fetchone() == None:
            # insert into player table
            db.c.execute("INSERT INTO player (player_id, name) \
                VALUES (%s, %s)", 
                (discord_id, member_name))
        
        # check to see if user is in xp table | guild: if not, add them
        db.c.execute("SELECT 1 FROM xp WHERE player_id = %s AND guild_id = %s",
            (discord_id, messsage.guild.id))
        if db.c.fetchone() == None:
            db.c.execute("INSERT INTO xp (player_id, guild_id, xp) \
                VALUES (%s, %s, 1)", (discord_id, messsage.guild.id))

        # add 1 xp per message
        db.c.execute("UPDATE xp SET xp=xp+1 WHERE player_id=%s AND guild_id = %s",
            (discord_id, messsage.guild.id))

        db.conn.commit()

        # if users are married, update their marriage score per message
        try:
            db.c.execute("SELECT 1 FROM marriage WHERE (player_id = %s OR \
                spouse_id = %s) AND guild_id = %s",
                (messsage.author.id, messsage.author.id, messsage.guild.id))
            if db.c.fetchone() == None:
                return

            await self.update_marriage_score(messsage)
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")
            return

    async def update_marriage_score(self, messsage):
        try:
            # get author partner
            db.c.execute("SELECT player_id, spouse_id FROM marriage \
                WHERE (player_id = %s OR spouse_id = %s) AND guild_id = %s",
                (messsage.author.id, messsage.author.id, messsage.guild.id))
            select_return = db.c.fetchone()
            if messsage.author.id == select_return[0]:
                playerpartner = select_return[1]
            else:
                playerpartner = select_return[0]

            db.c.execute("SELECT SUM(xp) FROM xp WHERE player_id IN (%s, %s) AND \
                guild_id = %s", (messsage.author.id, playerpartner, 
                messsage.guild.id))
            xpSum = db.c.fetchone()[0]

            # update author's marriage score
            db.c.execute("UPDATE marriage set marriage_score = %s \
                WHERE (player_id = %s OR spouse_id = %s) AND guild_id = %s", 
                (xpSum, messsage.author.id, messsage.author.id, messsage.guild.id))

            db.conn.commit()
        except mysql.Error as e:
            log.error(f"Error message: {e.msg}")
            log.error(f"Error: {e}")
            return

    # COMMAND ERROR HANDLING
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        log.warning(f'{error} does not exist from {ctx.author}'
	       f' on guild {ctx.author.guild.id}')

def setup(client):
    client.add_cog(Guild_Events(client))
