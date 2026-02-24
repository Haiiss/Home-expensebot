import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- 1. WEB SERVER TO KEEP BOT ALIVE ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- 2. FILE HELPERS ---
FILE_NAME = "balance.txt"

def get_balance():
    if not os.path.exists(FILE_NAME):
        return 0.0
    try:
        with open(FILE_NAME, "r") as f:
            return float(f.read())
    except:
        return 0.0

def save_balance(new_bal):
    with open(FILE_NAME, "w") as f:
        f.write(str(new_bal))

def parse_expense(content):
    """Extracts amount from '-50 bread'"""
    content = content.strip()
    if content.startswith("-"):
        try:
            parts = content[1:].strip().split(" ", 1)
            return float(parts[0])
        except:
            return 0.0
    return 0.0

def parse_addition(content):
    """Extracts amount from '!add 500'"""
    content = content.strip()
    if content.startswith("!add"):
        try:
            parts = content.split(" ")
            return float(parts[1])
        except:
            return 0.0
    return 0.0

# --- 3. BOT LOGIC ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Handle Expense (- amount)
    exp_amount = parse_expense(message.content)
    if exp_amount > 0:
        balance = get_balance()
        if exp_amount > balance:
            await message.reply(f"❌ **You don't have enough Money**\n💰 Current Balance: **{balance}**")
            return

        new_balance = balance - exp_amount
        save_balance(new_balance)
        
        # Check if the user ran out of money exactly
        if new_balance == 0:
            await message.reply(f"✅ Spent: **{exp_amount}**.\n**You have run out of money**")
        else:
            await message.reply(f"✅ Spent: **{exp_amount}**.\n💰 **New Balance: {new_balance}**")

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.author == bot.user or before.content == after.content:
        return

    current_balance = get_balance()

    # Check if the message was an expense (-)
    old_exp = parse_expense(before.content)
    new_exp = parse_expense(after.content)

    # Check if the message was an addition (!add)
    old_add = parse_addition(before.content)
    new_add = parse_addition(after.content)

    # CASE A: Correcting an Expense
    if old_exp > 0 or new_exp > 0:
        temp_balance = current_balance + old_exp # Refund the old amount
        if new_exp > temp_balance:
            await after.reply(f"❌ **Not enough money for this correction.**\n💰 Max available: **{temp_balance}**")
            return
        
        final_balance = temp_balance - new_exp
        save_balance(final_balance)
        
        # Exact zero check for edits
        if final_balance == 0:
            await after.reply(f"🔧 **Expense Corrected!**\n**You have run out of money**")
        else:
            await after.reply(f"🔧 **Expense Corrected!**\n💰 **Updated Balance: {final_balance}**")

    # CASE B: Correcting an Addition (!add)
    elif old_add > 0 or new_add > 0:
        # Subtract the old mistake, add the new amount
        temp_balance = current_balance - old_add + new_add
        if temp_balance < 0:
            await after.reply(f"❌ **Correction failed.** This would put your balance into negative (**{temp_balance}**).")
            return
        save_balance(temp_balance)
        
        if temp_balance == 0:
            await after.reply(f"🔧 **Addition Corrected!**\n**You have run out of money**")
        else:
            await after.reply(f"🔧 **Addition Corrected!**\n💰 **Updated Balance: {temp_balance}**")

# --- 4. COMMANDS ---

@bot.command()
async def add(ctx, amount: float):
    balance = get_balance() + amount
    save_balance(balance)
    if balance == 0: # Technically possible if someone adds 0 or corrects a fix
        await ctx.send(f"💵 Added **{amount}**.\n**You have run out of money**")
    else:
        await ctx.send(f"💵 Added **{amount}**.\n💰 **New Balance: {balance}**")

@bot.command()
async def fix(ctx, amount: float):
    save_balance(amount)
    if amount == 0:
        await ctx.send(f"🔧 Manual override! **You have run out of money**")
    else:
        await ctx.send(f"🔧 Manual override! Balance set to: **{amount}**")

@bot.command()
async def status(ctx):
    balance = get_balance()
    if balance == 0:
        await ctx.send(f"💰 **Current Balance: {balance}**\n**You have run out of money**")
    else:
        await ctx.send(f"💰 **Current Balance: {balance}**")

# --- 5. START ---
keep_alive()
try:
    bot.run(os.environ['DISCORD_TOKEN'])
except discord.errors.HTTPException:
    print("\n\n\nBLOCKED BY DISCORD! Restart the Repl.\n\n\n")