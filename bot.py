import discord
from discord.ext import commands
from discord import ui

import asyncio
import json
import os
import random
import tempfile
from datetime import datetime


# =========================================================
# KONFIGURATION
# =========================================================

PREFIX = "?"
DATA_FILE = "bot_data.json"

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

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

DEVELOPER_APPLICATION_ROLE_ID = 1541393345295683634
DEVELOPER_TASK_PING_ROLE_ID = 1523674698574200904

COMMUNITY_PANEL_PERMISSION_ROLE_ID = 1544679876206796930

NAMETAG = "RLP | "


# =========================================================
# TOKEN AUS .ENV
# =========================================================

def load_env_file():
    token = os.getenv("DEIN_TOKEN")

    if token:
        return token.strip()

    if not os.path.exists(".env"):
        return None

    try:
        with open(".env", "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)

                key = key.strip()
                value = value.strip()

                if key == "DISCORD_TOKEN":

                    value = value.strip('"').strip("'")

                    return value

    except Exception as e:
        print(f"Fehler beim Lesen der .env: {e}")

    return None


TOKEN = load_env_file()


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

DEFAULT_DATA = {
    "license_plates": {},
    "tasks": {},
    "active_shifts": [],
    "applications": {},
    "panel_messages": {}
}


data = {}


def deep_merge(defaults, loaded):

    result = {}

    for key, value in defaults.items():

        if isinstance(value, dict):

            loaded_value = loaded.get(key, {})

            if isinstance(loaded_value, dict):
                result[key] = deep_merge(value, loaded_value)
            else:
                result[key] = value.copy()

        elif isinstance(value, list):

            loaded_value = loaded.get(key, [])

            if isinstance(loaded_value, list):
                result[key] = loaded_value.copy()
            else:
                result[key] = value.copy()

        else:

            result[key] = loaded.get(key, value)

    for key, value in loaded.items():

        if key not in result:
            result[key] = value

    return result


def save_data():

    try:

        directory = os.path.dirname(
            os.path.abspath(DATA_FILE)
        )

        fd, temp_path = tempfile.mkstemp(
            dir=directory,
            prefix="bot_data_",
            suffix=".tmp"
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temp_path,
            DATA_FILE
        )

    except Exception as e:

        print(f"Fehler beim Speichern: {e}")


def load_data():

    global data

    loaded = {}

    if os.path.exists(DATA_FILE):

        try:

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                loaded = json.load(file)

            if not isinstance(loaded, dict):
                loaded = {}

        except Exception as e:

            print(f"Fehler beim Laden der Daten: {e}")

    data = deep_merge(
        DEFAULT_DATA,
        loaded
    )

    # Altes Zahlenspiel vollständig entfernen
    data.pop("number_game", None)

    save_data()


load_data()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

async def get_or_fetch_channel(channel_id):

    channel = bot.get_channel(channel_id)

    if channel:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


def is_admin(member):
    return member.guild_permissions.administrator


def has_role(member, role_id):

    return any(
        role.id == role_id
        for role in member.roles
    )


def can_use_role(member, role_id):

    return (
        is_admin(member)
        or has_role(member, role_id)
    )


def user_text(user):

    return (
        f"{user.mention} ♡ Name: {user.name}. "
        f"ID: `{user.id}`"
    )


def make_embed(
    title,
    description="",
    color=None
):

    if color is None:
        color = discord.Color.blurple()

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.timestamp = datetime.now()

    return embed


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(
    ui.Modal,
    title="Nametag ändern"
):

    name = ui.TextInput(
        label="Dein Name",
        placeholder="Gib deinen Namen ein",
        max_length=30
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

        name = self.name.value.strip()

        if not name:

            await interaction.response.send_message(
                "❌ Bitte gib einen Namen ein.",
                ephemeral=True
            )
            return

        new_nick = f"{NAMETAG}{name}"

        try:

            await interaction.user.edit(
                nick=new_nick
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde geändert.",
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

        super().__init__(
            timeout=None
        )

        button = ui.Button(
            label="Nametag ändern",
            style=discord.ButtonStyle.primary,
            emoji="🏷️",
            custom_id="nametag_change"
        )

        button.callback = self.change_nametag

        self.add_item(button)

    async def change_nametag(self, interaction):

        await interaction.response.send_modal(
            NametagModal()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

def get_user_plate(user_id):

    return data["license_plates"].get(
        str(user_id)
    )


def create_license_panel_embed():

    embed = make_embed(
        "🚘 Kennzeichen-System",
        "Verwalte hier dein persönliches Kennzeichen.\n\n"
        "Mit **Kennzeichen setzen** kannst du ein neues "
        "Kennzeichen speichern oder dein bestehendes ändern.\n\n"
        "Mit **Kennzeichen entfernen** wird es sofort "
        "aus diesem Panel entfernt.",
        discord.Color.blue()
    )

    plates = data.get(
        "license_plates",
        {}
    )

    if not plates:

        embed.add_field(
            name="📋 Aktuelle Kennzeichen",
            value="Noch keine Kennzeichen eingetragen.",
            inline=False
        )

    else:

        lines = []

        for user_id, plate in plates.items():

            lines.append(
                f"🚘 <@{user_id}> — **{plate}**"
            )

        text = "\n".join(lines)

        if len(text) > 4000:
            text = text[:3990] + "\n..."

        embed.add_field(
            name="📋 Aktuelle Kennzeichen",
            value=text,
            inline=False
        )

    embed.set_footer(
        text="RLP • Kennzeichen-System"
    )

    return embed


async def refresh_license_panel():

    channel = await get_or_fetch_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if not channel:
        return

    message_id = data["panel_messages"].get(
        "license_plate"
    )

    if not message_id:
        return

    try:

        message = await channel.fetch_message(
            int(message_id)
        )

        await message.edit(
            embed=create_license_panel_embed(),
            view=LicensePlateView()
        )

    except discord.NotFound:

        message = await channel.send(
            embed=create_license_panel_embed(),
            view=LicensePlateView()
        )

        data["panel_messages"][
            "license_plate"
        ] = message.id

        save_data()

    except discord.Forbidden:

        print(
            "Keine Berechtigung für das Kennzeichen-Panel."
        )

    except Exception as e:

        print(
            f"Kennzeichen-Panel Fehler: {e}"
        )


class LicensePlateModal(
    ui.Modal,
    title="Kennzeichen setzen"
):

    plate = ui.TextInput(
        label="Kennzeichen",
        placeholder="z.B. GM-RL 123",
        max_length=20
    )

    async def on_submit(self, interaction):

        plate = self.plate.value.strip()

        if not plate:

            await interaction.response.send_message(
                "❌ Bitte gib ein Kennzeichen ein.",
                ephemeral=True
            )
            return

        data["license_plates"][
            str(interaction.user.id)
        ] = plate

        save_data()

        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde gespeichert.",
            ephemeral=True
        )


class LicensePlateView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        set_button = ui.Button(
            label="Kennzeichen setzen",
            style=discord.ButtonStyle.primary,
            emoji="🚘",
            custom_id="plate_set"
        )

        show_button = ui.Button(
            label="Mein Kennzeichen",
            style=discord.ButtonStyle.secondary,
            emoji="👁️",
            custom_id="plate_show"
        )

        remove_button = ui.Button(
            label="Kennzeichen entfernen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="plate_remove"
        )

        set_button.callback = self.set_plate
        show_button.callback = self.show_plate
        remove_button.callback = self.remove_plate

        self.add_item(set_button)
        self.add_item(show_button)
        self.add_item(remove_button)

    async def set_plate(self, interaction):

        await interaction.response.send_modal(
            LicensePlateModal()
        )

    async def show_plate(self, interaction):

        plate = get_user_plate(
            interaction.user.id
        )

        if not plate:

            await interaction.response.send_message(
                "ℹ️ Du hast aktuell kein Kennzeichen gespeichert.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🚘 Dein aktuelles Kennzeichen: **{plate}**",
            ephemeral=True
        )

    async def remove_plate(self, interaction):

        user_id = str(
            interaction.user.id
        )

        if user_id not in data["license_plates"]:

            await interaction.response.send_message(
                "ℹ️ Du hast aktuell kein Kennzeichen gespeichert.",
                ephemeral=True
            )
            return

        old_plate = data["license_plates"].pop(
            user_id
        )

        save_data()

        # Panel sofort aktualisieren
        await refresh_license_panel()

        await interaction.response.send_message(
            f"🗑️ Dein Kennzeichen **{old_plate}** wurde entfernt.",
            ephemeral=True
        )


# =========================================================
# ENTWICKLER-AUFGABEN
# =========================================================

def create_task_embed(task_id):

    task = data["tasks"].get(
        str(task_id)
    )

    if not task:
        return None

    if task.get("done"):

        status = "🟢 Erledigt"

    elif task.get("taken_by"):

        status = "🟡 In Bearbeitung"

    else:

        status = "⚪ Offen"

    creator = bot.get_user(
        int(task["creator"])
    )

    creator_text = (
        user_text(creator)
        if creator
        else f"<@{task['creator']}>"
    )

    taken_text = (
        f"<@{task['taken_by']}>"
        if task.get("taken_by")
        else "Niemand"
    )

    done_text = (
        f"<@{task['done_by']}>"
        if task.get("done_by")
        else "Noch nicht erledigt"
    )

    embed = make_embed(
        "🛠️ Entwickleraufgabe",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="📋 Aufgabe",
        value=task["text"],
        inline=False
    )

    embed.add_field(
        name="👤 Erstellt von",
        value=creator_text,
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=status,
        inline=False
    )

    embed.add_field(
        name="🙋 Übernommen von",
        value=taken_text,
        inline=False
    )

    embed.add_field(
        name="✅ Erledigt von",
        value=done_text,
        inline=False
    )

    embed.add_field(
        name="Aufgaben-ID",
        value=f"`{task_id}`",
        inline=False
    )

    return embed


class DeveloperTaskModal(
    ui.Modal,
    title="Neue Entwickleraufgabe"
):

    task = ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction):

        task_id = str(
            random.randint(
                100000,
                999999
            )
        )

        while task_id in data["tasks"]:

            task_id = str(
                random.randint(
                    100000,
                    999999
                )
            )

        data["tasks"][task_id] = {
            "text": self.task.value.strip(),
            "creator": interaction.user.id,
            "taken_by": None,
            "done": False,
            "done_by": None,
            "message_id": None
        }

        save_data()

        channel = await get_or_fetch_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Aufgaben-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        message = await channel.send(
            content=f"<@&{DEVELOPER_TASK_PING_ROLE_ID}>",
            embed=create_task_embed(task_id),
            view=DeveloperTaskView(task_id),
            allowed_mentions=discord.AllowedMentions(
                roles=True
            )
        )

        data["tasks"][task_id][
            "message_id"
        ] = message.id

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe **{task_id}** wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskPanelView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        button = ui.Button(
            label="Aufgabe erstellen",
            style=discord.ButtonStyle.primary,
            emoji="🛠️",
            custom_id="developer_task_create"
        )

        button.callback = self.create_task

        self.add_item(button)

    async def create_task(self, interaction):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(ui.View):

    def __init__(self, task_id):

        super().__init__(
            timeout=None
        )

        self.task_id = str(task_id)

        take = ui.Button(
            label="Übernehmen",
            style=discord.ButtonStyle.primary,
            emoji="🙋",
            custom_id=f"task_take_{self.task_id}"
        )

        done = ui.Button(
            label="Erledigt",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"task_done_{self.task_id}"
        )

        delete = ui.Button(
            label="Löschen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id=f"task_delete_{self.task_id}"
        )

        take.callback = self.take_task
        done.callback = self.done_task
        delete.callback = self.delete_task

        self.add_item(take)
        self.add_item(done)
        self.add_item(delete)

    async def take_task(self, interaction):

        task = data["tasks"].get(
            self.task_id
        )

        if not task:

            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )
            return

        if task.get("done"):

            await interaction.response.send_message(
                "⚠️ Die Aufgabe ist bereits erledigt.",
                ephemeral=True
            )
            return

        if not can_use_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        if task.get("taken_by"):

            await interaction.response.send_message(
                "⚠️ Die Aufgabe wurde bereits übernommen.",
                ephemeral=True
            )
            return

        task["taken_by"] = interaction.user.id

        save_data()

        await interaction.response.edit_message(
            embed=create_task_embed(
                self.task_id
            ),
            view=DeveloperTaskView(
                self.task_id
            )
        )

    async def done_task(self, interaction):

        task = data["tasks"].get(
            self.task_id
        )

        if not task:

            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )
            return

        if task.get("done"):

            await interaction.response.send_message(
                "⚠️ Aufgabe bereits erledigt.",
                ephemeral=True
            )
            return

        taken_by = task.get(
            "taken_by"
        )

        if not taken_by and not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Die Aufgabe wurde noch nicht übernommen.",
                ephemeral=True
            )
            return

        if (
            taken_by
            and interaction.user.id != taken_by
            and not is_admin(interaction.user)
        ):

            await interaction.response.send_message(
                "❌ Nur der Bearbeiter oder ein Administrator "
                "kann die Aufgabe erledigen.",
                ephemeral=True
            )
            return

        task["done"] = True
        task["done_by"] = interaction.user.id

        save_data()

        try:

            creator = await bot.fetch_user(
                int(task["creator"])
            )

            await creator.send(
                f"✅ Deine Entwickleraufgabe "
                f"**{self.task_id}** wurde erledigt."
            )

        except Exception:
            pass

        await interaction.response.edit_message(
            embed=create_task_embed(
                self.task_id
            ),
            view=DeveloperTaskView(
                self.task_id
            )
        )

    async def delete_task(self, interaction):

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Administratoren können Aufgaben löschen.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        data["tasks"].pop(
            self.task_id,
            None
        )

        save_data()

        try:
            await interaction.message.delete()
        except Exception:
            pass

        await interaction.followup.send(
            "🗑️ Aufgabe wurde gelöscht.",
            ephemeral=True
        )


