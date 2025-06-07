import discord
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import get
from datetime import datetime, timedelta

# Intents et configuration du bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionnaire pour stocker les bannissements
ban_list = {}

ADMIN_IDS = []

@bot.event
async def on_ready():
    print(f"Bot prêt en tant que {bot.user}")
    await bot.tree.sync()

@bot.event
async def on_guild_join(guild: discord.Guild):
    admin_members = [guild.get_member(admin_id) for admin_id in ADMIN_IDS]
    admin_present = any(admin for admin in admin_members if admin is not None)

    embed = discord.Embed(
        title="Ajout dans un serveur",
        description=f"Le bot a été ajouté au serveur : **{guild.name}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="ID du serveur", value=guild.id, inline=False)
    embed.add_field(name="Propriétaire", value=guild.owner.mention if guild.owner else "Inconnu", inline=False)
    embed.add_field(name="Nombre de membres", value=guild.member_count, inline=False)
    embed.timestamp = datetime.utcnow()

    # Envoi du message aux admins configurés
    for admin_id in ADMIN_IDS:
        try:
            admin_user = bot.get_user(admin_id)
            if admin_user:
                await admin_user.send(embed=embed)
        except Exception as e:
            print(f"Impossible d'envoyer un MP à {admin_id}: {e}")

    # Vérifie si les admins sont présents sur le serveur
    if not admin_present:
        await guild.leave()
        print(f"Le bot a quitté le serveur {guild.name} car aucun administrateur n'était présent.")

@bot.event
async def on_guild_remove(guild: discord.Guild):
    embed = discord.Embed(
        title="Bot retiré d'un serveur",
        description=f"Le bot a quitté le serveur : **{guild.name}**",
        color=discord.Color.red()
    )
    embed.add_field(name="ID du serveur", value=guild.id, inline=False)
    embed.add_field(name="Nombre de membres", value=guild.member_count, inline=False)
    embed.timestamp = datetime.utcnow()

    # Envoi du message aux admins configurés
    for admin_id in ADMIN_IDS:
        try:
            admin_user = bot.get_user(admin_id)
            if admin_user:
                await admin_user.send(embed=embed)
        except Exception as e:
            print(f"Impossible d'envoyer un MP à {admin_id}: {e}")

# Commande /ban
@bot.tree.command(name="ban", description="Bannir un membre avec une raison facultative")
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Vous n'avez pas la permission de bannir des membres.", ephemeral=True)
        return

    await membre.ban(reason=raison)
    ban_list[membre.id] = {
        "nom": str(membre),
        "raison": raison,
        "par": str(interaction.user),
        "date": datetime.utcnow()
    }

    embed = discord.Embed(title="Membre banni", color=discord.Color.red())
    embed.add_field(name="Membre", value=f"{membre.mention} ({membre.id})", inline=False)
    embed.add_field(name="Raison", value=raison, inline=False)
    embed.add_field(name="Par", value=interaction.user.mention, inline=False)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /unban
@bot.tree.command(name="unban", description="Débannir un utilisateur par ID")
async def unban(interaction: discord.Interaction, utilisateur_id: int):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Vous n'avez pas la permission de débannir des membres.", ephemeral=True)
        return

    utilisateur = await bot.fetch_user(utilisateur_id)
    await interaction.guild.unban(utilisateur)
    ban_list.pop(utilisateur_id, None)

    embed = discord.Embed(title="Membre débanni", color=discord.Color.green())
    embed.add_field(name="Utilisateur", value=f"{utilisateur} ({utilisateur_id})", inline=False)
    embed.add_field(name="Par", value=interaction.user.mention, inline=False)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /ban-list
@bot.tree.command(name="ban-list", description="Afficher la liste des utilisateurs bannis")
async def ban_list_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Vous n'avez pas la permission de voir la liste des bannis.", ephemeral=True)
        return

    if not ban_list:
        await interaction.response.send_message("La liste des bannis est vide.", ephemeral=True)
        return

    embed = discord.Embed(title="Liste des utilisateurs bannis", color=discord.Color.orange())

    for user_id, details in ban_list.items():
        embed.add_field(
            name=f"Utilisateur: {details['nom']} ({user_id})",
            value=f"**Raison**: {details['raison']}\n**Par**: {details['par']}\n**Date**: {details['date'].strftime('%Y-%m-%d %H:%M:%S')} UTC",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# Commande /kick
@bot.tree.command(name="kick", description="Expulser un membre avec une raison facultative")
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Vous n'avez pas la permission d'expulser des membres.", ephemeral=True)
        return

    await membre.kick(reason=raison)

    embed = discord.Embed(title="Membre expulsé", color=discord.Color.orange())
    embed.add_field(name="Membre", value=f"{membre.mention} ({membre.id})", inline=False)
    embed.add_field(name="Raison", value=raison, inline=False)
    embed.add_field(name="Par", value=interaction.user.mention, inline=False)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /timeout
@bot.tree.command(name="timeout", description="Mettre un membre en timeout pour une durée spécifiée")
async def timeout(interaction: discord.Interaction, membre: discord.Member, temps: str, raison: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Vous n'avez pas la permission de mettre des membres en timeout.", ephemeral=True)
        return

    # Conversion du temps
    try:
        duree = 0
        if "d" in temps:
            duree += int(temps.replace("d", "")) * 86400
        elif "h" in temps:
            duree += int(temps.replace("h", "")) * 3600
        elif "m" in temps:
            duree += int(temps.replace("m", "")) * 60
        else:
            raise ValueError("Format de temps invalide.")

        timeout_until = datetime.utcnow() + timedelta(seconds=duree)
    except ValueError:
        await interaction.response.send_message("Le format du temps est invalide. Utilisez par exemple 1d, 5h, ou 30m.", ephemeral=True)
        return

    await membre.timeout(until=timeout_until, reason=raison)

    embed = discord.Embed(title="Membre en timeout", color=discord.Color.blue())
    embed.add_field(name="Membre", value=f"{membre.mention} ({membre.id})", inline=False)
    embed.add_field(name="Durée", value=temps, inline=False)
    embed.add_field(name="Raison", value=raison, inline=False)
    embed.add_field(name="Par", value=interaction.user.mention, inline=False)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /unmute
@bot.tree.command(name="unmute", description="Retirer le timeout d'un membre")
async def unmute(interaction: discord.Interaction, membre: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Vous n'avez pas la permission de retirer le timeout des membres.", ephemeral=True)
        return

    await membre.timeout(until=None)

    embed = discord.Embed(title="Timeout retiré", color=discord.Color.green())
    embed.add_field(name="Membre", value=f"{membre.mention} ({membre.id})", inline=False)
    embed.add_field(name="Par", value=interaction.user.mention, inline=False)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /embed
@bot.tree.command(name="embed", description="Envoyer un embed personnalisé dans un salon")
async def embed(interaction: discord.Interaction, salon: discord.TextChannel, titre: str, message: str, couleur: str = "blue", footer: str = "", image: str = ""):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    # Conversion de la couleur
    try:
        couleur_embed = getattr(discord.Color, couleur)()
    except AttributeError:
        couleur_embed = discord.Color.blue()

    embed = discord.Embed(title=titre, description=message, color=couleur_embed)
    if footer:
        embed.set_footer(text=footer)
    if image:
        embed.set_image(url=image)

    await salon.send(embed=embed)
    await interaction.response.send_message(f"Embed envoyé dans {salon.mention}", ephemeral=True)

# Commande /say
@bot.tree.command(name="say", description="Envoyer un message dans un salon")
async def say(interaction: discord.Interaction, salon: discord.TextChannel, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    await salon.send(message)
    await interaction.response.send_message(f"Message envoyé dans {salon.mention}", ephemeral=True)

# Commande /lock
@bot.tree.command(name="lock", description="Verrouille un salon pour empêcher les membres d'envoyer des messages")
async def lock(interaction: discord.Interaction, salon: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    overwrite = salon.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message(f"Le salon {salon.mention} a été verrouillé.", ephemeral=True)

# Commande /unlock
@bot.tree.command(name="unlock", description="Déverrouille un salon pour permettre aux membres d'envoyer des messages")
async def unlock(interaction: discord.Interaction, salon: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    overwrite = salon.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = True
    await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message(f"Le salon {salon.mention} a été déverrouillé.", ephemeral=True)

# Commande /hide
@bot.tree.command(name="hide", description="Cache un salon pour les membres")
async def hide(interaction: discord.Interaction, salon: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    overwrite = salon.overwrites_for(interaction.guild.default_role)
    overwrite.view_channel = False
    await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message(f"Le salon {salon.mention} a été caché.", ephemeral=True)

# Commande /unhide
@bot.tree.command(name="unhide", description="Rend un salon visible pour les membres")
async def unhide(interaction: discord.Interaction, salon: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    overwrite = salon.overwrites_for(interaction.guild.default_role)
    overwrite.view_channel = True
    await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message(f"Le salon {salon.mention} est maintenant visible.", ephemeral=True)

# Commande /lock-all
@bot.tree.command(name="lock-all", description="Verrouille tous les salons du serveur")
async def lock_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    for salon in interaction.guild.text_channels:
        overwrite = salon.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message("Tous les salons ont été verrouillés.", ephemeral=True)

# Commande /unlock-all
@bot.tree.command(name="unlock-all", description="Déverrouille tous les salons du serveur")
async def unlock_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    for salon in interaction.guild.text_channels:
        overwrite = salon.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message("Tous les salons ont été déverrouillés.", ephemeral=True)

# Commande /hide-all
@bot.tree.command(name="hide-all", description="Cache tous les salons du serveur pour les membres")
async def hide_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    for salon in interaction.guild.text_channels:
        overwrite = salon.overwrites_for(interaction.guild.default_role)
        overwrite.view_channel = False
        await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message("Tous les salons ont été cachés.", ephemeral=True)

# Commande /unhide-all
@bot.tree.command(name="unhide-all", description="Rend tous les salons visibles pour les membres")
async def unhide_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les salons.", ephemeral=True)
        return

    for salon in interaction.guild.text_channels:
        overwrite = salon.overwrites_for(interaction.guild.default_role)
        overwrite.view_channel = True
        await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message("Tous les salons sont maintenant visibles.", ephemeral=True)

# Commande /info-serveur
@bot.tree.command(name="info-serveur", description="Afficher les informations sur le serveur")
async def info_serveur(interaction: discord.Interaction):
    serveur = interaction.guild
    embed = discord.Embed(title="Informations sur le serveur", color=discord.Color.blue())
    embed.add_field(name="Nom", value=serveur.name, inline=False)
    embed.add_field(name="ID", value=serveur.id, inline=False)
    embed.add_field(name="Propriétaire", value=serveur.owner.mention, inline=False)
    embed.add_field(name="Créé le", value=serveur.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=False)
    embed.add_field(name="Membres", value=serveur.member_count, inline=False)
    embed.add_field(name="Rôles", value=len(serveur.roles), inline=False)
    embed.set_thumbnail(url=serveur.icon.url if serveur.icon else None)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /info-membre
@bot.tree.command(name="info-membre", description="Afficher les informations sur un membre")
async def info_membre(interaction: discord.Interaction, membre: discord.Member):
    embed = discord.Embed(title=f"Informations sur {membre.name}", color=discord.Color.green())
    embed.add_field(name="Nom d'utilisateur", value=f"{membre.name}#{membre.discriminator}", inline=False)
    embed.add_field(name="ID", value=membre.id, inline=False)
    embed.add_field(name="Créé le", value=membre.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=False)
    embed.add_field(name="Rejoint le", value=membre.joined_at.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=False)
    embed.add_field(name="Rôles", value=", ".join([role.mention for role in membre.roles if role.name != "@everyone"]) or "Aucun", inline=False)
    embed.set_thumbnail(url=membre.avatar.url if membre.avatar else None)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /info-role
@bot.tree.command(name="info-role", description="Afficher les informations sur un rôle")
async def info_role(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title=f"Informations sur le rôle {role.name}", color=role.color)
    embed.add_field(name="Nom", value=role.name, inline=False)
    embed.add_field(name="ID", value=role.id, inline=False)
    embed.add_field(name="Créé le", value=role.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=False)
    embed.add_field(name="Couleur", value=str(role.color), inline=False)
    embed.add_field(name="Membres", value=len(role.members), inline=False)
    embed.add_field(name="Mentionnable", value="Oui" if role.mentionable else "Non", inline=False)
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# Commande /ping avec bouton d'actualisation
class PingView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Actualiser", style=discord.ButtonStyle.green, custom_id="refresh_ping"))

@bot.tree.command(name="ping", description="Affiche la latence du bot avec un bouton pour actualiser")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="Pong!", description=f"Latence actuelle : `{latency} ms`", color=discord.Color.blue())
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed, view=PingView(), ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data.get("custom_id") == "refresh_ping":
        latency = round(bot.latency * 1000)
        embed = discord.Embed(title="Pong!", description=f"Latence actuelle : `{latency} ms`", color=discord.Color.blue())
        embed.timestamp = datetime.utcnow()

        await interaction.response.edit_message(embed=embed, view=PingView())

# Commande /support
@bot.tree.command(name="support", description="Affiche le lien du serveur support")
async def support(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support du Bot",
        description="Besoin d'aide ? Rejoignez notre serveur support : [Cliquez ici](URL DU SERV)",
        color=discord.Color.green()
    )
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Commande /leave
@bot.tree.command(name="leave", description="Coommande BUG")
async def leave(interaction: discord.Interaction, serveur_id: int):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    guild = bot.get_guild(serveur_id)
    if guild:
        await guild.leave()
        await interaction.response.send_message(f"Le bot a quitté le serveur **{guild.name}** ({serveur_id}).", ephemeral=True)
    else:
        await interaction.response.send_message(f"Le serveur avec l'ID {serveur_id} est introuvable ou le bot n'y est pas présent.", ephemeral=True)

# Lancer le bot
bot.run("TON TOKEN")