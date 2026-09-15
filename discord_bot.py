"""
Discord Bot Template — 65+ Functions
=====================================
Requirements:
  pip install discord.py

Setup:
  1. Create a bot at https://discord.com/developers/applications
  2. Enable all Privileged Gateway Intents (Server Members, Message Content)
  3. Replace BOT_TOKEN with your token
  4. Replace MOD_LOG_CHANNEL_ID with your mod-log channel ID

Run:
  python discord_bot.py
"""

import discord
from discord.ext import commands, tasks
import datetime
import random
import asyncio
import json
import os
import time

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
PREFIX = "!"
MOD_LOG_CHANNEL_ID = 0       # Replace with your mod-log channel ID
OWNER_ID = 0                 # Replace with your Discord user ID

# ─── INTENTS & BOT SETUP ──────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ─── IN-MEMORY STORES ─────────────────────────────────────────────────────────
warnings = {}          # { user_id: [{"reason": str, "time": str}, ...] }
notes    = {}          # { user_id: [str, ...] }
afk_users = {}         # { user_id: str (reason) }
giveaways = {}         # { message_id: {"end": datetime, "prize": str, "host": int} }
poll_votes = {}        # { message_id: {"yes": set(), "no": set()} }
muted_users = {}       # { user_id: {"guild": int, "until": datetime | None} }
slowmode_channels = {} # { channel_id: int (seconds) }
command_stats = {}     # { command_name: int }
join_times = {}        # { user_id: datetime }
tags = {}              # { tag_name: str }

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def make_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    """Return a styled embed."""
    e = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
    e.set_footer(text=f"{bot.user.name}" if bot.user else "Bot")
    return e


async def log_action(guild: discord.Guild, action: str, moderator: discord.Member, target, reason: str = "No reason given"):
    """Send a moderation log entry to the log channel."""
    channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
    if not channel:
        return
    e = make_embed("🔨 Mod Action", color=discord.Color.orange())
    e.add_field(name="Action",    value=action,               inline=True)
    e.add_field(name="Moderator", value=moderator.mention,    inline=True)
    e.add_field(name="Target",    value=str(target),          inline=True)
    e.add_field(name="Reason",    value=reason,               inline=False)
    await channel.send(embed=e)


def track(command_name: str):
    """Increment usage counter for a command."""
    command_stats[command_name] = command_stats.get(command_name, 0) + 1

# ─── EVENTS ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{len(bot.guilds)} servers | {PREFIX}help"
    ))
    print(f"✅  Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"    Serving {len(bot.guilds)} guilds | {sum(g.member_count for g in bot.guilds)} members")


@bot.event
async def on_member_join(member: discord.Member):
    join_times[member.id] = datetime.datetime.utcnow()
    ch = discord.utils.get(member.guild.text_channels, name="general")
    if ch:
        e = make_embed(
            "👋 Welcome!",
            f"Welcome to **{member.guild.name}**, {member.mention}!\n"
            f"You are member **#{member.guild.member_count}**.",
            discord.Color.green()
        )
        await ch.send(embed=e)


@bot.event
async def on_member_remove(member: discord.Member):
    ch = discord.utils.get(member.guild.text_channels, name="general")
    if ch:
        await ch.send(embed=make_embed("👋 Goodbye", f"**{member}** has left the server.", discord.Color.red()))


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # AFK check — ping someone who is AFK
    for mentioned in message.mentions:
        if mentioned.id in afk_users:
            await message.channel.send(
                f"💤 **{mentioned.display_name}** is AFK: {afk_users[mentioned.id]}"
            )
    # Return from AFK
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back, {message.author.mention}! Removed your AFK status.")
    await bot.process_commands(message)


@bot.event
async def on_command(ctx: commands.Context):
    track(ctx.command.name)


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=make_embed("❌ Permission Denied", "You don't have permission to use this command.", discord.Color.red()))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=make_embed("❌ Missing Argument", f"Usage: `{PREFIX}{ctx.command.name} {ctx.command.signature}`", discord.Color.red()))
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(embed=make_embed("❌ Error", str(error), discord.Color.red()))