# =========================================================
# ENTWICKLER-SCHICHT
# =========================================================

def create_shift_embed():

    active = data.get(
        "active_shifts",
        []
    )

    embed = make_embed(
        "🕐 Entwickler-Schicht",
        "Verwalte hier deine aktuelle Entwickler-Schicht.",
        discord.Color.green()
    )

    if not active:

        embed.add_field(
            name="👥 Aktuell im Dienst",
            value="Niemand ist aktuell im Dienst.",
            inline=False
        )

    else:

        members = []

        for user_id in active:

            members.append(
                f"🟢 <@{user_id}>"
            )

        embed.add_field(
            name="👥 Aktuell im Dienst",
            value="\n".join(members),
            inline=False
        )

    embed.set_footer(
        text="RLP • Entwickler-Schicht"
    )

    return embed


class DeveloperShiftView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        start = ui.Button(
            label="Schicht starten",
            style=discord.ButtonStyle.success,
            emoji="🟢",
            custom_id="shift_start"
        )

        stop = ui.Button(
            label="Schicht beenden",
            style=discord.ButtonStyle.danger,
            emoji="🔴",
            custom_id="shift_stop"
        )

        start.callback = self.start_shift
        stop.callback = self.stop_shift

        self.add_item(start)
        self.add_item(stop)

    async def start_shift(self, interaction):

        if not can_use_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        if interaction.user.id in data["active_shifts"]:

            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        data["active_shifts"].append(
            interaction.user.id
        )

        save_data()

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

        await interaction.response.edit_message(
            embed=create_shift_embed(),
            view=DeveloperShiftView()
        )

        await send_log(
            f"🟢 **Schicht gestartet:** "
            f"{interaction.user.mention}"
        )

    async def stop_shift(self, interaction):

        if interaction.user.id not in data["active_shifts"]:

            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        data["active_shifts"].remove(
            interaction.user.id
        )

        save_data()

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

        await interaction.response.edit_message(
            embed=create_shift_embed(),
            view=DeveloperShiftView()
        )

        await send_log(
            f"🔴 **Schicht beendet:** "
            f"{interaction.user.mention}"
        )


