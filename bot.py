import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import tempfile
import random
import time
import asyncio

# =========================================================
# CONFIG
# =========================================================

PREFIX = "?"
DATA_FILE = "bot_data.json"

# =========================================================
# NUR DIESER SERVER DARF DEN BOT BENUTZEN
# =========================================================

ALLOWED_GUILD_ID = 1519481018221072454
GUILD_ID = ALLOWED_GUILD_ID

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

EMOJI_QUIZ_RESET_ROLE_ID = 1520102918219628756

GERMANY_TZ = ZoneInfo("Europe/Berlin")

# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError(
        "TOKEN wurde nicht gefunden. "
        "Bitte die Umgebungsvariable TOKEN in Wispbyte setzen."
    )

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
# SERVER-SCHUTZ
# =========================================================

def is_allowed_guild(guild):
    return (
        guild is not None
        and guild.id == ALLOWED_GUILD_ID
    )


async def allowed_guild_only(interaction):
    """
    Prüft, ob eine Button-/Modal-Interaktion
    auf dem erlaubten Server stattfindet.
    """

    if not is_allowed_guild(interaction.guild):

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

        return False

    return True


@bot.check
async def global_guild_check(ctx):
    """
    ALLE Prefix-Commands funktionieren ausschließlich
    auf dem erlaubten Server.
    """

    return (
        ctx.guild is not None
        and ctx.guild.id == ALLOWED_GUILD_ID
    )


@bot.event
async def on_command_error(ctx, error):

    # Auf anderen Servern keine Fehlermeldung anzeigen.
    if isinstance(error, commands.CheckFailure):
        return

    # Unbekannte Commands ebenfalls nicht crashen lassen.
    if isinstance(error, commands.CommandNotFound):
        return

    print(
        f"Command-Fehler bei {ctx.command}: {error}"
    )


# =========================================================
# DATA
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


def load_data():

    if not os.path.exists(DATA_FILE):
        return json.loads(
            json.dumps(DEFAULT_DATA)
        )

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

    except Exception:

        loaded = {}

    for key, value in DEFAULT_DATA.items():

        if key not in loaded:
            loaded[key] = json.loads(
                json.dumps(value)
            )

    if not isinstance(
        loaded["emoji_quiz"],
        dict
    ):
        loaded["emoji_quiz"] = {}

    for key, value in DEFAULT_DATA["emoji_quiz"].items():

        if key not in loaded["emoji_quiz"]:
            loaded["emoji_quiz"][key] = json.loads(
                json.dumps(value)
            )

    for key in (
        "points",
        "current",
        "user_stats"
    ):

        if not isinstance(
            loaded["emoji_quiz"].get(key),
            dict
        ):
            loaded["emoji_quiz"][key] = {}

    return loaded


data = load_data()


def save_data():

    temp_path = None

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
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temp_path,
            DATA_FILE
        )

        temp_path = None

    except Exception as e:

        print(
            f"Fehler beim Speichern: {e}"
        )

        if temp_path:

            try:
                os.remove(temp_path)
            except Exception:
                pass


# =========================================================
# HELPERS
# =========================================================

def now_local():
    return datetime.now(
        GERMANY_TZ
    )


def console_log(message):

    print(
        f"[{now_local().strftime('%d.%m.%Y %H:%M:%S')}] "
        f"{message}"
    )


def has_role(member, role_id):

    return any(
        role.id == role_id
        for role in member.roles
    )


def is_admin(member):

    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
    )


async def get_or_fetch_channel(channel_id):

    channel = bot.get_channel(
        channel_id
    )

    if channel:

        if getattr(
            channel,
            "guild",
            None
        ) is not None:

            if channel.guild.id != ALLOWED_GUILD_ID:
                return None

        return channel

    try:

        channel = await bot.fetch_channel(
            channel_id
        )

        if getattr(
            channel,
            "guild",
            None
        ) is None:

            return None

        if channel.guild.id != ALLOWED_GUILD_ID:
            return None

        return channel

    except Exception as e:

        console_log(
            f"Kanal {channel_id} konnte nicht geladen werden: {e}"
        )

        return None


# =========================================================
# COMMUNITY
# =========================================================

