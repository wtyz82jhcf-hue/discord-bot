import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import tempfile
import random
import time

# =========================================================
# EINSTELLUNGEN
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

EMOJI_QUIZ_CHANNEL_ID = 1533409789256925185

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

DEVELOPER_APPLICATION_ROLE_ID = 1541393345295683634
DEVELOPER_TASK_PING_ROLE_ID = 1523674698574200904

COMMUNITY_PANEL_PERMISSION_ROLE_ID = 1544679876206796930

GERMANY_TZ = ZoneInfo("Europe/Berlin")

# =========================================================
# BOT
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

startup_sync_done = False

# =========================================================
# DATEN
# =========================================================

DEFAULT_DATA = {
    "nametags": {},
    "license_plates": {},
    "tasks": {},
    "active_shifts": {},
    "applications": {},
    "panel_messages": {},
    "next_task_id": 1,
    "next_application_id": 1,

    "emoji_quiz": {
        "points": {},
        "current": {},
        "user_stats": {}
    }
}


def deep_merge(defaults, current):
    if not isinstance(current, dict):
        current = {}

    result = {}

    for key, default_value in defaults.items():

        if key not in current:
            if isinstance(default_value, dict):
                result[key] = deep_merge(
                    default_value,
                    {}
                )
            else:
                result[key] = default_value

        else:
            current_value = current[key]

            if isinstance(default_value, dict):

                if isinstance(current_value, dict):
                    result[key] = deep_merge(
                        default_value,
                        current_value
                    )
                else:
                    result[key] = deep_merge(
                        default_value,
                        {}
                    )

            else:
                result[key] = current_value

    for key, value in current.items():

        if key not in result:
            result[key] = value

    return result


def load_data():

    if not os.path.exists(DATA_FILE):
        return deep_merge(
            DEFAULT_DATA,
            {}
        )

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

        return deep_merge(
            DEFAULT_DATA,
            loaded
        )

    except Exception as e:

        print(
            f"[DATA] Fehler beim Laden: {e}"
        )

        return deep_merge(
            DEFAULT_DATA,
            {}
        )


def save_data():

    try:

        directory = os.path.dirname(
            os.path.abspath(DATA_FILE)
        )

        fd, temp_path = tempfile.mkstemp(
            prefix="bot_data_",
            suffix=".tmp",
            dir=directory
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temp_path,
            DATA_FILE
        )

    except Exception as e:

        print(
            f"[DATA] Fehler beim Speichern: {e}"
        )


data = load_data()


def normalize_data():

    global data

    if not isinstance(
        data.get("nametags"),
        dict
    ):
        data["nametags"] = {}

    if not isinstance(
        data.get("license_plates"),
        dict
    ):
        data["license_plates"] = {}

    if not isinstance(
        data.get("tasks"),
        dict
    ):
        data["tasks"] = {}

    if not isinstance(
        data.get("active_shifts"),
        dict
    ):
        data["active_shifts"] = {}

    if not isinstance(
        data.get("applications"),
        dict
    ):
        data["applications"] = {}

    if not isinstance(
        data.get("panel_messages"),
        dict
    ):
        data["panel_messages"] = {}

    if not isinstance(
        data.get("next_task_id"),
        int
    ):
        data["next_task_id"] = 1

    if not isinstance(
        data.get("next_application_id"),
        int
    ):
        data["next_application_id"] = 1

    if not isinstance(
        data.get("emoji_quiz"),
        dict
    ):
        data["emoji_quiz"] = {}

    if not isinstance(
        data["emoji_quiz"].get("points"),
        dict
    ):
        data["emoji_quiz"]["points"] = {}

    if not isinstance(
        data["emoji_quiz"].get("current"),
        dict
    ):
        data["emoji_quiz"]["current"] = {}

    if not isinstance(
        data["emoji_quiz"].get("user_stats"),
        dict
    ):
        data["emoji_quiz"]["user_stats"] = {}

    # Altes Nummernspiel entfernen
    data.pop(
        "number_game",
        None
    )

    data.pop(
        "number_games",
        None
    )

    save_data()


normalize_data()

# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def now_local():
    return datetime.now(
        GERMANY_TZ
    )


def console_log(message):

    print(
        f"[LOG {now_local().strftime('%d.%m.%Y %H:%M:%S')}] "
        f"{message}"
    )


def user_text(user):

    return (
        f"{user.mention} ♡ "
        f"Name: {user.name}. "
        f"ID: `{user.id}`"
    )


def has_role(member, role_id):

    return any(
        role.id == role_id
        for role in member.roles
    )


def is_admin(member):

    return (
        member.guild_permissions.administrator
    )


def has_shift_permission(member):

    return (
        is_admin(member)
        or has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        )
    )


async def get_guild():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild:
        return guild

    try:

        return await bot.fetch_guild(
            GUILD_ID
        )

    except Exception as e:

        console_log(
            f"GUILD konnte nicht geladen werden: {e}"
        )

        return None


async def get_or_fetch_channel(channel_id):

    channel = bot.get_channel(
        channel_id
    )

    if channel:
        return channel

    try:

        return await bot.fetch_channel(
            channel_id
        )

    except Exception as e:

        console_log(
            f"Kanal {channel_id} konnte nicht geladen werden: {e}"
        )

        return None


async def safe_dm(user, message):

    try:

        await user.send(
            message
        )

        return True

    except Exception as e:

        console_log(
            f"DM an {user.id} fehlgeschlagen: {e}"
        )

        return False


# =========================================================
# TOKEN
# =========================================================

def load_env_file():

    token = os.getenv(
        "DISCORD_TOKEN"
    )

    if token:
        return token.strip()

    if not os.path.exists(".env"):
        return None

    try:

        with open(
            ".env",
            "r",
            encoding="utf-8"
        ) as f:

            for line in f:

                line = line.strip()

                if (
                    not line
                    or line.startswith("#")
                    or "=" not in line
                ):
                    continue

                key, value = line.split(
                    "=",
                    1
                )

                key = key.strip()
                value = value.strip()

                value = value.strip(
                    '"'
                ).strip(
                    "'"
                )

                if key == "DISCORD_TOKEN":
                    return value

    except Exception as e:

        console_log(
            f".env Fehler: {e}"
        )

    return None


TOKEN = load_env_file()

if not TOKEN:

    print(
        "FEHLER: DISCORD_TOKEN fehlt."
    )

    raise SystemExit


# =========================================================
# PANEL-HILFEN
# =========================================================