# =========================================================
# DEVELOPER-BEWERBUNG
# =========================================================

class DeveloperApplicationModal(
    ui.Modal,
    title="Developer-Bewerbung"
):

    name = ui.TextInput(
        label="Name",
        placeholder="Wie heißt du?",
        max_length=50
    )

    age = ui.TextInput(
        label="Alter",
        placeholder="Wie alt bist du?",
        max_length=3
    )

    experience = ui.TextInput(
        label="Erfahrung",
        placeholder="Welche Erfahrungen hast du?",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    motivation = ui.TextInput(
        label="Motivation",
        placeholder="Warum möchtest du Developer werden?",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    additional = ui.TextInput(
        label="Zusätzliche Informationen",
        placeholder="Optional",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000
    )

    async def on_submit(self, interaction):

        user_id = str(
            interaction.user.id
        )

        existing = data["applications"].get(
            user_id
        )

        if (
            existing
            and existing.get("status") == "open"
        ):

            await interaction.response.send_message(
                "❌ Du hast bereits eine offene Bewerbung.",
                ephemeral=True
            )
            return

        data["applications"][user_id] = {
            "user_id": interaction.user.id,
            "name": self.name.value,
            "age": self.age.value,
            "experience": self.experience.value,
            "motivation": self.motivation.value,
            "additional": self.additional.value,
            "status": "open",
            "message_id": None
        }

        save_data()

        channel = await get_or_fetch_channel(
            DEV_APPLICATION_RESULT_CHANNEL_ID
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = make_embed(
            "💻 Neue Developer-Bewerbung",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name.value,
            inline=False
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=False
        )

        embed.add_field(
            name="🛠️ Erfahrung",
            value=self.experience.value,
            inline=False
        )

        embed.add_field(
            name="🎯 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.add_field(
            name="📝 Zusätzlich",
            value=self.additional.value or "Keine Angabe",
            inline=False
        )

        embed.add_field(
            name="👤 Bewerber",
            value=user_text(interaction.user),
            inline=False
        )

        message = await channel.send(
            embed=embed,
            view=DeveloperApplicationDecisionView(
                user_id
            )
        )

        data["applications"][user_id][
            "message_id"
        ] = message.id

        save_data()

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich eingereicht.",
            ephemeral=True
        )


class DeveloperApplicationPanelView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        button = ui.Button(
            label="Jetzt bewerben",
            style=discord.ButtonStyle.primary,
            emoji="💻",
            custom_id="developer_application_open"
        )

        button.callback = self.open_application

        self.add_item(button)

    async def open_application(self, interaction):

        await interaction.response.send_modal(
            DeveloperApplicationModal()
        )


class DeveloperApplicationDecisionView(ui.View):

    def __init__(self, user_id):

        super().__init__(
            timeout=None
        )

        self.user_id = str(
            user_id
        )

        accept = ui.Button(
            label="Annehmen",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"application_accept_{self.user_id}"
        )

        reject = ui.Button(
            label="Ablehnen",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id=f"application_reject_{self.user_id}"
        )

        accept.callback = self.accept
        reject.callback = self.reject

        self.add_item(accept)
        self.add_item(reject)

    async def accept(self, interaction):

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Administratoren können Bewerbungen bearbeiten.",
                ephemeral=True
            )
            return

        application = data["applications"].get(
            self.user_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )
            return

        if application.get("status") != "open":

            await interaction.response.send_message(
                "⚠️ Diese Bewerbung wurde bereits bearbeitet.",
                ephemeral=True
            )
            return

        application["status"] = "accepted"

        save_data()

        member = interaction.guild.get_member(
            int(self.user_id)
        )

        role = interaction.guild.get_role(
            DEVELOPER_APPLICATION_ROLE_ID
        )

        if member and role:

            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

        try:

            applicant = await bot.fetch_user(
                int(self.user_id)
            )

            await applicant.send(
                "🎉 Deine Developer-Bewerbung wurde angenommen!"
            )

        except Exception:
            pass

        await interaction.response.edit_message(
            content="✅ Diese Bewerbung wurde angenommen.",
            view=None
        )

    async def reject(self, interaction):

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Administratoren können Bewerbungen bearbeiten.",
                ephemeral=True
            )
            return

        application = data["applications"].get(
            self.user_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )
            return

        if application.get("status") != "open":

            await interaction.response.send_message(
                "⚠️ Diese Bewerbung wurde bereits bearbeitet.",
                ephemeral=True
            )
            return

        application["status"] = "rejected"

        save_data()

        try:

            applicant = await bot.fetch_user(
                int(self.user_id)
            )

            await applicant.send(
                "❌ Deine Developer-Bewerbung wurde leider abgelehnt."
            )

        except Exception:
            pass

        await interaction.response.edit_message(
            content="❌ Diese Bewerbung wurde abgelehnt.",
            view=None
        )