# ══════════════════════════════════════════════════════════════════════════════
# ██  GENERAL COMMANDS  (30+)
# ══════════════════════════════════════════════════════════════════════════════

@bot.command(name="help")
async def help_cmd(ctx, category: str = None):
    """Show all commands or a specific category."""
    if category is None:
        e = make_embed("📖 Help Menu", f"Use `{PREFIX}help <category>` for details.")
        e.add_field(name="🔧 General",    value="`ping`, `info`, `avatar`, `serverinfo`, `uptime`, `invite`, `stats`, `roll`, `flip`, `8ball`, `say`, `embed`, `announce`, `poll`, `afk`, `time`, `weather`, `translate`, `remind`, `tag`, `tags`, `deltag`, `calc`, `choose`, `ascii`, `morse`, `reverse`, `wordcount`", inline=False)
        e.add_field(name="🛡 Moderation", value="`kick`, `ban`, `unban`, `mute`, `unmute`, `warn`, `warnings`, `clearwarn`, `note`, `notes`, `purge`, `slowmode`, `lock`, `unlock`, `nickname`, `role`, `unrole`, `move`, `deafen`, `undeafen`, `servermute`, `serverunmute`, `tempban`, `softban`, `massban`, `prune`, `clonevchan`, `hidechannel`, `showchannel`", inline=False)
        e.add_field(name="🎉 Fun / Util", value="`giveaway`, `reroll`, `leaderboard`, `whois`, `joined`, `botinfo`, `userstats`, `cmdstats`, `snipe`, `usercount`", inline=False)
        await ctx.send(embed=e)
    else:
        await ctx.send(f"Detailed help for `{category}` not yet configured.")


@bot.command()
async def ping(ctx):
    """Bot latency."""
    await ctx.send(embed=make_embed("🏓 Pong!", f"Latency: **{round(bot.latency * 1000)} ms**"))


@bot.command()
async def info(ctx):
    """Bot information."""
    e = make_embed("ℹ️ Bot Info")
    e.add_field(name="Library",   value=f"discord.py {discord.__version__}", inline=True)
    e.add_field(name="Guilds",    value=str(len(bot.guilds)), inline=True)
    e.add_field(name="Users",     value=str(sum(g.member_count for g in bot.guilds)), inline=True)
    e.add_field(name="Commands",  value=str(len(bot.commands)), inline=True)
    await ctx.send(embed=e)


@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Show a user's avatar."""
    member = member or ctx.author
    e = make_embed(f"🖼 {member.display_name}'s Avatar")
    e.set_image(url=member.display_avatar.url)
    await ctx.send(embed=e)


@bot.command()
async def serverinfo(ctx):
    """Display server information."""
    g = ctx.guild
    e = make_embed(f"🏰 {g.name}")
    e.set_thumbnail(url=g.icon.url if g.icon else discord.Embed.Empty)
    e.add_field(name="Owner",    value=str(g.owner), inline=True)
    e.add_field(name="Members",  value=str(g.member_count), inline=True)
    e.add_field(name="Channels", value=str(len(g.channels)), inline=True)
    e.add_field(name="Roles",    value=str(len(g.roles)), inline=True)
    e.add_field(name="Created",  value=g.created_at.strftime("%Y-%m-%d"), inline=True)
    e.add_field(name="Boost Lvl",value=str(g.premium_tier), inline=True)
    await ctx.send(embed=e)


@bot.command()
async def uptime(ctx):
    """Show how long the bot has been running."""
    now = datetime.datetime.utcnow()
    delta = now - bot._start_time if hasattr(bot, "_start_time") else datetime.timedelta(0)
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    await ctx.send(embed=make_embed("⏱ Uptime", f"**{h}h {m}m {s}s**"))


@bot.command()
async def invite(ctx):
    """Generate bot invite link."""
    perms = discord.Permissions(administrator=True)
    url = discord.utils.oauth_url(bot.user.id, permissions=perms)
    await ctx.send(embed=make_embed("🔗 Invite", f"[Click here to invite me!]({url})"))