async def delete_old_panel_messages(
    channel,
    title
):

    if channel is None:
        return

    try:

        async for message in channel.history(
            limit=150
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

        console_log(
            f"Panel-Löschung fehlgeschlagen: {e}"
        )


async def save_panel_message(
    key,
    message
):

    data["panel_messages"][key] = message.id

    save_data()


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(
    discord.ui.Modal,
    title="Nametag ändern"
):

    nametag = discord.ui.TextInput(
        label="Neuer Nametag",
        placeholder="Dein gewünschter Nametag",
        max_length=32,
        required=True
    )

    async def on_submit(
        self,
        interaction
    ):

        if not has_role(
            interaction.user,
            NAMETAG_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        new_name = str(
            self.nametag.value
        ).strip()

        if not new_name:

            await interaction.response.send_message(
                "❌ Der Nametag darf nicht leer sein.",
                ephemeral=True
            )

            return

        try:

            await interaction.user.edit(
                nick=new_name
            )

            data["nametags"][
                str(interaction.user.id)
            ] = new_name

            save_data()

            console_log(
                f"Nametag geändert: {interaction.user} -> {new_name}"
            )

            await interaction.response.send_message(
                "✅ Nametag geändert.",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Fehler: `{e}`",
                ephemeral=True
            )


class NametagView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Nametag ändern",
        style=discord.ButtonStyle.primary,
        emoji="🏷️",
        custom_id="nametag_change"
    )
    async def change(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            NametagModal()
        )


async def refresh_nametag_panel():

    channel = await get_or_fetch_channel(
        NAMETAG_CHANNEL_ID
    )

    if not channel:
        return

    title = "🏷️ Nametag-System"

    await delete_old_panel_messages(
        channel,
        title
    )

    embed = discord.Embed(
        title=title,
        description=(
            "Hier kannst du deinen Nametag ändern.\n\n"
            "Klicke auf **Nametag ändern**."
        ),
        color=discord.Color.blue()
    )

    message = await channel.send(
        embed=embed,
        view=NametagView()
    )

    await save_panel_message(
        "nametag",
        message
    )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(
    discord.ui.Modal,
    title="Kennzeichen setzen"
):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z.B. GM-RP 123",
        max_length=20
    )

    async def on_submit(
        self,
        interaction
    ):

        plate = str(
            self.plate.value
        ).strip()

        if not plate:

            await interaction.response.send_message(
                "❌ Kennzeichen darf nicht leer sein.",
                ephemeral=True
            )

            return

        data["license_plates"][
            str(interaction.user.id)
        ] = plate

        save_data()

        console_log(
            f"Kennzeichen gesetzt: {interaction.user} -> {plate}"
        )

        await interaction.response.send_message(
            f"✅ Kennzeichen **{plate}** gespeichert.",
            ephemeral=True
        )

        # WICHTIG:
        # NICHT löschen.
        # Vorhandene Nachricht wird bearbeitet.
        await update_license_panel()


class LicensePlateView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Kennzeichen setzen",
        style=discord.ButtonStyle.success,
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

    @discord.ui.button(
        label="Mein Kennzeichen",
        style=discord.ButtonStyle.primary,
        emoji="🔎",
        custom_id="plate_show"
    )
    async def show_plate(
        self,
        interaction,
        button
    ):

        plate = data["license_plates"].get(
            str(interaction.user.id)
        )

        if not plate:

            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"🚗 Dein Kennzeichen: **{plate}**",
            ephemeral=True
        )

    @discord.ui.button(
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

        user_id = str(
            interaction.user.id
        )

        if user_id not in data["license_plates"]:

            await interaction.response.send_message(
                "❌ Kein Kennzeichen vorhanden.",
                ephemeral=True
            )

            return

        old = data["license_plates"].pop(
            user_id
        )

        save_data()

        console_log(
            f"Kennzeichen entfernt: {interaction.user} -> {old}"
        )

        await interaction.response.send_message(
            "✅ Kennzeichen entfernt.",
            ephemeral=True
        )

        await update_license_panel()


async def build_license_embed():

    channel = await get_or_fetch_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if not channel:
        return None

    lines = []

    for user_id, plate in data[
        "license_plates"
    ].items():

        member = None

        try:
            member = channel.guild.get_member(
                int(user_id)
            )
        except Exception:
            pass

        mention = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        lines.append(
            f"• {mention} — **{plate}**"
        )

    if not lines:
        text = "Noch keine Kennzeichen eingetragen."
    else:
        text = "\n".join(lines)

    return discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen verwalten.\n\n"
            "**Aktuelle Kennzeichen:**\n"
            f"{text}"
        ),
        color=discord.Color.green()
    )


async def update_license_panel():

    channel = await get_or_fetch_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if not channel:
        return

    message_id = data[
        "panel_messages"
    ].get(
        "license_plates"
    )

    embed = await build_license_embed()

    if not embed:
        return

    if message_id:

        try:

            message = await channel.fetch_message(
                int(message_id)
            )

            await message.edit(
                embed=embed,
                view=LicensePlateView()
            )

            return

        except Exception:
            pass

    # Nur wenn die gespeicherte Nachricht nicht mehr existiert:
    # neue Nachricht senden.
    message = await channel.send(
        embed=embed,
        view=LicensePlateView()
    )

    await save_panel_message(
        "license_plates",
        message
    )


# =========================================================
# DEV AUFGABEN
# =========================================================

def task_status(task):

    if task.get("completed"):
        return "🟢 Erledigt"

    if task.get("taken_by"):
        return "🟡 In Bearbeitung"

    return "⚪ Offen"


class DeveloperTaskView(
    discord.ui.View
):

    def __init__(
        self,
        task_id
    ):

        super().__init__(
            timeout=None
        )

        self.task_id = str(
            task_id
        )

        take = discord.ui.Button(
            label="Übernehmen",
            style=discord.ButtonStyle.primary,
            emoji="🙋",
            custom_id=f"task_take_{self.task_id}"
        )

        done = discord.ui.Button(
            label="Erledigt",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"task_done_{self.task_id}"
        )

        delete = discord.ui.Button(
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


    async def take_task(
        self,
        interaction
    ):

        task = data["tasks"].get(
            self.task_id
        )

        if not task:

            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )

            return

        if not has_shift_permission(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        if task.get("completed"):

            await interaction.response.send_message(
                "❌ Aufgabe bereits erledigt.",
                ephemeral=True
            )

            return

        if task.get("taken_by"):

            await interaction.response.send_message(
                "❌ Aufgabe bereits übernommen.",
                ephemeral=True
            )

            return

        task["taken_by"] = interaction.user.id

        save_data()

        await interaction.response.send_message(
            "✅ Aufgabe übernommen.",
            ephemeral=True
        )

        console_log(
            f"Aufgabe #{self.task_id} übernommen von {interaction.user}"
        )

        await refresh_task_panel()


    async def done_task(
        self,
        interaction
    ):

        task = data["tasks"].get(
            self.task_id
        )

        if not task:

            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )

            return

        if task.get("completed"):

            await interaction.response.send_message(
                "❌ Bereits erledigt.",
                ephemeral=True
            )

            return

        taken_by = task.get(
            "taken_by"
        )

        if not is_admin(
            interaction.user
        ):

            if not taken_by:

                await interaction.response.send_message(
                    "❌ Aufgabe wurde noch nicht übernommen.",
                    ephemeral=True
                )

                return

            if int(taken_by) != interaction.user.id:

                await interaction.response.send_message(
                    "❌ Nur der übernehmende Developer kann die Aufgabe erledigen.",
                    ephemeral=True
                )

                return

        task["completed"] = True
        task["completed_by"] = interaction.user.id

        save_data()

        creator_id = task.get(
            "creator_id"
        )

        if creator_id:

            try:

                creator = await bot.fetch_user(
                    int(creator_id)
                )

                await safe_dm(
                    creator,
                    (
                        f"✅ Deine Entwickleraufgabe "
                        f"**#{self.task_id}** wurde von "
                        f"{interaction.user.mention} erledigt."
                    )
                )

            except Exception:
                pass

        await interaction.response.send_message(
            "✅ Aufgabe erledigt.",
            ephemeral=True
        )

        console_log(
            f"Aufgabe #{self.task_id} erledigt von {interaction.user}"
        )

        await refresh_task_panel()


    async def delete_task(
        self,
        interaction
    ):

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

        await interaction.followup.send(
            "🗑️ Aufgabe gelöscht.",
            ephemeral=True
        )

        console_log(
            f"Aufgabe #{self.task_id} gelöscht von {interaction.user}"
        )

        await refresh_task_panel()


