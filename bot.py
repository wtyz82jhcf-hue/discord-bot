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

SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200

NUMBER_GAME_CHANNEL_ID = 1556308645942136872

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

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
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        if isinstance(loaded, dict):
            data.update(loaded)

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
        print(f"Fehler beim Speichern: {e}")


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_channel(channel_id):
    return bot.get_channel(channel_id)


def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def make_embed(
    title,
    description="",
    color=discord.Color.blue()
):
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


def member_info(user_id):
    """
    Gibt Ping, Name und User-ID zurück.
    """

    user = bot.get_user(int(user_id))

    if user:
        return (
            f"{user.mention}\n"
            f"**Name:** {user}\n"
            f"**User-ID:** `{user.id}`"
        )

    return (
        f"<@{user_id}>\n"
        f"**User-ID:** `{user_id}`"
    )


# =========================================================
# ABWECHSELNDER STATUS
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
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.end_headers()

        self.wfile.write(
            b"Bot is running"
        )

    def log_message(self, format, *args):
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
        f"Webserver gestartet auf Port {port}"
    )


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(
    ui.Modal,
    title="🏷️ Nametag setzen"
):

    nametag = ui.TextInput(
        label="Nametag",
        placeholder="Dein Nametag",
        max_length=32
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            NAMETAG_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )

            return

        new_nickname = (
            f"RLP | {self.nametag.value}"
        )

        try:

            await interaction.user.edit(
                nick=new_nickname
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf **{new_nickname}** gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann deinen Nickname nicht ändern.",
                ephemeral=True
            )