# =========================================================
# COMMUNITY
# =========================================================

class FeedbackModal(
    ui.Modal,
    title="Community-Feedback"
):

    text = ui.TextInput(
        label="Dein Feedback",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction):

        channel = await get_or_fetch_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel:

            embed = make_embed(
                "💬 Neues Community-Feedback",
                self.text.value,
                discord.Color.blue()
            )

            embed.add_field(
                name="👤 Von",
                value=user_text(
                    interaction.user
                ),
                inline=False
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Dein Feedback wurde gesendet.",
            ephemeral=True
        )


class SuggestionModal(
    ui.Modal,
    title="Community-Vorschlag"
):

    text = ui.TextInput(
        label="Dein Vorschlag",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction):

        channel = await get_or_fetch_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel:

            embed = make_embed(
                "💡 Neuer Community-Vorschlag",
                self.text.value,
                discord.Color.green()
            )

            embed.add_field(
                name="👤 Von",
                value=user_text(
                    interaction.user
                ),
                inline=False
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde gesendet.",
            ephemeral=True
        )


class CommunityPanelView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        feedback = ui.Button(
            label="Feedback",
            style=discord.ButtonStyle.primary,
            emoji="💬",
            custom_id="community_feedback"
        )

        suggestion = ui.Button(
            label="Vorschlag",
            style=discord.ButtonStyle.success,
            emoji="💡",
            custom_id="community_suggestion"
        )

        feedback.callback = self.feedback
        suggestion.callback = self.suggestion

        self.add_item(feedback)
        self.add_item(suggestion)

    async def feedback(self, interaction):

        await interaction.response.send_modal(
            FeedbackModal()
        )

    async def suggestion(self, interaction):

        await interaction.response.send_modal(
            SuggestionModal()
        )