async def refresh_task_panel():

    channel = await get_or_fetch_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if not channel:
        return

    title = "🛠️ Entwickleraufgabe"

    # Altes Aufgaben-Panel entfernen.
    await delete_old_panel_messages(
        channel,
        title
    )

    if not data["tasks"]:

        embed = discord.Embed(
            title=title,
            description="Aktuell gibt es keine Entwickleraufgaben.",
            color=discord.Color.blurple()
        )

        message = await channel.send(
            embed=embed
        )

        await save_panel_message(
            "developer_tasks",
            message
        )

        return

    for task_id, task in data[
        "tasks"
    ].items():

        creator_id = task.get(
            "creator_id"
        )

        taken_by = task.get(
            "taken_by"
        )

        completed_by = task.get(
            "completed_by"
        )

        embed = discord.Embed(
            title=title,
            color=(
                discord.Color.green()
                if task.get("completed")
                else discord.Color.orange()
                if task.get("taken_by")
                else discord.Color.blurple()
            )
        )

        embed.add_field(
            name="📋 Aufgabe",
            value=task.get(
                "text",
                "Keine Beschreibung"
            ),
            inline=False
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=(
                f"<@{creator_id}> ♡ "
                f"Name: {task.get('creator_name', 'Unbekannt')}. "
                f"ID: `{creator_id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Status",
            value=task_status(task),
            inline=True
        )

        embed.add_field(
            name="🙋 Übernommen von",
            value=(
                f"<@{taken_by}>"
                if taken_by
                else "Niemand"
            ),
            inline=True
        )

        embed.add_field(
            name="✅ Erledigt von",
            value=(
                f"<@{completed_by}>"
                if completed_by
                else "Niemand"
            ),
            inline=True
        )

        embed.add_field(
            name="Aufgaben-ID",
            value=f"`{task_id}`",
            inline=False
        )

        await channel.send(
            content=f"<@&{DEVELOPER_TASK_PING_ROLE_ID}>",
            embed=embed,
            view=DeveloperTaskView(
                task_id
            )
        )

    console_log(
        f"Dev-Aufgaben automatisch aktualisiert: "
        f"{len(data['tasks'])} Aufgabe(n)"
    )


@bot.command(
    name="task"
)
@commands.guild_only()
async def create_task(
    ctx,
    *,
    task_text: str
):

    if not has_shift_permission(
        ctx.author
    ):

        await ctx.send(
            "❌ Keine Berechtigung."
        )

        return

    task_id = str(
        data["next_task_id"]
    )

    data["next_task_id"] += 1

    data["tasks"][task_id] = {
        "text": task_text,
        "creator_id": ctx.author.id,
        "creator_name": ctx.author.name,
        "taken_by": None,
        "completed": False,
        "completed_by": None,
        "created_at": now_local().isoformat()
    }

    save_data()

    await ctx.send(
        f"✅ Entwickleraufgabe **#{task_id}** erstellt."
    )

    await refresh_task_panel()


# =========================================================
# DEV SCHICHT
# =========================================================

class DeveloperShiftView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="developer_shift_start"
    )
    async def start(
        self,
        interaction,
        button
    ):

        if not has_shift_permission(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        user_id = str(
            interaction.user.id
        )

        if user_id in data[
            "active_shifts"
        ]:

            await interaction.response.send_message(
                "❌ Du bist bereits im Dienst.",
                ephemeral=True
            )

            return

        start = now_local()

        data[
            "active_shifts"
        ][user_id] = {
            "started_at": start.isoformat()
        }

        save_data()

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            try:
                await interaction.user.add_roles(
                    role
                )
            except Exception:
                pass

        await send_shift_log(
            interaction,
            True,
            start
        )

        await interaction.response.send_message(
            "🟢 Schicht gestartet.",
            ephemeral=True
        )

        await refresh_shift_panel()


    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="developer_shift_stop"
    )
    async def stop(
        self,
        interaction,
        button
    ):

        user_id = str(
            interaction.user.id
        )

        if user_id not in data[
            "active_shifts"
        ]:

            await interaction.response.send_message(
                "❌ Du hast keine aktive Schicht.",
                ephemeral=True
            )

            return

        end = now_local()

        data[
            "active_shifts"
        ].pop(
            user_id,
            None
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
            except Exception:
                pass

        await send_shift_log(
            interaction,
            False,
            end
        )

        await interaction.response.send_message(
            "🔴 Schicht beendet.",
            ephemeral=True
        )

        await refresh_shift_panel()


async def send_shift_log(
    interaction,
    started,
    time_value
):

    channel = await get_or_fetch_channel(
        SHIFT_LOG_CHANNEL_ID
    )

    if not channel:
        return

    if started:

        content = (
            "[**🟢**](https://discord.com/assets/2d6d478121939bde.svg) "
            "**Developer-Schicht gestartet**"
        )

        description = (
            f"{interaction.user.mention} ♡ "
            "hat seine Schicht gestartet."
        )

        color = discord.Color.green()

    else:

        content = (
            "[**🔴**](https://discord.com/assets/2d6d478121939bde.svg) "
            "**Developer-Schicht beendet**"
        )

        description = (
            f"{interaction.user.mention} ♡ "
            "hat seine Schicht beendet."
        )

        color = discord.Color.red()

    embed = discord.Embed(
        description=description,
        color=color
    )

    embed.add_field(
        name="Developer",
        value=(
            f"{interaction.user.name}. "
            f"`{interaction.user.id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="",
        value=(
            f"**heute um "
            f"{time_value.strftime('%H:%M')} Uhr**"
        ),
        inline=False
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    await channel.send(
        content=content,
        embed=embed
    )


async def refresh_shift_panel():

    channel = await get_or_fetch_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if not channel:
        return

    title = "🟢 Developer-Schicht"

    await delete_old_panel_messages(
        channel,
        title
    )

    active = []

    for user_id, shift in data[
        "active_shifts"
    ].items():

        active.append(
            f"🟢 <@{user_id}> — seit "
            f"`{shift.get('started_at')}`"
        )

    if not active:

        text = (
            "Aktuell ist niemand im Developer-Dienst."
        )

    else:

        text = "\n".join(
            active
        )

    embed = discord.Embed(
        title=title,
        description=(
            "Starte oder beende deine Developer-Schicht.\n\n"
            "**Aktive Schichten:**\n"
            f"{text}"
        ),
        color=discord.Color.green()
    )

    message = await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )

    await save_panel_message(
        "developer_shift",
        message
    )


async def sync_shift_roles():

    guild = await get_guild()

    if not guild:
        return

    role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if not role:
        return

    active_ids = {
        int(x)
        for x in data[
            "active_shifts"
        ].keys()
    }

    for member in guild.members:

        should_have = (
            member.id in active_ids
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

        except Exception:
            pass


# =========================================================
# DEVELOPER BEWERBUNG
# =========================================================

class DeveloperApplicationModal(
    discord.ui.Modal,
    title="Developer-Bewerbung"
):

    name = discord.ui.TextInput(
        label="Name",
        max_length=100
    )

    age = discord.ui.TextInput(
        label="Alter",
        max_length=3
    )

    experience = discord.ui.TextInput(
        label="Erfahrung",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    motivation = discord.ui.TextInput(
        label="Motivation",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    additional = discord.ui.TextInput(
        label="Weitere Informationen",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction
    ):

        for application in data[
            "applications"
        ].values():

            if (
                application.get("user_id")
                == interaction.user.id
                and application.get("status")
                == "open"
            ):

                await interaction.response.send_message(
                    "❌ Du hast bereits eine offene Bewerbung.",
                    ephemeral=True
                )

                return

        application_id = str(
            data["next_application_id"]
        )

        data["next_application_id"] += 1

        data[
            "applications"
        ][application_id] = {

            "user_id": interaction.user.id,
            "username": interaction.user.name,
            "name": str(self.name.value),
            "age": str(self.age.value),
            "experience": str(self.experience.value),
            "motivation": str(self.motivation.value),
            "additional": str(self.additional.value),
            "status": "open",
            "created_at": now_local().isoformat()
        }

        save_data()

        channel = await get_or_fetch_channel(
            DEV_APPLICATION_RESULT_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="🧑‍💻 Neue Developer-Bewerbung",
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="👤 Name",
                value=str(self.name.value),
                inline=False
            )

            embed.add_field(
                name="🎂 Alter",
                value=str(self.age.value),
                inline=True
            )

            embed.add_field(
                name="🛠️ Erfahrung",
                value=str(self.experience.value),
                inline=False
            )

            embed.add_field(
                name="💭 Motivation",
                value=str(self.motivation.value),
                inline=False
            )

            embed.add_field(
                name="➕ Weitere Informationen",
                value=(
                    str(self.additional.value)
                    or "Keine Angaben"
                ),
                inline=False
            )

            embed.add_field(
                name="👤 Bewerber",
                value=user_text(
                    interaction.user
                ),
                inline=False
            )

            embed.add_field(
                name="Bewerbungs-ID",
                value=f"`{application_id}`",
                inline=False
            )

            await channel.send(
                embed=embed,
                view=ApplicationDecisionView(
                    application_id
                )
            )

        await interaction.response.send_message(
            "✅ Bewerbung abgeschickt.",
            ephemeral=True
        )


class ApplicationDecisionView(
    discord.ui.View
):

    def __init__(
        self,
        application_id
    ):

        super().__init__(
            timeout=None
        )

        self.application_id = str(
            application_id
        )

        accept = discord.ui.Button(
            label="Annehmen",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=(
                f"application_accept_"
                f"{self.application_id}"
            )
        )

        reject = discord.ui.Button(
            label="Ablehnen",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id=(
                f"application_reject_"
                f"{self.application_id}"
            )
        )

        accept.callback = self.accept
        reject.callback = self.reject

        self.add_item(accept)
        self.add_item(reject)


    async def accept(
        self,
        interaction
    ):

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Administratoren.",
                ephemeral=True
            )

            return

        application = data[
            "applications"
        ].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )

            return

        if application.get("status") != "open":

            await interaction.response.send_message(
                "❌ Bereits bearbeitet.",
                ephemeral=True
            )

            return

        application["status"] = "accepted"
        application["decided_by"] = interaction.user.id

        save_data()

        member = interaction.guild.get_member(
            int(application["user_id"])
        )

        if member:

            role = interaction.guild.get_role(
                DEVELOPER_APPLICATION_ROLE_ID
            )

            if role:

                try:
                    await member.add_roles(
                        role
                    )
                except Exception:
                    pass

            await safe_dm(
                member,
                "🎉 Deine Developer-Bewerbung wurde angenommen!"
            )

        await interaction.response.send_message(
            "✅ Bewerbung angenommen.",
            ephemeral=True
        )


    async def reject(
        self,
        interaction
    ):

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Administratoren.",
                ephemeral=True
            )

            return

        application = data[
            "applications"
        ].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )

            return

        if application.get("status") != "open":

            await interaction.response.send_message(
                "❌ Bereits bearbeitet.",
                ephemeral=True
            )

            return

        application["status"] = "rejected"
        application["decided_by"] = interaction.user.id

        save_data()

        try:

            user = await bot.fetch_user(
                int(application["user_id"])
            )

            await safe_dm(
                user,
                "❌ Deine Developer-Bewerbung wurde leider abgelehnt."
            )

        except Exception:
            pass

        await interaction.response.send_message(
            "❌ Bewerbung abgelehnt.",
            ephemeral=True
        )


class DeveloperApplicationView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Developer-Bewerbung",
        style=discord.ButtonStyle.primary,
        emoji="🧑‍💻",
        custom_id="developer_application_open"
    )
    async def open_application(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            DeveloperApplicationModal()
        )


