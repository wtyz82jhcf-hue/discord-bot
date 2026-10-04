import discord
from discord.ext import commands
from discord import ui
import json
import os
import random
import asyncio

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200

NUMBER_GAME_CHANNEL_ID = 1556308645942136872

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

OWNER_ROLE_ID = 1544691379613999164
SUGGESTION_REVIEW_ROLE_ID = 1530188150456979526

NAMETAG = "RLP | "
PREFIX = "?"

DATA_FILE = "bot_data.json"

NUMBER_GAME_MAX = 10**18


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# =========================================================
# DATEN
# =========================================================

data = {
    "license_plates": {},
    "tasks": {},
    "number_game": {},
    "active_shifts": []
}


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict):
            data.update(loaded)

    except Exception as e:
        print(f"Fehler beim Laden der Daten: {e}")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )
    except Exception as e:
        print(f"Fehler beim Speichern: {e}")


load_data()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_channel(channel_id):
    return bot.get_channel(channel_id)


def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def make_embed(title, description="", color=discord.Color.blurple()):
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


async def send_log(message):
    channel = get_channel(SHIFT_LOG_CHANNEL_ID)

    if channel:
        await channel.send(message)


def get_active_shifts():
    result = set()

    for user_id in data.get("active_shifts", []):
        try:
            result.add(int(user_id))
        except (ValueError, TypeError):
            pass

    return result


def save_active_shifts(active_shifts):
    data["active_shifts"] = list(active_shifts)
    save_data()


def create_shift_embed():
    active_shifts = get_active_shifts()

    embed = make_embed(
        "🛠️ Entwickler-Schicht",
        "Hier kannst du deine Schicht starten oder beenden."
    )

    if not active_shifts:
        embed.add_field(
            name="Aktuell im Dienst",
            value="Niemand ist aktuell im Dienst.",
            inline=False
        )

    else:
        names = []

        for user_id in active_shifts:
            member = bot.get_user(user_id)

            if member:
                names.append(f"🟢 {member.mention}")

        if names:
            embed.add_field(
                name="Aktuell im Dienst",
                value="\n".join(names),
                inline=False
            )
        else:
            embed.add_field(
                name="Aktuell im Dienst",
                value="Niemand ist aktuell im Dienst.",
                inline=False
            )

    return embed


# =========================================================
# WEB SERVER FÜR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        pass


def start_web_server():
    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(f"Webserver gestartet auf Port {port}")


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(ui.Modal, title="Nametag setzen"):

    name = ui.TextInput(
        label="Dein Name",
        placeholder="Gib deinen Namen ein",
        max_length=30
    )

    async def on_submit(self, interaction):

        member = interaction.user

        if not has_role(member, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für den Nametag.",
                ephemeral=True
            )
            return

        new_name = f"{NAMETAG}{self.name.value}"

        try:
            await member.edit(nick=new_name)

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf **{new_name}** gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nickname nicht ändern.",
                ephemeral=True
            )


class NametagView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Nametag setzen",
        style=discord.ButtonStyle.primary,
        custom_id="nametag_set"
    )
    async def set_nametag(self, interaction, button):

        await interaction.response.send_modal(
            NametagModal()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(ui.Modal, title="Kennzeichen setzen"):

    plate = ui.TextInput(
        label="Kennzeichen",
        placeholder="z.B. GM-RL 123",
        max_length=20
    )

    async def on_submit(self, interaction):

        user_id = str(interaction.user.id)

        plate = self.plate.value.strip()

        data["license_plates"][user_id] = plate
        save_data()

        await interaction.response.send_message(
            f"🚘 Dein Kennzeichen wurde auf **{plate}** gesetzt.",
            ephemeral=True
        )


class LicensePlateView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Kennzeichen setzen",
        style=discord.ButtonStyle.primary,
        custom_id="plate_set"
    )
    async def set_plate(self, interaction, button):

        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @ui.button(
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger,
        custom_id="plate_remove"
    )
    async def remove_plate(self, interaction, button):

        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "⚠️ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        data["license_plates"].pop(user_id)
        save_data()

        await interaction.response.send_message(
            "✅ Dein Kennzeichen wurde entfernt.",
            ephemeral=True
        )


