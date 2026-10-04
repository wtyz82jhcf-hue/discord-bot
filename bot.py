import discord
from discord.ext import commands
from discord import ui
import json
import os
import random
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


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

DEV_APPLICATION_CHANNEL_ID = 1541391365219295343
DEV_APPLICATION_RESULT_CHANNEL_ID = 1548404201493762181

SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200

NUMBER_GAME_CHANNEL_ID = 1556308645942136872

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

# Rolle, die man bei angenommener Dev-Bewerbung bekommt
DEVELOPER_APPLICATION_ROLE_ID = 1541393345295683634

DEVELOPER_TASK_PING_ROLE_ID = 1523674698574200904

PREFIX = "?"
DATA_FILE = "bot_data.json"

NUMBER_GAME_MAX = 10**18


# =========================================================
# BOT
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
    "active_shifts": [],
    "applications": {}
}


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        if isinstance(loaded, dict):
            data.update(loaded)

        data.setdefault("license_plates", {})
        data.setdefault("tasks", {})
        data.setdefault("number_game", {})
        data.setdefault("active_shifts", [])
        data.setdefault("applications", {})

    except Exception as e:
        print(f"Fehler beim Laden der Daten: {e}")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )
    except Exception as e:
        print(f"Fehler beim Speichern der Daten: {e}")


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_channel(channel_id):
    return bot.get_channel(channel_id)


def has_role(member, role_id):
    return any(
        role.id == role_id
        for role in member.roles
    )


