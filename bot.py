import os
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID", "").strip()
LEAKS_CATEGORY_NAME = os.getenv("LEAKS_CATEGORY_NAME", "💎・LEAKS")
DAILY_CHANNEL_NAME = os.getenv("DAILY_CHANNEL_NAME", "🏠・leak-du-jour")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Les noms sont comparés sans tenir compte des majuscules, espaces et séparateurs.
TYPE_CONFIG = [
    ("MLO", ("mlo", "mapping", "maps", "map")),
    ("Script", ("script", "scripts", "resource", "ressource", "qbcore", "esx")),
    ("Véhicules", ("vehicule", "véhicule", "vehicle", "vehicles", "voiture", "cars")),
    ("Clothes", ("clothes", "cloth", "vetement", "vêtement", "tenue", "eup")),
    ("Weapon", ("weapon", "weapons", "arme", "armes")),
    ("Hub", ("hub",)),
    ("Base FiveM", ("base-fivem", "base fivem", "base")),
    ("Peds", ("peds", "ped", "personnage")),
    ("Blips", ("blips", "blip")),
]

CATEGORY_CHANNEL_HINTS = {
    "MLO": ("mapping", "mlo", "maps"),
    "Script": ("scripts", "script"),
    "Véhicules": ("vehicules", "véhicules", "vehicles", "voitures"),
    "Clothes": ("clothes", "vetements", "vêtements"),
    "Weapon": ("weapon", "armes"),
    "Hub": ("hub",),
    "Base FiveM": ("base-fivem", "base fivem"),
    "Peds": ("peds",),
    "Blips": ("blips",),
}

RULES = """📜・RÈGLEMENT OFFICIEL

Bienvenue sur notre serveur ! 🔥

Tu trouveras ici des ressources et leaks FiveM, ainsi que des services Discord gratuits : création de serveurs, développement de bots et bien plus encore.

Merci de respecter les règles suivantes.

🤝 1. RESPECT
・Le respect entre tous les membres est obligatoire.
・Les insultes abusives, le harcèlement et les discriminations sont interdits.
・Les provocations et les conflits inutiles ne sont pas tolérés.
・Le staff doit être respecté.

📦 2. RESSOURCES FIVEM
・Les ressources FiveM sont publiées uniquement par le propriétaire du serveur.
・Les membres ne peuvent pas publier leurs propres ressources sans autorisation.
・La redistribution non autorisée des ressources est interdite.
・Respectez les licences et les droits des créateurs.
・Tout fichier malveillant est strictement interdit.

🤖 3. SERVICES DISCORD GRATUITS
・La création de serveurs Discord et de bots est proposée gratuitement.
・Les demandes doivent être effectuées dans le salon prévu à cet effet.
・Décrivez clairement votre projet et vos besoins.
・Les demandes abusives, répétitives ou irréalisables pourront être refusées.
・Le délai de réalisation dépend de la disponibilité du créateur.
・La gratuité du service ne garantit pas une réalisation immédiate.
・Toute modification supplémentaire doit être discutée au préalable.
・Aucune utilisation des bots pour le spam, le raid ou le harcèlement ne sera tolérée.

🎫 4. SUPPORT & COMMANDES
・Ouvrez un ticket pour demander un service ou obtenir de l’aide.
・Une seule demande par ticket, dans la mesure du possible.
・Soyez patient et respectueux pendant le traitement de votre demande.
・Ne contactez pas le créateur en messages privés pour réclamer un service.
・Toute demande doit respecter les règles de Discord.

📢 5. PUBLICITÉ
・La publicité est autorisée uniquement dans les salons prévus à cet effet.
・Le spam et les messages répétitifs sont interdits.
・La publicité non sollicitée en messages privés est interdite.

🔐 6. SÉCURITÉ
・Le partage de mots de passe, de tokens ou de comptes volés est interdit.
・Ne transmettez jamais votre token Discord personnel.
・Les bots doivent respecter les conditions d’utilisation de Discord.
・Toute tentative de piratage, d’arnaque ou de vol de données est interdite.

⚠️ 7. SANCTIONS
En cas de non-respect du règlement, le staff peut appliquer :
・Un avertissement.
・Un mute temporaire.
・Un kick.
・Un bannissement temporaire ou définitif selon la gravité.

✅ 8. ACCEPTATION
En rejoignant et en restant sur ce serveur, tu acceptes ce règlement ainsi que les règles de Discord.

━━━━━━━━━━━━━━━━━━━━

🔥 Merci d’être parmi nous et de profiter de nos ressources et services gratuits !

👑 Le Fondateur
"""

