import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import os
import asyncio
from datetime import datetime, timezone

# ============================================================
# THE DOND BOT — Standalone bot.py
# Put your Discord bot token below.
# No Admin/User IDs are required; Discord permissions are used.
# ============================================================

TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

DATA_FILE = "bot_data.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------------------------------------
# Persistent data
# ------------------------------------------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"embeds": {}, "settings": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("embeds", {})
        data.setdefault("settings", {})
        return data
    except Exception:
        return {"embeds": {}, "settings": {}}

data = load_data()

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def replace_placeholders(text, interaction):
    if not text:
        return text

    guild = interaction.guild
    user = interaction.user

    values = {
        "{user}": user.mention,
        "{username}": user.name,
        "{user_id}": str(user.id),
        "{server}": guild.name if guild else "",
        "{member_count}": str(guild.member_count) if guild else "0",
        "{date}": datetime.now().strftime("%Y-%m-%d"),
        "{time}": datetime.now().strftime("%H:%M:%S"),
    }

    for key, value in values.items():
        text = text.replace(key, value)

    return text

def has_manage_permission(interaction):
    perms = interaction.user.guild_permissions
    return perms.administrator or perms.manage_guild

async def permission_error(interaction):
    await interaction.response.send_message(
        "❌ You need **Administrator** or **Manage Server** permission to use this command.",
        ephemeral=True
    )

# ------------------------------------------------------------
# Embed builder
# ------------------------------------------------------------

class EmbedModal(Modal, title="Create / Edit Embed"):
    title_input = TextInput(
        label="Embed Title",
        placeholder="Enter the embed title...",
        required=False,
        max_length=256
    )

    description_input = TextInput(
        label="Description",
        placeholder="Enter the embed description...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    color_input = TextInput(
        label="Color",
        placeholder="Example: #5865F2",
        default="#5865F2",
        required=False,
        max_length=7
    )

    footer_input = TextInput(
        label="Footer",
        placeholder="Enter footer text...",
        required=False,
        max_length=2048
    )

    image_input = TextInput(
        label="Large Image URL",
        placeholder="https://...",
        required=False,
        max_length=1000
    )

    def __init__(self, interaction, template_name=None):
        super().__init__()
        self.original_interaction = interaction
        self.template_name = template_name

        if template_name and template_name in data["embeds"]:
            saved = data["embeds"][template_name]
            self.title_input.default = saved.get("title", "")[:256]
            self.description_input.default = saved.get("description", "")[:4000]
            self.color_input.default = saved.get("color", "#5865F2")[:7]
            self.footer_input.default = saved.get("footer", "")[:2048]
            self.image_input.default = saved.get("image", "")[:1000]

    async def on_submit(self, interaction: discord.Interaction):
        color_text = self.color_input.value.strip() or "#5865F2"

        try:
            color = int(color_text.replace("#", ""), 16)
            if color < 0 or color > 0xFFFFFF:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid color. Use a format like `#5865F2`.",
                ephemeral=True
            )
            return

        template_name = self.template_name or f"embed-{interaction.user.id}-{int(datetime.now().timestamp())}"

        data["embeds"][template_name] = {
            "title": self.title_input.value,
            "description": self.description_input.value,
            "color": f"#{color:06X}",
            "footer": self.footer_input.value,
            "image": self.image_input.value,
            "thumbnail": "",
            "author": "",
            "timestamp": True,
            "fields": []
        }
        save_data()

        embed = build_embed(data["embeds"][template_name], interaction)

        view = EmbedActionView(template_name)

        await interaction.response.send_message(
            "✅ **Embed created successfully!**\n"
            f"Template: `{template_name}`\n\n"
            "Use the buttons below to preview or send it.",
            embed=embed,
            view=view,
            ephemeral=True
        )

def build_embed(config, interaction):
    try:
        color = int(config.get("color", "#5865F2").replace("#", ""), 16)
    except Exception:
        color = 0x5865F2

    embed = discord.Embed(
        title=replace_placeholders(config.get("title", ""), interaction) or None,
        description=replace_placeholders(config.get("description", ""), interaction) or None,
        color=color
    )

    footer = replace_placeholders(config.get("footer", ""), interaction)
    if footer:
        embed.set_footer(text=footer)

    image = config.get("image", "")
    if image:
        embed.set_image(url=image)

    thumbnail = config.get("thumbnail", "")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    author = config.get("author", "")
    if author:
        embed.set_author(name=replace_placeholders(author, interaction))

    for field in config.get("fields", []):
        embed.add_field(
            name=replace_placeholders(field.get("name", "Field"), interaction),
            value=replace_placeholders(field.get("value", "\u200b"), interaction),
            inline=field.get("inline", False)
        )

    if config.get("timestamp", True):
        embed.timestamp = datetime.now(timezone.utc)

    return embed