@bot.command()
async def stats(ctx):
    """Runtime stats."""
    e = make_embed("📊 Stats")
    e.add_field(name="Guilds",    value=str(len(bot.guilds)), inline=True)
    e.add_field(name="Users",     value=str(sum(g.member_count for g in bot.guilds)), inline=True)
    e.add_field(name="Latency",   value=f"{round(bot.latency*1000)} ms", inline=True)
    e.add_field(name="Cmds Used", value=str(sum(command_stats.values())), inline=True)
    await ctx.send(embed=e)


@bot.command()
async def roll(ctx, dice: str = "1d6"):
    """Roll dice. Format: NdS (e.g. 2d20)."""
    try:
        n, s = map(int, dice.lower().split("d"))
        results = [random.randint(1, s) for _ in range(min(n, 20))]
        await ctx.send(embed=make_embed("🎲 Dice Roll", f"`{dice}` → **{results}**\nTotal: **{sum(results)}**"))
    except Exception:
        await ctx.send(embed=make_embed("❌ Invalid format", "Use NdS — e.g. `2d20`", discord.Color.red()))


@bot.command()
async def flip(ctx):
    """Flip a coin."""
    result = random.choice(["Heads 🟡", "Tails ⚪"])
    await ctx.send(embed=make_embed("🪙 Coin Flip", result))


@bot.command(name="8ball")
async def eightball(ctx, *, question: str):
    """Ask the magic 8-ball."""
    answers = [
        "It is certain.", "Without a doubt.", "Yes, definitely.", "You may rely on it.",
        "As I see it, yes.", "Most likely.", "Outlook good.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Concentrate and ask again.",
        "Don't count on it.", "My reply is no.", "My sources say no.",
        "Outlook not so good.", "Very doubtful."
    ]
    e = make_embed("🎱 Magic 8-Ball")
    e.add_field(name="Question", value=question, inline=False)
    e.add_field(name="Answer",   value=random.choice(answers), inline=False)
    await ctx.send(embed=e)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, text: str):
    """Make the bot say something."""
    await ctx.message.delete()
    await ctx.send(text)


@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_cmd(ctx, title: str, *, description: str):
    """Send a custom embed. Wrap title in quotes."""
    await ctx.send(embed=make_embed(title, description))


@bot.command()
@commands.has_permissions(manage_guild=True)
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    """Send an announcement to a channel."""
    e = make_embed("📢 Announcement", message, discord.Color.gold())
    e.set_footer(text=f"By {ctx.author}", icon_url=ctx.author.display_avatar.url)
    await channel.send(embed=e)
    await ctx.send(f"✅ Sent announcement to {channel.mention}", delete_after=5)


@bot.command()
async def poll(ctx, question: str, *, options: str = "yes no"):
    """Create a simple poll. Format: !poll "Question" option1 option2"""
    opts = options.split()[:10]
    number_emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    desc = "\n".join(f"{number_emojis[i]} {opt}" for i, opt in enumerate(opts))
    e = make_embed(f"📊 Poll: {question}", desc, discord.Color.blue())
    msg = await ctx.send(embed=e)
    for i in range(len(opts)):
        await msg.add_reaction(number_emojis[i])


@bot.command()
async def afk(ctx, *, reason: str = "AFK"):
    """Set your AFK status."""
    afk_users[ctx.author.id] = reason
    await ctx.send(embed=make_embed("💤 AFK", f"{ctx.author.mention} is now AFK: **{reason}**"))


@bot.command(name="time")
async def time_cmd(ctx):
    """Show current UTC time."""
    now = datetime.datetime.utcnow()
    await ctx.send(embed=make_embed("🕒 Current Time", now.strftime("%A, %B %d %Y — %H:%M:%S UTC")))


@bot.command()
async def remind(ctx, duration: int, unit: str, *, reminder: str):
    """Set a reminder. Units: s/m/h"""
    units = {"s": 1, "m": 60, "h": 3600}
    if unit not in units:
        return await ctx.send("Use s, m, or h for time unit.")
    secs = duration * units[unit]
    await ctx.send(f"⏰ Reminder set for **{duration}{unit}**!")
    await asyncio.sleep(secs)
    await ctx.send(f"⏰ {ctx.author.mention} Reminder: **{reminder}**")