class NametagView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Nametag setzen",
        style=discord.ButtonStyle.primary,
        emoji="🏷️",
        custom_id="nametag_set"
    )
    async def set_nametag(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            NametagModal()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(
    ui.Modal,
    title="🚗 Kennzeichen setzen"
):

    plate = ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. GM-RL 123",
        max_length=20
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        user_id = str(
            interaction.user.id
        )

        plate = self.plate.value.upper()

        data["license_plates"][user_id] = plate

        save_data()

        await interaction.response.send_message(
            f"🚗 Dein Kennzeichen wurde auf **{plate}** gesetzt.",
            ephemeral=True
        )


class LicensePlateView(ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Kennzeichen setzen",
        style=discord.ButtonStyle.primary,
        emoji="🚗",
        custom_id="plate_set"
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
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="plate_remove"
    )
    async def remove_plate(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        user_id = str(
            interaction.user.id
        )

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
# ENTWICKLER AUFGABEN
# =========================================================

class DeveloperTaskModal(
    ui.Modal,
    title="🛠️ Neue Entwickleraufgabe"
):

    task = ui.TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        task_id = str(
            random.randint(
                100000,
                999999
            )
        )

        # Sicherstellen, dass ID nicht doppelt ist
        while task_id in data["tasks"]:

            task_id = str(
                random.randint(
                    100000,
                    999999
                )
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
                "❌ Der Entwickler-Aufgaben-Channel wurde nicht gefunden.",
                ephemeral=True
            )

            return

        embed = create_task_embed(
            task_id
        )

        await channel.send(
            embed=embed,
            view=DeveloperTaskView(
                task_id
            )
        )

        await interaction.response.send_message(
            "✅ Die Entwickleraufgabe wurde erstellt.",
            ephemeral=True
        )


def create_task_embed(task_id):

    task = data["tasks"].get(
        task_id
    )

    if not task:

        return make_embed(
            "❌ Aufgabe nicht gefunden",
            "Diese Aufgabe existiert nicht mehr.",
            discord.Color.red()
        )

    creator_id = task["creator"]
    taken_by = task.get("taken_by")
    done_by = task.get("done_by")

    if done_by:

        status = "🟢 **Erledigt**"

    elif taken_by:

        status = "🟡 **In Bearbeitung**"

    else:

        status = "🔵 **Offen**"

    embed = make_embed(
        "🛠️ Entwickleraufgabe",
        "",
        discord.Color.blue()
    )

    embed.add_field(
        name="📋 Aufgabe",
        value=task["task"],
        inline=False
    )

    embed.add_field(
        name="👤 Erstellt von",
        value=member_info(
            creator_id
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=status,
        inline=False
    )

    if taken_by:

        embed.add_field(
            name="🙋 Übernommen von",
            value=member_info(
                taken_by
            ),
            inline=False
        )

    else:

        embed.add_field(
            name="🙋 Übernommen von",
            value="Niemand",
            inline=False
        )

    if done_by:

        embed.add_field(
            name="✅ Erledigt von",
            value=member_info(
                done_by
            ),
            inline=False
        )

    else:

        embed.add_field(
            name="✅ Erledigt von",
            value="Noch nicht erledigt",
            inline=False
        )

    embed.set_footer(
        text=f"Aufgaben-ID: {task_id}"
    )

    return embed


class DeveloperTaskPanelView(
    ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="developer_task_create"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(
    ui.View
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

        # Persistente Custom IDs
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
        interaction: discord.Interaction,
        button: ui.Button
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
                f"⚠️ Diese Aufgabe wurde bereits von <@{task['taken_by']}> übernommen.",
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

    @ui.button(
        label="Erledigt",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def done_task(
        self,
        interaction: discord.Interaction,
        button: ui.Button
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
                "⚠️ Diese Aufgabe wurde bereits erledigt.",
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
            view=DeveloperTaskView(
                self.task_id
            )
        )

    @ui.button(
        label="Löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def delete_task(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen Aufgaben löschen.",
                ephemeral=True
            )

            return

        if self.task_id in data["tasks"]:

            del data["tasks"][
                self.task_id
            ]

            save_data()

        await interaction.response.edit_message(
            embed=make_embed(
                "🗑️ Aufgabe gelöscht",
                f"Die Aufgabe `{self.task_id}` wurde von "
                f"{interaction.user.mention} gelöscht.",
                discord.Color.red()
            ),
            view=None
        )


# =========================================================
# ENTWICKLERSCHICHT
# =========================================================

def get_active_shifts():

    result = set()

    for user_id in data.get(
        "active_shifts",
        []
    ):

        try:

            result.add(
                int(user_id)
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    return result


def save_active_shifts(
    active_shifts
):

    data["active_shifts"] = list(
        active_shifts
    )

    save_data()


def create_shift_embed():

    active_shifts = get_active_shifts()

    embed = make_embed(
        "🛠️ Entwicklerschicht",
        "Verwalte hier deine Entwicklerschicht.",
        discord.Color.green()
    )

    if active_shifts:

        users = []

        for user_id in active_shifts:

            users.append(
                f"• <@{user_id}>"
            )

        embed.add_field(
            name="🟢 Aktive Entwickler",
            value="\n".join(users),
            inline=False
        )

    else:

        embed.add_field(
            name="🟢 Aktive Entwickler",
            value="Niemand ist aktuell in einer Schicht.",
            inline=False
        )

    return embed


async def send_shift_log(
    message
):

    channel = get_channel(
        SHIFT_LOG_CHANNEL_ID
    )

    if channel:

        try:

            await channel.send(
                embed=make_embed(
                    "🕐 Schichtprotokoll",
                    message,
                    discord.Color.blue()
                )
            )

        except Exception as e:

            print(
                f"Schicht-Log-Fehler: {e}"
            )


class DeveloperShiftView(
    ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für Entwicklerschichten.",
                ephemeral=True
            )

            return

        active_shifts = get_active_shifts()

        if interaction.user.id in active_shifts:

            await interaction.response.send_message(
                "⚠️ Du bist bereits in einer Schicht.",
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

        await send_shift_log(
            f"🟢 {interaction.user.mention}\n"
            f"**Name:** {interaction.user}\n"
            f"**User-ID:** `{interaction.user.id}`\n\n"
            f"hat seine Entwicklerschicht gestartet."
        )

        await interaction.response.edit_message(
            embed=create_shift_embed(),
            view=DeveloperShiftView()
        )

    @ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="shift_stop"
    )
    async def stop_shift(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        active_shifts = get_active_shifts()

        if interaction.user.id not in active_shifts:

            await interaction.response.send_message(
                "⚠️ Du bist aktuell in keiner Schicht.",
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

        await send_shift_log(
            f"🔴 {interaction.user.mention}\n"
            f"**Name:** {interaction.user}\n"
            f"**User-ID:** `{interaction.user.id}`\n\n"
            f"hat seine Entwicklerschicht beendet."
        )

        await interaction.response.edit_message(
            embed=create_shift_embed(),
            view=DeveloperShiftView()
        )


# =========================================================
# ZAHLENSPIEL
# =========================================================

class NumberGuessModal(
    ui.Modal,
    title="🔢 Zahl erraten"
):

    guess = ui.TextInput(
        label="Deine Zahl",
        placeholder="Eine Zahl eingeben",
        max_length=19
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel_id = str(
            interaction.channel.id
        )

        if channel_id not in data["number_game"]:

            await interaction.response.send_message(
                "❌ Hier läuft gerade kein Zahlenspiel.",
                ephemeral=True
            )

            return

        try:

            number = int(
                self.guess.value
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ Bitte gib eine gültige Zahl ein.",
                ephemeral=True
            )

            return

        if number < 1 or number > NUMBER_GAME_MAX:

            await interaction.response.send_message(
                f"❌ Die Zahl muss zwischen **1** und **{NUMBER_GAME_MAX:,}** liegen.",
                ephemeral=True
            )

            return

        target = data["number_game"][
            channel_id
        ]

        if number == target:

            await interaction.response.send_message(
                embed=make_embed(
                    "🎉 Richtige Zahl!",
                    f"{interaction.user.mention} hat die Zahl erraten!",
                    discord.Color.green()
                )
            )

            data["number_game"][
                channel_id
            ] = random.randint(
                1,
                NUMBER_GAME_MAX
            )

            save_data()

        elif number < target:

            await interaction.response.send_message(
                "📈 Die gesuchte Zahl ist **größer**.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "📉 Die gesuchte Zahl ist **kleiner**.",
                ephemeral=True
            )


class NumberGameView(
    ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Zahl erraten",
        style=discord.ButtonStyle.primary,
        emoji="🔢",
        custom_id="number_guess"
    )
    async def guess_number(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            NumberGuessModal()
        )

    @ui.button(
        label="Neue Zahl",
        style=discord.ButtonStyle.success,
        emoji="🔄",
        custom_id="number_new"
    )
    async def new_number(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        data["number_game"][
            str(interaction.channel.id)
        ] = random.randint(
            1,
            NUMBER_GAME_MAX
        )

        save_data()

        await interaction.response.send_message(
            embed=make_embed(
                "🔄 Neue Zahl",
                "Eine neue Zahl wurde ausgewählt.",
                discord.Color.green()
            ),
            ephemeral=True
        )


# =========================================================
# COMMUNITY
# =========================================================

class FeedbackModal(
    ui.Modal,
    title="💬 Feedback"
):

    feedback = ui.TextInput(
        label="Dein Feedback",
        placeholder="Was möchtest du uns mitteilen?",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel:

            embed = make_embed(
                "💬 Neues Community-Feedback",
                self.feedback.value,
                discord.Color.blue()
            )

            embed.add_field(
                name="👤 Von",
                value=(
                    f"{interaction.user.mention}\n"
                    f"**Name:** {interaction.user}\n"
                    f"**User-ID:** `{interaction.user.id}`"
                ),
                inline=False
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            embed=make_embed(
                "💙 Danke!",
                "Danke für dein Feedback!",
                discord.Color.green()
            ),
            ephemeral=True
        )


class SuggestionModal(
    ui.Modal,
    title="💡 Vorschlag"
):

    suggestion = ui.TextInput(
        label="Dein Vorschlag",
        placeholder="Was können wir verbessern?",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel:

            embed = make_embed(
                "💡 Neuer Community-Vorschlag",
                self.suggestion.value,
                discord.Color.gold()
            )

            embed.add_field(
                name="👤 Von",
                value=(
                    f"{interaction.user.mention}\n"
                    f"**Name:** {interaction.user}\n"
                    f"**User-ID:** `{interaction.user.id}`"
                ),
                inline=False
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            embed=make_embed(
                "💙 Danke!",
                "Danke für deinen Vorschlag!",
                discord.Color.green()
            ),
            ephemeral=True
        )


class CommunityView(
    ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Feedback",
        style=discord.ButtonStyle.primary,
        emoji="💬",
        custom_id="community_feedback"
    )
    async def feedback(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            FeedbackModal()
        )

    @ui.button(
        label="Vorschlag",
        style=discord.ButtonStyle.success,
        emoji="💡",
        custom_id="community_suggestion"
    )
    async def suggestion(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            SuggestionModal()
        )


class CommunityPanelView(
    ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Feedback senden",
        style=discord.ButtonStyle.primary,
        emoji="💬",
        custom_id="community_panel_feedback"
    )
    async def feedback(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            FeedbackModal()
        )

    @ui.button(
        label="Vorschlag senden",
        style=discord.ButtonStyle.success,
        emoji="💡",
        custom_id="community_panel_suggestion"
    )
    async def suggestion(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        await interaction.response.send_modal(
            SuggestionModal()
        )


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def nametag(ctx):

    embed = make_embed(
        "🏷️ Nametag-System",
        "Klicke auf **Nametag setzen**, um deinen Nametag zu ändern.",
        discord.Color.blue()
    )

    await ctx.send(
        embed=embed,
        view=NametagView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def kennzeichen(ctx):

    embed = make_embed(
        "🚗 Kennzeichen-System",
        "Hier kannst du dein Kennzeichen setzen oder entfernen.",
        discord.Color.blue()
    )

    await ctx.send(
        embed=embed,
        view=LicensePlateView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def entwickler(ctx):

    embed = make_embed(
        "🛠️ Entwickler-System",
        "Erstelle hier neue Aufgaben für das Entwicklerteam.",
        discord.Color.blue()
    )

    embed.add_field(
        name="📌 Hinweis",
        value="Neue Aufgaben werden automatisch im Entwickler-Aufgaben-Channel erstellt.",
        inline=False
    )

    await ctx.send(
        embed=embed,
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

    data["number_game"][
        str(ctx.channel.id)
    ] = random.randint(
        1,
        NUMBER_GAME_MAX
    )

    save_data()

    embed = make_embed(
        "🔢 Zahlenspiel",
        f"Errate eine Zahl zwischen **1** und **{NUMBER_GAME_MAX:,}**.",
        discord.Color.purple()
    )

    embed.add_field(
        name="🎯 Ziel",
        value="Finde die geheime Zahl!",
        inline=False
    )

    await ctx.send(
        embed=embed,
        view=NumberGameView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def community(ctx):

    embed = make_embed(
        "💙 Community",
        "Deine Meinung ist uns wichtig!",
        discord.Color.blue()
    )

    embed.add_field(
        name="💬 Feedback",
        value="Teile uns deine Meinung mit.",
        inline=True
    )

    embed.add_field(
        name="💡 Vorschlag",
        value="Hast du eine Idee? Schick sie uns!",
        inline=True
    )

    await ctx.send(
        embed=embed,
        view=CommunityView()
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def communitypanel(ctx):

    embed = make_embed(
        "🌟 Community Panel",
        "Hier kannst du direkt Feedback und Vorschläge an das Team senden.",
        discord.Color.blue()
    )

    embed.add_field(
        name="💬 Feedback",
        value="Wir freuen uns über deine Meinung.",
        inline=True
    )

    embed.add_field(
        name="💡 Vorschlag",
        value="Verbesserungsidee? Immer her damit!",
        inline=True
    )

    await ctx.send(
        embed=embed,
        view=CommunityPanelView()
    )


@bot.command()
async def helpme(ctx):

    embed = make_embed(
        "📚 RLP Bot Hilfe",
        "Hier findest du die verfügbaren Befehle.",
        discord.Color.blue()
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
        name="🕐 Schicht",
        value="`?schicht`",
        inline=False
    )

    embed.add_field(
        name="🔢 Zahlenspiel",
        value="`?zahlenspiel`",
        inline=False
    )

    embed.add_field(
        name="💙 Community",
        value="`?community`",
        inline=False
    )

    embed.add_field(
        name="🌟 Community Panel",
        value="`?communitypanel`",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# FEHLERBEHANDLUNG
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

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            embed=make_embed(
                "❌ Keine Berechtigung",
                "Du benötigst Administrator-Rechte für diesen Befehl.",
                discord.Color.red()
            )
        )

        return

    print(
        f"Command-Fehler: {error}"
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
        CommunityView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    # Bereits vorhandene Aufgaben wieder registrieren
    for task_id in list(
        data["tasks"].keys()
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


# =========================================================
# START
# =========================================================

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

        except Exception as e:

            print(
                f"FEHLER: {e}"
            )
