import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
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


# =========================================================
# TOKEN AUS .ENV LADEN
# =========================================================

def load_env_file():
    token = os.getenv("DISCORD_TOKEN")

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

                if key.strip() == "DISCORD_TOKEN":
                    return value.strip().strip('"').strip("'")

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
    intents=intents
)


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
    "next_application_id": 1
}


def deep_merge(default, current):
    if isinstance(default, dict) and isinstance(current, dict):
        result = {}

        for key, value in default.items():
            if key in current:
                result[key] = deep_merge(value, current[key])
            else:
                result[key] = value

        for key, value in current.items():
            if key not in result:
                result[key] = value

        return result

    return current


def load_data():
    if not os.path.exists(DATA_FILE):
        return deep_merge(DEFAULT_DATA, {})

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            current = json.load(file)

        return deep_merge(DEFAULT_DATA, current)

    except Exception as e:
        print(f"Fehler beim Laden der Daten: {e}")
        return deep_merge(DEFAULT_DATA, {})


data = load_data()


def save_data():
    try:
        directory = os.path.dirname(os.path.abspath(DATA_FILE))

        fd, temp_path = tempfile.mkstemp(
            prefix="bot_data_",
            suffix=".tmp",
            dir=directory
        )

        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_path, DATA_FILE)

    except Exception as e:
        print(f"Fehler beim Speichern: {e}")


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_user_info(user):
    return (
        f"{user.mention} ♡ Name: {user.name}. "
        f"ID: `{user.id}`"
    )


def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def has_shift_permission(member):
    return member.guild_permissions.administrator or has_role(
        member,
        SHIFT_PERMISSION_ROLE_ID
    )


async def get_or_fetch_channel(channel_id):
    channel = bot.get_channel(channel_id)

    if channel is not None:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


async def get_guild():
    guild = bot.get_guild(GUILD_ID)

    if guild is not None:
        return guild

    try:
        return await bot.fetch_guild(GUILD_ID)
    except Exception:
        return None


def now_time():
    return datetime.now().strftime("%H:%M Uhr")


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(discord.ui.Modal, title="Nametag ändern"):

    nametag = discord.ui.TextInput(
        label="Neuer Nametag",
        placeholder="z. B. RyZe",
        max_length=32,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        if not has_role(member, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, deinen Nametag zu ändern.",
                ephemeral=True
            )
            return

        try:
            await member.edit(nick=str(self.nametag))

            data["nametags"][str(member.id)] = str(self.nametag)
            save_data()

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf **{self.nametag}** geändert.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag ändern",
        style=discord.ButtonStyle.primary,
        emoji="🏷️",
        custom_id="nametag_change"
    )
    async def change(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(NametagModal())


def create_nametag_embed():
    return discord.Embed(
        title="🏷️ Nametag-System",
        description=(
            "Mit dem Button unten kannst du deinen Discord-Namen "
            "auf deinen gewünschten Nametag ändern."
        ),
        color=discord.Color.blurple()
    )


# =========================================================
# KENNZEICHEN
# =========================================================

def create_license_panel_embed():
    embed = discord.Embed(
        title="🚘 Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen verwalten.\n\n"
            "Alle aktuell gespeicherten Kennzeichen:"
        ),
        color=discord.Color.blurple()
    )

    plates = data.get("license_plates", {})

    if not plates:
        embed.add_field(
            name="Keine Kennzeichen",
            value="Aktuell sind keine Kennzeichen gespeichert.",
            inline=False
        )
    else:
        lines = []

        for user_id, plate in plates.items():
            lines.append(
                f"🚘 <@{user_id}> — **{plate}**"
            )

        embed.add_field(
            name="Aktuelle Kennzeichen",
            value="\n".join(lines),
            inline=False
        )

    return embed


class LicensePlateModal(discord.ui.Modal, title="Kennzeichen setzen"):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. GM-RZ 123",
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        plate_value = str(self.plate).strip().upper()

        data["license_plates"][str(interaction.user.id)] = plate_value
        save_data()

        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen wurde auf **{plate_value}** gesetzt.",
            ephemeral=True
        )