def normalize(value: str) -> str:
    return re.sub(r"[\s\-_・]+", " ", value.casefold()).strip()

def classify_type(text: str, channel_name: str = "") -> str:
    combined = normalize(f"{channel_name} {text}")
    # Vérifier les termes les plus spécifiques avant les termes génériques.
    for kind, keywords in TYPE_CONFIG:
        if any(normalize(word) in combined for word in keywords):
            return kind
    return "Ressource FiveM"

def find_daily_channel(guild: discord.Guild):
    exact = discord.utils.find(lambda c: isinstance(c, discord.TextChannel) and c.name == DAILY_CHANNEL_NAME, guild.text_channels)
    if exact:
        return exact
    # Repli si les emojis/séparateurs du nom ne correspondent pas exactement.
    target = normalize(DAILY_CHANNEL_NAME.replace("🏠", ""))
    return discord.utils.find(
        lambda c: isinstance(c, discord.TextChannel) and normalize(c.name).endswith(target.split()[-1]),
        guild.text_channels
    )

def is_leaks_category(channel: discord.abc.GuildChannel) -> bool:
    category = getattr(channel, "category", None)
    if not category:
        return False
    return normalize(category.name) == normalize(LEAKS_CATEGORY_NAME)

def valid_http_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def build_leak_embed(title: str, description: str, kind: str, preview_url: str = "",
                     download_url: str = "", source: str = "", image_url: str = "") -> discord.Embed:
    embed = discord.Embed(
        title=f"🗺️ Nouvel ajout — {kind}",
        description=(description.strip() or "Une ressource a été ajoutée dans les leaks.")[:4000],
        color=discord.Color.from_rgb(128, 57, 165),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="📄 Contenu", value=f"# {title[:900]}", inline=False)
    if preview_url:
        embed.add_field(name="🎥 Preview", value=f"[Regarder la preview]({preview_url})", inline=False)
    if download_url:
        embed.add_field(name="💻 Download", value=f"[Télécharger la ressource]({download_url})", inline=False)
    if source:
        embed.add_field(name="📍 Source", value=source[:1024], inline=False)
    embed.add_field(name="📁 Type", value=kind, inline=True)
    embed.add_field(name="📅 Date", value=datetime.now().strftime("%d/%m/%Y"), inline=True)
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text="Leak du jour • NSK Leaks")
    return embed

async def publish_to_daily(guild: discord.Guild, embed: discord.Embed, original_message: discord.Message | None = None):
    daily = find_daily_channel(guild)
    if daily is None:
        print(f"Salon {DAILY_CHANNEL_NAME!r} introuvable dans {guild.name}.")
        return
    try:
        await daily.send(embed=embed)
    except discord.Forbidden:
        print(f"Permission manquante pour envoyer un message dans #{daily.name}.")

class LeakCategorySelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        options = []
        usable_channels = []
        for channel in guild.text_channels:
            if channel.category and normalize(channel.category.name) == normalize(LEAKS_CATEGORY_NAME):
                continue
            if channel.name == DAILY_CHANNEL_NAME:
                continue
            matched_type = None
            n = normalize(channel.name)
            for kind, hints in CATEGORY_CHANNEL_HINTS.items():
                if any(normalize(hint) in n for hint in hints):
                    matched_type = kind
                    break
            if matched_type:
                usable_channels.append((channel, matched_type))
        # Ajouter d'abord les salons trouvés sur le serveur.
        seen = set()
        for channel, kind in usable_channels:
            if channel.id in seen:
                continue
            seen.add(channel.id)
            options.append(discord.SelectOption(
                label=channel.name[:100],
                description=f"Publier une ressource de type {kind}"[:100],
                value=f"{channel.id}:{kind}"
            ))
        if not options:
            options = [
                discord.SelectOption(label="Mappings / MLO", value="0:MLO"),
                discord.SelectOption(label="Scripts", value="0:Script"),
                discord.SelectOption(label="Véhicules", value="0:Véhicules"),
                discord.SelectOption(label="Clothes", value="0:Clothes"),
                discord.SelectOption(label="Weapon", value="0:Weapon"),
                discord.SelectOption(label="Hub", value="0:Hub"),
                discord.SelectOption(label="Base FiveM", value="0:Base FiveM"),
                discord.SelectOption(label="Peds", value="0:Peds"),
                discord.SelectOption(label="Blips", value="0:Blips"),
            ]
        super().__init__(
            placeholder="Choisis le salon / type de ressource…",
            min_values=1, max_values=1, options=options[:25], custom_id="add_leak:category"
        )

    async def callback(self, interaction: discord.Interaction):
        channel_id, kind = self.values[0].split(":", 1)
        target = self.guild.get_channel(int(channel_id)) if channel_id != "0" else None
        if channel_id != "0" and not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message("Je ne trouve plus ce salon. Relance `/add_leak`.", ephemeral=True)
        await interaction.response.send_modal(LeakDetailsModal(kind=kind, target_channel=target, guild=self.guild))

class LeakCategoryView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(LeakCategorySelect(guild))

class LeakDetailsModal(discord.ui.Modal, title="Personnaliser le leak"):
    title_input = discord.ui.TextInput(label="Titre de la ressource", placeholder="Ex. Fleeca Bank Tower", max_length=100)
    description_input = discord.ui.TextInput(
        label="Description", placeholder="Décris la ressource…",
        style=discord.TextStyle.paragraph, required=True, max_length=1000
    )
    preview_input = discord.ui.TextInput(label="Lien de preview (facultatif)", required=False, max_length=300)
    download_input = discord.ui.TextInput(label="Lien de téléchargement (facultatif)", required=False, max_length=300)
    source_input = discord.ui.TextInput(label="Source (facultatif)", required=False, max_length=100)

    def __init__(self, kind: str, target_channel: discord.TextChannel | None, guild: discord.Guild):
        super().__init__(timeout=300)
        self.kind = kind
        self.target_channel = target_channel
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        preview = str(self.preview_input.value).strip()
        download = str(self.download_input.value).strip()
        if not valid_http_url(preview) or not valid_http_url(download):
            return await interaction.response.send_message("Les liens doivent commencer par `https://` ou `http://`.", ephemeral=True)
        title = str(self.title_input.value).strip()
        description = str(self.description_input.value).strip()
        source = str(self.source_input.value).strip()
        embed = build_leak_embed(title, description, self.kind, preview, download, source)
        target = self.target_channel or find_daily_channel(self.guild)
        if target is None:
            return await interaction.response.send_message(
                "Je ne trouve pas le salon de destination. Vérifie les noms des salons sur le serveur.",
                ephemeral=True
            )
        try:
            await target.send(embed=embed)
            # Si la ressource est publiée dans un salon de catégorie, copie aussi l'annonce au salon du jour.
            daily = find_daily_channel(self.guild)
            if daily and daily.id != target.id:
                await daily.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Le leak **{title}** a été publié dans {target.mention}"
                + (f" et dans {daily.mention}." if daily and daily.id != target.id else "."),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission d'envoyer des messages/embeds dans le salon choisi.",
                ephemeral=True
            )