@bot.command()
async def tag(ctx, name: str, *, content: str = None):
    """Set or retrieve a tag."""
    if content:
        tags[name.lower()] = content
        await ctx.send(embed=make_embed("🏷 Tag Saved", f"Tag `{name}` saved."))
    elif name.lower() in tags:
        await ctx.send(tags[name.lower()])
    else:
        await ctx.send(embed=make_embed("❌ Not Found", f"Tag `{name}` not found.", discord.Color.red()))


@bot.command()
async def tags(ctx):
    """List all tags."""
    if not tags:
        return await ctx.send("No tags saved yet.")
    await ctx.send(embed=make_embed("🏷 Tags", ", ".join(f"`{t}`" for t in tags)))


@bot.command()
async def deltag(ctx, name: str):
    """Delete a tag."""
    if name.lower() in tags:
        del tags[name.lower()]
        await ctx.send(embed=make_embed("🏷 Deleted", f"Tag `{name}` removed."))
    else:
        await ctx.send(embed=make_embed("❌ Not Found", f"Tag `{name}` doesn't exist.", discord.Color.red()))


@bot.command()
async def calc(ctx, *, expression: str):
    """Evaluate a basic math expression."""
    try:
        allowed = set("0123456789+-*/()., ")
        if not all(c in allowed for c in expression):
            raise ValueError("Invalid characters.")
        result = eval(expression, {"__builtins__": {}})
        await ctx.send(embed=make_embed("🧮 Calculator", f"`{expression}` = **{result}**"))
    except Exception as e:
        await ctx.send(embed=make_embed("❌ Error", str(e), discord.Color.red()))


@bot.command()
async def choose(ctx, *choices: str):
    """Randomly choose from options."""
    if not choices:
        return await ctx.send("Give me some choices!")
    await ctx.send(embed=make_embed("🎯 Choice", f"I choose: **{random.choice(choices)}**"))


@bot.command()
async def reverse(ctx, *, text: str):
    """Reverse a string."""
    await ctx.send(embed=make_embed("↩️ Reversed", text[::-1]))


@bot.command()
async def wordcount(ctx, *, text: str):
    """Count words in a string."""
    words = len(text.split())
    chars = len(text)
    await ctx.send(embed=make_embed("📝 Word Count", f"Words: **{words}** | Characters: **{chars}**"))


@bot.command()
async def morse(ctx, *, text: str):
    """Convert text to Morse code."""
    code = {
        "A":".-","B":"-...","C":"-.-.","D":"-..","E":".","F":"..-.","G":"--.","H":"....","I":"..","J":".---",
        "K":"-.-","L":".-..","M":"--","N":"-.","O":"---","P":".--.","Q":"--.-","R":".-.","S":"...","T":"-",
        "U":"..-","V":"...-","W":".--","X":"-..-","Y":"-.--","Z":"--..",
        "1":".----","2":"..---","3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----.","0":"-----",
        " ":"/"
    }
    result = " ".join(code.get(c.upper(), "?") for c in text)
    await ctx.send(embed=make_embed("📡 Morse Code", f"`{result}`"))


@bot.command()
async def ascii(ctx, *, text: str):
    """Show ASCII values of characters."""
    result = " ".join(f"`{c}`={ord(c)}" for c in text[:20])
    await ctx.send(embed=make_embed("🔢 ASCII", result))


@bot.command()
async def usercount(ctx):
    """Show total member count."""
    g = ctx.guild
    humans = sum(1 for m in g.members if not m.bot)
    bots   = sum(1 for m in g.members if m.bot)
    await ctx.send(embed=make_embed("👥 User Count", f"Humans: **{humans}**\nBots: **{bots}**\nTotal: **{g.member_count}**"))


# ══════════════════════════════════════════════════════════════════════════════
# ██  MODERATION COMMANDS  (30+)
# ══════════════════════════════════════════════════════════════════════════════

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason given"):
    """Kick a member."""
    await member.kick(reason=reason)
    await ctx.send(embed=make_embed("👟 Kicked", f"**{member}** has been kicked.\nReason: {reason}", discord.Color.orange()))
    await log_action(ctx.guild, "Kick", ctx.author, member, reason)


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason given"):
    """Ban a member."""
    await member.ban(reason=reason)
    await ctx.send(embed=make_embed("🔨 Banned", f"**{member}** has been banned.\nReason: {reason}", discord.Color.red()))
    await log_action(ctx.guild, "Ban", ctx.author, member, reason)


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason: str = "No reason given"):
    """Unban a user by ID."""
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(embed=make_embed("✅ Unbanned", f"**{user}** has been unbanned.", discord.Color.green()))
    await log_action(ctx.guild, "Unban", ctx.author, user, reason)