class SuggestionModal(
    discord.ui.Modal,
    title="💡 Vorschlag"
):

    suggestion = discord.ui.TextInput(
        label="Dein Vorschlag",
        style=discord.TextStyle.paragraph,
        placeholder="Schreibe deinen Vorschlag...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction):

        if not is_allowed_guild(
            interaction.guild
        ):

            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

            return

        channel = await get_or_fetch_channel(
            SUGGESTION_CHANNEL_ID
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Vorschlagskanal nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="💡 Neuer Vorschlag",
            description=self.suggestion.value,
            color=discord.Color.green()
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.timestamp = now_local()

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Vorschlag gesendet.",
            ephemeral=True
        )


class FeedbackModal(
    discord.ui.Modal,
    title="💬 Feedback"
):

    feedback = discord.ui.TextInput(
        label="Dein Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Schreibe dein Feedback...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction):

        if not is_allowed_guild(
            interaction.guild
        ):

            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

            return

        channel = await get_or_fetch_channel(
            FEEDBACK_CHANNEL_ID
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Feedbackkanal nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="💬 Neues Feedback",
            description=self.feedback.value,
            color=discord.Color.blurple()
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.timestamp = now_local()

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

        if not await allowed_guild_only(
            interaction
        ):
            return

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

        if not await allowed_guild_only(
            interaction
        ):
            return

        await interaction.response.send_modal(
            FeedbackModal()
        )


@bot.command(
    name="communitypanel"
)
@commands.guild_only()
async def communitypanel(ctx):

    if not is_allowed_guild(
        ctx.guild
    ):
        return

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
@commands.guild_only()
async def community(ctx):

    if not is_allowed_guild(
        ctx.guild
    ):
        return

    embed = discord.Embed(
        title="🌐 Community",
        description="Willkommen im Community-Bereich.",
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(
    discord.ui.Modal,
    title="🏷️ Nametag"
):

    name = discord.ui.TextInput(
        label="Nametag",
        placeholder="Dein gewünschter Nametag",
        required=True,
        max_length=32
    )

    async def on_submit(self, interaction):

        if not is_allowed_guild(
            interaction.guild
        ):

            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

            return

        data["nametags"][
            str(interaction.user.id)
        ] = self.name.value

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Nametag wurde auf "
            f"**{self.name.value}** gesetzt.",
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
        label="Nametag setzen",
        style=discord.ButtonStyle.primary,
        emoji="🏷️",
        custom_id="nametag_set"
    )
    async def set_nametag(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        await interaction.response.send_modal(
            NametagModal()
        )


async def refresh_nametag_panel():

    channel = await get_or_fetch_channel(
        NAMETAG_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "Klicke auf den Button, "
            "um deinen Nametag festzulegen."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(
    discord.ui.Modal,
    title="🚗 Kennzeichen"
):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. GM-AB 123",
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction):

        if not is_allowed_guild(
            interaction.guild
        ):

            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

            return

        data["license_plates"][
            str(interaction.user.id)
        ] = self.plate.value

        save_data()

        await interaction.response.send_message(
            f"✅ Kennzeichen gespeichert: "
            f"**{self.plate.value}**",
            ephemeral=True
        )


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
        custom_id="license_set"
    )
    async def set_plate(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        await interaction.response.send_modal(
            LicensePlateModal()
        )


async def update_license_panel():

    channel = await get_or_fetch_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description=(
            "Klicke auf den Button, "
            "um dein Kennzeichen zu speichern."
        ),
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# ENTWICKLERAUFGABEN
# =========================================================

class DeveloperTaskModal(
    discord.ui.Modal,
    title="🛠️ Entwickleraufgabe"
):

    task = discord.ui.TextInput(
        label="Aufgabe",
        style=discord.TextStyle.paragraph,
        placeholder="Beschreibe die Entwickleraufgabe...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction):

        if not is_allowed_guild(
            interaction.guild
        ):

            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

            return

        task_id = str(
            data["next_task_id"]
        )

        data["next_task_id"] += 1

        data["tasks"][task_id] = {
            "id": task_id,
            "title": self.task.value,
            "created_by": interaction.user.id,
            "created_at": now_local().isoformat(),
            "status": "open"
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe **#{task_id}** wurde erstellt.",
            ephemeral=True
        )

        await send_developer_task(
            task_id
        )


class DeveloperTaskView(
    discord.ui.View
):

    def __init__(
        self,
        task_id=None
    ):

        super().__init__(
            timeout=None
        )

        self.task_id = (
            str(task_id)
            if task_id is not None
            else None
        )

    @discord.ui.button(
        label="Aufgabe übernehmen",
        style=discord.ButtonStyle.success,
        emoji="🛠️",
        custom_id="developer_task_take"
    )
    async def take_task(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        if not self.task_id:

            await interaction.response.send_message(
                "❌ Keine Aufgabe gefunden.",
                ephemeral=True
            )

            return

        task = data["tasks"].get(
            self.task_id
        )

        if not task:

            await interaction.response.send_message(
                "❌ Aufgabe nicht gefunden.",
                ephemeral=True
            )

            return

        if task.get("status") != "open":

            await interaction.response.send_message(
                "❌ Diese Aufgabe wurde bereits übernommen.",
                ephemeral=True
            )

            return

        task["status"] = "taken"
        task["taken_by"] = interaction.user.id
        task["taken_at"] = now_local().isoformat()

        save_data()

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} hat Aufgabe "
            f"**#{self.task_id}** übernommen."
        )


class DeveloperTaskPanelView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Neue Aufgabe",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="developer_new_task"
    )
    async def new_task(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        if not (
            is_admin(interaction.user)
            or has_role(
                interaction.user,
                DEVELOPER_TASK_PING_ROLE_ID
            )
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


async def send_developer_task(
    task_id
):

    channel = await get_or_fetch_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if not channel:
        return

    task = data["tasks"].get(
        str(task_id)
    )

    if not task:
        return

    embed = discord.Embed(
        title="🛠️ Entwickleraufgabe",
        description=task["title"],
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Aufgaben-ID",
        value=f"#{task_id}",
        inline=True
    )

    embed.add_field(
        name="Status",
        value="🟢 Offen",
        inline=True
    )

    # Alte Aufgaben werden NICHT gelöscht.
    await channel.send(
        embed=embed,
        view=DeveloperTaskView(
            task_id
        )
    )


async def refresh_task_panel():

    channel = await get_or_fetch_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="🛠️ Entwickleraufgaben",
        description=(
            "Über den Button kannst du eine neue "
            "Entwickleraufgabe erstellen."
        ),
        color=discord.Color.orange()
    )

    # Alte Panels werden NICHT gelöscht.
    await channel.send(
        embed=embed,
        view=DeveloperTaskPanelView()
    )


# =========================================================
# SCHICHTSYSTEM
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
        emoji="▶️",
        custom_id="shift_start"
    )
    async def start(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        user_id = str(
            interaction.user.id
        )

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für eine Schicht.",
                ephemeral=True
            )

            return

        if user_id in data["active_shifts"]:

            await interaction.response.send_message(
                "❌ Du bist bereits im Dienst.",
                ephemeral=True
            )

            return

        data["active_shifts"][user_id] = {
            "started": now_local().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            "▶️ Deine Schicht wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        custom_id="shift_stop"
    )
    async def stop(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        user_id = str(
            interaction.user.id
        )

        if user_id not in data["active_shifts"]:

            await interaction.response.send_message(
                "❌ Du hast keine aktive Schicht.",
                ephemeral=True
            )

            return

        shift = data["active_shifts"].pop(
            user_id
        )

        save_data()

        await interaction.response.send_message(
            "⏹️ Deine Schicht wurde beendet.",
            ephemeral=True
        )

        channel = await get_or_fetch_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if channel:

            await channel.send(
                f"🕐 {interaction.user.mention} "
                f"hat seine Schicht beendet."
            )


async def sync_shift_roles():
    return


async def refresh_shift_panel():

    channel = await get_or_fetch_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="🕐 Entwicklerschicht",
        description=(
            "Starte oder beende hier "
            "deine Entwicklerschicht."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class DeveloperApplicationModal(
    discord.ui.Modal,
    title="👨‍💻 Entwickler-Bewerbung"
):

    reason = discord.ui.TextInput(
        label="Warum möchtest du Entwickler werden?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):

        if not is_allowed_guild(
            interaction.guild
        ):

            await interaction.response.send_message(
                "❌ Dieser Bot funktioniert nur auf dem vorgesehenen Server.",
                ephemeral=True
            )

            return

        application_id = str(
            data["next_application_id"]
        )

        data["next_application_id"] += 1

        data["applications"][
            application_id
        ] = {
            "id": application_id,
            "user_id": interaction.user.id,
            "reason": self.reason.value,
            "status": "open",
            "created_at": now_local().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Bewerbung **#{application_id}** wurde eingereicht.",
            ephemeral=True
        )

        await send_application(
            application_id
        )


class DeveloperApplicationView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.primary,
        emoji="👨‍💻",
        custom_id="developer_apply"
    )
    async def apply(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        await interaction.response.send_modal(
            DeveloperApplicationModal()
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

    @discord.ui.button(
        label="Annehmen",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="application_accept"
    )
    async def accept(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        application = data["applications"].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )

            return

        application["status"] = "accepted"

        save_data()

        await interaction.response.send_message(
            "✅ Bewerbung wurde angenommen."
        )

    @discord.ui.button(
        label="Ablehnen",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="application_decline"
    )
    async def decline(
        self,
        interaction,
        button
    ):

        if not await allowed_guild_only(
            interaction
        ):
            return

        if not is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        application = data["applications"].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Bewerbung nicht gefunden.",
                ephemeral=True
            )

            return

        application["status"] = "declined"

        save_data()

        await interaction.response.send_message(
            "❌ Bewerbung wurde abgelehnt."
        )


async def send_application(
    application_id
):

    channel = await get_or_fetch_channel(
        DEV_APPLICATION_RESULT_CHANNEL_ID
    )

    if not channel:
        return

    application = data["applications"].get(
        str(application_id)
    )

    if not application:
        return

    embed = discord.Embed(
        title="👨‍💻 Neue Entwickler-Bewerbung",
        description=application["reason"],
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Bewerber",
        value=f"<@{application['user_id']}>"
    )

    embed.add_field(
        name="Bewerbungs-ID",
        value=f"#{application_id}"
    )

    await channel.send(
        embed=embed,
        view=ApplicationDecisionView(
            application_id
        )
    )


async def refresh_application_panel():

    channel = await get_or_fetch_channel(
        DEV_APPLICATION_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="👨‍💻 Entwickler-Bewerbung",
        description=(
            "Klicke auf den Button, "
            "um dich zu bewerben."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# =========================================================
# EMOJI QUIZ
# =========================================================

EMOJI_QUIZ = [

    ("⚽🥅", "Fußball",
     "Dort wird ein Ball ins Tor geschossen.",
     "F", "Sport"),

    ("🏀🧺", "Basketball",
     "Der Ball muss durch einen Korb.",
     "B", "Sport"),

    ("🎾", "Tennis",
     "Man spielt es mit Schläger und Netz.",
     "T", "Sport"),

    ("🏎️🏁", "Formel 1",
     "Motorsport mit schnellen Rennwagen.",
     "F", "Sport"),

    ("🏊‍♂️🌊", "Schwimmen",
     "Sport im Wasser.",
     "S", "Sport"),

    ("🚴‍♂️", "Radfahren",
     "Man benutzt dafür ein Fahrrad.",
     "R", "Sport"),

    ("🏇", "Reiten",
     "Sport mit einem Pferd.",
     "R", "Sport"),

    ("🥊", "Boxen",
     "Kampfsport mit Handschuhen.",
     "B", "Sport"),

    ("🏐", "Volleyball",
     "Ballspiel über ein Netz.",
     "V", "Sport"),

    ("🏓", "Tischtennis",
     "Tennis auf einem Tisch.",
     "T", "Sport"),

    ("🇩🇪🍺🥨", "Deutschland",
     "Ein Land in Europa.",
     "D", "Länder"),

    ("🇫🇷🥐🗼", "Frankreich",
     "Dort steht ein sehr berühmter Turm.",
     "F", "Länder"),

    ("🇮🇹🍕🍝", "Italien",
     "Bekannt für Pizza und Pasta.",
     "I", "Länder"),

    ("🇯🇵🍣🗻", "Japan",
     "Inselstaat in Asien.",
     "J", "Länder"),

    ("🇺🇸🗽🍔", "USA",
     "Dort steht die Freiheitsstatue.",
     "U", "Länder"),

    ("🇬🇧👑☕", "England",
     "Teil des Vereinigten Königreichs.",
     "E", "Länder"),

    ("🇪🇸💃🥘", "Spanien",
     "Bekannt für Flamenco und Paella.",
     "S", "Länder"),

    ("🇧🇷⚽🌴", "Brasilien",
     "Großes Land in Südamerika.",
     "B", "Länder"),

    ("🇨🇦🍁", "Kanada",
     "Das Ahornblatt ist ein bekanntes Symbol.",
     "K", "Länder"),

    ("🇦🇺🦘", "Australien",
     "Dort leben Kängurus.",
     "A", "Länder"),

    ("🇬🇷🏛️", "Griechenland",
     "Bekannt für antike Tempel.",
     "G", "Länder"),

    ("🇳🇱🌷🚲", "Niederlande",
     "Bekannt für Tulpen und Fahrräder.",
     "N", "Länder"),

    ("🇨🇭🏔️🧀", "Schweiz",
     "Bekannt für Berge und Käse.",
     "S", "Länder"),

    ("🇳🇴❄️🏔️", "Norwegen",
     "Skandinavisches Land mit vielen Fjorden.",
     "N", "Länder"),

    ("🇮🇸🌋❄️", "Island",
     "Insel mit Vulkanen und Gletschern.",
     "I", "Länder"),

    ("🍕", "Pizza",
     "Rundes Gericht mit Belag.",
     "P", "Essen"),

    ("🍔🍟", "Burger",
     "Typisches Fast Food mit Brötchen.",
     "B", "Essen"),

    ("🌭", "Hotdog",
     "Wurst im länglichen Brötchen.",
     "H", "Essen"),

    ("🍣", "Sushi",
     "Japanisches Gericht mit Reis.",
     "S", "Essen"),

    ("🌮", "Taco",
     "Mexikanisches Gericht mit gefüllter Schale.",
     "T", "Essen"),

    ("🍝🍅", "Spaghetti",
     "Lange italienische Nudeln.",
     "S", "Essen"),

    ("🥨", "Brezel",
     "Beliebtes deutsches Gebäck.",
     "B", "Essen"),

    ("🍦", "Eis",
     "Kalt und süß.",
     "E", "Essen"),

    ("🍫", "Schokolade",
     "Süße Nascherei aus Kakao.",
     "S", "Essen"),

    ("🍿🎬", "Popcorn",
     "Typischer Snack im Kino.",
     "P", "Essen"),

    ("🍎👩‍⚕️", "Apfel",
     "Eine bekannte Frucht.",
     "A", "Essen"),

    ("🍌", "Banane",
     "Gelbe Frucht.",
     "B", "Essen"),

    ("🍉☀️", "Wassermelone",
     "Große Sommerfrucht mit viel Wasser.",
     "W", "Essen"),

    ("🥞🍁", "Pfannkuchen",
     "Flaches Gericht, oft mit Sirup.",
     "P", "Essen"),

    ("🍰🎂", "Kuchen",
     "Gibt es oft zum Geburtstag.",
     "K", "Essen"),

    ("🐶", "Hund",
     "Treuer Begleiter des Menschen.",
     "H", "Tiere"),

    ("🐱", "Katze",
     "Sagt häufig Miau.",
     "K", "Tiere"),

    ("🦁", "Löwe",
     "Große Raubkatze.",
     "L", "Tiere"),

    ("🐯", "Tiger",
     "Gestreifte Raubkatze.",
     "T", "Tiere"),

    ("🐘", "Elefant",
     "Sehr großes Tier mit Rüssel.",
     "E", "Tiere"),

    ("🦒", "Giraffe",
     "Hat einen sehr langen Hals.",
     "G", "Tiere"),

    ("🐼🎋", "Panda",
     "Bekommt man oft mit Bambus verbunden.",
     "P", "Tiere"),

    ("🐨🌿", "Koala",
     "Lebt in Australien.",
     "K", "Tiere"),

    ("🦊", "Fuchs",
     "Rotbraunes Wildtier.",
     "F", "Tiere"),

    ("🐺🌕", "Wolf",
     "Lebt oft in Rudeln.",
     "W", "Tiere"),

    ("🐸", "Frosch",
     "Kann weit springen.",
     "F", "Tiere"),

    ("🐍", "Schlange",
     "Hat keine Beine.",
     "S", "Tiere"),

    ("🦈🌊", "Hai",
     "Raubtier des Meeres.",
     "H", "Tiere"),

    ("🐬🌊", "Delfin",
     "Sehr intelligentes Meerestier.",
     "D", "Tiere"),

    ("🐧❄️", "Pinguin",
     "Vogel, der nicht fliegen kann.",
     "P", "Tiere"),

    ("🗼🇫🇷", "Eiffelturm",
     "Berühmtes Wahrzeichen in Paris.",
     "E", "Orte"),

    ("🗽🇺🇸", "Freiheitsstatue",
     "Berühmtes Wahrzeichen in New York.",
     "F", "Orte"),

    ("🏰👑", "Schloss",
     "Dort können Könige und Königinnen leben.",
     "S", "Orte"),

    ("🏝️🌊", "Insel",
     "Land, das von Wasser umgeben ist.",
     "I", "Orte"),

    ("🏖️☀️", "Strand",
     "Sand, Meer und Sonne.",
     "S", "Orte"),

    ("🏔️❄️", "Berg",
     "Hohe Landschaftsform.",
     "B", "Orte"),

    ("🌋🔥", "Vulkan",
     "Kann Lava ausstoßen.",
     "V", "Orte"),

    ("🏫📚", "Schule",
     "Dort lernen Schüler.",
     "S", "Orte"),

    ("🏥🚑", "Krankenhaus",
     "Dort arbeiten viele Ärzte.",
     "K", "Orte"),

    ("✈️🌍", "Flughafen",
     "Dort starten und landen Flugzeuge.",
     "F", "Orte"),

    ("🎬🦸", "Superheldenfilm",
     "Film mit außergewöhnlichen Helden.",
     "S", "Filme"),

    ("🦖🌴", "Jurassic Park",
     "Dinosaurier sind hier das Thema.",
     "J", "Filme"),

    ("🧙‍♂️💍", "Der Herr der Ringe",
     "Fantasy mit einem besonderen Ring.",
     "D", "Filme"),

    ("🧊👸", "Die Eiskönigin",
     "Animationsfilm mit Eis und einer Königin.",
     "D", "Filme"),

    ("🤖🚗", "Transformers",
     "Roboter können zu Fahrzeugen werden.",
     "T", "Filme"),

    ("🦁👑", "Der König der Löwen",
     "Ein Löwe steht im Mittelpunkt.",
     "D", "Filme"),

    ("🐠🔎", "Findet Nemo",
     "Ein kleiner Fisch wird gesucht.",
     "F", "Filme"),

    ("👽🚲🌕", "E.T.",
     "Ein Außerirdischer und ein Fahrrad.",
     "E", "Filme"),

    ("🏴‍☠️🚢", "Piratenfilm",
     "Abenteuer auf hoher See.",
     "P", "Filme"),

    ("🧙‍♂️⚡", "Harry Potter",
     "Zauberei und ein junger Zauberer.",
     "H", "Filme"),

    ("👨‍⚕️🏥", "Arzt",
     "Arbeitet häufig im Krankenhaus.",
     "A", "Berufe"),

    ("👨‍🚒🔥", "Feuerwehrmann",
     "Hilft bei Bränden und Notfällen.",
     "F", "Berufe"),

    ("👮‍♂️🚓", "Polizist",
     "Arbeitet für die Polizei.",
     "P", "Berufe"),

    ("👨‍🍳🍳", "Koch",
     "Bereitet Essen zu.",
     "K", "Berufe"),

    ("👨‍🏫📚", "Lehrer",
     "Unterrichtet Schüler.",
     "L", "Berufe"),

    ("👨‍🔧🔩", "Mechaniker",
     "Arbeitet an Fahrzeugen und Maschinen.",
     "M", "Berufe"),

    ("👨‍💻💻", "Programmierer",
     "Schreibt Software und Code.",
     "P", "Berufe"),

    ("👨‍✈️✈️", "Pilot",
     "Fliegt Flugzeuge.",
     "P", "Berufe"),

    ("👨‍🚀🚀", "Astronaut",
     "Reist ins Weltall.",
     "A", "Berufe"),

    ("📸👨‍🎨", "Fotograf",
     "Macht Fotos.",
     "F", "Berufe"),

    ("🌧️☂️", "Regenschirm",
     "Hilft bei schlechtem Wetter.",
     "R", "Alltag"),

    ("📱💬", "Handy",
     "Damit kann man telefonieren.",
     "H", "Alltag"),

    ("💻⌨️", "Computer",
     "Elektronisches Gerät zum Arbeiten und Spielen.",
     "C", "Alltag"),

    ("🚗⛽", "Auto",
     "Fährt auf Straßen.",
     "A", "Alltag"),

    ("🚲🔔", "Fahrrad",
     "Hat zwei Räder und Pedale.",
     "F", "Alltag"),

    ("⌚⏰", "Uhr",
     "Zeigt die Zeit.",
     "U", "Alltag"),

    ("🔑🚪", "Schlüssel",
     "Öffnet zum Beispiel eine Tür.",
     "S", "Alltag"),

    ("🎒📚", "Rucksack",
     "Darin kann man Sachen transportieren.",
     "R", "Alltag"),

    ("🎧🎵", "Kopfhörer",
     "Damit hört man Musik.",
     "K", "Alltag"),

    ("📺🍿", "Fernseher",
     "Damit kann man Filme und Serien schauen.",
     "F", "Alltag"),

    ("🎄🎁", "Weihnachten",
     "Fest mit Geschenken und Tannenbaum.",
     "W", "Feste"),

    ("🎃👻", "Halloween",
     "Fest mit Kürbissen und Verkleidungen.",
     "H", "Feste"),

    ("🎂🎉", "Geburtstag",
     "Man feiert den Tag der Geburt.",
     "G", "Feste"),

    ("❤️💐", "Valentinstag",
     "Tag rund um Liebe und Freundschaft.",
     "V", "Feste"),

    ("🎆🥳", "Silvester",
     "Feier zum Jahreswechsel.",
     "S", "Feste"),

    ("🐰🥚", "Ostern",
     "Fest mit Eiern und Osterhase.",
     "O", "Feste"),

    ("🌞🏖️", "Sommer",
     "Warme Jahreszeit.",
     "S", "Jahreszeiten"),

    ("🍂🌧️", "Herbst",
     "Blätter werden bunt und fallen.",
     "H", "Jahreszeiten"),

    ("❄️⛄", "Winter",
     "Kalte Jahreszeit.",
     "W", "Jahreszeiten"),

    ("🌸🌱", "Frühling",
     "Alles beginnt wieder zu blühen.",
     "F", "Jahreszeiten"),

    ("🧊🥤", "Eiswürfel",
     "Gefrorenes Wasser.",
     "E", "Gegenstände"),

    ("✏️📖", "Schulzeug",
     "Findet man häufig im Unterricht.",
     "S", "Gegenstände"),

    ("☂️🌧️", "Regenschirm",
     "Schützt vor Regen.",
     "R", "Gegenstände"),

    ("🕶️☀️", "Sonnenbrille",
     "Schützt die Augen vor Sonne.",
     "S", "Gegenstände"),

    ("🎸🎵", "Gitarre",
     "Musikinstrument mit Saiten.",
     "G", "Gegenstände"),

    ("🥁🎵", "Schlagzeug",
     "Musikinstrument zum Schlagen.",
     "S", "Gegenstände"),

    ("🎹🎵", "Klavier",
     "Tasteninstrument.",
     "K", "Gegenstände"),

    ("🎨🖌️", "Malen",
     "Dabei benutzt man oft Pinsel und Farben.",
     "M", "Hobbys"),

    ("📚🛋️", "Lesen",
     "Man macht es mit Büchern.",
     "L", "Hobbys"),

    ("🎮🕹️", "Gaming",
     "Spielen mit Konsole oder Computer.",
     "G", "Hobbys"),

    ("🌙⭐", "Nacht",
     "Die Sonne ist nicht am Himmel.",
     "N", "Sonstiges"),

    ("☀️🌡️", "Hitze",
     "Sehr hohe Temperatur.",
     "H", "Sonstiges"),

    ("🌨️❄️", "Schnee",
     "Weiße Niederschläge im Winter.",
     "S", "Sonstiges"),

    ("🌈🌧️", "Regenbogen",
     "Kann nach Regen erscheinen.",
     "R", "Sonstiges"),

    ("⚡🌩️", "Gewitter",
     "Blitz und Donner gehören dazu.",
     "G", "Sonstiges"),

    ("🔥🪵", "Feuer",
     "Kann sehr heiß sein.",
     "F", "Sonstiges"),

    ("💤🛏️", "Schlafen",
     "Macht man meistens nachts.",
     "S", "Sonstiges"),

    ("😂🤣", "Lachen",
     "Macht man bei etwas Lustigem.",
     "L", "Sonstiges"),

    ("😴🛏️", "Müde",
     "So fühlt man sich vor dem Schlafen.",
     "M", "Sonstiges"),

    ("🎉🥳", "Party",
     "Musik, Spaß und Feiern.",
     "P", "Sonstiges")
]

# =========================================================
# QUIZ COOLDOWNS
# =========================================================

quiz_hint_cooldowns = {}
quiz_skip_cooldowns = {}
quiz_initial_cooldowns = {}
quiz_answer_cooldowns = {}


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

    state = data["emoji_quiz"].get(
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

    emoji, answer, hint, initial, category = EMOJI_QUIZ[index]

    data["emoji_quiz"]["current"] = {
        "index": index,
        "emoji": emoji,
        "answer": answer,
        "hint": hint,
        "initial": initial,
        "category": category,
        "created_at": now_local().isoformat(),
        "users": {}
    }

    save_data()

    return data["emoji_quiz"]["current"]


def get_user_quiz_stats(
    user_id
):

    user_id = str(
        user_id
    )

    users = get_quiz_state().setdefault(
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
        data["emoji_quiz"]["points"].get(
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

    data["emoji_quiz"]["points"][user_id] = (
        get_points(user_id)
        + amount
    )

    save_data()


# =========================================================
# RESET
# =========================================================

@bot.command(
    name="reset"
)
@commands.guild_only()
async def reset_emoji_quiz_points(
    ctx,
    member: discord.Member = None
):

    if not is_allowed_guild(
        ctx.guild
    ):
        return

    if not has_role(
        ctx.author,
        EMOJI_QUIZ_RESET_ROLE_ID
    ):

        await ctx.send(
            "❌ Du hast keine Berechtigung "
            "für diesen Befehl."
        )

        return

    if member is None:

        await ctx.send(
            "❌ Benutzung: `?reset @User`"
        )

        return

    user_id = str(
        member.id
    )

    data["emoji_quiz"]["points"][user_id] = 0

    save_data()

    await ctx.send(
        f"✅ Die Emoji-Quiz-Punkte von "
        f"{member.mention} wurden auf **0** gesetzt."
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

        if not await allowed_guild_only(
            interaction
        ):
            return

        user_id = interaction.user.id
        now = time.monotonic()

        if (
            now
            - quiz_hint_cooldowns.get(
                user_id,
                0
            )
            < 4
        ):

            await interaction.response.send_message(
                "⏳ Warte kurz.",
                ephemeral=True
            )

            return

        quiz_hint_cooldowns[user_id] = now

        stats = get_user_quiz_stats(
            user_id
        )

        if stats["hints"] >= 3:

            await interaction.response.send_message(
                "❌ Deine 3 Tipps sind aufgebraucht.",
                ephemeral=True
            )

            return

        stats["hints"] += 1

        save_data()

        current = get_quiz_state()

        await interaction.response.send_message(
            f"💡 **Tipp:** "
            f"{current.get('hint', 'Kein Tipp verfügbar.')}\n\n"
            f"Dir bleiben **{3 - stats['hints']} Tipp(e)**.",
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

        if not await allowed_guild_only(
            interaction
        ):
            return

        user_id = interaction.user.id
        now = time.monotonic()

        if (
            now
            - quiz_initial_cooldowns.get(
                user_id,
                0
            )
            < 4
        ):

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
                "❌ Deine 3 Anfangsbuchstaben-Hilfen "
                "sind aufgebraucht.",
                ephemeral=True
            )

            return

        stats["initials"] += 1

        save_data()

        answer = get_quiz_state().get(
            "answer",
            ""
        )

        shown = answer[
            :min(
                stats["initials"],
                len(answer)
            )
        ]

        await interaction.response.send_message(
            f"🔤 **Anfangsbuchstaben:** `{shown}`\n\n"
            f"Dir bleiben **"
            f"{3 - stats['initials']} Hilfe(n)**.",
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

        if not await allowed_guild_only(
            interaction
        ):
            return

        user_id = interaction.user.id
        now = time.monotonic()

        if (
            now
            - quiz_skip_cooldowns.get(
                user_id,
                0
            )
            < 10
        ):

            await interaction.response.send_message(
                "⏳ Bitte warte kurz.",
                ephemeral=True
            )

            return

        quiz_skip_cooldowns[user_id] = now

        stats = get_user_quiz_stats(
            user_id
        )

        if stats["skips"] >= 3:

            await interaction.response.send_message(
                "❌ Du hast bereits 3 Überspringen benutzt.",
                ephemeral=True
            )

            return

        stats["skips"] += 1

        save_data()

        await interaction.response.send_message(
            f"⏭️ Quiz übersprungen.\n"
            f"Dir bleiben **"
            f"{3 - stats['skips']} Überspringen**.",
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

        if not await allowed_guild_only(
            interaction
        ):
            return

        points = data["emoji_quiz"]["points"]

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
                f"**{position}.** "
                f"<@{user_id}> — "
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


async def send_new_quiz_panel():

    channel = await get_or_fetch_channel(
        EMOJI_QUIZ_CHANNEL_ID
    )

    if not channel:
        return

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].title
                == "🎯 Emoji Quiz"
            ):

                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception as e:

        console_log(
            f"Emoji-Quiz Panel Fehler: {e}"
        )

    current = create_new_quiz()

    embed = discord.Embed(
        title="🎯 Emoji Quiz",
        description=(
            "Errate den Begriff anhand der Emojis!\n\n"
            f"# {current['emoji']}\n\n"
            f"📚 **Kategorie:** {current['category']}\n\n"
            "💡 3 Tipps\n"
            "🔤 3 Anfangsbuchstaben-Hilfen\n"
            "⏭️ 3 Überspringen\n\n"
            "Schreibe deine Antwort hier in den Kanal."
        ),
        color=discord.Color.blurple()
    )

    message = await channel.send(
        embed=embed,
        view=EmojiQuizView()
    )

    data["panel_messages"][
        "emoji_quiz"
    ] = message.id

    save_data()


async def ensure_quiz_panel():

    channel = await get_or_fetch_channel(
        EMOJI_QUIZ_CHANNEL_ID
    )

    if not channel:
        return

    await send_new_quiz_panel()


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.event
async def on_message(
    message
):

    # Bots ignorieren
    if message.author.bot:
        return

    # DMs komplett ignorieren
    if message.guild is None:
        return

    # ANDERE SERVER KOMPLETT IGNORIEREN
    if message.guild.id != ALLOWED_GUILD_ID:
        return

    # =====================================================
    # EMOJI QUIZ
    # =====================================================

    if message.channel.id == EMOJI_QUIZ_CHANNEL_ID:

        answer_text = message.content.strip()

        if answer_text:

            user_id = message.author.id
            now = time.monotonic()

            if (
                now
                - quiz_answer_cooldowns.get(
                    user_id,
                    0
                )
                < 2
            ):

                try:
                    await message.delete()
                except Exception:
                    pass

                return

            quiz_answer_cooldowns[user_id] = now

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

            if given == correct:

                # =================================================
                # EXAKT 1 PUNKT
                # =================================================

                add_points(
                    user_id,
                    1
                )

                points = get_points(
                    user_id
                )

                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(
                    f"🎉 {message.author.mention} "
                    f"hat **richtig** geraten!\n\n"
                    f"✅ **Lösung:** "
                    f"{current.get('answer')}\n"
                    f"🏆 **+1 Punkt**\n"
                    f"📊 **Gesamt:** "
                    f"{points} Punkte",
                    delete_after=5
                )

                await send_new_quiz_panel()

                return

            wrong_message = await message.channel.send(
                f"❌ {message.author.mention} "
                f"**leider falsch!**\n\n"
                f"Deine Antwort "
                f"**{answer_text}** "
                f"war nicht richtig."
            )

            await asyncio.sleep(
                4
            )

            try:
                await message.delete()
            except Exception:
                pass

            try:
                await wrong_message.delete()
            except Exception:
                pass

            return

    # Commands NUR auf dem erlaubten Server
    await bot.process_commands(
        message
    )


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

    # =====================================================
    # PRÜFEN, OB DER ERLAUBTE SERVER VORHANDEN IST
    # =====================================================

    guild = bot.get_guild(
        ALLOWED_GUILD_ID
    )

    if guild is None:

        console_log(
            f"❌ Erlaubter Server "
            f"{ALLOWED_GUILD_ID} wurde nicht gefunden."
        )

        return

    console_log(
        f"✅ Erlaubter Server gefunden: "
        f"{guild.name} ({guild.id})"
    )

    if startup_sync_done:
        return

    startup_sync_done = True

    # =====================================================
    # PERSISTENTE VIEWS
    # =====================================================

    try:
        bot.add_view(
            NametagView()
        )
    except Exception as e:
        console_log(
            f"Nametag View Fehler: {e}"
        )

    try:
        bot.add_view(
            LicensePlateView()
        )
    except Exception as e:
        console_log(
            f"Kennzeichen View Fehler: {e}"
        )

    try:
        bot.add_view(
            DeveloperShiftView()
        )
    except Exception as e:
        console_log(
            f"Schicht View Fehler: {e}"
        )

    try:
        bot.add_view(
            DeveloperApplicationView()
        )
    except Exception as e:
        console_log(
            f"Bewerbungs View Fehler: {e}"
        )

    try:
        bot.add_view(
            CommunityPanelView()
        )
    except Exception as e:
        console_log(
            f"Community View Fehler: {e}"
        )

    try:
        bot.add_view(
            DeveloperTaskPanelView()
        )
    except Exception as e:
        console_log(
            f"Task Panel View Fehler: {e}"
        )

    try:
        bot.add_view(
            EmojiQuizView()
        )
    except Exception as e:
        console_log(
            f"Emoji Quiz View Fehler: {e}"
        )

    # =====================================================
    # ALTE ENTWICKLERAUFGABEN
    # =====================================================

    for task_id in data["tasks"].keys():

        try:

            bot.add_view(
                DeveloperTaskView(
                    task_id
                )
            )

        except Exception as e:

            console_log(
                f"Task View #{task_id} Fehler: {e}"
            )

    # =====================================================
    # OFFENE BEWERBUNGEN
    # =====================================================

    for (
        application_id,
        application
    ) in data["applications"].items():

        if application.get(
            "status"
        ) == "open":

            try:

                bot.add_view(
                    ApplicationDecisionView(
                        application_id
                    )
                )

            except Exception as e:

                console_log(
                    f"Bewerbungs-View "
                    f"#{application_id} Fehler: {e}"
                )

    # =====================================================
    # SCHICHTROLLEN
    # =====================================================

    try:

        await sync_shift_roles()

    except Exception as e:

        console_log(
            f"Schichtrollen Fehler: {e}"
        )

    # =====================================================
    # NAMETAG PANEL
    # =====================================================

    try:

        await refresh_nametag_panel()

    except Exception as e:

        console_log(
            f"Nametag-Panel Fehler: {e}"
        )

    # =====================================================
    # KENNZEICHEN PANEL
    # =====================================================

    try:

        await update_license_panel()

    except Exception as e:

        console_log(
            f"Kennzeichen-Panel Fehler: {e}"
        )

    # =====================================================
    # DEVELOPER TASK PANEL
    # =====================================================

    try:

        await refresh_task_panel()

    except Exception as e:

        console_log(
            f"Aufgaben-Panel Fehler: {e}"
        )

    # =====================================================
    # SCHICHT PANEL
    # =====================================================

    try:

        await refresh_shift_panel()

    except Exception as e:

        console_log(
            f"Schicht-Panel Fehler: {e}"
        )

    # =====================================================
    # BEWERBUNGS PANEL
    # =====================================================

    try:

        await refresh_application_panel()

    except Exception as e:

        console_log(
            f"Bewerbungs-Panel Fehler: {e}"
        )

    # =====================================================
    # EMOJI QUIZ
    # =====================================================

    try:

        await ensure_quiz_panel()

    except Exception as e:

        console_log(
            f"Emoji-Quiz Fehler: {e}"
        )

    console_log(
        "✅ Alle Panels wurden synchronisiert."
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
