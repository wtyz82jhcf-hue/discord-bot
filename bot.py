import discord
from discord.ext import commands, tasks
from discord import ui

import asyncio
import json
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

# Nametag
NAMETAG_CHANNEL_ID = 1555684071911202836
NAMETAG_ROLE_ID = 1520102928398942348

# Kennzeichen
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

# Developer Aufgaben
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_TASK_PING_ROLE_ID = 1523674698574200904

# Developer Schicht
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

# Developer Bewerbung
DEV_APPLICATION_CHANNEL_ID = 1541391365219295343
DEV_APPLICATION_RESULT_CHANNEL_ID = 1548404201493762181
DEVELOPER_APPLICATION_ROLE_ID = 1541393345295683634

# Community
SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200

PREFIX = "?"
DATA_FILE = "bot_data.json"


# =========================================================
# INTENTS / BOT
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
    "applications": {}
}

data = {}


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        data = DEFAULT_DATA.copy()
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        if not isinstance(loaded, dict):
            loaded = {}

        data = loaded

    except Exception as error:
        print(f"[DATEN] Fehler beim Laden: {error}")
        data = {}

    # Fehlende Bereiche wieder hinzufügen
    for key, value in DEFAULT_DATA.items():
        if key not in data:
            if isinstance(value, dict):
                data[key] = {}
            elif isinstance(value, list):
                data[key] = []
            else:
                data[key] = value

    # Altes Zahlenspiel vollständig entfernen
    data.pop("number_game", None)
    data.pop("number_games", None)
    data.pop("counting_game", None)
    data.pop("counting", None)

    save_data()


def save_data():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as error:
        print(f"[DATEN] Fehler beim Speichern: {error}")


load_data()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_channel(channel_id):
    return bot.get_channel(channel_id)


def has_role(member, role_id):
    if not isinstance(member, discord.Member):
        return False

    return any(role.id == role_id for role in member.roles)


def is_admin(member):
    return (
        isinstance(member, discord.Member)
        and member.guild_permissions.administrator
    )


