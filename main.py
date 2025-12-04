import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class VRBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self._synced = False
    
    async def setup_hook(self):
        await self.load_extension("src.moderation")
        await self.load_extension("src.automod")
        await self.load_extension("src.antispam")
        await self.load_extension("src.antilink")
    
    async def on_ready(self):
        print(f"Bot đã sẵn sàng: {self.user.name} (ID: {self.user.id})")
        print(f"Đang hoạt động trên {len(self.guilds)} server")
        
        if not self._synced:
            await self.tree.sync()
            self._synced = True
            print(f"Đã đồng bộ {len(self.tree.get_commands())} lệnh slash")
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="CẢNH SÁT VIỆT REALM | /vrhelp"
            )
        )
    
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        automod = self.get_cog("AutoModCog")
        if automod:
            blocked = await automod.check_blocked_words(message)
            if blocked:
                return
        
        antilink = self.get_cog("AntiLinkCog")
        if antilink:
            scam_detected = await antilink.check_scam_links(message)
            if scam_detected:
                return
            
            link_blocked = await antilink.check_blocked_links(message)
            if link_blocked:
                return
        
        antispam = self.get_cog("AntiSpamCog")
        if antispam:
            spam_detected = await antispam.check_spam(message)
            if spam_detected:
                return
        
        await self.process_commands(message)

bot = VRBot()

@bot.tree.command(name="vrhelp", description="Show all commands of CẢNH SÁT VIỆT REALM")
async def vrhelp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 CẢNH SÁT VIỆT REALM - Command List",
        description="Discord Moderation Bot with Auto Moderation features",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🔨 Moderation Commands",
        value=(
            "`/vrban [user] [duration] [reason]` - Ban user\n"
            "`/vrunban [user] [reason]` - UnBan user\n"
            "`/vrmute [user] [duration] [reason]` - Mute user\n"
            "`/vrunmute [user] [reason]` - UnMute user\n"
            "`/vrwarn [user] [reason]` - Warn user\n"
            "`/vrunwarn [user] [reason]` - UnWarn user"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Configuration Commands",
        value=(
            "`/vrsetlog [channel]` - Set log channel\n"
            "`/vrsetmutedrole [role]` - Set muted role\n"
            "`/vrbypass [type] [id]` - Add/Remove bypass"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Info Commands",
        value=(
            "`/vrhelp` - Show this help\n"
            "`/vrstatus` - Check bot status"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🤖 Auto Moderation",
        value=(
            "• Auto Ban/Mute blocked words\n"
            "• 3-Level Warning System (Warn → Mute → Ban)\n"
            "• Anti-Spam & Anti-Flood\n"
            "• Scam/Token Logger Detection\n"
            "• Auto Delete Blocked Links"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⏱️ Duration Format",
        value=(
            "`s` - seconds | `m` - minutes | `h` - hours\n"
            "`d` - days | `w` - weeks | `mo` - months\n"
            "Example: `1d`, `2h`, `30m` | Empty = Permanent"
        ),
        inline=False
    )
    
    embed.set_footer(text="CẢNH SÁT VIỆT REALM | Discord Moderation Bot")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="vrstatus", description="Kiểm tra trạng thái bot")
async def vrstatus(interaction: discord.Interaction):
    from src.utils import JSONStorage
    
    config = await JSONStorage.load("config.json")
    guild_config = config.get("guilds", {}).get(str(interaction.guild.id), {})
    
    log_channel = interaction.guild.get_channel(guild_config.get("log_channel", 0))
    muted_role = interaction.guild.get_role(guild_config.get("muted_role", 0))
    
    bypass_users = len(guild_config.get("bypass_users", []))
    bypass_roles = len(guild_config.get("bypass_roles", []))
    bypass_channels = len(guild_config.get("bypass_channels", []))
    
    embed = discord.Embed(
        title="📊 Trạng Thái CẢNH SÁT VIỆT REALM",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📡 Kết nối",
        value=f"Latency: `{round(bot.latency * 1000)}ms`",
        inline=True
    )
    
    embed.add_field(
        name="📋 Log Channel",
        value=log_channel.mention if log_channel else "Chưa thiết lập",
        inline=True
    )
    
    embed.add_field(
        name="🔇 Muted Role",
        value=muted_role.mention if muted_role else "Chưa thiết lập",
        inline=True
    )
    
    embed.add_field(
        name="🛡️ Bypass",
        value=f"Users: {bypass_users} | Roles: {bypass_roles} | Channels: {bypass_channels}",
        inline=False
    )
    
    warn_data = await JSONStorage.load("warn.json")
    guild_warns = warn_data.get("warnings", {}).get(str(interaction.guild.id), {})
    total_warns = sum(len(warns) for warns in guild_warns.values())
    
    embed.add_field(
        name="⚠️ Tổng Cảnh Cáo",
        value=str(total_warns),
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    
    if not token:
        print("=" * 50)
        print("LỖI: Không tìm thấy DISCORD_BOT_TOKEN")
        print("Vui lòng thêm token vào Secrets với key: DISCORD_BOT_TOKEN")
        print("=" * 50)
        return
    
    print("Đang khởi động CẢNH SÁT VIỆT REALM...")
    bot.run(token)

if __name__ == "__main__":
    main()