# =========================================================
# PANEL EMBEDS
# =========================================================

def nametag_panel():

    return make_embed(
        "🏷️ Nametag-System",
        "Ändere hier dein persönliches RLP-Nametag.\n\n"
        "Klicke auf **Nametag ändern**, um deinen Namen "
        "zu aktualisieren.",
        discord.Color.blurple()
    )


def developer_task_panel():

    return make_embed(
        "🛠️ Entwickleraufgaben",
        "Hier können neue Aufgaben für das Developer-Team "
        "erstellt und bearbeitet werden.",
        discord.Color.orange()
    )


def developer_shift_panel():

    return create_shift_embed()


def developer_application_panel():

    return make_embed(
        "💻 Developer-Bewerbung",
        "Du möchtest Teil des Developer-Teams werden?\n\n"
        "Klicke auf **Jetzt bewerben** und fülle die Bewerbung aus.",
        discord.Color.blurple()
    )


def community_panel():

    return make_embed(
        "🌐 Community",
        "Teile deine Ideen mit dem Team.\n\n"
        "💡 **Vorschlag**\n"
        "Sende uns eine Idee für den Server.\n\n"
        "💬 **Feedback**\n"
        "Teile uns deine Meinung mit.",
        discord.Color.green()
    )


# =========================================================
# PANEL VERWALTUNG
# =========================================================