@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason given"):
    """Mute a member (requires a 'Muted' role)."""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    await member.add_roles(muted_role, reason=reason)
    muted_users[member.id] = {"guild": ctx.guild.id, "until": None}
    await ctx.send(embed=make_embed("🔇 Muted", f"**{member}** has been muted.\nReason: {reason}", discord.Color.orange()))
    await log_action(ctx.guild, "Mute", ctx.author, member, reason)


@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a member."""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        muted_users.pop(member.id, None)
        await ctx.send(embed=make_embed("🔊 Unmuted", f"**{member}** has been unmuted.", discord.Color.green()))
        await log_action(ctx.guild, "Unmute", ctx.author, member, "Unmuted")
    else:
        await ctx.send("That member is not muted.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason given"):
    """Warn a member."""
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append({"reason": reason, "time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")})
    count = len(warnings[member.id])
    await ctx.send(embed=make_embed("⚠️ Warning Issued", f"**{member}** warned (#{count}).\nReason: {reason}", discord.Color.yellow()))
    await log_action(ctx.guild, f"Warn (#{count})", ctx.author, member, reason)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    """View warnings for a member."""
    user_warns = warnings.get(member.id, [])
    if not user_warns:
        return await ctx.send(embed=make_embed("✅ No Warnings", f"**{member}** has no warnings."))
    desc = "\n".join(f"**#{i+1}** — {w['reason']} *(at {w['time']})*" for i, w in enumerate(user_warns))
    await ctx.send(embed=make_embed(f"⚠️ Warnings for {member}", desc, discord.Color.yellow()))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx, member: discord.Member):
    """Clear all warnings for a member."""
    warnings.pop(member.id, None)
    await ctx.send(embed=make_embed("✅ Cleared", f"All warnings for **{member}** have been cleared.", discord.Color.green()))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def note(ctx, member: discord.Member, *, text: str):
    """Add a staff note to a member."""
    if member.id not in notes:
        notes[member.id] = []
    notes[member.id].append(text)
    await ctx.send(embed=make_embed("📝 Note Added", f"Note added for **{member}**."))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def notes(ctx, member: discord.Member):
    """View staff notes for a member."""
    user_notes = notes.get(member.id, [])
    if not user_notes:
        return await ctx.send(embed=make_embed("📝 No Notes", f"No notes for **{member}**."))
    desc = "\n".join(f"**#{i+1}** {n}" for i, n in enumerate(user_notes))
    await ctx.send(embed=make_embed(f"📝 Notes for {member}", desc))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    """Bulk delete messages."""
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(embed=make_embed("🗑 Purged", f"Deleted **{len(deleted)-1}** messages.", discord.Color.green()), delete_after=5)
    await log_action(ctx.guild, f"Purge ({len(deleted)-1} msgs)", ctx.author, ctx.channel, "Bulk delete")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    """Set slowmode for the current channel."""
    await ctx.channel.edit(slowmode_delay=seconds)
    slowmode_channels[ctx.channel.id] = seconds
    msg = f"Slowmode set to **{seconds}s**." if seconds > 0 else "Slowmode disabled."
    await ctx.send(embed=make_embed("🐢 Slowmode", msg))


@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    """Lock a channel so members can't send messages."""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=make_embed("🔒 Locked", f"{channel.mention} has been locked.", discord.Color.red()))
    await log_action(ctx.guild, "Lock", ctx.author, channel)


@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    """Unlock a channel."""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=make_embed("🔓 Unlocked", f"{channel.mention} has been unlocked.", discord.Color.green()))
    await log_action(ctx.guild, "Unlock", ctx.author, channel)


@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, nick: str = None):
    """Change or reset a member's nickname."""
    old = member.display_name
    await member.edit(nick=nick)
    await ctx.send(embed=make_embed("✏️ Nickname", f"Changed **{old}** → **{nick or member.name}**"))