class LicensePlateView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen setzen",
        style=discord.ButtonStyle.success,
        emoji="🚘",
        custom_id="license_set"
    )
    async def set_plate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(LicensePlateModal())

    @discord.ui.button(
        label="Mein Kennzeichen",
        style=discord.ButtonStyle.primary,
        emoji="📋",
        custom_id="license_show"
    )
    async def show_plate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        plate = data["license_plates"].get(str(interaction.user.id))

        if not plate:
            await interaction.response.send_message(
                "❌ Du hast noch kein Kennzeichen gespeichert.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🚘 Dein Kennzeichen: **{plate}**",
            ephemeral=True
        )

    @discord.ui.button(
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="license_remove"
    )
    async def remove_plate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen gespeichert.",
                ephemeral=True
            )
            return

        old_plate = data["license_plates"].pop(user_id)
        save_data()

        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Das Kennzeichen **{old_plate}** wurde entfernt.",
            ephemeral=True
        )


async def refresh_license_panel():

    channel = await get_or_fetch_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    message_id = data["panel_messages"].get("license")

    message = None

    if message_id:
        try:
            message = await channel.fetch_message(int(message_id))
        except Exception:
            message = None

    if message is not None:
        try:
            await message.edit(
                embed=create_license_panel_embed(),
                view=LicensePlateView()
            )
            return
        except Exception:
            pass

    try:
        async for old_message in channel.history(limit=50):
            if (
                old_message.author.id == bot.user.id
                and old_message.embeds
                and old_message.embeds[0].title == "🚘 Kennzeichen-System"
            ):
                try:
                    await old_message.delete()
                except Exception:
                    pass

    except Exception:
        pass

    try:
        new_message = await channel.send(
            embed=create_license_panel_embed(),
            view=LicensePlateView()
        )

        data["panel_messages"]["license"] = new_message.id
        save_data()

    except Exception as e:
        print(f"Fehler beim License-Panel: {e}")


# =========================================================
# DEVELOPER AUFGABEN
# =========================================================

def task_user_info(user_id):

    user = bot.get_user(int(user_id))

    if user:
        return get_user_info(user)

    return f"<@{user_id}> ♡ ID: `{user_id}`"


def create_task_embed(task):

    status = task.get("status", "open")

    if status == "done":
        status_text = "🟢 Erledigt"
    elif status == "taken":
        status_text = "🟡 In Bearbeitung"
    else:
        status_text = "⚪ Offen"

    embed = discord.Embed(
        title="🛠️ Entwickleraufgabe",
        color=(
            discord.Color.green()
            if status == "done"
            else discord.Color.orange()
            if status == "taken"
            else discord.Color.blurple()
        )
    )

    embed.add_field(
        name="📋 Aufgabe",
        value=task["description"],
        inline=False
    )

    embed.add_field(
        name="👤 Erstellt von",
        value=task_user_info(task["creator_id"]),
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=status_text,
        inline=True
    )

    taken_by = task.get("taken_by")

    embed.add_field(
        name="🙋 Übernommen von",
        value=(
            task_user_info(taken_by)
            if taken_by
            else "Niemand"
        ),
        inline=True
    )

    done_by = task.get("done_by")

    embed.add_field(
        name="✅ Erledigt von",
        value=(
            task_user_info(done_by)
            if done_by
            else "Noch nicht erledigt"
        ),
        inline=False
    )

    embed.add_field(
        name="Aufgaben-ID",
        value=f"`{task['id']}`",
        inline=False
    )

    return embed