async def refresh_application_panel():

    channel = await get_or_fetch_channel(
        DEV_APPLICATION_CHANNEL_ID
    )

    if not channel:
        return

    title = "🧑‍💻 Developer-Bewerbung"

    await delete_old_panel_messages(
        channel,
        title
    )

    embed = discord.Embed(
        title=title,
        description=(
            "Du möchtest Developer werden?\n\n"
            "Klicke auf den Button und bewirb dich."
        ),
        color=discord.Color.blurple()
    )

    message = await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )

    await save_panel_message(
        "developer_application",
        message
    )


# =========================================================
# COMMUNITY
# =========================================================

class SuggestionModal(
    discord.ui.Modal,
    title="Community-Vorschlag"
):

    text = discord.ui.TextInput(
        label="Dein Vorschlag",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):

        channel = await get_or_fetch_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="💡 Neuer Community-Vorschlag",
                description=str(
                    self.text.value
                ),
                color=discord.Color.gold()
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
            "✅ Vorschlag gesendet.",
            ephemeral=True
        )


class FeedbackModal(
    discord.ui.Modal,
    title="Community-Feedback"
):

    text = discord.ui.TextInput(
        label="Dein Feedback",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):

        channel = await get_or_fetch_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="💬 Neues Community-Feedback",
                description=str(
                    self.text.value
                ),
                color=discord.Color.blue()
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
            "✅ Feedback gesendet.",
            ephemeral=True
        )


class CommunityPanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Vorschlag senden",
        style=discord.ButtonStyle.success,
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

    @discord.ui.button(
        label="Feedback senden",
        style=discord.ButtonStyle.primary,
        emoji="💬",
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


@bot.command(
    name="communitypanel"
)
@commands.guild_only()
async def communitypanel(
    ctx
):

    if (
        not is_admin(ctx.author)
        and not has_role(
            ctx.author,
            COMMUNITY_PANEL_PERMISSION_ROLE_ID
        )
    ):

        await ctx.send(
            "❌ Keine Berechtigung."
        )

        return

    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "Hier kannst du einen Community-Vorschlag "
            "oder Feedback senden."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=CommunityPanelView()
    )