class EmbedActionView(View):
    def __init__(self, template_name):
        super().__init__(timeout=300)
        self.template_name = template_name

    @discord.ui.button(label="Preview", emoji="👁️", style=discord.ButtonStyle.primary)
    async def preview(self, interaction, button):
        if not has_manage_permission(interaction):
            await permission_error(interaction)
            return

        config = data["embeds"].get(self.template_name)
        if not config:
            await interaction.response.send_message("❌ Template not found.", ephemeral=True)
            return

        await interaction.response.send_message(
            "### 👁️ Embed Preview",
            embed=build_embed(config, interaction),
            ephemeral=True
        )

    @discord.ui.button(label="Send Here", emoji="📤", style=discord.ButtonStyle.success)
    async def send_here(self, interaction, button):
        if not has_manage_permission(interaction):
            await permission_error(interaction)
            return

        config = data["embeds"].get(self.template_name)
        if not config:
            await interaction.response.send_message("❌ Template not found.", ephemeral=True)
            return

        await interaction.channel.send(embed=build_embed(config, interaction))
        await interaction.response.send_message("✅ Embed sent.", ephemeral=True)

    @discord.ui.button(label="Delete", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def delete(self, interaction, button):
        if not has_manage_permission(interaction):
            await permission_error(interaction)
            return

        if self.template_name in data["embeds"]:
            del data["embeds"][self.template_name]
            save_data()

        await interaction.response.edit_message(
            content=f"🗑️ Deleted `{self.template_name}`.",
            embed=None,
            view=None
        )

# ------------------------------------------------------------
# Commands
# ------------------------------------------------------------

@bot.tree.command(name="embed", description="Create a professional custom embed.")
@app_commands.describe(name="Optional template name to edit")
async def embed_command(interaction: discord.Interaction, name: str = None):
    if not has_manage_permission(interaction):
        await permission_error(interaction)
        return

    if name and name not in data["embeds"]:
        await interaction.response.send_message(
            f"❌ Template `{name}` does not exist.",
            ephemeral=True
        )
        return

    await interaction.response.send_modal(EmbedModal(interaction, name))

@bot.tree.command(name="embed-list", description="List saved embed templates.")
async def embed_list(interaction: discord.Interaction):
    if not has_manage_permission(interaction):
        await permission_error(interaction)
        return

    names = list(data["embeds"].keys())

    if not names:
        await interaction.response.send_message(
            "📭 No saved embed templates.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="✨ Saved Embed Templates",
        description="\n".join(f"• `{name}`" for name in names),
        color=0x5865F2
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="embed-send", description="Send a saved embed in the current channel.")
@app_commands.describe(name="Saved embed template name")
async def embed_send(interaction: discord.Interaction, name: str):
    if not has_manage_permission(interaction):
        await permission_error(interaction)
        return

    config = data["embeds"].get(name)
    if not config:
        await interaction.response.send_message(
            f"❌ Template `{name}` does not exist.",
            ephemeral=True
        )
        return

    await interaction.channel.send(embed=build_embed(config, interaction))
    await interaction.response.send_message("✅ Embed sent successfully.", ephemeral=True)

@bot.tree.command(name="embed-delete", description="Delete a saved embed template.")
@app_commands.describe(name="Saved embed template name")
async def embed_delete(interaction: discord.Interaction, name: str):
    if not has_manage_permission(interaction):
        await permission_error(interaction)
        return

    if name not in data["embeds"]:
        await interaction.response.send_message(
            f"❌ Template `{name}` does not exist.",
            ephemeral=True
        )
        return

    del data["embeds"][name]
    save_data()

    await interaction.response.send_message(
        f"🗑️ Deleted embed template `{name}`.",
        ephemeral=True
    )

@bot.tree.command(name="embed-preview", description="Preview a saved embed.")
@app_commands.describe(name="Saved embed template name")
async def embed_preview(interaction: discord.Interaction, name: str):
    if not has_manage_permission(interaction):
        await permission_error(interaction)
        return

    config = data["embeds"].get(name)
    if not config:
        await interaction.response.send_message(
            f"❌ Template `{name}` does not exist.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=build_embed(config, interaction),
        ephemeral=True
    )


# ------------------------------------------------------------
# !help prefix command
# ------------------------------------------------------------

@bot.command(name="help")
async def help_command(ctx):
    """Show all available bot commands."""
    embed = discord.Embed(
        title="👑 THE DOND BOT — Command Help",
        description="Here are all currently available commands:",
        color=0xD4AF37
    )

    embed.add_field(
        name="✨ Embed Commands",
        value=(
            "`/embed` — Create or edit an embed\n"
            "`/embed-list` — List saved embed templates\n"
            "`/embed-send` — Send a saved embed\n"
            "`/embed-delete` — Delete a saved embed template\n"
            "`/embed-preview` — Preview a saved embed"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 General Commands",
        value=(
            "`!help` — Show this help menu\n"
            "`/ping` — Check bot latency\n"
            "`/server-info` — Show server information"
        ),
        inline=False
    )

    embed.set_footer(text="THE DOND • Invite • Earn • Dominate")

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    await ctx.send(embed=embed)

# ------------------------------------------------------------
# Basic bot commands
# ------------------------------------------------------------

@bot.tree.command(name="ping", description="Check bot latency.")
async def ping(interaction):
    await interaction.response.send_message(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )

@bot.tree.command(name="server-info", description="Show server information.")
async def server_info(interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title=f"🏠 {guild.name}",
        color=0xD4AF37
    )
    embed.add_field(name="👥 Members", value=str(guild.member_count))
    embed.add_field(name="🆔 Server ID", value=str(guild.id))
    embed.add_field(name="📅 Created", value=discord.utils.format_dt(guild.created_at, "D"))

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)

# ------------------------------------------------------------
# Startup
# ------------------------------------------------------------

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Logged in as {bot.user} ({bot.user.id})")
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Slash command sync error: {e}")

    print("THE DOND BOT is online.")

if __name__ == "__main__":
    if TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        print("ERROR: Open bot.py and replace PASTE_YOUR_BOT_TOKEN_HERE with your bot token.")
    else:
        bot.run(TOKEN)