# =========================================================
# ENTWICKLER-AUFGABEN
# =========================================================

class DeveloperTaskModal(ui.Modal, title="Neue Entwickler-Aufgabe"):

    task = ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):

        task_id = str(random.randint(100000, 999999))

        while task_id in data["tasks"]:
            task_id = str(random.randint(100000, 999999))

        data["tasks"][task_id] = {
            "text": self.task.value,
            "creator": interaction.user.id,
            "taken_by": None,
            "done": False
        }

        save_data()

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel:

            embed = make_embed(
                "🛠️ Neue Entwickler-Aufgabe",
                self.task.value
            )

            embed.add_field(
                name="Status",
                value="🟡 Offen",
                inline=False
            )

            await channel.send(
                embed=embed,
                view=DeveloperTaskView(task_id)
            )

        await interaction.response.send_message(
            "✅ Aufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        custom_id="developer_task_create"
    )
    async def create_task(self, interaction, button):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(ui.View):

    def __init__(self, task_id):

        super().__init__(timeout=None)

        self.task_id = str(task_id)

        self.children[0].custom_id = (
            f"task_take_{self.task_id}"
        )

        self.children[1].custom_id = (
            f"task_done_{self.task_id}"
        )

        self.children[2].custom_id = (
            f"task_delete_{self.task_id}"
        )

    @ui.button(
        label="Aufgabe übernehmen",
        style=discord.ButtonStyle.primary
    )
    async def take(self, interaction, button):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        if task["taken_by"] is not None:

            await interaction.response.send_message(
                "⚠️ Diese Aufgabe wurde bereits übernommen.",
                ephemeral=True
            )
            return

        task["taken_by"] = interaction.user.id

        save_data()

        await interaction.response.send_message(
            "✅ Du hast die Aufgabe übernommen.",
            ephemeral=True
        )

    @ui.button(
        label="Erledigt",
        style=discord.ButtonStyle.success
    )
    async def done(self, interaction, button):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        task["done"] = True

        save_data()

        await interaction.response.send_message(
            "✅ Aufgabe wurde als erledigt markiert.",
            ephemeral=True
        )

    @ui.button(
        label="Löschen",
        style=discord.ButtonStyle.danger
    )
    async def delete(self, interaction, button):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        data["tasks"].pop(self.task_id)
        save_data()

        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass

        await interaction.response.send_message(
            "🗑️ Aufgabe wurde gelöscht.",
            ephemeral=True
        )


# =========================================================
# SCHICHT
# =========================================================

class DeveloperShiftView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        custom_id="shift_start"
    )
    async def start_shift(self, interaction, button):

        member = interaction.user
        active_shifts = get_active_shifts()

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für die Schicht.",
                ephemeral=True
            )
            return

        if member.id in active_shifts:
            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        active_shifts.add(member.id)
        save_active_shifts(active_shifts)

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            try:
                await member.add_roles(role)

            except discord.Forbidden:

                await interaction.response.send_message(
                    "⚠️ Schicht gestartet, aber ich konnte "
                    "die Entwicklerrolle nicht vergeben.",
                    ephemeral=True
                )
                return

        await send_log(
            f"🟢 **Schicht gestartet:** {member.mention}"
        )

        await interaction.response.edit_message(
            embed=create_shift_embed(),
            view=DeveloperShiftView()
        )

    @ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        custom_id="shift_stop"
    )
    async def stop_shift(self, interaction, button):

        member = interaction.user
        active_shifts = get_active_shifts()

        if member.id not in active_shifts:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        active_shifts.remove(member.id)
        save_active_shifts(active_shifts)

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                pass

        await send_log(
            f"🔴 **Schicht beendet:** {member.mention}"
        )

        await interaction.response.edit_message(
            embed=create_shift_embed(),
            view=DeveloperShiftView()
        )


# =========================================================
# ZAHLENSPIEL
# =========================================================