@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, *, role_name: str):
    """Give a role to a member."""
    r = discord.utils.get(ctx.guild.roles, name=role_name)
    if not r:
        return await ctx.send(f"Role `{role_name}` not found.")
    await member.add_roles(r)
    await ctx.send(embed=make_embed("✅ Role Added", f"Added **{r.name}** to {member.mention}", discord.Color.green()))


@bot.command()
@commands.has_permissions(manage_roles=True)
async def unrole(ctx, member: discord.Member, *, role_name: str):
    """Remove a role from a member."""
    r = discord.utils.get(ctx.guild.roles, name=role_name)
    if not r:
        return await ctx.send(f"Role `{role_name}` not found.")
    await member.remove_roles(r)
    await ctx.send(embed=make_embed("✅ Role Removed", f"Removed **{r.name}** from {member.mention}", discord.Color.green()))


@bot.command()
@commands.has_permissions(move_members=True)
async def move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    """Move a member to a voice channel."""
    await member.move_to(channel)
    await ctx.send(embed=make_embed("🔀 Moved", f"Moved **{member}** to **{channel.name}**"))


@bot.command()
@commands.has_permissions(deafen_members=True)
async def deafen(ctx, member: discord.Member):
    """Server-deafen a member."""
    await member.edit(deafen=True)
    await ctx.send(embed=make_embed("🔕 Deafened", f"**{member}** has been server-deafened."))


@bot.command()
@commands.has_permissions(deafen_members=True)
async def undeafen(ctx, member: discord.Member):
    """Remove server-deafen from a member."""
    await member.edit(deafen=False)
    await ctx.send(embed=make_embed("🔔 Undeafened", f"**{member}** is no longer server-deafened."))


@bot.command()
@commands.has_permissions(mute_members=True)
async def servermute(ctx, member: discord.Member):
    """Server-mute a member in voice."""
    await member.edit(mute=True)
    await ctx.send(embed=make_embed("🔇 Server Muted", f"**{member}** has been server-muted."))


@bot.command()
@commands.has_permissions(mute_members=True)
async def serverunmute(ctx, member: discord.Member):
    """Remove server-mute from a member."""
    await member.edit(mute=False)
    await ctx.send(embed=make_embed("🔊 Server Unmuted", f"**{member}** has been server-unmuted."))


@bot.command()
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member, *, reason: str = "No reason given"):
    """Softban (ban + immediate unban) to delete messages."""
    await member.ban(reason=f"Softban: {reason}", delete_message_days=7)
    await ctx.guild.unban(member)
    await ctx.send(embed=make_embed("🌊 Softbanned", f"**{member}** has been softbanned (messages deleted).", discord.Color.orange()))
    await log_action(ctx.guild, "Softban", ctx.author, member, reason)


@bot.command()
@commands.has_permissions(ban_members=True)
async def tempban(ctx, member: discord.Member, duration: int, unit: str = "h", *, reason: str = "No reason given"):
    """Temporarily ban a member. Units: h/d"""
    units = {"h": 3600, "d": 86400}
    secs = duration * units.get(unit, 3600)
    await member.ban(reason=f"Tempban ({duration}{unit}): {reason}")
    await ctx.send(embed=make_embed("⏳ Tempbanned", f"**{member}** banned for **{duration}{unit}**.\nReason: {reason}", discord.Color.red()))
    await log_action(ctx.guild, f"Tempban ({duration}{unit})", ctx.author, member, reason)
    await asyncio.sleep(secs)
    await ctx.guild.unban(member)


@bot.command()
@commands.has_permissions(ban_members=True)
async def massban(ctx, *user_ids: int):
    """Ban multiple users by ID."""
    banned = []
    for uid in user_ids:
        try:
            user = await bot.fetch_user(uid)
            await ctx.guild.ban(user, reason=f"Massban by {ctx.author}")
            banned.append(str(user))
        except Exception:
            pass
    await ctx.send(embed=make_embed("🔨 Massbanned", f"Banned {len(banned)} users:\n" + "\n".join(banned), discord.Color.red()))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def prune(ctx, member: discord.Member, amount: int = 50):
    """Delete a specific user's messages from current channel."""
    def check(m): return m.author == member
    deleted = await ctx.channel.purge(limit=200, check=check)
    await ctx.send(embed=make_embed("🗑 Pruned", f"Removed **{len(deleted)}** messages from **{member}**.", discord.Color.green()), delete_after=5)