@bot.command(
    name="community"
)
async def community(
    ctx
):

    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "Willkommen im Community-Bereich."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# EMOJI QUIZ
# =========================================================

# Sehr großer Fragenpool.
# Jede Frage besteht aus:
# (Emoji, Antwort, Tipp, Anfangsbuchstaben, Kategorie)

EMOJI_QUIZ = [

    ("⚽🥅", "Fußball", "Dort wird ein Ball ins Tor geschossen.", "F", "Sport"),
    ("🏀🧺", "Basketball", "Der Ball muss durch einen Korb.", "B", "Sport"),
    ("🎾", "Tennis", "Man spielt es mit Schläger und Netz.", "T", "Sport"),
    ("🏎️🏁", "Formel 1", "Motorsport mit schnellen Rennwagen.", "F", "Sport"),
    ("🏊‍♂️🌊", "Schwimmen", "Sport im Wasser.", "S", "Sport"),
    ("🚴‍♂️", "Radfahren", "Man benutzt dafür ein Fahrrad.", "R", "Sport"),
    ("🏇", "Reiten", "Sport mit einem Pferd.", "R", "Sport"),
    ("🥊", "Boxen", "Kampfsport mit Handschuhen.", "B", "Sport"),
    ("🏐", "Volleyball", "Ballspiel über ein Netz.", "V", "Sport"),
    ("🏓", "Tischtennis", "Tennis auf einem Tisch.", "T", "Sport"),

    ("🇩🇪🍺🥨", "Deutschland", "Ein Land in Europa.", "D", "Länder"),
    ("🇫🇷🥐🗼", "Frankreich", "Dort steht ein sehr berühmter Turm.", "F", "Länder"),
    ("🇮🇹🍕🍝", "Italien", "Bekannt für Pizza und Pasta.", "I", "Länder"),
    ("🇯🇵🍣🗻", "Japan", "Inselstaat in Asien.", "J", "Länder"),
    ("🇺🇸🗽🍔", "USA", "Dort steht die Freiheitsstatue.", "U", "Länder"),
    ("🇬🇧👑☕", "England", "Teil des Vereinigten Königreichs.", "E", "Länder"),
    ("🇪🇸💃🥘", "Spanien", "Bekannt für Flamenco und Paella.", "S", "Länder"),
    ("🇧🇷⚽🌴", "Brasilien", "Großes Land in Südamerika.", "B", "Länder"),
    ("🇨🇦🍁", "Kanada", "Das Ahornblatt ist ein bekanntes Symbol.", "K", "Länder"),
    ("🇦🇺🦘", "Australien", "Dort leben Kängurus.", "A", "Länder"),
    ("🇬🇷🏛️", "Griechenland", "Bekannt für antike Tempel.", "G", "Länder"),
    ("🇳🇱🌷🚲", "Niederlande", "Bekannt für Tulpen und Fahrräder.", "N", "Länder"),
    ("🇨🇭🏔️🧀", "Schweiz", "Bekannt für Berge und Käse.", "S", "Länder"),
    ("🇳🇴❄️🏔️", "Norwegen", "Skandinavisches Land mit vielen Fjorden.", "N", "Länder"),
    ("🇮🇸🌋❄️", "Island", "Insel mit Vulkanen und Gletschern.", "I", "Länder"),

    ("🍕", "Pizza", "Rundes Gericht mit Belag.", "P", "Essen"),
    ("🍔🍟", "Burger", "Typisches Fast Food mit Brötchen.", "B", "Essen"),
    ("🌭", "Hotdog", "Wurst im länglichen Brötchen.", "H", "Essen"),
    ("🍣", "Sushi", "Japanisches Gericht mit Reis.", "S", "Essen"),
    ("🌮", "Taco", "Mexikanisches Gericht mit gefüllter Schale.", "T", "Essen"),
    ("🍝🍅", "Spaghetti", "Lange italienische Nudeln.", "S", "Essen"),
    ("🥨", "Brezel", "Beliebtes deutsches Gebäck.", "B", "Essen"),
    ("🍦", "Eis", "Kalt und süß.", "E", "Essen"),
    ("🍫", "Schokolade", "Süße Nascherei aus Kakao.", "S", "Essen"),
    ("🍿🎬", "Popcorn", "Typischer Snack im Kino.", "P", "Essen"),
    ("🍎👩‍⚕️", "Apfel", "Eine bekannte Frucht.", "A", "Essen"),
    ("🍌", "Banane", "Gelbe Frucht.", "B", "Essen"),
    ("🍉☀️", "Wassermelone", "Große Sommerfrucht mit viel Wasser.", "W", "Essen"),
    ("🥞🍁", "Pfannkuchen", "Flaches Gericht, oft mit Sirup.", "P", "Essen"),
    ("🍰🎂", "Kuchen", "Gibt es oft zum Geburtstag.", "K", "Essen"),

    ("🐶", "Hund", "Treuer Begleiter des Menschen.", "H", "Tiere"),
    ("🐱", "Katze", "Sagt häufig Miau.", "K", "Tiere"),
    ("🦁", "Löwe", "Große Raubkatze.", "L", "Tiere"),
    ("🐯", "Tiger", "Gestreifte Raubkatze.", "T", "Tiere"),
    ("🐘", "Elefant", "Sehr großes Tier mit Rüssel.", "E", "Tiere"),
    ("🦒", "Giraffe", "Hat einen sehr langen Hals.", "G", "Tiere"),
    ("🐼🎋", "Panda", "Bekommt man oft mit Bambus verbunden.", "P", "Tiere"),
    ("🐨🌿", "Koala", "Lebt in Australien.", "K", "Tiere"),
    ("🦊", "Fuchs", "Rotbraunes Wildtier.", "F", "Tiere"),
    ("🐺🌕", "Wolf", "Lebt oft in Rudeln.", "W", "Tiere"),
    ("🐸", "Frosch", "Kann weit springen.", "F", "Tiere"),
    ("🐍", "Schlange", "Hat keine Beine.", "S", "Tiere"),
    ("🦈🌊", "Hai", "Raubtier des Meeres.", "H", "Tiere"),
    ("🐬🌊", "Delfin", "Sehr intelligentes Meerestier.", "D", "Tiere"),
    ("🐧❄️", "Pinguin", "Vogel, der nicht fliegen kann.", "P", "Tiere"),

    ("🗼🇫🇷", "Eiffelturm", "Berühmtes Wahrzeichen in Paris.", "E", "Orte"),
    ("🗽🇺🇸", "Freiheitsstatue", "Berühmtes Wahrzeichen in New York.", "F", "Orte"),
    ("🏰👑", "Schloss", "Dort können Könige und Königinnen leben.", "S", "Orte"),
    ("🏝️🌊", "Insel", "Land, das von Wasser umgeben ist.", "I", "Orte"),
    ("🏖️☀️", "Strand", "Sand, Meer und Sonne.", "S", "Orte"),
    ("🏔️❄️", "Berg", "Hohe Landschaftsform.", "B", "Orte"),
    ("🌋🔥", "Vulkan", "Kann Lava ausstoßen.", "V", "Orte"),
    ("🏫📚", "Schule", "Dort lernen Schüler.", "S", "Orte"),
    ("🏥🚑", "Krankenhaus", "Dort arbeiten viele Ärzte.", "K", "Orte"),
    ("✈️🌍", "Flughafen", "Dort starten und landen Flugzeuge.", "F", "Orte"),

    ("🎬🦸", "Superheldenfilm", "Film mit außergewöhnlichen Helden.", "S", "Filme"),
    ("🦖🌴", "Jurassic Park", "Dinosaurier sind hier das Thema.", "J", "Filme"),
    ("🧙‍♂️💍", "Der Herr der Ringe", "Fantasy mit einem besonderen Ring.", "D", "Filme"),
    ("🧊👸", "Die Eiskönigin", "Animationsfilm mit Eis und einer Königin.", "D", "Filme"),
    ("🤖🚗", "Transformers", "Roboter können zu Fahrzeugen werden.", "T", "Filme"),
    ("🦁👑", "Der König der Löwen", "Ein Löwe steht im Mittelpunkt.", "D", "Filme"),
    ("🐠🔎", "Findet Nemo", "Ein kleiner Fisch wird gesucht.", "F", "Filme"),
    ("👽🚲🌕", "E.T.", "Ein Außerirdischer und ein Fahrrad.", "E", "Filme"),
    ("🏴‍☠️🚢", "Piratenfilm", "Abenteuer auf hoher See.", "P", "Filme"),
    ("🧙‍♂️⚡", "Harry Potter", "Zauberei und ein junger Zauberer.", "H", "Filme"),

    ("👨‍⚕️🏥", "Arzt", "Arbeitet häufig im Krankenhaus.", "A", "Berufe"),
    ("👨‍🚒🔥", "Feuerwehrmann", "Hilft bei Bränden und Notfällen.", "F", "Berufe"),
    ("👮‍♂️🚓", "Polizist", "Arbeitet für die Polizei.", "P", "Berufe"),
    ("👨‍🍳🍳", "Koch", "Bereitet Essen zu.", "K", "Berufe"),
    ("👨‍🏫📚", "Lehrer", "Unterrichtet Schüler.", "L", "Berufe"),
    ("👨‍🔧🔩", "Mechaniker", "Arbeitet an Fahrzeugen und Maschinen.", "M", "Berufe"),
    ("👨‍💻💻", "Programmierer", "Schreibt Software und Code.", "P", "Berufe"),
    ("👨‍✈️✈️", "Pilot", "Fliegt Flugzeuge.", "P", "Berufe"),
    ("👨‍🚀🚀", "Astronaut", "Reist ins Weltall.", "A", "Berufe"),
    ("📸👨‍🎨", "Fotograf", "Macht Fotos.", "F", "Berufe"),

    ("🌧️☂️", "Regenschirm", "Hilft bei schlechtem Wetter.", "R", "Alltag"),
    ("📱💬", "Handy", "Damit kann man telefonieren.", "H", "Alltag"),
    ("💻⌨️", "Computer", "Elektronisches Gerät zum Arbeiten und Spielen.", "C", "Alltag"),
    ("🚗⛽", "Auto", "Fährt auf Straßen.", "A", "Alltag"),
    ("🚲🔔", "Fahrrad", "Hat zwei Räder und Pedale.", "F", "Alltag"),
    ("⌚⏰", "Uhr", "Zeigt die Zeit.", "U", "Alltag"),
    ("🔑🚪", "Schlüssel", "Öffnet zum Beispiel eine Tür.", "S", "Alltag"),
    ("🎒📚", "Rucksack", "Darin kann man Sachen transportieren.", "R", "Alltag"),
    ("🎧🎵", "Kopfhörer", "Damit hört man Musik.", "K", "Alltag"),
    ("📺🍿", "Fernseher", "Damit kann man Filme und Serien schauen.", "F", "Alltag"),

    ("🎄🎁", "Weihnachten", "Fest mit Geschenken und Tannenbaum.", "W", "Feste"),
    ("🎃👻", "Halloween", "Fest mit Kürbissen und Verkleidungen.", "H", "Feste"),
    ("🎂🎉", "Geburtstag", "Man feiert den Tag der Geburt.", "G", "Feste"),
    ("❤️💐", "Valentinstag", "Tag rund um Liebe und Freundschaft.", "V", "Feste"),
    ("🎆🥳", "Silvester", "Feier zum Jahreswechsel.", "S", "Feste"),
    ("🐰🥚", "Ostern", "Fest mit Eiern und Osterhase.", "O", "Feste"),

    ("🌞🏖️", "Sommer", "Warme Jahreszeit.", "S", "Jahreszeiten"),
    ("🍂🌧️", "Herbst", "Blätter werden bunt und fallen.", "H", "Jahreszeiten"),
    ("❄️⛄", "Winter", "Kalte Jahreszeit.", "W", "Jahreszeiten"),
    ("🌸🌱", "Frühling", "Alles beginnt wieder zu blühen.", "F", "Jahreszeiten"),

    ("🧊🥤", "Eiswürfel", "Gefrorenes Wasser.", "E", "Gegenstände"),
    ("✏️📖", "Schulzeug", "Findet man häufig im Unterricht.", "S", "Gegenstände"),
    ("☂️🌧️", "Regenschirm", "Schützt vor Regen.", "R", "Gegenstände"),
    ("🕶️☀️", "Sonnenbrille", "Schützt die Augen vor Sonne.", "S", "Gegenstände"),
    ("🎸🎵", "Gitarre", "Musikinstrument mit Saiten.", "G", "Gegenstände"),
    ("🥁🎵", "Schlagzeug", "Musikinstrument zum Schlagen.", "S", "Gegenstände"),
    ("🎹🎵", "Klavier", "Tasteninstrument.", "K", "Gegenstände"),
    ("🎨🖌️", "Malen", "Dabei benutzt man oft Pinsel und Farben.", "M", "Hobbys"),
    ("📚🛋️", "Lesen", "Man macht es mit Büchern.", "L", "Hobbys"),
    ("🎮🕹️", "Gaming", "Spielen mit Konsole oder Computer.", "G", "Hobbys"),

    ("🌙⭐", "Nacht", "Die Sonne ist nicht am Himmel.", "N", "Sonstiges"),
    ("☀️🌡️", "Hitze", "Sehr hohe Temperatur.", "H", "Sonstiges"),
    ("🌨️❄️", "Schnee", "Weiße Niederschläge im Winter.", "S", "Sonstiges"),
    ("🌈🌧️", "Regenbogen", "Kann nach Regen erscheinen.", "R", "Sonstiges"),
    ("⚡🌩️", "Gewitter", "Blitz und Donner gehören dazu.", "G", "Sonstiges"),
    ("🔥🪵", "Feuer", "Kann sehr heiß sein.", "F", "Sonstiges"),
    ("💤🛏️", "Schlafen", "Macht man meistens nachts.", "S", "Sonstiges"),
    ("😂🤣", "Lachen", "Macht man bei etwas Lustigem.", "L", "Sonstiges"),
    ("😴🛏️", "Müde", "So fühlt man sich vor dem Schlafen.", "M", "Sonstiges"),
    ("🎉🥳", "Party", "Musik, Spaß und Feiern.", "P", "Sonstiges")
]