class DeveloperTaskView(discord.ui.View):

    def __init__(self, task_id):
        super().__init__(timeout=None)
        self.task_id = str(task_id)

    @discord.ui.button(
        label="Übernehmen",
        style=discord.ButtonStyle.primary,
        emoji="🙋",
        custom_id="task_take"
    )
    async def take_task(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )
            return

        if not has_shift_permission(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        if task.get("status") == "done":
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
        task["status"] = "taken"

        save_data()

        await interaction.message.edit(
            embed=create_task_embed(task),
            view=DeveloperTaskView(self.task_id)
        )

        await interaction.response.send_message(
            "✅ Du hast die Aufgabe übernommen.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Erledigt",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="task_done"
    )
    async def done_task(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )
            return

        is_admin = interaction.user.guild_permissions.administrator

        if task.get("taken_by"):
            allowed = (
                task["taken_by"] == interaction.user.id
                or is_admin
            )
        else:
            allowed = is_admin

        if not allowed:
            await interaction.response.send_message(
                "❌ Nur der Übernehmer oder ein Administrator kann die Aufgabe erledigen.",
                ephemeral=True
            )
            return

        task["status"] = "done"
        task["done_by"] = interaction.user.id

        save_data()

        try:
            creator = await bot.fetch_user(int(task["creator_id"]))

            await creator.send(
                f"✅ Deine Entwickleraufgabe **#{task['id']}** wurde erledigt."
            )

        except Exception:
            pass

        await interaction.message.edit(
            embed=create_task_embed(task),
            view=DeveloperTaskView(self.task_id)
        )

        await interaction.response.send_message(
            "✅ Aufgabe wurde als erledigt markiert.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="task_delete"
    )
    async def delete_task(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren können Aufgaben löschen.",
                ephemeral=True
            )
            return

        task = data["tasks"].get(self.task_id)

        if not task:
            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        data["tasks"].pop(self.task_id, None)
        save_data()

        try:
            await interaction.message.delete()
        except Exception:
            pass

        try:
            await interaction.followup.send(
                "✅ Aufgabe wurde gelöscht.",
                ephemeral=True
            )
        except Exception:
            pass


# =========================================================
# DEVELOPER SCHICHT
# =========================================================

class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied nicht gefunden.",
                ephemeral=True
            )
            return

        if not has_shift_permission(member):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, eine Developer-Schicht zu starten.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        if user_id in data["active_shifts"]:
            await interaction.response.send_message(
                "❌ Du hast bereits eine aktive Schicht.",
                ephemeral=True
            )
            return

        started_at = datetime.now()

        data["active_shifts"][user_id] = {
            "started_at": started_at.isoformat(),
            "username": interaction.user.name
        }

        save_data()

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role:
            try:
                await member.add_roles(role)
            except Exception as e:
                print(f"Fehler beim Hinzufügen der Schichtrolle: {e}")

        # ============================
        # SCHICHT-LOG START
        # ============================

        log_channel = await get_or_fetch_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:

            embed = discord.Embed(
                title="🟢 Developer-Schicht gestartet",
                description=(
                    f"{interaction.user.mention} ♡ "
                    f"hat seine Schicht gestartet."
                ),
                color=discord.Color.green(),
                timestamp=datetime.now()
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
                value=f"**heute um {now_time()}**",
                inline=False
            )

            try:
                embed.set_thumbnail(
                    url=interaction.user.display_avatar.url
                )
            except Exception:
                pass

            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"Fehler beim Schicht-Start-Log: {e}")

        await interaction.response.send_message(
            "🟢 Deine Developer-Schicht wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="shift_stop"
    )
    async def stop_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied nicht gefunden.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        if user_id not in data["active_shifts"]:
            await interaction.response.send_message(
                "❌ Du hast keine aktive Schicht.",
                ephemeral=True
            )
            return

        shift_data = data["active_shifts"].get(user_id)

        data["active_shifts"].pop(user_id, None)
        save_data()

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role:
            try:
                await member.remove_roles(role)
            except Exception as e:
                print(f"Fehler beim Entfernen der Schichtrolle: {e}")

        # ============================
        # SCHICHT-LOG ENDE
        # ============================

        log_channel = await get_or_fetch_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:

            embed = discord.Embed(
                title="🔴 Developer-Schicht beendet",
                description=(
                    f"{interaction.user.mention} ♡ "
                    f"hat seine Schicht beendet."
                ),
                color=discord.Color.red(),
                timestamp=datetime.now()
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
                value=f"**heute um {now_time()}**",
                inline=False
            )

            try:
                embed.set_thumbnail(
                    url=interaction.user.display_avatar.url
                )
            except Exception:
                pass

            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"Fehler beim Schicht-Ende-Log: {e}")

        await interaction.response.send_message(
            "🔴 Deine Developer-Schicht wurde beendet.",
            ephemeral=True
        )