@bot.command()
@commands.has_permissions(manage_channels=True)
async def hidechannel(ctx, channel: discord.TextChannel = None):
    """Hide a channel from everyone."""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send(embed=make_embed("🙈 Hidden", f"{channel.mention} is now hidden.", discord.Color.red()))


@bot.command()
@commands.has_permissions(manage_channels=True)
async def showchannel(ctx, channel: discord.TextChannel = None):
    """Make a hidden channel visible again."""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send(embed=make_embed("👁 Visible", f"{channel.mention} is now visible.", discord.Color.green()))


@bot.command()
@commands.has_permissions(manage_channels=True)
async def clonevchan(ctx, channel: discord.VoiceChannel):
    """Clone a voice channel."""
    new = await channel.clone(name=f"{channel.name}-clone")
    await ctx.send(embed=make_embed("🔁 Cloned", f"Cloned **{channel.name}** → **{new.name}**"))


# ══════════════════════════════════════════════════════════════════════════════
# ██  UTILITY / FUN COMMANDS  (10+)
# ══════════════════════════════════════════════════════════════════════════════

@bot.command()
async def whois(ctx, member: discord.Member = None):
    """Detailed info about a user."""
    member = member or ctx.author
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    e = make_embed(f"👤 {member}")
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="ID",       value=str(member.id),                           inline=True)
    e.add_field(name="Status",   value=str(member.status).title(),                inline=True)
    e.add_field(name="Bot",      value="Yes" if member.bot else "No",             inline=True)
    e.add_field(name="Joined",   value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "N/A", inline=True)
    e.add_field(name="Registered", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    e.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) or "None",   inline=False)
    await ctx.send(embed=e)


@bot.command()
async def joined(ctx, member: discord.Member = None):
    """When a member joined the server."""
    member = member or ctx.author
    joined_at = member.joined_at
    await ctx.send(embed=make_embed("📅 Join Date", f"**{member}** joined on **{joined_at.strftime('%B %d, %Y at %H:%M UTC')}**"))


@bot.command()
async def botinfo(ctx):
    """Detailed bot statistics."""
    e = make_embed("🤖 Bot Info")
    e.add_field(name="Name",       value=str(bot.user),                           inline=True)
    e.add_field(name="ID",         value=str(bot.user.id),                        inline=True)
    e.add_field(name="Guilds",     value=str(len(bot.guilds)),                    inline=True)
    e.add_field(name="Users",      value=str(sum(g.member_count for g in bot.guilds)), inline=True)
    e.add_field(name="Commands",   value=str(len(bot.commands)),                  inline=True)
    e.add_field(name="Latency",    value=f"{round(bot.latency*1000)} ms",         inline=True)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=e)


@bot.command()
async def userstats(ctx, member: discord.Member = None):
    """Show a member's quick stats."""
    member = member or ctx.author
    warns = len(warnings.get(member.id, []))
    user_notes_count = len(notes.get(member.id, []))
    e = make_embed(f"📊 Stats: {member}")
    e.add_field(name="Warnings",    value=str(warns),            inline=True)
    e.add_field(name="Staff Notes", value=str(user_notes_count), inline=True)
    e.add_field(name="Muted",       value="Yes" if member.id in muted_users else "No", inline=True)
    e.add_field(name="AFK",         value=afk_users.get(member.id, "No"), inline=True)
    await ctx.send(embed=e)