# =========================================================
# EMOJI QUIZ STATE
# =========================================================

quiz_cooldowns = {}
quiz_skip_cooldowns = {}
quiz_hint_cooldowns = {}
quiz_initial_cooldowns = {}

QUIZ_MESSAGE_ID = None


def normalize_answer(text):

    text = text.lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss"
    }

    for a, b in replacements.items():
        text = text.replace(
            a,
            b
        )

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789 "
    )

    text = "".join(
        char
        for char in text
        if char in allowed
    )

    return " ".join(
        text.split()
    )


def get_quiz_state():

    state = data[
        "emoji_quiz"
    ].get(
        "current"
    )

    if not isinstance(
        state,
        dict
    ):
        state = {}

    return state


def create_new_quiz():

    old_index = get_quiz_state().get(
        "index"
    )

    available = list(
        range(
            len(EMOJI_QUIZ)
        )
    )

    if old_index in available:
        available.remove(
            old_index
        )

    index = random.choice(
        available
    )

    emoji, answer, hint, initial, category = (
        EMOJI_QUIZ[index]
    )

    data[
        "emoji_quiz"
    ][
        "current"
    ] = {

        "index": index,
        "emoji": emoji,
        "answer": answer,
        "hint": hint,
        "initial": initial,
        "category": category,

        "created_at": now_local().isoformat(),

        # Die Limits gelten für jeden Nutzer
        # pro aktuellem Quiz.
        "users": {}
    }

    save_data()

    return data[
        "emoji_quiz"
    ][
        "current"
    ]