@bot.event
async def on_ready():
    try:
        if GUILD_ID.isdigit():
            guild_obj = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Connecté comme {bot.user} — {len(synced)} commandes synchronisées sur le serveur {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Connecté comme {bot.user} — {len(synced)} commandes globales synchronisées.")
    except discord.DiscordException as exc:
        print(f"Erreur de synchronisation : {exc}")

@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    """Envoie le formulaire dans tout nouveau salon dont le nom concerne une création de bot Discord."""
    if not isinstance(channel, discord.TextChannel):
        return

    def plain_name(value: str) -> str:
        value = unicodedata.normalize("NFKD", value.casefold())
        value = "".join(char for char in value if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    channel_name = plain_name(channel.name)

    # Formulaire de plainte : déclenché pour les nouveaux tickets dont le nom contient "plainte".
    if "plainte" in channel_name or "signalement" in channel_name:
        complaint = discord.Embed(
            title="⚠️ Formulaire de Signalement / Plainte",
            description=(
                "Merci de remplir ce formulaire avec un maximum de preuves. "
                "Toute fausse accusation ou tout abus du système de signalement pourra entraîner une sanction.\n\n"
                "**1. Informations sur la victime et le mis en cause**\n"
                "• Votre pseudo Discord :\n"
                "• Pseudo de la personne signalée :\n"
                "• ID Discord de la personne signalée (si possible) :\n"
                "  *(Clic droit sur son profil → Copier l’identifiant.)*\n\n"
                "**2. Motif du signalement**\n"
                "• Quel est le motif principal de la plainte ?\n"
                "→ Réponse :\n\n"
                "**3. Description des faits**\n"
                "• Où les faits se sont-ils déroulés ?\n"
                "☐ Dans un salon public (nom du salon : ______)\n"
                "☐ En messages privés (MP)\n"
                "☐ Dans un salon vocal\n"
                "• Date et heure approximatives des faits :\n"
                "• Explication détaillée, dans l’ordre chronologique :\n"
                "→ Réponse :\n\n"
                "**4. Preuves (obligatoires)**\n"
                "⚠️ Sans preuve tangible (captures d’écran, enregistrements ou éléments vérifiables), "
                "aucune sanction ne pourra être appliquée.\n"
                "• Ajoutez les preuves dans ce ticket et expliquez ce qu’elles démontrent.\n\n"
                "✍️ **Répondez directement dans ce ticket en copiant les questions et en complétant vos réponses.**"
            ),
            color=discord.Color.orange(),
        )
        complaint.set_footer(text="NSK Leaks • Signalement / Plainte")
        try:
            await channel.send(embed=complaint)
        except discord.Forbidden:
            print(f"Impossible d'envoyer le formulaire de plainte dans #{channel.name} : permissions manquantes.")
        except discord.DiscordException as exc:
            print(f"Erreur d'envoi du formulaire de plainte dans #{channel.name} : {exc}")
        return

    # Formulaire de partenariat : déclenché pour les nouveaux tickets contenant "partenariat".
    if "partenariat" in channel_name or "partnership" in channel_name:
        partnership = discord.Embed(
            title="🤝 DEMANDE DE PARTENARIAT",
            description=(
                "Merci de l'intérêt que vous portez à notre serveur !\n"
                "Afin que l'équipe puisse étudier votre demande rapidement, merci de répondre aux questions ci-dessous dans ce ticket.\n\n"
                "📌 **1. NOM DU SERVEUR**\n"
                "└── Quel est le nom de votre serveur Discord ?\n\n"
                "📊 **2. STATISTIQUES**\n"
                "└── Combien de membres comptez-vous et quelle est votre activité moyenne (membres actifs/connectés) ?\n\n"
                "🔗 **3. LIEN D'INVITATION**\n"
                "└── Quel est le lien d'invitation permanent de votre serveur ?\n\n"
                "📜 **4. TYPE DE PARTENARIAT**\n"
                "└── Que proposez-vous (échange de salons, pub, événement commun, rôle dédié...) ?\n\n"
                "📍 **5. VISIBILITÉ**\n"
                "└── Où sera affichée notre publicité chez vous (salon dédié, mention, etc.) ?\n\n"
                "⚠️ Rappel : Nous nous réservons le droit de refuser tout serveur ne respectant pas les conditions de la communauté.\n\n"
                "✍️ **Répondez directement dans ce ticket en recopiant les questions et en complétant vos réponses.**"
            ),
            color=discord.Color.from_rgb(46, 204, 113),
        )
        partnership.set_footer(text="NSK Leaks • Demande de partenariat")
        try:
            await channel.send(embed=partnership)
        except discord.Forbidden:
            print(f"Impossible d'envoyer le formulaire de partenariat dans #{channel.name} : permissions manquantes.")
        except discord.DiscordException as exc:
            print(f"Erreur d'envoi du formulaire de partenariat dans #{channel.name} : {exc}")
        return

    if "creation bot discord" not in channel_name:
        return

    form = discord.Embed(
        title="🤖 Formulaire de Demande de Bot Discord",
        description="""Merci de remplir ce formulaire avec le plus de précisions possible afin que nous puissions étudier votre projet et vous proposer une estimation du délai.

**1. Informations générales**
• Nom / pseudo Discord :
• Nom du serveur Discord concerné :
• Nom souhaité pour le bot :

**2. Type et objectif du bot**
• Catégorie principale (choisir une ou plusieurs options) :
☐ Modération / Anti-raid
☐ Économie / Jeux / Niveaux (XP)
☐ Musique
☐ Intégration API externe (Twitch, YouTube, site web…)
☐ Système de tickets / support
☐ Autre (précisez) :
• Description globale du projet et besoin principal :

**3. Fonctionnalités détaillées**
• Commandes souhaitées (nom, rôle et personnes autorisées) :
Exemple : `/ban @user [raison]` — bannit un membre (administrateur uniquement).
Exemple : `/profile` — affiche la fiche du joueur.
• Systèmes automatiques / événements souhaités :
Exemple : message de bienvenue, rôles automatiques, logs, notifications.

**4. Aspects techniques et hébergement**
• Langage souhaité : ☐ Python (discord.py) ☐ JavaScript / TypeScript (discord.js) ☐ Indifférent
• Hébergement : ☐ Hébergement 24/7 par le staff ☐ Mon hébergeur / VPS ☐ Aide à l’installation

**5. Délais et budget (facultatif)**
• Date de livraison souhaitée :
• Budget éventuel / précisions :

✍️ **Réponds directement dans ce ticket en copiant les questions et en complétant tes réponses.**""",
        color=discord.Color.from_rgb(128, 57, 165),
    )
    form.set_footer(text="NSK Leaks • Demande de création de bot")
    try:
        await channel.send(embed=form)
    except discord.Forbidden:
        print(f"Impossible d'envoyer le formulaire dans #{channel.name} : permissions manquantes.")
    except discord.DiscordException as exc:
        print(f"Erreur d'envoi du formulaire dans #{channel.name} : {exc}")

@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)
    if message.author.bot or not message.guild or not isinstance(message.channel, discord.TextChannel):
        return
    if not is_leaks_category(message.channel):
        return

    content = message.content.strip()
    if not content and not message.attachments and not message.embeds:
        return

    # Récupération de quelques champs fréquents dans les posts de leaks.
    def extract(pattern: str) -> str:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ""

    title = extract(r"(?:titre|nom|contenu)\s*:\s*(.+)")
    preview = extract(r"(?:preview|préview)\s*:\s*(https?://\S+)")
    download = extract(r"(?:download|téléchargement|lien)\s*:\s*(https?://\S+)")
    description = extract(r"(?:description)\s*:\s*(.+)")
    if not title:
        # Le nom du fichier joint ou la première ligne sert de titre.
        title = message.attachments[0].filename if message.attachments else (content.splitlines()[0][:100] if content else "Nouvelle ressource")
    if not description:
        description = content[:3500] if content else "Une nouvelle ressource a été publiée dans la catégorie leaks."
    if not download and message.attachments:
        download = message.attachments[0].url
    image_url = ""
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_url = attachment.url
            break
    kind = classify_type(f"{title}\n{content}", message.channel.name)
    embed = build_leak_embed(title, description, kind, preview, download, f"#{message.channel.name}", image_url)
    await publish_to_daily(message.guild, embed, message)

@bot.tree.command(name="rules", description="Publier le règlement officiel du serveur")
async def rules(interaction: discord.Interaction):
    # Discord limite la description d'un embed à 4096 caractères; le règlement tient dans cette limite.
    embed = discord.Embed(title="📜・RÈGLEMENT OFFICIEL", description=RULES[:4000], color=discord.Color.blurple())
    embed.set_footer(text=f"{interaction.guild.name if interaction.guild else 'NSK Leaks'} • Merci de respecter le règlement")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_leak", description="Créer et personnaliser une annonce de leak")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def add_leak(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
    await interaction.response.send_message(
        "📦 **Ajouter un leak**\nChoisis le type de ressource / salon à utiliser. Tu pourras ensuite personnaliser le titre, la description et les liens.",
        view=LeakCategoryView(interaction.guild),
        ephemeral=True
    )

@bot.tree.command(name="ban", description="Bannir un membre du serveur")
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(membre="Membre à bannir", raison="Raison du bannissement")
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison précisée"):
    if membre.id in (interaction.user.id, bot.user.id):
        return await interaction.response.send_message("Cette action n'est pas autorisée sur ce membre.", ephemeral=True)
    await membre.ban(reason=f"{raison} | Par {interaction.user} ({interaction.user.id})")
    await interaction.response.send_message(f"🔨 **{membre}** a été banni. Raison : {raison}")

@bot.tree.command(name="kick", description="Expulser un membre du serveur")
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(membre="Membre à expulser", raison="Raison de l'expulsion")
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison précisée"):
    if membre.id in (interaction.user.id, bot.user.id):
        return await interaction.response.send_message("Cette action n'est pas autorisée sur ce membre.", ephemeral=True)
    await membre.kick(reason=f"{raison} | Par {interaction.user} ({interaction.user.id})")
    await interaction.response.send_message(f"👢 **{membre}** a été expulsé. Raison : {raison}")

@bot.tree.command(name="mute", description="Rendre un membre muet temporairement")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membre="Membre à rendre muet", minutes="Durée en minutes (1 à 40320)", raison="Raison du mute")
async def mute(interaction: discord.Interaction, membre: discord.Member, minutes: app_commands.Range[int, 1, 40320], raison: str = "Aucune raison précisée"):
    if membre.id in (interaction.user.id, bot.user.id):
        return await interaction.response.send_message("Cette action n'est pas autorisée sur ce membre.", ephemeral=True)
    from datetime import timedelta
    await membre.timeout(timedelta(minutes=minutes), reason=f"{raison} | Par {interaction.user} ({interaction.user.id})")
    await interaction.response.send_message(f"🔇 **{membre}** est muet pendant **{minutes} minute(s)**. Raison : {raison}")

@bot.tree.command(name="clear", description="Supprimer un nombre de messages dans ce salon")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(nombre="Nombre de messages à supprimer (1 à 100)")
async def clear(interaction: discord.Interaction, nombre: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
        return await interaction.response.send_message("Cette commande fonctionne uniquement dans un salon textuel.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"🧹 **{len(deleted)}** message(s) supprimé(s).", ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ Tu n'as pas les permissions nécessaires pour utiliser cette commande."
    elif isinstance(error, app_commands.BotMissingPermissions):
        message = "❌ Il me manque des permissions pour effectuer cette action."
    else:
        print(f"Erreur commande : {repr(error)}")
        message = "❌ Une erreur est survenue. Vérifie mes permissions, les noms des salons et la hiérarchie des rôles."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.DiscordException:
        pass

if not TOKEN:
    raise RuntimeError("Le token est manquant. Ajoute DISCORD_TOKEN dans le fichier .env.")

bot.run(TOKEN)