def make_embed(title, description, color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    embed.set_footer(
        text="RLP Community Bot"
    )

    return embed


def member_info(member):
    if member is None:
        return "Unbekannt"

    return f"{member.mention}\n**Name:** {member}\n**ID:** `{member.id}`"


async def safe_dm(user, embed):
    try:
        await user.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


# =========================================================
# NAMETAG SYSTEM
# =========================================================

class NametagModal(ui.Modal, title="Nametag ändern"):

    nametag = ui.TextInput(
        label="Dein neuer Nametag",
        placeholder="Zum Beispiel: Max Mustermann",
        min_length=2,
        max_length=32,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Dieser Vorgang funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if not has_role(interaction.user, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, deinen Nametag über dieses System zu ändern.",
                ephemeral=True
            )
            return

        new_name = str(self.nametag).strip()

        if len(new_name) < 2:
            await interaction.response.send_message(
                "❌ Der Nametag ist zu kurz.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.edit(
                nick=new_name,
                reason="Nametag-System"
            )

            embed = make_embed(
                "✅ Nametag geändert",
                f"Dein Nametag wurde erfolgreich auf **{new_name}** geändert.",
                discord.Color.green()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nametag nicht ändern. "
                "Meine Bot-Rolle muss in der Rollenliste über deiner höchsten Rolle stehen.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord konnte den Nametag gerade nicht ändern. Bitte versuche es erneut.",
                ephemeral=True
            )

        except Exception as error:
            print(f"[NAMETAG] Fehler: {error}")

            await interaction.response.send_message(
                "❌ Beim Ändern des Nametags ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class NametagView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Nametag ändern",
        style=discord.ButtonStyle.primary,
        emoji="🏷️",
        custom_id="rlp_nametag_change"
    )
    async def nametag_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not has_role(interaction.user, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für das Nametag-System.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(NametagModal())


@bot.command(name="nametag")
async def nametag_command(ctx):

    embed = discord.Embed(
        title="🏷️ Nametag-System",
        description=(
            "Willkommen beim **Nametag-System** unseres Servers.\n\n"
            "Mit diesem System kannst du deinen sichtbaren Namen auf dem "
            "Discord-Server einfach und sicher ändern.\n\n"
            "### 📋 So funktioniert es\n"
            "**1.** Klicke unten auf **Nametag ändern**.\n"
            "**2.** Trage deinen gewünschten Nametag ein.\n"
            "**3.** Bestätige deine Eingabe.\n"
            "**4.** Dein Name wird anschließend automatisch aktualisiert.\n\n"
            "### ℹ️ Bitte beachten\n"
            "• Verwende einen vernünftigen und regelkonformen Namen.\n"
            "• Unpassende oder beleidigende Namen sind nicht erlaubt.\n"
            "• Für dieses System wird die entsprechende Nametag-Berechtigung benötigt.\n"
            "• Der Button bleibt auch nach einem Bot-Neustart funktionsfähig."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔐 Berechtigung",
        value=(
            "Wenn du die erforderliche Rolle besitzt, kannst du deinen "
            "Nametag direkt über den Button ändern."
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Probleme?",
        value=(
            "Falls dein Nametag nicht geändert werden kann, wende dich bitte "
            "an ein zuständiges Teammitglied."
        ),
        inline=False
    )

    embed.set_footer(
        text="RLP Community • Nametag-System"
    )

    await ctx.send(
        embed=embed,
        view=NametagView()
    )


# =========================================================
# KENNZEICHEN SYSTEM
# =========================================================

class LicensePlateModal(ui.Modal, title="Kennzeichen festlegen"):

    plate = ui.TextInput(
        label="Dein Kennzeichen",
        placeholder="Zum Beispiel: GM-RP 123",
        min_length=2,
        max_length=15,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        plate = str(self.plate).strip().upper()

        if len(plate) < 2 or len(plate) > 15:
            await interaction.response.send_message(
                "❌ Dein Kennzeichen muss zwischen 2 und 15 Zeichen lang sein.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        old_plate = data["license_plates"].get(user_id)

        data["license_plates"][user_id] = {
            "plate": plate,
            "user_name": str(interaction.user),
            "updated_at": discord.utils.utcnow().isoformat()
        }

        save_data()

        if old_plate:
            description = (
                f"Dein Kennzeichen wurde erfolgreich geändert.\n\n"
                f"**Neues Kennzeichen:** `{plate}`"
            )
        else:
            description = (
                f"Dein Kennzeichen wurde erfolgreich gespeichert.\n\n"
                f"**Kennzeichen:** `{plate}`"
            )

        embed = make_embed(
            "🚗 Kennzeichen gespeichert",
            description,
            discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class LicensePlateView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Kennzeichen setzen / ändern",
        style=discord.ButtonStyle.primary,
        emoji="🚗",
        custom_id="rlp_plate_set"
    )
    async def set_plate(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @ui.button(
        label="Kennzeichen anzeigen",
        style=discord.ButtonStyle.secondary,
        emoji="🔎",
        custom_id="rlp_plate_show"
    )
    async def show_plate(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        user_id = str(interaction.user.id)
        stored = data["license_plates"].get(user_id)

        if not stored:
            await interaction.response.send_message(
                "❌ Du hast aktuell kein Kennzeichen gespeichert.",
                ephemeral=True
            )
            return

        if isinstance(stored, dict):
            plate = stored.get("plate", "Unbekannt")
        else:
            # Unterstützung alter gespeicherter Daten
            plate = str(stored)

        embed = make_embed(
            "🚗 Dein Kennzeichen",
            f"Dein aktuell gespeichertes Kennzeichen lautet:\n\n**`{plate}`**"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @ui.button(
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="rlp_plate_remove"
    )
    async def remove_plate(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein gespeichertes Kennzeichen.",
                ephemeral=True
            )
            return

        del data["license_plates"][user_id]
        save_data()

        embed = make_embed(
            "🗑️ Kennzeichen entfernt",
            "Dein gespeichertes Kennzeichen wurde erfolgreich entfernt.",
            discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


@bot.command(name="kennzeichen")
async def kennzeichen_command(ctx):

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Hier kannst du dein persönliches Kennzeichen verwalten.\n\n"
            "### Funktionen\n"
            "🚗 **Setzen / ändern**\n"
            "Speichere ein neues Kennzeichen oder ändere dein bestehendes.\n\n"
            "🔎 **Anzeigen**\n"
            "Zeigt dir dein aktuell gespeichertes Kennzeichen.\n\n"
            "🗑️ **Entfernen**\n"
            "Entfernt dein Kennzeichen vollständig aus dem System.\n\n"
            "Dein gespeichertes Kennzeichen bleibt auch nach einem Neustart "
            "des Bots erhalten."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Community • Kennzeichen-System"
    )

    await ctx.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# DEVELOPER AUFGABEN
# =========================================================

def build_task_embed(task_id):

    task_data = data["tasks"].get(str(task_id))

    if not task_data:
        return make_embed(
            "❌ Aufgabe nicht gefunden",
            "Diese Aufgabe existiert nicht mehr.",
            discord.Color.red()
        )

    status = task_data.get("status", "Offen")

    if status == "Offen":
        color = discord.Color.orange()
        status_text = "🟠 Offen"

    elif status == "In Bearbeitung":
        color = discord.Color.yellow()
        status_text = "🟡 In Bearbeitung"

    elif status == "Erledigt":
        color = discord.Color.green()
        status_text = "🟢 Erledigt"

    else:
        color = discord.Color.blurple()
        status_text = status

    embed = discord.Embed(
        title=f"🛠️ Developer-Aufgabe #{task_id}",
        description=task_data.get(
            "description",
            "Keine Beschreibung vorhanden."
        ),
        color=color,
        timestamp=discord.utils.utcnow()
    )

    creator_id = task_data.get("creator_id")

    embed.add_field(
        name="👤 Erstellt von",
        value=(
            f"<@{creator_id}>\n"
            f"**Name:** {task_data.get('creator_name', 'Unbekannt')}\n"
            f"**ID:** `{creator_id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=status_text,
        inline=False
    )

    taken_by = task_data.get("taken_by")

    if taken_by:
        embed.add_field(
            name="👨‍💻 Übernommen von",
            value=(
                f"<@{taken_by}>\n"
                f"**Name:** {task_data.get('taken_by_name', 'Unbekannt')}\n"
                f"**ID:** `{taken_by}`"
            ),
            inline=False
        )

    done_by = task_data.get("done_by")

    if done_by:
        embed.add_field(
            name="✅ Erledigt von",
            value=(
                f"<@{done_by}>\n"
                f"**Name:** {task_data.get('done_by_name', 'Unbekannt')}\n"
                f"**ID:** `{done_by}`"
            ),
            inline=False
        )

    embed.set_footer(
        text="RLP Community • Developer-System"
    )

    return embed


class DeveloperTaskModal(ui.Modal, title="Neue Developer-Aufgabe"):

    description = ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe möglichst genau...",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not (
            has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID)
            or is_admin(interaction.user)
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Developer-Aufgaben zu erstellen.",
                ephemeral=True
            )
            return

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Developer-Aufgaben-Kanal konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        while True:
            task_id = random.randint(100000, 999999)

            if str(task_id) not in data["tasks"]:
                break

        data["tasks"][str(task_id)] = {
            "description": str(self.description).strip(),
            "creator_id": interaction.user.id,
            "creator_name": str(interaction.user),
            "status": "Offen",
            "taken_by": None,
            "taken_by_name": None,
            "done_by": None,
            "done_by_name": None,
            "message_id": None,
            "created_at": discord.utils.utcnow().isoformat()
        }

        save_data()

        embed = build_task_embed(task_id)

        ping = f"<@&{DEVELOPER_TASK_PING_ROLE_ID}>"

        message = await channel.send(
            content=ping,
            embed=embed,
            view=DeveloperTaskView(task_id),
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        data["tasks"][str(task_id)]["message_id"] = message.id
        save_data()

        await interaction.response.send_message(
            f"✅ Developer-Aufgabe **#{task_id}** wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="rlp_task_create"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not (
            has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID)
            or is_admin(interaction.user)
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
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

        self.take_button.custom_id = f"rlp_task_take_{self.task_id}"
        self.done_button.custom_id = f"rlp_task_done_{self.task_id}"
        self.delete_button.custom_id = f"rlp_task_delete_{self.task_id}"

    @ui.button(
        label="Übernehmen",
        style=discord.ButtonStyle.primary,
        emoji="🛠️"
    )
    async def take_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        task_data = data["tasks"].get(self.task_id)

        if not task_data:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        if not (
            has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID)
            or is_admin(interaction.user)
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Developer-Aufgaben zu übernehmen.",
                ephemeral=True
            )
            return

        if task_data.get("status") == "Erledigt":
            await interaction.response.send_message(
                "❌ Diese Aufgabe wurde bereits erledigt.",
                ephemeral=True
            )
            return

        if task_data.get("taken_by"):
            await interaction.response.send_message(
                f"❌ Diese Aufgabe wurde bereits von "
                f"<@{task_data['taken_by']}> übernommen.",
                ephemeral=True
            )
            return

        task_data["status"] = "In Bearbeitung"
        task_data["taken_by"] = interaction.user.id
        task_data["taken_by_name"] = str(interaction.user)

        save_data()

        await interaction.response.edit_message(
            embed=build_task_embed(self.task_id),
            view=self
        )

    @ui.button(
        label="Als erledigt markieren",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def done_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        task_data = data["tasks"].get(self.task_id)

        if not task_data:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        if task_data.get("status") == "Erledigt":
            await interaction.response.send_message(
                "❌ Diese Aufgabe wurde bereits erledigt.",
                ephemeral=True
            )
            return

        allowed = (
            interaction.user.id == task_data.get("taken_by")
            or is_admin(interaction.user)
        )

        if not allowed:
            await interaction.response.send_message(
                "❌ Nur die Person, die diese Aufgabe übernommen hat, "
                "oder ein Administrator kann sie als erledigt markieren.",
                ephemeral=True
            )
            return

        task_data["status"] = "Erledigt"
        task_data["done_by"] = interaction.user.id
        task_data["done_by_name"] = str(interaction.user)
        task_data["completed_at"] = discord.utils.utcnow().isoformat()

        save_data()

        await interaction.response.edit_message(
            embed=build_task_embed(self.task_id),
            view=self
        )

        creator_id = task_data.get("creator_id")

        try:
            creator = await bot.fetch_user(creator_id)

            dm_embed = discord.Embed(
                title="✅ Developer-Aufgabe abgeschlossen",
                description=(
                    f"Deine Developer-Aufgabe **#{self.task_id}** "
                    f"wurde erfolgreich abgeschlossen."
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )

            dm_embed.add_field(
                name="🛠️ Aufgabe",
                value=task_data.get("description", "Keine Beschreibung"),
                inline=False
            )

            dm_embed.add_field(
                name="✅ Erledigt von",
                value=f"{interaction.user} (`{interaction.user.id}`)",
                inline=False
            )

            dm_embed.set_footer(
                text="RLP Community • Developer-System"
            )

            await safe_dm(
                creator,
                dm_embed
            )

        except Exception as error:
            print(f"[AUFGABE DM] Fehler: {error}")

    @ui.button(
        label="Löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def delete_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Nur Administratoren können Developer-Aufgaben löschen.",
                ephemeral=True
            )
            return

        if self.task_id not in data["tasks"]:
            await interaction.response.send_message(
                "❌ Diese Aufgabe existiert nicht mehr.",
                ephemeral=True
            )
            return

        del data["tasks"][self.task_id]
        save_data()

        try:
            await interaction.message.delete()
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "✅ Aufgabe wurde aus dem System entfernt.",
                    ephemeral=True
                )


@bot.command(name="entwickler")
async def entwickler_command(ctx):

    embed = discord.Embed(
        title="🛠️ Developer-Aufgaben",
        description=(
            "Über dieses Panel können neue Aufgaben für das Developer-Team "
            "erstellt werden.\n\n"
            "Nach der Erstellung kann eine Aufgabe von einem Developer "
            "übernommen und anschließend als erledigt markiert werden.\n\n"
            "**Die Aufgaben und ihr Status bleiben auch nach einem "
            "Bot-Neustart gespeichert.**"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Community • Developer-System"
    )

    await ctx.send(
        embed=embed,
        view=DeveloperTaskPanelView()
    )


# =========================================================
# DEVELOPER SCHICHT
# =========================================================

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


class DeveloperShiftView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="rlp_shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Dieser Vorgang funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if not (
            has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID)
            or is_admin(interaction.user)
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, eine Developer-Schicht zu starten.",
                ephemeral=True
            )
            return

        active_shifts = get_active_shifts()

        if interaction.user.id in active_shifts:
            await interaction.response.send_message(
                "❌ Du befindest dich bereits in einer aktiven Schicht.",
                ephemeral=True
            )
            return

        active_shifts.add(interaction.user.id)
        save_active_shifts(active_shifts)

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:
            try:
                await interaction.user.add_roles(
                    role,
                    reason="Developer-Schicht gestartet"
                )
            except discord.Forbidden:
                print(
                    "[SCHICHT] Developer-Schichtrolle "
                    "konnte nicht vergeben werden."
                )

        log_channel = get_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:

            embed = discord.Embed(
                title="🟢 Developer-Schicht gestartet",
                description=f"{interaction.user.mention} hat seine Schicht gestartet.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="Developer",
                value=f"{interaction.user}\n`{interaction.user.id}`",
                inline=False
            )

            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Developer-Schicht wurde gestartet.",
            ephemeral=True
        )

    @ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="rlp_shift_stop"
    )
    async def stop_shift(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Dieser Vorgang funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        active_shifts = get_active_shifts()

        if interaction.user.id not in active_shifts:
            await interaction.response.send_message(
                "❌ Du hast aktuell keine aktive Developer-Schicht.",
                ephemeral=True
            )
            return

        active_shifts.remove(interaction.user.id)
        save_active_shifts(active_shifts)

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:
            try:
                await interaction.user.remove_roles(
                    role,
                    reason="Developer-Schicht beendet"
                )
            except discord.Forbidden:
                print(
                    "[SCHICHT] Developer-Schichtrolle "
                    "konnte nicht entfernt werden."
                )

        log_channel = get_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:

            embed = discord.Embed(
                title="🔴 Developer-Schicht beendet",
                description=f"{interaction.user.mention} hat seine Schicht beendet.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="Developer",
                value=f"{interaction.user}\n`{interaction.user.id}`",
                inline=False
            )

            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Developer-Schicht wurde beendet.",
            ephemeral=True
        )


@bot.command(name="schicht")
async def shift_command(ctx):

    embed = discord.Embed(
        title="🕐 Developer-Schichtsystem",
        description=(
            "Über dieses Panel kannst du deine Developer-Schicht "
            "starten oder beenden.\n\n"
            "🟢 **Schicht starten**\n"
            "Du wirst als aktiv eingetragen und erhältst die "
            "Developer-Schichtrolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Du wirst aus der aktiven Schicht entfernt und die "
            "Schichtrolle wird entfernt.\n\n"
            "Aktive Schichten werden gespeichert und gehen bei einem "
            "Bot-Neustart nicht verloren."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Community • Developer-Schichten"
    )

    await ctx.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# DEVELOPER BEWERBUNG
# =========================================================

def build_application_embed(application_id):

    application = data["applications"].get(
        str(application_id)
    )

    if not application:
        return None

    status = application.get("status", "offen")

    if status == "angenommen":
        color = discord.Color.green()
        status_text = "✅ Angenommen"

    elif status == "abgelehnt":
        color = discord.Color.red()
        status_text = "❌ Abgelehnt"

    else:
        color = discord.Color.orange()
        status_text = "🟠 Offen"

    embed = discord.Embed(
        title=f"💻 Developer-Bewerbung #{application_id}",
        color=color,
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 Bewerber",
        value=(
            f"<@{application.get('user_id')}>\n"
            f"**Name:** {application.get('user_name')}\n"
            f"**ID:** `{application.get('user_id')}`"
        ),
        inline=False
    )

    embed.add_field(
        name="📛 Angegebener Name",
        value=application.get("name", "-"),
        inline=False
    )

    embed.add_field(
        name="🎂 Alter",
        value=application.get("age", "-"),
        inline=False
    )

    embed.add_field(
        name="💻 Erfahrung",
        value=application.get("experience", "-"),
        inline=False
    )

    embed.add_field(
        name="💡 Motivation",
        value=application.get("motivation", "-"),
        inline=False
    )

    additional = application.get("additional")

    if additional:
        embed.add_field(
            name="📝 Sonstiges",
            value=additional,
            inline=False
        )

    embed.add_field(
        name="📊 Status",
        value=status_text,
        inline=False
    )

    if application.get("accepted_by"):
        embed.add_field(
            name="✅ Angenommen von",
            value=f"<@{application['accepted_by']}>",
            inline=False
        )

    if application.get("rejected_by"):
        embed.add_field(
            name="❌ Abgelehnt von",
            value=f"<@{application['rejected_by']}>",
            inline=False
        )

    embed.set_footer(
        text="RLP Community • Developer-Bewerbung"
    )

    return embed


class DevApplicationModal(
    ui.Modal,
    title="Developer-Bewerbung"
):

    applicant_name = ui.TextInput(
        label="Dein Name",
        placeholder="Wie möchtest du genannt werden?",
        max_length=50,
        required=True
    )

    age = ui.TextInput(
        label="Dein Alter",
        placeholder="Zum Beispiel: 16",
        max_length=3,
        required=True
    )

    experience = ui.TextInput(
        label="Deine Erfahrung",
        placeholder="Welche Erfahrung hast du bereits?",
        style=discord.TextStyle.paragraph,
        max_length=750,
        required=True
    )

    motivation = ui.TextInput(
        label="Warum möchtest du Developer werden?",
        placeholder="Erkläre deine Motivation...",
        style=discord.TextStyle.paragraph,
        max_length=750,
        required=True
    )

    additional = ui.TextInput(
        label="Sonstiges",
        placeholder="Gibt es noch etwas Wichtiges?",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        for application in data["applications"].values():

            if (
                application.get("user_id") == interaction.user.id
                and application.get("status") == "offen"
            ):
                await interaction.response.send_message(
                    "❌ Du hast bereits eine offene Developer-Bewerbung.",
                    ephemeral=True
                )
                return

        result_channel = get_channel(
            DEV_APPLICATION_RESULT_CHANNEL_ID
        )

        if result_channel is None:
            await interaction.response.send_message(
                "❌ Der Bewerbungskanal für das Team konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        while True:
            application_id = random.randint(
                100000,
                999999
            )

            if str(application_id) not in data["applications"]:
                break

        data["applications"][str(application_id)] = {
            "user_id": interaction.user.id,
            "user_name": str(interaction.user),
            "name": str(self.applicant_name).strip(),
            "age": str(self.age).strip(),
            "experience": str(self.experience).strip(),
            "motivation": str(self.motivation).strip(),
            "additional": str(self.additional).strip(),
            "status": "offen",
            "message_id": None,
            "accepted_by": None,
            "rejected_by": None,
            "created_at": discord.utils.utcnow().isoformat()
        }

        save_data()

        message = await result_channel.send(
            embed=build_application_embed(
                application_id
            ),
            view=DevApplicationDecisionView(
                application_id
            )
        )

        data["applications"][str(application_id)]["message_id"] = message.id
        save_data()

        embed = make_embed(
            "✅ Bewerbung eingereicht",
            (
                "Deine Developer-Bewerbung wurde erfolgreich eingereicht.\n\n"
                "Das zuständige Team kann deine Bewerbung jetzt bearbeiten."
            ),
            discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class DevApplicationPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Developer-Bewerbung starten",
        style=discord.ButtonStyle.primary,
        emoji="💻",
        custom_id="rlp_dev_application_start"
    )
    async def application_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
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

        self.accept_button.custom_id = (
            f"rlp_application_accept_{self.application_id}"
        )

        self.reject_button.custom_id = (
            f"rlp_application_reject_{self.application_id}"
        )

    @ui.button(
        label="Annehmen",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def accept_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not is_admin(interaction.user):
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

        application["status"] = "angenommen"
        application["accepted_by"] = interaction.user.id
        application["rejected_by"] = None

        save_data()

        role_added = False

        guild = interaction.guild

        if guild:
            member = guild.get_member(
                application["user_id"]
            )

            role = guild.get_role(
                DEVELOPER_APPLICATION_ROLE_ID
            )

            if member and role:
                try:
                    await member.add_roles(
                        role,
                        reason=(
                            "Developer-Bewerbung angenommen "
                            f"von {interaction.user}"
                        )
                    )

                    role_added = True

                except discord.Forbidden:
                    print(
                        "[BEWERBUNG] Developer-Rolle konnte "
                        "nicht vergeben werden. Rollen-Hierarchie prüfen."
                    )

                except discord.HTTPException as error:
                    print(
                        f"[BEWERBUNG] Rollenfehler: {error}"
                    )

        await interaction.response.edit_message(
            embed=build_application_embed(
                self.application_id
            ),
            view=self
        )

        try:
            applicant = await bot.fetch_user(
                application["user_id"]
            )

            description = (
                "Deine Developer-Bewerbung wurde **angenommen**. 🎉\n\n"
                "Willkommen im Developer-Team!"
            )

            if not role_added:
                description += (
                    "\n\nℹ️ Die Developer-Rolle konnte nicht automatisch "
                    "vergeben werden. Ein Administrator sollte die "
                    "Bot-Rollenhierarchie prüfen."
                )

            dm_embed = make_embed(
                "✅ Developer-Bewerbung angenommen",
                description,
                discord.Color.green()
            )

            await safe_dm(
                applicant,
                dm_embed
            )

        except Exception as error:
            print(
                f"[BEWERBUNG DM] Fehler: {error}"
            )

    @ui.button(
        label="Ablehnen",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def reject_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not is_admin(interaction.user):
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
        application["accepted_by"] = None

        save_data()

        await interaction.response.edit_message(
            embed=build_application_embed(
                self.application_id
            ),
            view=self
        )

        try:
            applicant = await bot.fetch_user(
                application["user_id"]
            )

            dm_embed = make_embed(
                "❌ Developer-Bewerbung",
                (
                    "Deine Developer-Bewerbung wurde leider abgelehnt.\n\n"
                    "Vielen Dank für dein Interesse am Developer-Team."
                ),
                discord.Color.red()
            )

            await safe_dm(
                applicant,
                dm_embed
            )

        except Exception as error:
            print(
                f"[BEWERBUNG DM] Fehler: {error}"
            )


@bot.command(name="devbewerbung")
async def dev_application_command(ctx):

    if ctx.channel.id != DEV_APPLICATION_CHANNEL_ID:
        await ctx.send(
            f"❌ Dieses Panel gehört in <#{DEV_APPLICATION_CHANNEL_ID}>."
        )
        return

    embed = discord.Embed(
        title="💻 Developer-Bewerbung",
        description=(
            "Du möchtest unser Developer-Team unterstützen?\n\n"
            "Über den Button unter dieser Nachricht kannst du deine "
            "Developer-Bewerbung einreichen.\n\n"
            "### Bevor du dich bewirbst\n"
            "• Beantworte alle Fragen ehrlich und ausführlich.\n"
            "• Beschreibe deine bisherigen Erfahrungen.\n"
            "• Erkläre, warum du unser Developer-Team unterstützen möchtest.\n"
            "• Pro Person kann immer nur eine offene Bewerbung bestehen.\n\n"
            "Nach dem Absenden wird deine Bewerbung an das zuständige "
            "Team weitergeleitet."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Community • Developer-Bewerbung"
    )

    await ctx.send(
        embed=embed,
        view=DevApplicationPanelView()
    )


# =========================================================
# COMMUNITY SYSTEM
# =========================================================

class SuggestionModal(
    ui.Modal,
    title="Community-Vorschlag"
):

    suggestion = ui.TextInput(
        label="Dein Vorschlag",
        placeholder="Beschreibe deinen Vorschlag...",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Vorschlagskanal konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💡 Neuer Community-Vorschlag",
            description=str(self.suggestion).strip(),
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Eingereicht von",
            value=(
                f"{interaction.user.mention}\n"
                f"**Name:** {interaction.user}\n"
                f"**ID:** `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.set_footer(
            text="RLP Community • Vorschlag"
        )

        message = await channel.send(
            embed=embed
        )

        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")
        except discord.HTTPException:
            pass

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde erfolgreich eingereicht.",
            ephemeral=True
        )


class FeedbackModal(
    ui.Modal,
    title="Community-Feedback"
):

    feedback = ui.TextInput(
        label="Dein Feedback",
        placeholder="Schreibe uns dein Feedback...",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Feedbackkanal konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📝 Neues Community-Feedback",
            description=str(self.feedback).strip(),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Eingereicht von",
            value=(
                f"{interaction.user.mention}\n"
                f"**Name:** {interaction.user}\n"
                f"**ID:** `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.set_footer(
            text="RLP Community • Feedback"
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Vielen Dank! Dein Feedback wurde erfolgreich eingereicht.",
            ephemeral=True
        )


class CommunityPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Vorschlag einreichen",
        style=discord.ButtonStyle.primary,
        emoji="💡",
        custom_id="rlp_community_suggestion"
    )
    async def suggestion_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            SuggestionModal()
        )

    @ui.button(
        label="Feedback senden",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="rlp_community_feedback"
    )
    async def feedback_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            FeedbackModal()
        )


@bot.command(name="communitypanel")
async def community_panel_command(ctx):

    embed = discord.Embed(
        title="🌐 RLP Community",
        description=(
            "Deine Meinung ist uns wichtig!\n\n"
            "Über dieses Panel kannst du direkt mithelfen, unsere "
            "Community weiterzuentwickeln.\n\n"
            "### 💡 Vorschlag einreichen\n"
            "Du hast eine neue Idee, einen Verbesserungsvorschlag oder "
            "einen Wunsch für den Server? Teile ihn mit uns.\n\n"
            "### 📝 Feedback senden\n"
            "Du möchtest uns mitteilen, was gut läuft oder wo wir uns "
            "verbessern können? Sende uns dein Feedback.\n\n"
            "Klicke einfach auf den passenden Button."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Community • Community-System"
    )

    await ctx.send(
        embed=embed,
        view=CommunityPanelView()
    )


@bot.command(name="community")
async def community_command(ctx):

    embed = discord.Embed(
        title="🌐 Community-System",
        description=(
            "Mit dem Community-System kannst du Vorschläge und Feedback "
            "an das Team senden.\n\n"
            f"💡 **Vorschläge:** <#{SUGGESTION_CHANNEL_ID}>\n"
            f"📝 **Feedback:** <#{FEEDBACK_CHANNEL_ID}>\n\n"
            "Nutze das Community-Panel, um etwas einzureichen."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


# =========================================================
# HELP
# =========================================================

@bot.command(name="helpme")
async def help_command(ctx):

    embed = discord.Embed(
        title="🤖 RLP Community Bot",
        description=(
            "Hier findest du die verfügbaren Bot-Systeme.\n\n"
            "**🏷️ `?nametag`**\n"
            "Öffnet das Nametag-System.\n\n"
            "**🚗 `?kennzeichen`**\n"
            "Öffnet das Kennzeichen-System.\n\n"
            "**🛠️ `?entwickler`**\n"
            "Öffnet das Developer-Aufgaben-System.\n\n"
            "**🕐 `?schicht`**\n"
            "Öffnet das Developer-Schichtsystem.\n\n"
            "**💻 `?devbewerbung`**\n"
            "Öffnet das Developer-Bewerbungs-System.\n\n"
            "**🌐 `?communitypanel`**\n"
            "Öffnet das Community-Panel.\n\n"
            "**🌐 `?community`**\n"
            "Zeigt Informationen zum Community-System."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Community Bot"
    )

    await ctx.send(embed=embed)


# =========================================================
# PERSISTENTE VIEWS
# =========================================================

def setup_persistent_views():

    # Feste Panels
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
        DevApplicationPanelView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    # Gespeicherte Developer-Aufgaben
    for task_id, task_data in data.get(
        "tasks",
        {}
    ).items():

        if task_data.get("status") != "Erledigt":
            try:
                bot.add_view(
                    DeveloperTaskView(task_id)
                )
            except Exception as error:
                print(
                    f"[VIEW] Aufgabe {task_id}: {error}"
                )

    # Offene Bewerbungen
    for application_id, application in data.get(
        "applications",
        {}
    ).items():

        if application.get("status") == "offen":
            try:
                bot.add_view(
                    DevApplicationDecisionView(
                        application_id
                    )
                )
            except Exception as error:
                print(
                    f"[VIEW] Bewerbung {application_id}: {error}"
                )


# =========================================================
# SCHICHTEN NACH NEUSTART SYNCHRONISIEREN
# =========================================================

async def sync_active_shift_roles():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        return

    role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:
        return

    active_shifts = get_active_shifts()
    invalid_users = []

    for user_id in active_shifts:

        member = guild.get_member(
            user_id
        )

        if member is None:
            invalid_users.append(
                user_id
            )
            continue

        if role not in member.roles:
            try:
                await member.add_roles(
                    role,
                    reason="Aktive Developer-Schicht nach Bot-Neustart synchronisiert"
                )

            except discord.Forbidden:
                print(
                    f"[SCHICHT] Rolle für {member} "
                    "konnte nicht synchronisiert werden."
                )

            except discord.HTTPException as error:
                print(
                    f"[SCHICHT] Discord-Fehler: {error}"
                )

    if invalid_users:

        for user_id in invalid_users:
            active_shifts.discard(
                user_id
            )

        save_active_shifts(
            active_shifts
        )


# =========================================================
# STATUS
# =========================================================

@tasks.loop(seconds=30)
async def status_loop():

    try:
        guild = bot.get_guild(
            GUILD_ID
        )

        if guild:
            activity = discord.Game(
                name=f"RLP Community • {guild.member_count} Mitglieder"
            )
        else:
            activity = discord.Game(
                name="RLP Community"
            )

        await bot.change_presence(
            status=discord.Status.online,
            activity=activity
        )

    except Exception as error:
        print(
            f"[STATUS] Fehler: {error}"
        )


@status_loop.before_loop
async def before_status_loop():
    await bot.wait_until_ready()


# =========================================================
# EVENTS
# =========================================================

startup_sync_done = False


@bot.event
async def on_ready():

    global startup_sync_done

    print("===================================")
    print(f"Bot online als: {bot.user}")
    print(f"Bot-ID: {bot.user.id}")
    print("===================================")

    if not status_loop.is_running():
        status_loop.start()

    if not startup_sync_done:
        startup_sync_done = True

        try:
            await sync_active_shift_roles()
        except Exception as error:
            print(
                f"[STARTUP] Schicht-Synchronisierung: {error}"
            )

    print("[STARTUP] Persistente Systeme sind bereit.")


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
            "❌ Du hast keine Berechtigung für diesen Befehl."
        )
        return

    if isinstance(
        error,
        commands.CommandOnCooldown
    ):
        await ctx.send(
            "⏳ Bitte warte kurz, bevor du den Befehl erneut verwendest."
        )
        return

    print(
        f"[COMMAND ERROR] {type(error).__name__}: {error}"
    )

    try:
        await ctx.send(
            "❌ Beim Ausführen des Befehls ist ein Fehler aufgetreten."
        )
    except discord.HTTPException:
        pass


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"RLP Community Bot is running."
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
        f"[WEB] Health-Server läuft auf Port {port}."
    )


# =========================================================
# START
# =========================================================

async def main():

    setup_persistent_views()

    async with bot:
        await bot.start(
            TOKEN
        )


if __name__ == "__main__":

    if not TOKEN:
        print(
            "FEHLER: DISCORD_TOKEN fehlt."
        )

    else:

        try:

            start_web_server()

            asyncio.run(
                main()
            )

        except discord.LoginFailure:
            print(
                "FEHLER: Discord-Token ist falsch."
            )

        except KeyboardInterrupt:
            print(
                "Bot wurde beendet."
            )

        except Exception as error:
            print(
                f"FEHLER: {type(error).__name__}: {error}"
            )