class NumberGameModal(ui.Modal, title="Zahlenspiel"):

    guess = ui.TextInput(
        label="Deine Zahl",
        placeholder="1 bis 1.000.000.000.000.000.000",
        min_length=1,
        max_length=19
    )

    async def on_submit(self, interaction):

        try:
            number = int(
                self.guess.value.strip()
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ Bitte gib eine gültige ganze Zahl ein.",
                ephemeral=True
            )
            return

        if number < 1 or number > NUMBER_GAME_MAX:

            await interaction.response.send_message(
                f"❌ Die Zahl muss zwischen 1 und "
                f"{NUMBER_GAME_MAX:,} liegen.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        game = data["number_game"].get(user_id)

        if not game:

            game = {
                "number": random.randint(
                    1,
                    NUMBER_GAME_MAX
                ),
                "attempts": 0
            }

        game["attempts"] += 1

        target = int(game["number"])

        if number == target:

            attempts = game["attempts"]

            data["number_game"].pop(
                user_id,
                None
            )

            save_data()

            await interaction.response.send_message(
                f"🎉 **Richtig!** Die Zahl war **{target}**.\n"
                f"Versuche: **{attempts}**",
                ephemeral=True
            )

        elif number < target:

            data["number_game"][user_id] = game
            save_data()

            await interaction.response.send_message(
                "⬆️ **Höher!** Versuch es nochmal.",
                ephemeral=True
            )

        else:

            data["number_game"][user_id] = game
            save_data()

            await interaction.response.send_message(
                "⬇️ **Niedriger!** Versuch es nochmal.",
                ephemeral=True
            )


class NumberGameView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Zahl raten",
        style=discord.ButtonStyle.primary,
        custom_id="number_guess"
    )
    async def guess(self, interaction, button):

        user_id = str(interaction.user.id)

        if user_id not in data["number_game"]:

            data["number_game"][user_id] = {
                "number": random.randint(
                    1,
                    NUMBER_GAME_MAX
                ),
                "attempts": 0
            }

            save_data()

        await interaction.response.send_modal(
            NumberGameModal()
        )

    @ui.button(
        label="Neues Spiel",
        style=discord.ButtonStyle.success,
        custom_id="number_new"
    )
    async def new_game(self, interaction, button):

        user_id = str(interaction.user.id)

        data["number_game"][user_id] = {
            "number": random.randint(
                1,
                NUMBER_GAME_MAX
            ),
            "attempts": 0
        }

        save_data()

        await interaction.response.send_message(
            "🎮 Neues Spiel gestartet! "
            "Klicke auf **Zahl raten**.",
            ephemeral=True
        )


# =========================================================
# COMMUNITY
# =========================================================

class FeedbackModal(ui.Modal, title="Feedback"):

    text = ui.TextInput(
        label="Dein Feedback",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction):

        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel:

            embed = make_embed(
                "💬 Neues Feedback",
                self.text.value
            )

            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Danke für dein Feedback!",
            ephemeral=True
        )


class SuggestionModal(ui.Modal, title="Vorschlag"):

    text = ui.TextInput(
        label="Dein Vorschlag",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction):

        channel = get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel:

            embed = make_embed(
                "💡 Neuer Vorschlag",
                self.text.value
            )

            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde gesendet!",
            ephemeral=True
        )


class CommunityView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Feedback",
        style=discord.ButtonStyle.primary,
        custom_id="community_feedback"
    )
    async def feedback(self, interaction, button):

        await interaction.response.send_modal(
            FeedbackModal()
        )

    @ui.button(
        label="Vorschlag",
        style=discord.ButtonStyle.success,
        custom_id="community_suggestion"
    )
    async def suggestion(self, interaction, button):

        await interaction.response.send_modal(
            SuggestionModal()
        )


# =========================================================
# COMMUNITY PANEL
# =========================================================

class CommunityPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Feedback",
        style=discord.ButtonStyle.primary,
        custom_id="community_panel_feedback"
    )
    async def feedback(self, interaction, button):

        await interaction.response.send_modal(
            FeedbackModal()
        )

    @ui.button(
        label="Vorschlag",
        style=discord.ButtonStyle.success,
        custom_id="community_panel_suggestion"
    )
    async def suggestion(self, interaction, button):

        await interaction.response.send_modal(
            SuggestionModal()
        )


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def nametag(ctx):

    await ctx.send(
        embed=make_embed(
            "🏷️ Nametag",
            "Klicke auf den Button, um deinen Nametag zu setzen."
        ),
        view=NametagView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def kennzeichen(ctx):

    await ctx.send(
        embed=make_embed(
            "🚘 Kennzeichen",
            "Setze dein persönliches Kennzeichen "
            "oder entferne es wieder."
        ),
        view=LicensePlateView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def entwickler(ctx):

    await ctx.send(
        embed=make_embed(
            "🛠️ Entwickler-Aufgaben",
            "Erstelle und verwalte Entwickler-Aufgaben."
        ),
        view=DeveloperTaskPanelView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def schicht(ctx):

    await ctx.send(
        embed=create_shift_embed(),
        view=DeveloperShiftView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def zahlenspiel(ctx):

    await ctx.send(
        embed=make_embed(
            "🔢 Zahlenspiel",
            "Der Bot denkt sich eine Zahl zwischen "
            f"**1 und {NUMBER_GAME_MAX:,}** aus.\n\n"
            "Klicke auf **Zahl raten**."
        ),
        view=NumberGameView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def community(ctx):

    await ctx.send(
        embed=make_embed(
            "🌐 Community",
            "Hier kannst du Feedback geben "
            "oder einen Vorschlag senden."
        ),
        view=CommunityView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def communitypanel(ctx):

    await ctx.send(
        embed=make_embed(
            "🌐 Community Panel",
            "Wähle aus, was du der Community mitteilen möchtest."
        ),
        view=CommunityPanelView()
    )


# =========================================================
# HELP
# =========================================================

@bot.command()
async def helpme(ctx):

    embed = make_embed(
        "📖 Bot-Befehle",
        "Verfügbare Befehle:"
    )

    embed.add_field(
        name="?nametag",
        value="Nametag-Panel öffnen.",
        inline=False
    )

    embed.add_field(
        name="?kennzeichen",
        value="Kennzeichen-Panel öffnen.",
        inline=False
    )

    embed.add_field(
        name="?entwickler",
        value="Entwickler-Aufgaben öffnen.",
        inline=False
    )

    embed.add_field(
        name="?schicht",
        value="Schicht-Panel öffnen.",
        inline=False
    )

    embed.add_field(
        name="?zahlenspiel",
        value="Zahlenspiel öffnen.",
        inline=False
    )

    embed.add_field(
        name="?community",
        value="Community-Panel öffnen.",
        inline=False
    )

    embed.add_field(
        name="?communitypanel",
        value="Community Panel öffnen.",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# COMMAND FEHLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Du brauchst Administrator-Rechte.",
            delete_after=5
        )
        return

    print(
        f"Command-Fehler: {error}"
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("======================================")
    print(f"Bot online: {bot.user}")
    print(f"Bot-ID: {bot.user.id}")
    print("======================================")


# =========================================================
# PERSISTENTE VIEWS
# =========================================================

async def setup_persistent_views():

    load_data()

    bot.add_view(
        NametagView()
    )

    bot.add_view(
        LicensePlateView()
    )

    bot.add_view(
        DeveloperTaskPanelView()
    )

    bot.add_view(
        DeveloperShiftView()
    )

    bot.add_view(
        NumberGameView()
    )

    bot.add_view(
        CommunityView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    for task_id in list(
        data["tasks"].keys()
    ):

        try:

            bot.add_view(
                DeveloperTaskView(task_id)
            )

        except Exception as e:

            print(
                f"Aufgabe {task_id} konnte nicht "
                f"registriert werden: {e}"
            )


# =========================================================
# START
# =========================================================

async def main():

    await setup_persistent_views()

    await bot.start(TOKEN)


if __name__ == "__main__":

    if not TOKEN:

        print("======================================")
        print("FEHLER: DISCORD_TOKEN fehlt.")
        print("======================================")

    else:

        try:

            start_web_server()

            asyncio.run(
                main()
            )

        except discord.LoginFailure:

            print("======================================")
            print("FEHLER: Discord-Token ist falsch.")
            print("======================================")

        except Exception as e:

            print("======================================")
            print("FEHLER:")
            print(e)
            print("======================================")