def make_embed(
    title,
    description="",
    color=discord.Color.blurple()
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.set_footer(
        text="RLP Community Bot"
    )

    return embed


def member_info(user_id):
    if not user_id:
        return "Niemand"

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return "Unbekannt"

    user = bot.get_user(user_id)

    if user:
        return (
            f"{user.mention}\n"
            f"Name: {user}\n"
            f"ID: `{user.id}`"
        )

    return (
        f"<@{user_id}>\n"
        f"ID: `{user_id}`"
    )


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


# =========================================================
# STATUS
# =========================================================

STATUS_LIST = [
    "🛠️ Developed by RyZe",
    "🤝 Für eine starke & aktive Community",
    "🚀 RLP | Gemeinsam stärker"
]


async def status_loop():
    await bot.wait_until_ready()

    index = 0

    while not bot.is_closed():
        try:
            await bot.change_presence(
                status=discord.Status.online,
                activity=discord.Game(
                    name=STATUS_LIST[index]
                )
            )

            index = (index + 1) % len(STATUS_LIST)

            await asyncio.sleep(10)

        except Exception as e:
            print(f"Status-Fehler: {e}")
            await asyncio.sleep(10)


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(
    ui.Modal,
    title="🏷️ Nametag ändern"
):

    nametag = ui.TextInput(
        label="Neuer Nametag",
        placeholder="Dein neuer Nametag...",
        required=True,
        max_length=32
    )

    async def on_submit(self, interaction):

        if not has_role(
            interaction.user,
            NAMETAG_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für das Nametag-System.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.edit(
                nick=self.nametag.value
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde zu "
                f"**{self.nametag.value}** geändert.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Nametag-Fehler: {e}")

            await interaction.response.send_message(
                "❌ Beim Ändern ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class NametagView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Nametag ändern",
        style=discord.ButtonStyle.primary,
        emoji="🏷️",
        custom_id="nametag_set"
    )
    async def change_nametag(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            NametagModal()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(ui.Modal):

    def __init__(self):
        super().__init__(
            title="🚗 Kennzeichen ändern"
        )

        self.plate = ui.TextInput(
            label="Neues Kennzeichen",
            placeholder="z.B. GM-RY 123",
            required=True,
            max_length=20
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction):

        plate = self.plate.value.strip().upper()

        if not plate:
            await interaction.response.send_message(
                "❌ Das Kennzeichen darf nicht leer sein.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        data["license_plates"][user_id] = plate

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen wurde auf "
            f"**{plate}** geändert.",
            ephemeral=True
        )


class LicensePlateView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Kennzeichen setzen / ändern",
        style=discord.ButtonStyle.primary,
        emoji="🚗",
        custom_id="plate_set"
    )
    async def set_plate(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @ui.button(
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="plate_remove"
    )
    async def remove_plate(
        self,
        interaction,
        button
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
# ENTWICKLERAUFGABEN
# =========================================================

def get_task_status(task):

    if task.get("done_by"):
        return "🟢 Erledigt"

    if task.get("taken_by"):
        return "🟡 In Bearbeitung"

    return "🔵 Offen"


def create_task_embed(task_id):

    task = data["tasks"].get(str(task_id))

    if not task:
        return make_embed(
            "❌ Aufgabe nicht gefunden",
            color=discord.Color.red()
        )

    embed = discord.Embed(
        title="🛠️ Entwickleraufgabe",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📋 Aufgabe",
        value=task.get(
            "task",
            "Keine Aufgabe"
        ),
        inline=False
    )

    embed.add_field(
        name="👤 Erstellt von",
        value=member_info(
            task.get("creator")
        ),
        inline=True
    )

    embed.add_field(
        name="📊 Status",
        value=get_task_status(task),
        inline=True
    )

    embed.add_field(
        name="🙋 Übernommen von",
        value=(
            member_info(task["taken_by"])
            if task.get("taken_by")
            else "Niemand"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ Erledigt von",
        value=(
            member_info(task["done_by"])
            if task.get("done_by")
            else "Noch nicht erledigt"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"Aufgaben-ID: {task_id}"
    )

    return embed


class DeveloperTaskModal(
    ui.Modal,
    title="🛠️ Neue Entwickleraufgabe"
):

    task = ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction):

        task_id = str(
            random.randint(100000, 999999)
        )

        while task_id in data["tasks"]:
            task_id = str(
                random.randint(100000, 999999)
            )

        data["tasks"][task_id] = {
            "task": self.task.value,
            "creator": interaction.user.id,
            "taken_by": None,
            "done_by": None
        }

        save_data()

        channel = get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Entwickler-Aufgabenkanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        await channel.send(
            content=f"<@&{DEVELOPER_TASK_PING_ROLE_ID}>",
            embed=create_task_embed(task_id),
            view=DeveloperTaskView(task_id),
            allowed_mentions=discord.AllowedMentions(
                roles=True
            )
        )

        await interaction.response.send_message(
            "✅ Die Entwickleraufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id="developer_task_create"
    )
    async def create_task(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren können Aufgaben erstellen.",
                ephemeral=True
            )
            return

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
        label="Übernehmen",
        style=discord.ButtonStyle.primary,
        emoji="🙋"
    )
    async def take_task(
        self,
        interaction,
        button
    ):

        task = data["tasks"].get(
            self.task_id
        )

        if not task:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        if task.get("done_by"):
            await interaction.response.send_message(
                "❌ Diese Aufgabe ist bereits erledigt.",
                ephemeral=True
            )
            return

        if task.get("taken_by"):
            await interaction.response.send_message(
                "❌ Diese Aufgabe wurde bereits übernommen.",
                ephemeral=True
            )
            return

        task["taken_by"] = interaction.user.id

        save_data()

        await interaction.response.edit_message(
            embed=create_task_embed(
                self.task_id
            ),
            view=self
        )

    @ui.button(
        label="Erledigt",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def done_task(
        self,
        interaction,
        button
    ):

        task = data["tasks"].get(
            self.task_id
        )

        if not task:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        if task.get("done_by"):
            await interaction.response.send_message(
                "❌ Diese Aufgabe ist bereits erledigt.",
                ephemeral=True
            )
            return

        if not task.get("taken_by"):
            await interaction.response.send_message(
                "❌ Die Aufgabe muss zuerst übernommen werden.",
                ephemeral=True
            )
            return

        task["done_by"] = interaction.user.id

        save_data()

        await interaction.response.edit_message(
            embed=create_task_embed(
                self.task_id
            ),
            view=self
        )

        creator_id = task.get("creator")

        if creator_id:

            try:

                creator = await bot.fetch_user(
                    int(creator_id)
                )

                dm_embed = discord.Embed(
                    title="✅ Entwickleraufgabe erledigt",
                    description=(
                        "Eine von dir erstellte "
                        "Entwickleraufgabe wurde abgeschlossen."
                    ),
                    color=discord.Color.green()
                )

                dm_embed.add_field(
                    name="📋 Aufgabe",
                    value=task.get(
                        "task",
                        "Keine Aufgabe"
                    ),
                    inline=False
                )

                dm_embed.add_field(
                    name="👤 Erledigt von",
                    value=member_info(
                        interaction.user.id
                    ),
                    inline=False
                )

                dm_embed.add_field(
                    name="🆔 Aufgaben-ID",
                    value=f"`{self.task_id}`",
                    inline=True
                )

                await creator.send(
                    embed=dm_embed
                )

            except Exception as e:
                print(
                    f"Fehler bei Aufgaben-DM: {e}"
                )

    @ui.button(
        label="Löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def delete_task(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren können Aufgaben löschen.",
                ephemeral=True
            )
            return

        data["tasks"].pop(
            self.task_id,
            None
        )

        save_data()

        await interaction.response.edit_message(
            embed=make_embed(
                "🗑️ Aufgabe gelöscht",
                "Diese Entwickleraufgabe wurde gelöscht.",
                discord.Color.red()
            ),
            view=None
        )


# =========================================================
# ENTWICKLER-SCHICHT
# =========================================================

class DeveloperShiftView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="shift_start"
    )
    async def start_shift(
        self,
        interaction,
        button
    ):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für Entwickler-Schichten.",
                ephemeral=True
            )
            return

        active_shifts = get_active_shifts()

        if interaction.user.id in active_shifts:
            await interaction.response.send_message(
                "❌ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        active_shifts.add(
            interaction.user.id
        )

        save_active_shifts(
            active_shifts
        )

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            try:
                await interaction.user.add_roles(
                    role
                )
            except discord.Forbidden:
                pass

        log_channel = get_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:
            await log_channel.send(
                f"🟢 **Schicht gestartet**\n"
                f"👤 {interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            )

        await interaction.response.send_message(
            "🟢 Deine Schicht wurde gestartet.",
            ephemeral=True
        )

    @ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="shift_stop"
    )
    async def stop_shift(
        self,
        interaction,
        button
    ):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für Entwickler-Schichten.",
                ephemeral=True
            )
            return

        active_shifts = get_active_shifts()

        if interaction.user.id not in active_shifts:
            await interaction.response.send_message(
                "❌ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        active_shifts.remove(
            interaction.user.id
        )

        save_active_shifts(
            active_shifts
        )

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            try:
                await interaction.user.remove_roles(
                    role
                )
            except discord.Forbidden:
                pass

        log_channel = get_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:
            await log_channel.send(
                f"🔴 **Schicht beendet**\n"
                f"👤 {interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            )

        await interaction.response.send_message(
            "🔴 Deine Schicht wurde beendet.",
            ephemeral=True
        )


# =========================================================
# ZAHLENSPIEL
# =========================================================

def get_number_game():

    if not isinstance(
        data.get("number_game"),
        dict
    ):
        data["number_game"] = {}

    game = data["number_game"]

    game.setdefault(
        "active",
        False
    )

    game.setdefault(
        "player",
        None
    )

    game.setdefault(
        "secret",
        None
    )

    return game


def format_number(number):
    return f"{int(number):,}".replace(",", ".")


def create_number_game_embed():

    game = get_number_game()

    if not game["active"]:

        embed = discord.Embed(
            title="🎯 Zahlenspiel",
            description=(
                "Errate die geheime Zahl!\n\n"
                f"🔢 Bereich: **1 – {format_number(NUMBER_GAME_MAX)}**\n\n"
                "Klicke auf **Neues Spiel**, um zu starten."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📊 Status",
            value="🔵 Kein Spiel aktiv",
            inline=False
        )

        return embed

    embed = discord.Embed(
        title="🎯 Zahlenspiel",
        description=(
            "Ein Zahlenspiel läuft aktuell.\n\n"
            "Gib über **Zahl erraten** deine Vermutung ein."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="👤 Spieler",
        value=f"<@{game['player']}>",
        inline=True
    )

    embed.add_field(
        name="📊 Status",
        value="🟢 Läuft",
        inline=True
    )

    embed.add_field(
        name="🔢 Zahlenbereich",
        value=f"1 – {format_number(NUMBER_GAME_MAX)}",
        inline=False
    )

    return embed


class NumberGameGuessModal(
    ui.Modal,
    title="🎯 Zahl erraten"
):

    number = ui.TextInput(
        label="Deine Vermutung",
        placeholder="Gib eine Zahl ein...",
        required=True,
        max_length=19
    )

    async def on_submit(self, interaction):

        game = get_number_game()

        if not game["active"]:

            await interaction.response.send_message(
                "❌ Es läuft aktuell kein Zahlenspiel.",
                ephemeral=True
            )
            return

        if game["player"] != interaction.user.id:

            await interaction.response.send_message(
                "❌ Du hast dieses Zahlenspiel nicht gestartet.",
                ephemeral=True
            )
            return

        try:
            guess = int(
                self.number.value.strip()
            )
        except ValueError:

            await interaction.response.send_message(
                "❌ Bitte gib nur eine gültige ganze Zahl ein.",
                ephemeral=True
            )
            return

        if guess < 1 or guess > NUMBER_GAME_MAX:

            await interaction.response.send_message(
                (
                    f"❌ Die Zahl muss zwischen "
                    f"1 und {format_number(NUMBER_GAME_MAX)} liegen."
                ),
                ephemeral=True
            )
            return

        secret = game["secret"]

        if guess == secret:

            game["active"] = False
            game["player"] = None
            game["secret"] = None

            save_data()

            embed = discord.Embed(
                title="🎉 Zahl erraten!",
                description=(
                    f"{interaction.user.mention} hat "
                    "die geheime Zahl gefunden!"
                ),
                color=discord.Color.green()
            )

            embed.add_field(
                name="🔢 Richtige Zahl",
                value=f"**{format_number(secret)}**",
                inline=False
            )

            embed.set_footer(
                text="Klicke auf „Neues Spiel“, um erneut zu spielen."
            )

            await interaction.response.edit_message(
                embed=embed,
                view=NumberGameView()
            )

            return

        if guess < secret:
            message = (
                f"📈 **Zu niedrig!**\n\n"
                f"Deine Zahl: **{format_number(guess)}**"
            )
        else:
            message = (
                f"📉 **Zu hoch!**\n\n"
                f"Deine Zahl: **{format_number(guess)}**"
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


class NumberGameView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Neues Spiel",
        style=discord.ButtonStyle.success,
        emoji="🎮",
        custom_id="number_new_game"
    )
    async def new_game(
        self,
        interaction,
        button
    ):

        game = get_number_game()

        if game["active"]:

            await interaction.response.send_message(
                "⚠️ Es läuft bereits ein Zahlenspiel.",
                ephemeral=True
            )
            return

        game["active"] = True
        game["player"] = interaction.user.id

        game["secret"] = random.randint(
            1,
            NUMBER_GAME_MAX
        )

        save_data()

        await interaction.response.edit_message(
            embed=create_number_game_embed(),
            view=NumberGameView()
        )

    @ui.button(
        label="Zahl erraten",
        style=discord.ButtonStyle.primary,
        emoji="🔢",
        custom_id="number_guess"
    )
    async def guess_number(
        self,
        interaction,
        button
    ):

        game = get_number_game()

        if not game["active"]:

            await interaction.response.send_message(
                "❌ Es läuft aktuell kein Zahlenspiel.",
                ephemeral=True
            )
            return

        if game["player"] != interaction.user.id:

            await interaction.response.send_message(
                "❌ Du hast dieses Spiel nicht gestartet.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            NumberGameGuessModal()
        )

    @ui.button(
        label="Aufgeben",
        style=discord.ButtonStyle.danger,
        emoji="🏳️",
        custom_id="number_give_up"
    )
    async def give_up(
        self,
        interaction,
        button
    ):

        game = get_number_game()

        if not game["active"]:

            await interaction.response.send_message(
                "❌ Es läuft aktuell kein Zahlenspiel.",
                ephemeral=True
            )
            return

        if game["player"] != interaction.user.id:

            await interaction.response.send_message(
                "❌ Nur der Spieler kann das Spiel aufgeben.",
                ephemeral=True
            )
            return

        secret = game["secret"]

        game["active"] = False
        game["player"] = None
        game["secret"] = None

        save_data()

        embed = discord.Embed(
            title="🏳️ Zahlenspiel beendet",
            description=(
                f"{interaction.user.mention} hat aufgegeben."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="🔢 Die gesuchte Zahl war",
            value=f"**{format_number(secret)}**",
            inline=False
        )

        embed.set_footer(
            text="Klicke auf „Neues Spiel“, um erneut zu spielen."
        )

        await interaction.response.edit_message(
            embed=embed,
            view=NumberGameView()
        )


# =========================================================
# DEV-BEWERBUNG
# =========================================================

class DevApplicationModal(
    ui.Modal,
    title="🛠️ Entwickler-Bewerbung"
):

    name = ui.TextInput(
        label="Name / Discord-Name",
        placeholder="Wie heißt du?",
        required=True,
        max_length=100
    )

    age = ui.TextInput(
        label="Alter",
        placeholder="Wie alt bist du?",
        required=True,
        max_length=3
    )

    experience = ui.TextInput(
        label="Erfahrung",
        placeholder="Welche Erfahrungen hast du als Entwickler?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    motivation = ui.TextInput(
        label="Motivation",
        placeholder="Warum möchtest du Entwickler werden?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    additional = ui.TextInput(
        label="Weitere Informationen",
        placeholder="Gibt es noch etwas Wichtiges?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000
    )

    async def on_submit(self, interaction):

        # Prüfen, ob bereits eine offene Bewerbung existiert
        for application in data["applications"].values():

            if (
                application.get("user_id")
                == interaction.user.id
                and application.get("status")
                == "offen"
            ):

                await interaction.response.send_message(
                    "❌ Du hast bereits eine offene Entwickler-Bewerbung.",
                    ephemeral=True
                )
                return

        application_id = str(
            random.randint(
                100000,
                999999
            )
        )

        while application_id in data["applications"]:
            application_id = str(
                random.randint(
                    100000,
                    999999
                )
            )

        data["applications"][application_id] = {
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "name": self.name.value,
            "age": self.age.value,
            "experience": self.experience.value,
            "motivation": self.motivation.value,
            "additional": self.additional.value,
            "status": "offen"
        }

        save_data()

        channel = get_channel(
            DEV_APPLICATION_RESULT_CHANNEL_ID
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Der Bewerbungs-Auswertungskanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛠️ Neue Entwickler-Bewerbung",
            description="Eine neue Bewerbung wurde eingereicht.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=(
                f"{interaction.user.mention}\n"
                f"Discord: {interaction.user}\n"
                f"ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Name",
            value=self.name.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=True
        )

        embed.add_field(
            name="🛠️ Erfahrung",
            value=self.experience.value,
            inline=False
        )

        embed.add_field(
            name="💡 Motivation",
            value=self.motivation.value,
            inline=False
        )

        if self.additional.value.strip():

            embed.add_field(
                name="📌 Weitere Informationen",
                value=self.additional.value,
                inline=False
            )

        embed.add_field(
            name="📊 Status",
            value="🟡 Offen",
            inline=True
        )

        embed.set_footer(
            text=f"Bewerbungs-ID: {application_id}"
        )

        await channel.send(
            embed=embed,
            view=DevApplicationDecisionView(
                application_id
            )
        )

        await interaction.response.send_message(
            "✅ Deine Entwickler-Bewerbung wurde erfolgreich "
            "eingereicht.",
            ephemeral=True
        )


class DevApplicationPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Bewerbung starten",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id="dev_application_start"
    )
    async def start_application(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            DevApplicationModal()
        )


class DevApplicationDecisionView(ui.View):

    def __init__(self, application_id):

        super().__init__(timeout=None)

        self.application_id = str(
            application_id
        )

        self.children[0].custom_id = (
            f"devapp_accept_{self.application_id}"
        )

        self.children[1].custom_id = (
            f"devapp_reject_{self.application_id}"
        )

    async def finish_message(
        self,
        interaction,
        embed
    ):

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    @ui.button(
        label="Annehmen",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def accept_application(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Nur Administratoren können Bewerbungen bearbeiten.",
                ephemeral=True
            )
            return

        application = data["applications"].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Diese Bewerbung existiert nicht mehr.",
                ephemeral=True
            )
            return

        if application.get("status") != "offen":

            await interaction.response.send_message(
                "❌ Diese Bewerbung wurde bereits bearbeitet.",
                ephemeral=True
            )
            return

        # Bewerbung annehmen
        application["status"] = "angenommen"
        application["accepted_by"] = interaction.user.id

        save_data()

        # =====================================================
        # DEVELOPER ROLLE GEBEN
        # =====================================================

        role = interaction.guild.get_role(
            DEVELOPER_APPLICATION_ROLE_ID
        )

        role_success = False

        if role:

            try:

                applicant_member = interaction.guild.get_member(
                    int(application["user_id"])
                )

                if applicant_member:

                    if role not in applicant_member.roles:

                        await applicant_member.add_roles(
                            role,
                            reason="Entwickler-Bewerbung angenommen"
                        )

                    role_success = True

            except discord.Forbidden:
                print(
                    "❌ Bot darf die Developer-Rolle nicht vergeben."
                )

            except Exception as e:
                print(
                    f"❌ Fehler beim Vergeben der Developer-Rolle: {e}"
                )

        else:

            print(
                f"❌ Developer-Rolle {DEVELOPER_APPLICATION_ROLE_ID} "
                f"wurde nicht gefunden."
            )

        # =====================================================
        # ENTSCHEIDUNGS-EMBED
        # =====================================================

        embed = discord.Embed(
            title="✅ Entwickler-Bewerbung angenommen",
            description="Diese Bewerbung wurde angenommen.",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=(
                f"<@{application['user_id']}>\n"
                f"ID: `{application['user_id']}`"
            ),
            inline=False
        )

        embed.add_field(
            name="👮 Bearbeitet von",
            value=(
                f"{interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🛠️ Developer-Rolle",
            value=(
                "✅ Rolle wurde vergeben."
                if role_success
                else "⚠️ Rolle konnte nicht vergeben werden."
            ),
            inline=False
        )

        embed.set_footer(
            text=f"Bewerbungs-ID: {self.application_id}"
        )

        await self.finish_message(
            interaction,
            embed
        )

        # =====================================================
        # DM
        # =====================================================

        try:

            applicant = await bot.fetch_user(
                int(application["user_id"])
            )

            dm_embed = discord.Embed(
                title="🎉 Deine Entwickler-Bewerbung wurde angenommen!",
                description=(
                    "Herzlichen Glückwunsch!\n\n"
                    "Deine Bewerbung für das Entwickler-Team "
                    "wurde angenommen.\n\n"
                    "Die Developer-Rolle wurde dir automatisch "
                    "auf dem Server vergeben."
                ),
                color=discord.Color.green()
            )

            dm_embed.add_field(
                name="📊 Entscheidung",
                value="✅ Angenommen",
                inline=True
            )

            dm_embed.add_field(
                name="🛠️ Rolle",
                value=(
                    "✅ Developer-Rolle vergeben"
                    if role_success
                    else "⚠️ Rolle konnte nicht vergeben werden"
                ),
                inline=True
            )

            dm_embed.add_field(
                name="🆔 Bewerbungs-ID",
                value=f"`{self.application_id}`",
                inline=False
            )

            dm_embed.set_footer(
                text="RLP Community Bot • Entwickler-Team"
            )

            await applicant.send(
                embed=dm_embed
            )

        except discord.Forbidden:

            print(
                "⚠️ DM an angenommenen Bewerber konnte nicht gesendet werden."
            )

        except Exception as e:

            print(
                f"❌ Fehler bei Annahme-DM: {e}"
            )

    @ui.button(
        label="Ablehnen",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def reject_application(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Nur Administratoren können Bewerbungen bearbeiten.",
                ephemeral=True
            )
            return

        application = data["applications"].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Diese Bewerbung existiert nicht mehr.",
                ephemeral=True
            )
            return

        if application.get("status") != "offen":

            await interaction.response.send_message(
                "❌ Diese Bewerbung wurde bereits bearbeitet.",
                ephemeral=True
            )
            return

        application["status"] = "abgelehnt"
        application["rejected_by"] = interaction.user.id

        save_data()

        embed = discord.Embed(
            title="❌ Entwickler-Bewerbung abgelehnt",
            description="Diese Bewerbung wurde abgelehnt.",
            color=discord.Color.red()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=(
                f"<@{application['user_id']}>\n"
                f"ID: `{application['user_id']}`"
            ),
            inline=False
        )

        embed.add_field(
            name="👮 Bearbeitet von",
            value=(
                f"{interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.set_footer(
            text=f"Bewerbungs-ID: {self.application_id}"
        )

        await self.finish_message(
            interaction,
            embed
        )

        try:

            applicant = await bot.fetch_user(
                int(application["user_id"])
            )

            dm_embed = discord.Embed(
                title="📩 Update zu deiner Entwickler-Bewerbung",
                description=(
                    "Vielen Dank für dein Interesse an unserem "
                    "Entwickler-Team.\n\n"
                    "Deine Bewerbung wurde geprüft und "
                    "dieses Mal leider abgelehnt.\n\n"
                    "Wir wünschen dir weiterhin viel Erfolg!"
                ),
                color=discord.Color.red()
            )

            dm_embed.add_field(
                name="📊 Entscheidung",
                value="❌ Abgelehnt",
                inline=True
            )

            dm_embed.add_field(
                name="🆔 Bewerbungs-ID",
                value=f"`{self.application_id}`",
                inline=True
            )

            dm_embed.set_footer(
                text="RLP Community Bot • Entwickler-Team"
            )

            await applicant.send(
                embed=dm_embed
            )

        except discord.Forbidden:

            print(
                "⚠️ DM an abgelehnten Bewerber konnte nicht gesendet werden."
            )

        except Exception as e:

            print(
                f"❌ Fehler bei Ablehnungs-DM: {e}"
            )


# =========================================================
# COMMUNITY
# =========================================================

class SuggestionModal(
    ui.Modal,
    title="💡 Vorschlag einreichen"
):

    suggestion = ui.TextInput(
        label="Dein Vorschlag",
        placeholder="Was möchtest du vorschlagen?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction):

        channel = get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Vorschlagskanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💡 Neuer Community-Vorschlag",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="👤 Von",
            value=(
                f"{interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Vorschlag",
            value=self.suggestion.value,
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde eingereicht.",
            ephemeral=True
        )


class FeedbackModal(
    ui.Modal,
    title="⭐ Feedback geben"
):

    feedback = ui.TextInput(
        label="Dein Feedback",
        placeholder="Dein Feedback...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction):

        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Feedbackkanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⭐ Neues Community-Feedback",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 Von",
            value=(
                f"{interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="💬 Feedback",
            value=self.feedback.value,
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Vielen Dank für dein Feedback!",
            ephemeral=True
        )


class CommunityView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Vorschlag",
        style=discord.ButtonStyle.primary,
        emoji="💡",
        custom_id="community_suggestion"
    )
    async def suggestion(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            SuggestionModal()
        )

    @ui.button(
        label="Feedback",
        style=discord.ButtonStyle.success,
        emoji="⭐",
        custom_id="community_feedback"
    )
    async def feedback(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            FeedbackModal()
        )


class CommunityPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Vorschlag einreichen",
        style=discord.ButtonStyle.primary,
        emoji="💡",
        custom_id="community_panel_suggestion"
    )
    async def suggestion(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            SuggestionModal()
        )

    @ui.button(
        label="Feedback geben",
        style=discord.ButtonStyle.success,
        emoji="⭐",
        custom_id="community_panel_feedback"
    )
    async def feedback(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            FeedbackModal()
        )


# =========================================================
# BEFEHLE
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def nametag(ctx):

    embed = discord.Embed(
        title="🏷️ Nametag-System",
        description=(
            "Klicke auf den Button, um deinen Nametag zu ändern."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=NametagView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def kennzeichen(ctx):

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen setzen, "
            "ändern oder entfernen."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=LicensePlateView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def entwickler(ctx):

    embed = discord.Embed(
        title="🛠️ Entwickleraufgaben",
        description=(
            "Hier können Entwickleraufgaben erstellt "
            "und verwaltet werden."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=DeveloperTaskPanelView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def schicht(ctx):

    embed = discord.Embed(
        title="🕐 Entwickler-Schicht",
        description=(
            "Starte oder beende deine Entwickler-Schicht."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=DeveloperShiftView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def zahlenspiel(ctx):

    await ctx.send(
        embed=create_number_game_embed(),
        view=NumberGameView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def devbewerbung(ctx):

    embed = discord.Embed(
        title="🛠️ Entwickler-Bewerbung",
        description=(
            "Du möchtest Teil unseres Entwickler-Teams werden?\n\n"
            "Klicke auf **Bewerbung starten** und fülle "
            "das Formular aus.\n\n"
            "Deine Bewerbung wird anschließend vom "
            "Team geprüft."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=DevApplicationPanelView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def community(ctx):

    embed = discord.Embed(
        title="🤝 Community",
        description=(
            "Sende uns einen Vorschlag oder Feedback."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=CommunityView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def communitypanel(ctx):

    embed = discord.Embed(
        title="🤝 Community-Panel",
        description=(
            "Nutze die Buttons unten."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=CommunityPanelView()
    )


@bot.command()
async def helpme(ctx):

    embed = discord.Embed(
        title="📚 Bot-Hilfe",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🏷️ Nametag",
        value="`?nametag`",
        inline=False
    )

    embed.add_field(
        name="🚗 Kennzeichen",
        value="`?kennzeichen`",
        inline=False
    )

    embed.add_field(
        name="🛠️ Entwickler",
        value="`?entwickler`",
        inline=False
    )

    embed.add_field(
        name="📝 Dev-Bewerbung",
        value="`?devbewerbung`",
        inline=False
    )

    embed.add_field(
        name="🕐 Schicht",
        value="`?schicht`",
        inline=False
    )

    embed.add_field(
        name="🎯 Zahlenspiel",
        value="`?zahlenspiel`",
        inline=False
    )

    embed.add_field(
        name="🤝 Community",
        value="`?community`",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# FEHLERBEHANDLUNG
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
            embed=make_embed(
                "❌ Keine Berechtigung",
                "Du benötigst Administrator-Rechte.",
                discord.Color.red()
            )
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

    print(
        f"✅ Bot ist online als {bot.user}"
    )

    print(
        f"🌐 Server: {len(bot.guilds)}"
    )


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
        DevApplicationPanelView()
    )

    bot.add_view(
        CommunityView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    # Entwickleraufgaben wiederherstellen
    for task_id in list(
        data.get("tasks", {}).keys()
    ):

        try:

            bot.add_view(
                DeveloperTaskView(
                    task_id
                )
            )

        except Exception as e:

            print(
                f"Fehler bei Aufgabe {task_id}: {e}"
            )

    # Offene Bewerbungen wiederherstellen
    for application_id in list(
        data.get("applications", {}).keys()
    ):

        try:

            application = data["applications"][
                application_id
            ]

            if application.get("status") == "offen":

                bot.add_view(
                    DevApplicationDecisionView(
                        application_id
                    )
                )

        except Exception as e:

            print(
                f"Fehler bei Bewerbung "
                f"{application_id}: {e}"
            )


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(200)
        self.end_headers()

        self.wfile.write(
            b"Bot is running"
        )

    def log_message(
        self,
        format,
        *args
    ):
        pass


def start_web_server():

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(
        f"✅ Health-Server auf Port {port}"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    await setup_persistent_views()

    asyncio.create_task(
        status_loop()
    )

    await bot.start(
        TOKEN
    )


if __name__ == "__main__":

    if not TOKEN:

        print(
            "❌ FEHLER: DISCORD_TOKEN fehlt."
        )

    else:

        try:

            start_web_server()

            asyncio.run(
                main()
            )

        except discord.LoginFailure:

            print(
                "❌ FEHLER: Discord-Token ist falsch."
            )

        except Exception as e:

            print(
                f"❌ FEHLER: {e}"
            )