def get_user_quiz_stats(
    user_id
):

    user_id = str(
        user_id
    )

    current = get_quiz_state()

    users = current.setdefault(
        "users",
        {}
    )

    if user_id not in users:

        users[user_id] = {
            "hints": 0,
            "initials": 0,
            "skips": 0
        }

    return users[user_id]


def get_points(
    user_id
):

    return int(
        data[
            "emoji_quiz"
        ][
            "points"
        ].get(
            str(user_id),
            0
        )
    )


def add_points(
    user_id,
    amount
):

    user_id = str(
        user_id
    )

    current = get_points(
        user_id
    )

    data[
        "emoji_quiz"
    ][
        "points"
    ][user_id] = (
        current + amount
    )

    save_data()


async def send_new_quiz_panel():

    global QUIZ_MESSAGE_ID

    channel = await get_or_fetch_channel(
        EMOJI_QUIZ_CHANNEL_ID
    )

    if not channel:
        return

    # Alle alten Quiz-Panels des Bots löschen.
    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if message.embeds[0].title == "🎯 Emoji Quiz":

                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception as e:

        console_log(
            f"Emoji-Quiz alte Panels konnten nicht gelöscht werden: {e}"
        )

    current = create_new_quiz()

    embed = discord.Embed(
        title="🎯 Emoji Quiz",
        description=(
            "Errate den Begriff anhand der Emojis!\n\n"
            f"# {current['emoji']}\n\n"
            f"📚 **Kategorie:** {current['category']}\n\n"
            "💡 Du hast pro Quiz **3 Tipps**.\n"
            "🔤 Du hast pro Quiz **3 Anfangsbuchstaben-Hilfen**.\n"
            "⏭️ Du kannst ein Quiz **3-mal überspringen**.\n\n"
            "Schreibe deine Antwort einfach hier in den Kanal."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Viel Spaß beim Raten!"
    )

    message = await channel.send(
        embed=embed,
        view=EmojiQuizView()
    )

    QUIZ_MESSAGE_ID = message.id

    data[
        "panel_messages"
    ][
        "emoji_quiz"
    ] = message.id

    save_data()

    console_log(
        f"Neues Emoji-Quiz gestartet: {current['emoji']} "
        f"({current['category']})"
    )


# =========================================================
# EMOJI QUIZ VIEW
# =========================================================

class EmojiQuizView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Tipp anfordern",
        style=discord.ButtonStyle.primary,
        emoji="💡",
        custom_id="emoji_quiz_hint"
    )
    async def hint(
        self,
        interaction,
        button
    ):

        user_id = interaction.user.id

        now = time.monotonic()

        last = quiz_hint_cooldowns.get(
            user_id,
            0
        )

        if now - last < 4:

            await interaction.response.send_message(
                "⏳ Warte kurz, bevor du wieder einen Tipp anforderst.",
                ephemeral=True
            )

            return

        quiz_hint_cooldowns[user_id] = now

        stats = get_user_quiz_stats(
            user_id
        )

        if stats["hints"] >= 3:

            await interaction.response.send_message(
                "❌ Deine 3 Tipps für dieses Quiz sind bereits aufgebraucht.",
                ephemeral=True
            )

            return

        stats["hints"] += 1

        save_data()

        current = get_quiz_state()

        await interaction.response.send_message(
            (
                f"💡 **Tipp:** {current.get('hint', 'Kein Tipp verfügbar.')}\n\n"
                f"Dir bleiben **{3 - stats['hints']} Tipp(e)**."
            ),
            ephemeral=True
        )


    @discord.ui.button(
        label="Anfangsbuchstaben",
        style=discord.ButtonStyle.secondary,
        emoji="🔤",
        custom_id="emoji_quiz_initial"
    )
    async def initial(
        self,
        interaction,
        button
    ):

        user_id = interaction.user.id

        now = time.monotonic()

        last = quiz_initial_cooldowns.get(
            user_id,
            0
        )

        if now - last < 4:

            await interaction.response.send_message(
                "⏳ Warte kurz.",
                ephemeral=True
            )

            return

        quiz_initial_cooldowns[user_id] = now

        stats = get_user_quiz_stats(
            user_id
        )

        if stats["initials"] >= 3:

            await interaction.response.send_message(
                "❌ Deine 3 Anfangsbuchstaben-Hilfen sind aufgebraucht.",
                ephemeral=True
            )

            return

        stats["initials"] += 1

        save_data()

        current = get_quiz_state()

        answer = current.get(
            "answer",
            ""
        )

        initial_count = min(
            stats["initials"],
            len(answer)
        )

        shown = answer[
            :initial_count
        ]

        await interaction.response.send_message(
            (
                f"🔤 **Anfangsbuchstaben:** `{shown}`\n\n"
                f"Dir bleiben **{3 - stats['initials']} "
                "Anfangsbuchstaben-Hilfe(n)**."
            ),
            ephemeral=True
        )


    @discord.ui.button(
        label="Überspringen",
        style=discord.ButtonStyle.danger,
        emoji="⏭️",
        custom_id="emoji_quiz_skip"
    )
    async def skip(
        self,
        interaction,
        button
    ):

        user_id = interaction.user.id

        now = time.monotonic()

        last = quiz_skip_cooldowns.get(
            user_id,
            0
        )

        if now - last < 10:

            await interaction.response.send_message(
                "⏳ Bitte warte kurz vor dem nächsten Überspringen.",
                ephemeral=True
            )

            return

        quiz_skip_cooldowns[user_id] = now

        stats = get_user_quiz_stats(
            user_id
        )

        if stats["skips"] >= 3:

            await interaction.response.send_message(
                "❌ Du hast für dieses Quiz bereits 3 Überspringen benutzt.",
                ephemeral=True
            )

            return

        stats["skips"] += 1

        save_data()

        await interaction.response.send_message(
            (
                f"⏭️ Quiz übersprungen.\n"
                f"Dir bleiben **{3 - stats['skips']} Überspringen**."
            ),
            ephemeral=True
        )

        await send_new_quiz_panel()


    @discord.ui.button(
        label="Leaderboard",
        style=discord.ButtonStyle.success,
        emoji="🏆",
        custom_id="emoji_quiz_leaderboard"
    )
    async def leaderboard(
        self,
        interaction,
        button
    ):

        points = data[
            "emoji_quiz"
        ][
            "points"
        ]

        sorted_users = sorted(
            points.items(),
            key=lambda item: int(
                item[1]
            ),
            reverse=True
        )

        if not sorted_users:

            await interaction.response.send_message(
                "🏆 Noch hat niemand Punkte.",
                ephemeral=True
            )

            return

        lines = []

        for position, (
            user_id,
            score
        ) in enumerate(
            sorted_users[:10],
            start=1
        ):

            lines.append(
                f"**{position}.** <@{user_id}> — "
                f"**{score} Punkte**"
            )

        embed = discord.Embed(
            title="🏆 Emoji-Quiz Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# EMOJI QUIZ ANTWORTEN
# =========================================================

quiz_answer_cooldowns = {}


@bot.event
async def on_message(
    message
):

    if message.author.bot:
        return

    # Antworten nur im Emoji-Quiz-Kanal.
    if (
        message.channel.id
        == EMOJI_QUIZ_CHANNEL_ID
    ):

        # Nur normale Textantworten.
        answer_text = message.content.strip()

        if answer_text:

            user_id = message.author.id

            now = time.monotonic()

            last = quiz_answer_cooldowns.get(
                user_id,
                0
            )

            # Anti-Spam:
            # maximal eine Antwort alle 2 Sekunden.
            if now - last < 2:

                try:
                    await message.delete()
                except Exception:
                    pass

                return

            quiz_answer_cooldowns[
                user_id
            ] = now

            current = get_quiz_state()

            correct = normalize_answer(
                current.get(
                    "answer",
                    ""
                )
            )

            given = normalize_answer(
                answer_text
            )

            # Antwortnachricht entfernen,
            # damit der Quiz-Kanal nicht zugespammt wird.
            try:
                await message.delete()
            except Exception:
                pass

            if given == correct:

                add_points(
                    user_id,
                    10
                )

                points = get_points(
                    user_id
                )

                await message.channel.send(
                    (
                        f"🎉 {message.author.mention} "
                        f"hat **richtig** geraten!\n"
                        f"✅ Lösung: **{current.get('answer')}**\n"
                        f"🏆 +10 Punkte\n"
                        f"📊 Gesamt: **{points} Punkte**"
                    ),
                    delete_after=5
                )

                console_log(
                    f"Emoji Quiz richtig: "
                    f"{message.author} -> "
                    f"{current.get('answer')}"
                )

                await send_new_quiz_panel()

                return

    await bot.process_commands(
        message
    )


# =========================================================
# AUTOMATISCHE QUIZ-PANEL PRÜFUNG
# =========================================================

async def ensure_quiz_panel():

    channel = await get_or_fetch_channel(
        EMOJI_QUIZ_CHANNEL_ID
    )

    if not channel:
        return

    panel_id = data[
        "panel_messages"
    ].get(
        "emoji_quiz"
    )

    if panel_id:

        try:

            message = await channel.fetch_message(
                int(panel_id)
            )

            # Existiert bereits:
            # Beim Neustart soll es trotzdem neu gemacht werden.
            await message.delete()

        except Exception:
            pass

    await send_new_quiz_panel()


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global startup_sync_done

    console_log(
        f"Bot online: {bot.user} "
        f"(ID: {bot.user.id})"
    )

    if startup_sync_done:
        return

    startup_sync_done = True

    # =====================================================
    # PERSISTENTE VIEWS
    # =====================================================

    bot.add_view(
        NametagView()
    )

    bot.add_view(
        LicensePlateView()
    )

    bot.add_view(
        DeveloperShiftView()
    )

    bot.add_view(
        DeveloperApplicationView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    bot.add_view(
        EmojiQuizView()
    )

    # Alte Aufgaben-Buttons wieder aktivieren.
    for task_id in data[
        "tasks"
    ].keys():

        try:

            bot.add_view(
                DeveloperTaskView(
                    task_id
                )
            )

        except Exception as e:

            console_log(
                f"Task-View Fehler {task_id}: {e}"
            )

    # Alte Bewerbungs-Buttons wieder aktivieren.
    for application_id, application in data[
        "applications"
    ].items():

        if application.get(
            "status"
        ) != "open":
            continue

        try:

            bot.add_view(
                ApplicationDecisionView(
                    application_id
                )
            )

        except Exception as e:

            console_log(
                f"Application-View Fehler: {e}"
            )

    # =====================================================
    # SCHICHTEN SYNCHRONISIEREN
    # =====================================================

    await sync_shift_roles()

    # =====================================================
    # PANELS
    # =====================================================

    # Nametag: ALT LÖSCHEN -> NEU SENDEN
    try:
        await refresh_nametag_panel()
    except Exception as e:
        console_log(
            f"Nametag-Panel Fehler: {e}"
        )

    # Kennzeichen:
    # NICHT ALLES LÖSCHEN.
    # Bestehendes Panel wird bearbeitet.
    try:
        await update_license_panel()
    except Exception as e:
        console_log(
            f"Kennzeichen-Panel Fehler: {e}"
        )

    # Dev-Aufgaben:
    # ALT LÖSCHEN -> NEU SENDEN
    try:
        await refresh_task_panel()
    except Exception as e:
        console_log(
            f"Aufgaben-Panel Fehler: {e}"
        )

    # Developer-Schicht:
    # ALT LÖSCHEN -> NEU SENDEN
    try:
        await refresh_shift_panel()
    except Exception as e:
        console_log(
            f"Schicht-Panel Fehler: {e}"
        )

    # Developer-Bewerbung:
    # ALT LÖSCHEN -> NEU SENDEN
    try:
        await refresh_application_panel()
    except Exception as e:
        console_log(
            f"Bewerbungs-Panel Fehler: {e}"
        )

    # Emoji-Quiz:
    # ALT LÖSCHEN -> NEUES QUIZ SENDEN
    try:
        await ensure_quiz_panel()
    except Exception as e:
        console_log(
            f"Emoji-Quiz Panel Fehler: {e}"
        )

    console_log(
        "Alle Panels wurden synchronisiert."
    )


# =========================================================
# START
# =========================================================

try:

    bot.run(
        TOKEN
    )

except discord.LoginFailure:

    print(
        "FEHLER: Discord-Token ist falsch."
    )

except Exception as e:

    print(
        f"FEHLER beim Starten des Bots: {e}"
    )