async def remove_old_panel_messages(
    channel,
    title
):

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if message.embeds[0].title == title:

                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception as e:

        print(
            f"Panel-Suche fehlgeschlagen: {e}"
        )


async def refresh_panel(
    channel_id,
    title,
    embed,
    view,
    key
):

    channel = await get_or_fetch_channel(
        channel_id
    )

    if not channel:
        print(
            f"Kanal {channel_id} nicht gefunden."
        )
        return

    old_id = data["panel_messages"].get(
        key
    )

    if old_id:

        try:

            old_message = await channel.fetch_message(
                int(old_id)
            )

            await old_message.delete()

        except Exception:
            pass

    await remove_old_panel_messages(
        channel,
        title
    )

    try:

        message = await channel.send(
            embed=embed,
            view=view
        )

        data["panel_messages"][
            key
        ] = message.id

        save_data()

    except discord.Forbidden:

        print(
            f"Keine Berechtigung im Panel-Kanal {channel_id}."
        )

    except Exception as e:

        print(
            f"Panel konnte nicht erstellt werden: {e}"
        )


async def refresh_all_panels():

    await refresh_panel(
        NAMETAG_CHANNEL_ID,
        "🏷️ Nametag-System",
        nametag_panel(),
        NametagView(),
        "nametag"
    )

    await refresh_panel(
        LICENSE_PLATE_CHANNEL_ID,
        "🚘 Kennzeichen-System",
        create_license_panel_embed(),
        LicensePlateView(),
        "license_plate"
    )

    await refresh_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        "🛠️ Entwickleraufgaben",
        developer_task_panel(),
        DeveloperTaskPanelView(),
        "developer_tasks"
    )

    await refresh_panel(
        DEVELOPER_SHIFT_CHANNEL_ID,
        "🕐 Entwickler-Schicht",
        developer_shift_panel(),
        DeveloperShiftView(),
        "developer_shift"
    )

    await refresh_panel(
        DEV_APPLICATION_CHANNEL_ID,
        "💻 Developer-Bewerbung",
        developer_application_panel(),
        DeveloperApplicationPanelView(),
        "developer_application"
    )


