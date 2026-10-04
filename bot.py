import discord
from discord.ext import commands
from discord import ui
import json
import os
import random
import asyncio

# =========================================================
# EINSTELLUNGEN
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

DATA_FILE = "bot_data.json"

data = {
    "license_plates": {},
    "tasks": {},
    "number_game": {}
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

    except Exception:
        print("WARNUNG: bot_data.json konnte nicht gelesen werden.")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Fehler beim Speichern:", e)


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def is_owner(member):
    return has_role(member, OWNER_ROLE_ID)


def get_channel(channel_id):
    return bot.get_channel(channel_id)


async def send_log(text):
    channel = get_channel(SHIFT_LOG_CHANNEL_ID)

    if channel is not None:
        try:
            await channel.send(text)
        except Exception:
            pass


# =========================================================
# EMBEDS
# =========================================================

def embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(ui.Modal, title="Nametag setzen"):

    name = ui.TextInput(
        label="Dein Name",
        placeholder="z.B. Max Mustermann",
        max_length=32
    )

    async def on_submit(self, interaction: discord.Interaction):

        member = interaction.user

        if not has_role(member, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für das Nametag-System.",
                ephemeral=True
            )
            return

        nickname = f"{NAMETAG}{self.name.value}"

        try:
            await member.edit(nick=nickname)

            await interaction.response.send_message(
                f"✅ Dein Name wurde auf **{nickname}** gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nickname nicht ändern. "
                "Meine Bot-Rolle muss über deiner Rolle stehen.",
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
    async def set_nametag(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_modal(NametagModal())


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(ui.Modal, title="Kennzeichen registrieren"):

    plate = ui.TextInput(
        label="Kennzeichen",
        placeholder="z.B. GM-RL 123",
        min_length=2,
        max_length=12
    )

    async def on_submit(self, interaction: discord.Interaction):

        value = self.plate.value.upper().strip()

        data["license_plates"][str(interaction.user.id)] = value
        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen wurde auf **{value}** gesetzt.",
            ephemeral=True
        )


class LicensePlateView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Kennzeichen setzen",
        style=discord.ButtonStyle.primary,
        custom_id="license_set"
    )
    async def set_plate(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_modal(LicensePlateModal())

    @ui.button(
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger,
        custom_id="license_remove"
    )
    async def remove_plate(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen gespeichert.",
                ephemeral=True
            )
            return

        del data["license_plates"][user_id]
        save_data()

        await interaction.response.send_message(
            "✅ Dein Kennzeichen wurde entfernt.",
            ephemeral=True
        )


# =========================================================
# ENTWICKLER-AUFGABEN
# =========================================================

class TaskModal(ui.Modal, title="Neue Entwickler-Aufgabe"):

    title_input = ui.TextInput(
        label="Aufgabe",
        placeholder="z.B. Neues System programmieren",
        max_length=100
    )

    description_input = ui.TextInput(
        label="Beschreibung",
        placeholder="Was soll gemacht werden?",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not has_role(interaction.user, DEVELOPER_SHIFT_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        task_id = str(random.randint(100000, 999999))

        data["tasks"][task_id] = {
            "title": self.title_input.value,
            "description": self.description_input.value,
            "creator": interaction.user.id,
            "taken_by": None,
            "done": False,
            "channel_id": interaction.channel.id,
            "message_id": None
        }

        save_data()

        task_embed = create_task_embed(task_id)

        message = await interaction.channel.send(
            embed=task_embed,
            view=DeveloperTaskView(task_id)
        )

        data["tasks"][task_id]["message_id"] = message.id
        save_data()

        await interaction.response.send_message(
            "✅ Aufgabe wurde erstellt.",
            ephemeral=True
        )


def create_task_embed(task_id):

    task = data["tasks"].get(task_id)

    if not task:
        return embed(
            "Aufgabe nicht gefunden",
            "Diese Aufgabe existiert nicht mehr.",
            discord.Color.red()
        )

    if task["done"]:
        status = "🟢 **Erledigt**"
    elif task["taken_by"]:
        status = f"🟡 **Übernommen von <@{task['taken_by']}>**"
    else:
        status = "🔴 **Offen**"

    e = embed(
        f"🛠️ {task['title']}",
        task["description"],
        discord.Color.blurple()
    )

    e.add_field(
        name="Status",
        value=status,
        inline=False
    )

    e.add_field(
        name="Aufgaben-ID",
        value=task_id,
        inline=False
    )

    e.set_footer(text="Entwickler-Aufgabe")

    return e


class DeveloperTaskView(ui.View):

    def __init__(self, task_id):
        super().__init__(timeout=None)
        self.task_id = str(task_id)

    @ui.button(
        label="Übernehmen",
        style=discord.ButtonStyle.primary,
        custom_id="task_take"
    )
    async def take(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        if not has_role(interaction.user, DEVELOPER_SHIFT_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Entwickler-Berechtigung.",
                ephemeral=True
            )
            return

        if task["done"]:
            await interaction.response.send_message(
                "❌ Diese Aufgabe ist bereits erledigt.",
                ephemeral=True
            )
            return

        if task["taken_by"] and task["taken_by"] != interaction.user.id:
            await interaction.response.send_message(
                f"❌ Diese Aufgabe wurde bereits von "
                f"<@{task['taken_by']}> übernommen.",
                ephemeral=True
            )
            return

        task["taken_by"] = interaction.user.id
        save_data()

        await interaction.response.edit_message(
            embed=create_task_embed(self.task_id),
            view=DeveloperTaskView(self.task_id)
        )

    @ui.button(
        label="Erledigt",
        style=discord.ButtonStyle.success,
        custom_id="task_done"
    )
    async def done(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )
            return

        if not has_role(interaction.user, DEVELOPER_SHIFT_ROLE_ID):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        if task["taken_by"] and task["taken_by"] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Nur die Person, die die Aufgabe übernommen hat, "
                "kann sie als erledigt markieren.",
                ephemeral=True
            )
            return

        task["done"] = True
        save_data()

        await interaction.response.edit_message(
            embed=create_task_embed(self.task_id),
            view=DeveloperTaskView(self.task_id)
        )

    @ui.button(
        label="Löschen",
        style=discord.ButtonStyle.danger,
        custom_id="task_delete"
    )
    async def delete(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Nur der Owner kann Aufgaben löschen.",
                ephemeral=True
            )
            return

        data["tasks"].pop(self.task_id, None)
        save_data()

        await interaction.response.edit_message(
            embed=embed(
                "🗑️ Aufgabe gelöscht",
                f"Die Aufgabe **{self.task_id}** wurde gelöscht.",
                discord.Color.red()
            ),
            view=None
        )


class DeveloperTaskPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Neue Aufgabe",
        style=discord.ButtonStyle.primary,
        custom_id="developer_new_task"
    )
    async def new_task(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not has_role(interaction.user, DEVELOPER_SHIFT_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Entwickler-Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(TaskModal())


# =========================================================
# ENTWICKLER-SCHICHT
# =========================================================

active_shifts = set()


def create_shift_embed():
    if active_shifts:
        people = "\n".join(
            f"🟢 <@{user_id}> ist aktuell **im Dienst**."
            for user_id in active_shifts
        )

        description = (
            "Hier siehst du den aktuellen Entwickler-Schichtstatus.\n\n"
            + people
        )
    else:
        description = (
            "Hier siehst du den aktuellen Entwickler-Schichtstatus.\n\n"
            "🔴 **Niemand ist aktuell im Dienst.**"
        )

    return embed(
        "🛠️ Entwickler-Schicht",
        description,
        discord.Color.blurple()
    )


class DeveloperShiftView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        custom_id="shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        member = interaction.user

        if not has_role(member, SHIFT_PERMISSION_ROLE_ID):
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

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

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
    async def stop_shift(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        member = interaction.user

        if member.id not in active_shifts:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        active_shifts.remove(member.id)

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

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
        placeholder="1 bis 100",
        min_length=1,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            number = int(self.guess.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte gib eine Zahl ein.",
                ephemeral=True
            )
            return

        if number < 1 or number > 100:
            await interaction.response.send_message(
                "❌ Die Zahl muss zwischen 1 und 100 liegen.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        game = data["number_game"].get(user_id)

        if not game:
            game = {
                "number": random.randint(1, 100),
                "attempts": 0
            }

        game["attempts"] += 1

        target = game["number"]

        if number == target:

            attempts = game["attempts"]

            del data["number_game"][user_id]
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
    async def guess(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["number_game"]:
            data["number_game"][user_id] = {
                "number": random.randint(1, 100),
                "attempts": 0
            }
            save_data()

        await interaction.response.send_modal(NumberGameModal())


    @ui.button(
        label="Neues Spiel",
        style=discord.ButtonStyle.success,
        custom_id="number_new"
    )
    async def new_game(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        user_id = str(interaction.user.id)

        data["number_game"][user_id] = {
            "number": random.randint(1, 100),
            "attempts": 0
        }

        save_data()

        await interaction.response.send_message(
            "🎮 Neues Spiel gestartet! Klicke auf **Zahl raten**.",
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

    async def on_submit(self, interaction: discord.Interaction):

        channel = get_channel(FEEDBACK_CHANNEL_ID)

        if channel:
            e = embed(
                "💬 Neues Feedback",
                self.text.value
            )

            e.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            await channel.send(embed=e)

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

    async def on_submit(self, interaction: discord.Interaction):

        channel = get_channel(SUGGESTION_CHANNEL_ID)

        if channel:
            e = embed(
                "💡 Neuer Vorschlag",
                self.text.value
            )

            e.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            await channel.send(embed=e)

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
    async def feedback(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_modal(FeedbackModal())

    @ui.button(
        label="Vorschlag",
        style=discord.ButtonStyle.success,
        custom_id="community_suggestion"
    )
    async def suggestion(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_modal(SuggestionModal())


# =========================================================
# PANEL-BEFEHLE
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def nametag(ctx):

    e = embed(
        "🏷️ Nametag",
        "Klicke auf den Button, um deinen Nametag zu setzen."
    )

    await ctx.send(
        embed=e,
        view=NametagView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def kennzeichen(ctx):

    e = embed(
        "🚘 Kennzeichen",
        "Setze dein persönliches Kennzeichen oder entferne es wieder."
    )

    await ctx.send(
        embed=e,
        view=LicensePlateView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def entwickler(ctx):

    e = embed(
        "🛠️ Entwickler-Aufgaben",
        "Erstelle und verwalte Entwickler-Aufgaben."
    )

    await ctx.send(
        embed=e,
        view=DeveloperTaskPanelView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def schicht(ctx):

    e = create_shift_embed()

    await ctx.send(
        embed=e,
        view=DeveloperShiftView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def zahlenspiel(ctx):

    e = embed(
        "🔢 Zahlenspiel",
        "Denke dir eine Zahl zwischen **1 und 100** aus.\n\n"
        "Klicke auf **Zahl raten**, um zu starten."
    )

    await ctx.send(
        embed=e,
        view=NumberGameView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def community(ctx):

    e = embed(
        "🌐 Community",
        "Hier kannst du Feedback geben oder einen Vorschlag senden."
    )

    await ctx.send(
        embed=e,
        view=CommunityView()
    )


# =========================================================
# FEHLER BEI COMMANDS
# =========================================================

@nametag.error
@kennzeichen.error
@entwickler.error
@schicht.error
@zahlenspiel.error
@community.error
async def command_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Du brauchst Administrator-Rechte für diesen Befehl.",
            delete_after=5
        )


# =========================================================
# START
# =========================================================

@bot.event
async def on_ready():

    print("======================================")
    print(f"Bot online: {bot.user}")
    print(f"Bot-ID: {bot.user.id}")
    print("======================================")

    load_data()

    # Permanente Buttons registrieren
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(DeveloperTaskPanelView())
    bot.add_view(DeveloperShiftView())
    bot.add_view(NumberGameView())
    bot.add_view(CommunityView())

    # Gespeicherte Aufgaben wieder aktivieren
    for task_id in list(data["tasks"].keys()):
        try:
            bot.add_view(DeveloperTaskView(task_id))
        except Exception:
            pass


# =========================================================
# TOKEN PRÜFEN UND BOT STARTEN
# =========================================================

if TOKEN == "HIER_DEIN_DISCORD_BOT_TOKEN_EINTRAGEN":
    print("")
    print("======================================")
    print("FEHLER: Du hast deinen Bot-Token noch")
    print("nicht in bot.py eingetragen.")
    print("======================================")
    print("")
else:
    load_data()

    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("")
        print("======================================")
        print("FEHLER: Der Discord-Token ist falsch.")
        print("======================================")
    except Exception as e:
        print("")
        print("======================================")
        print("FEHLER:")
        print(e)
        print("======================================")