def create_shift_embed():

    return discord.Embed(
        title="💻 Developer-Schicht",
        description=(
            "Hier kannst du deine Developer-Schicht starten "
            "oder beenden.\n\n"
            "🟢 **Schicht starten**\n"
            "🔴 **Schicht beenden**"
        ),
        color=discord.Color.blurple()
    )


# =========================================================
# DEVELOPER BEWERBUNG
# =========================================================

class DeveloperApplicationModal(
    discord.ui.Modal,
    title="Developer Bewerbung"
):

    name_field = discord.ui.TextInput(
        label="Name",
        max_length=100,
        required=True
    )

    age_field = discord.ui.TextInput(
        label="Alter",
        max_length=3,
        required=True
    )

    experience_field = discord.ui.TextInput(
        label="Erfahrung",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    motivation_field = discord.ui.TextInput(
        label="Warum möchtest du Developer werden?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    additional_field = discord.ui.TextInput(
        label="Zusätzliche Informationen",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        for application in data["applications"].values():
            if (
                str(application.get("user_id")) == user_id
                and application.get("status") == "open"
            ):
                await interaction.response.send_message(
                    "❌ Du hast bereits eine offene Bewerbung.",
                    ephemeral=True
                )
                return

        application_id = str(data["next_application_id"])
        data["next_application_id"] += 1

        application = {
            "id": application_id,
            "user_id": interaction.user.id,
            "name": str(self.name_field),
            "age": str(self.age_field),
            "experience": str(self.experience_field),
            "motivation": str(self.motivation_field),
            "additional": str(self.additional_field),
            "status": "open"
        }

        data["applications"][application_id] = application
        save_data()

        await send_application_message(application)

        await interaction.response.send_message(
            "✅ Deine Developer-Bewerbung wurde erfolgreich abgeschickt.",
            ephemeral=True
        )


class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer bewerben",
        style=discord.ButtonStyle.success,
        emoji="💻",
        custom_id="developer_apply"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            DeveloperApplicationModal()
        )


class ApplicationDecisionView(discord.ui.View):

    def __init__(self, application_id):
        super().__init__(timeout=None)
        self.application_id = str(application_id)

    @discord.ui.button(
        label="Annehmen",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="application_accept"
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren können Bewerbungen bearbeiten.",
                ephemeral=True
            )
            return

        application = data["applications"].get(self.application_id)

        if not application:
            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )
            return

        if application.get("status") != "open":
            await interaction.response.send_message(
                "❌ Diese Bewerbung wurde bereits bearbeitet.",
                ephemeral=True
            )
            return

        application["status"] = "accepted"
        application["decided_by"] = interaction.user.id

        save_data()

        guild = interaction.guild
        member = guild.get_member(int(application["user_id"]))

        if member:

            role = guild.get_role(
                DEVELOPER_APPLICATION_ROLE_ID
            )

            if role:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    print(f"Fehler bei Developer-Rolle: {e}")

            try:
                await member.send(
                    "✅ Deine Developer-Bewerbung wurde angenommen!"
                )
            except Exception:
                pass

        embed = interaction.message.embeds[0]

        embed.color = discord.Color.green()

        await interaction.message.edit(
            embed=embed,
            view=None
        )

        await interaction.response.send_message(
            "✅ Bewerbung wurde angenommen.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Ablehnen",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="application_reject"
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren können Bewerbungen bearbeiten.",
                ephemeral=True
            )
            return

        application = data["applications"].get(self.application_id)

        if not application:
            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )
            return

        if application.get("status") != "open":
            await interaction.response.send_message(
                "❌ Diese Bewerbung wurde bereits bearbeitet.",
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

            await user.send(
                "❌ Deine Developer-Bewerbung wurde abgelehnt."
            )

        except Exception:
            pass

        embed = interaction.message.embeds[0]

        embed.color = discord.Color.red()

        await interaction.message.edit(
            embed=embed,
            view=None
        )

        await interaction.response.send_message(
            "❌ Bewerbung wurde abgelehnt.",
            ephemeral=True
        )


async def send_application_message(application):

    channel = await get_or_fetch_channel(
        DEV_APPLICATION_RESULT_CHANNEL_ID
    )

    if channel is None:
        return

    user = bot.get_user(int(application["user_id"]))

    if user:
        user_text = get_user_info(user)
    else:
        user_text = f"<@{application['user_id']}>"

    embed = discord.Embed(
        title="💻 Neue Developer-Bewerbung",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👤 Benutzer",
        value=user_text,
        inline=False
    )

    embed.add_field(
        name="Name",
        value=application["name"],
        inline=False
    )

    embed.add_field(
        name="Alter",
        value=application["age"],
        inline=True
    )

    embed.add_field(
        name="Erfahrung",
        value=application["experience"],
        inline=False
    )

    embed.add_field(
        name="Motivation",
        value=application["motivation"],
        inline=False
    )

    embed.add_field(
        name="Zusätzliche Informationen",
        value=(
            application["additional"]
            if application["additional"]
            else "Keine"
        ),
        inline=False
    )

    embed.add_field(
        name="Bewerbungs-ID",
        value=f"`{application['id']}`",
        inline=False
    )

    await channel.send(
        embed=embed,
        view=ApplicationDecisionView(application["id"])
    )


def create_application_panel_embed():

    return discord.Embed(
        title="💻 Developer-Bewerbung",
        description=(
            "Du möchtest unser Developer-Team unterstützen?\n\n"
            "Klicke auf den Button und fülle die Bewerbung aus."
        ),
        color=discord.Color.blurple()
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
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = await get_or_fetch_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Vorschlagskanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💡 Neuer Community-Vorschlag",
            description=str(self.text),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Von",
            value=(
                f"{interaction.user.mention} ♡ "
                f"Name: {interaction.user.name}. "
                f"User-ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde gesendet.",
            ephemeral=True
        )


class FeedbackModal(
    discord.ui.Modal,
    title="Community-Feedback"
):

    text = discord.ui.TextInput(
        label="Dein Feedback",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = await get_or_fetch_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Feedbackkanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💬 Neues Community-Feedback",
            description=str(self.text),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Von",
            value=(
                f"{interaction.user.mention} ♡ "
                f"Name: {interaction.user.name}. "
                f"User-ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Dein Feedback wurde gesendet.",
            ephemeral=True
        )


class CommunityPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Vorschlag senden",
        style=discord.ButtonStyle.primary,
        emoji="💡",
        custom_id="community_suggestion"
    )
    async def suggestion(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            SuggestionModal()
        )

    @discord.ui.button(
        label="Feedback senden",
        style=discord.ButtonStyle.secondary,
        emoji="💬",
        custom_id="community_feedback"
    )
    async def feedback(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            FeedbackModal()
        )


def create_community_panel_embed():

    return discord.Embed(
        title="🌐 Community",
        description=(
            "Über dieses Panel kannst du der Community "
            "Vorschläge und Feedback senden."
        ),
        color=discord.Color.blurple()
    )


# =========================================================
# PANEL REFRESH
# =========================================================

async def refresh_fixed_panel(
    key,
    channel_id,
    embed,
    view,
    title
):

    channel = await get_or_fetch_channel(channel_id)

    if channel is None:
        print(f"Kanal nicht gefunden: {channel_id}")
        return

    message_id = data["panel_messages"].get(key)

    if message_id:

        try:
            message = await channel.fetch_message(
                int(message_id)
            )

            await message.edit(
                embed=embed,
                view=view
            )

            return

        except Exception:
            pass

    try:

        async for old_message in channel.history(limit=50):

            if (
                old_message.author.id == bot.user.id
                and old_message.embeds
                and old_message.embeds[0].title == title
            ):

                try:
                    await old_message.delete()
                except Exception:
                    pass

    except Exception:
        pass

    try:

        message = await channel.send(
            embed=embed,
            view=view
        )

        data["panel_messages"][key] = message.id

        save_data()

    except discord.Forbidden:
        print(
            f"Keine Rechte zum Senden im Kanal {channel_id}"
        )

    except Exception as e:
        print(
            f"Fehler beim Panel {key}: {e}"
        )


async def refresh_all_panels():

    await refresh_fixed_panel(
        "nametag",
        NAMETAG_CHANNEL_ID,
        create_nametag_embed(),
        NametagView(),
        "🏷️ Nametag-System"
    )

    await refresh_license_panel()

    await refresh_fixed_panel(
        "developer_task",
        DEVELOPER_TASK_CHANNEL_ID,
        discord.Embed(
            title="🛠️ Entwickleraufgaben",
            description=(
                "Hier können Entwickleraufgaben erstellt "
                "und übernommen werden."
            ),
            color=discord.Color.blurple()
        ),
        None,
        "🛠️ Entwickleraufgaben"
    )

    await refresh_fixed_panel(
        "developer_shift",
        DEVELOPER_SHIFT_CHANNEL_ID,
        create_shift_embed(),
        DeveloperShiftView(),
        "💻 Developer-Schicht"
    )

    await refresh_fixed_panel(
        "developer_application",
        DEV_APPLICATION_CHANNEL_ID,
        create_application_panel_embed(),
        DeveloperApplicationView(),
        "💻 Developer-Bewerbung"
    )


# =========================================================
# COMMUNITY PANEL COMMAND
# =========================================================

@bot.command()
async def communitypanel(ctx):

    if not has_role(
        ctx.author,
        COMMUNITY_PANEL_PERMISSION_ROLE_ID
    ) and not ctx.author.guild_permissions.administrator:

        await ctx.send(
            "❌ Du hast keine Berechtigung für diesen Befehl.",
            delete_after=5
        )
        return

    await ctx.send(
        embed=create_community_panel_embed(),
        view=CommunityPanelView()
    )


# =========================================================
# COMMUNITY INFO
# =========================================================

@bot.command()
async def community(ctx):

    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "Willkommen in unserer Community.\n\n"
            "Nutze das Community-Panel, um Vorschläge "
            "oder Feedback einzureichen."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


# =========================================================
# ENTWICKLERAUFGABE ERSTELLEN
# =========================================================

@bot.command()
async def task(ctx, *, description=None):

    if not has_shift_permission(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    if not description:
        await ctx.send(
            f"❌ Benutzung: `{PREFIX}task <Aufgabe>`",
            delete_after=5
        )
        return

    task_id = str(data["next_task_id"])
    data["next_task_id"] += 1

    task_data = {
        "id": task_id,
        "description": description,
        "creator_id": ctx.author.id,
        "status": "open",
        "taken_by": None,
        "done_by": None
    }

    data["tasks"][task_id] = task_data

    save_data()

    channel = await get_or_fetch_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        await ctx.send(
            "❌ Entwickler-Aufgabenkanal nicht gefunden.",
            delete_after=5
        )
        return

    role = f"<@&{DEVELOPER_TASK_PING_ROLE_ID}>"

    await channel.send(
        content=role,
        embed=create_task_embed(task_data),
        view=DeveloperTaskView(task_id)
    )

    await ctx.send(
        "✅ Entwickleraufgabe wurde erstellt.",
        delete_after=5
    )


# =========================================================
# STARTUP
# =========================================================

startup_sync_done = False


@bot.event
async def on_ready():

    global startup_sync_done

    print(
        f"Bot online: {bot.user} "
        f"(ID: {bot.user.id})"
    )

    if startup_sync_done:
        return

    startup_sync_done = True

    # Persistente Views
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(DeveloperShiftView())
    bot.add_view(DeveloperApplicationView())
    bot.add_view(CommunityPanelView())

    # Schichtrollen synchronisieren
    guild = await get_guild()

    if guild:

        role = guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            for user_id in list(
                data["active_shifts"].keys()
            ):

                member = guild.get_member(
                    int(user_id)
                )

                if member:

                    try:
                        if role not in member.roles:
                            await member.add_roles(role)
                    except Exception:
                        pass

    save_data()

    await refresh_all_panels()

    print("Alle Systeme geladen.")


# =========================================================
# FEHLERBEHANDLUNG
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "❌ Es fehlt ein Argument.",
            delete_after=5
        )
        return

    print(f"Command-Fehler: {error}")


# =========================================================
# BOT START
# =========================================================

if not TOKEN:

    print("FEHLER: DISCORD_TOKEN fehlt.")

else:

    try:

        bot.run(TOKEN)

    except discord.LoginFailure:

        print("FEHLER: Discord-Token ist falsch.")

    except Exception as e:

        print(f"FEHLER beim Starten des Bots: {e}")