# =========================================================
# COMMUNITY COMMANDS
# =========================================================

@bot.command()
async def communitypanel(ctx):

    if not has_role(
        ctx.author,
        COMMUNITY_PANEL_PERMISSION_ROLE_ID
    ):

        await ctx.send(
            "❌ Du hast keine Berechtigung für diesen Befehl.",
            delete_after=5
        )
        return

    await ctx.send(
        embed=community_panel(),
        view=CommunityPanelView()
    )


@bot.command()
async def community(ctx):

    await ctx.send(
        embed=community_panel()
    )


@bot.command()
async def helpme(ctx):

    embed = make_embed(
        "📖 Bot-Befehle",
        "Hier findest du die verfügbaren Befehle."
    )

    embed.add_field(
        name="?community",
        value="Community-Informationen anzeigen.",
        inline=False
    )

    embed.add_field(
        name="?communitypanel",
        value="Community-Panel erstellen.",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# READY
# =========================================================

startup_sync_done = False


@bot.event
async def on_ready():

    global startup_sync_done

    print()
    print("======================================")
    print(f"🤖 Bot online: {bot.user}")
    print(f"🆔 Bot-ID: {bot.user.id}")
    print("======================================")

    if startup_sync_done:
        return

    startup_sync_done = True

    await asyncio.sleep(2)

    # Feste Views
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
        DeveloperApplicationPanelView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    # Aufgaben-Views wiederherstellen
    for task_id in data["tasks"]:

        try:

            bot.add_view(
                DeveloperTaskView(
                    task_id
                )
            )

        except Exception as e:

            print(
                f"Task-View Fehler {task_id}: {e}"
            )

    # Bewerbungs-Views wiederherstellen
    for user_id, application in data[
        "applications"
    ].items():

        if application.get("status") == "open":

            try:

                bot.add_view(
                    DeveloperApplicationDecisionView(
                        user_id
                    )
                )

            except Exception as e:

                print(
                    f"Bewerbungs-View Fehler: {e}"
                )

    # Schichten synchronisieren
    guild = bot.get_guild(
        GUILD_ID
    )

    if guild:

        role = guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            active = set(
                data.get(
                    "active_shifts",
                    []
                )
            )

            for member in guild.members:

                should_have = (
                    member.id in active
                )

                has = (
                    role in member.roles
                )

                try:

                    if should_have and not has:

                        await member.add_roles(
                            role
                        )

                    elif not should_have and has:

                        await member.remove_roles(
                            role
                        )

                except discord.Forbidden:
                    pass

    # Panels aktualisieren
    await refresh_all_panels()

    print("✅ Alle Systeme geladen.")


# =========================================================
# FEHLER
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    print(
        f"Command-Fehler: {error}"
    )


# =========================================================
# START
# =========================================================

async def main():

    if not TOKEN:

        print()
        print("======================================")
        print("❌ DISCORD_TOKEN fehlt.")
        print("======================================")

        return

    try:

        await bot.start(
            TOKEN
        )

    except discord.LoginFailure:

        print()
        print("======================================")
        print("❌ Discord-Token ist ungültig.")
        print("======================================")

    except Exception as e:

        print()
        print("======================================")
        print("❌ BOT-FEHLER:")
        print(e)
        print("======================================")


if __name__ == "__main__":

    asyncio.run(
        main()
    )