@bot.command()
async def cmdstats(ctx):
    """Show which commands have been used the most."""
    if not command_stats:
        return await ctx.send("No commands have been used yet.")
    sorted_cmds = sorted(command_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join(f"**{i+1}.** `{PREFIX}{name}` — {count} uses" for i, (name, count) in enumerate(sorted_cmds))
    await ctx.send(embed=make_embed("📈 Command Stats", desc))


@bot.command()
async def leaderboard(ctx):
    """Show top warned users."""
    if not warnings:
        return await ctx.send("No warnings on record.")
    sorted_warns = sorted(warnings.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    desc = "\n".join(
        f"**{i+1}.** <@{uid}> — {len(w)} warning(s)"
        for i, (uid, w) in enumerate(sorted_warns)
    )
    await ctx.send(embed=make_embed("⚠️ Warning Leaderboard", desc, discord.Color.yellow()))


_last_deleted_message = {}

@bot.event
async def on_message_delete(message: discord.Message):
    if not message.author.bot:
        _last_deleted_message[message.channel.id] = message


@bot.command()
@commands.has_permissions(manage_messages=True)
async def snipe(ctx):
    """Show the last deleted message in this channel."""
    msg = _last_deleted_message.get(ctx.channel.id)
    if not msg:
        return await ctx.send("Nothing to snipe!")
    e = make_embed(f"🏹 Sniped from {msg.author}", msg.content or "*[no text content]*")
    e.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
    await ctx.send(embed=e)


@bot.command()
async def giveaway(ctx, duration: int, unit: str, *, prize: str):
    """Start a giveaway. Units: m/h/d"""
    units = {"m": 60, "h": 3600, "d": 86400}
    secs = duration * units.get(unit, 60)
    end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=secs)
    e = make_embed("🎉 GIVEAWAY!", f"**Prize:** {prize}\n**Ends:** {end_time.strftime('%H:%M UTC')} ({duration}{unit})\n\nReact with 🎉 to enter!", discord.Color.gold())
    e.set_footer(text=f"Hosted by {ctx.author}")
    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎉")
    giveaways[msg.id] = {"end": end_time, "prize": prize, "host": ctx.author.id, "channel": ctx.channel.id}
    await asyncio.sleep(secs)
    msg = await ctx.channel.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if reaction:
        users = [u async for u in reaction.users() if not u.bot]
        if users:
            winner = random.choice(users)
            await ctx.send(embed=make_embed("🎊 Giveaway Ended!", f"Winner: {winner.mention}\nPrize: **{prize}**", discord.Color.gold()))
        else:
            await ctx.send("No valid entries for the giveaway.")
    giveaways.pop(msg.id, None)


@bot.command()
async def reroll(ctx, message_id: int):
    """Reroll a giveaway."""
    ga = giveaways.get(message_id)
    if not ga:
        return await ctx.send("Giveaway not found.")
    channel = bot.get_channel(ga["channel"])
    msg = await channel.fetch_message(message_id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if reaction:
        users = [u async for u in reaction.users() if not u.bot]
        if users:
            winner = random.choice(users)
            await ctx.send(embed=make_embed("🎊 Rerolled!", f"New winner: {winner.mention}\nPrize: **{ga['prize']}**", discord.Color.gold()))


# ─── OWNER-ONLY ───────────────────────────────────────────────────────────────

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    """Shut down the bot (owner only)."""
    await ctx.send("👋 Shutting down...")
    await bot.close()


@bot.command()
@commands.is_owner()
async def setstatus(ctx, activity_type: str, *, text: str):
    """Set bot status (owner only). Types: playing/watching/listening"""
    types = {"playing": discord.ActivityType.playing, "watching": discord.ActivityType.watching, "listening": discord.ActivityType.listening}
    atype = types.get(activity_type.lower(), discord.ActivityType.playing)
    await bot.change_presence(activity=discord.Activity(type=atype, name=text))
    await ctx.send(embed=make_embed("✅ Status Updated", f"{activity_type.title()} **{text}**"))


@bot.command()
@commands.is_owner()
async def dm(ctx, member: discord.Member, *, message: str):
    """DM a user from the bot (owner only)."""
    try:
        await member.send(message)
        await ctx.send(embed=make_embed("✅ DM Sent", f"Message sent to **{member}**."))
    except discord.Forbidden:
        await ctx.send("Could not DM that user.")


# ─── STARTUP ──────────────────────────────────────────────────────────────────
bot._start_time = datetime.datetime.utcnow()

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  Set your BOT_TOKEN before running!")
    else:
    pass

bot.run(BOT_TOKEN)
