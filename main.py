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

@bot.tree.command(name="vrhelp", description="Hiển thị hướng dẫn sử dụng CẢNH SÁT VIỆT REALM")
async def vrhelp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="CẢNH SÁT VIỆT REALM - Hướng Dẫn",
        description="Bot quản lý server Discord với tính năng kiểm duyệt tự động",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📋 THIẾT LẬP BAN ĐẦU",
        value=(
            "`/vrsetlog #channel` - Đặt kênh ghi log\n"
            "`/vrsetmutedrole @role` - Đặt role muted\n"
            "⚠️ Lưu ý: Thiết lập 2 lệnh này trước khi sử dụng bot"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔨 LỆNH QUẢN LÝ",
        value=(
            "`/vrban @user [time] [lý do]` - Cấm người dùng\n"
            "`/vrunban [user_id] [lý do]` - Gỡ cấm\n"
            "`/vrmute @user [time] [lý do]` - Tắt tiếng\n"
            "`/vrunmute @user [lý do]` - Gỡ tắt tiếng\n"
            "`/vrwarn @user [lý do]` - Cảnh cáo\n"
            "`/vrunwarn @user [lý do]` - Giảm cảnh cáo"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛡️ QUẢN LÝ BYPASS",
        value=(
            "`/vrbypass user:@user` - Thêm bypass cho user\n"
            "`/vrbypass role:@role` - Thêm bypass cho role\n"
            "`/vrbypass channel:#channel` - Thêm bypass cho kênh\n"
            "`/vrunbypass ...` - Xóa bypass"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 THÔNG TIN",
        value=(
            "`/vrhelp` - Hiển thị hướng dẫn này\n"
            "`/vrstatus` - Kiểm tra trạng thái bot và config"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🤖 TÍNH NĂNG TỰ ĐỘNG",
        value=(
            "• Chống Spam: 5+ tin/5s, spam emoji, mention, trùng lặp\n"
            "• Chống Scam: Phát hiện token logger, link lừa đảo\n"
            "• Hệ thống cảnh cáo 3 cấp:\n"
            "  Lần 1: Cảnh cáo | Lần 2: Mute 10p | Lần 3: Ban 1 ngày"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⏱️ ĐỊNH DẠNG THỜI GIAN",
        value=(
            "`s`=giây | `m`=phút | `h`=giờ | `d`=ngày | `w`=tuần | `mo`=tháng\n"
            "Ví dụ: `30m`, `1h`, `7d` | Để trống = Vĩnh viễn"
        ),
        inline=False
    )
    
    embed.set_footer(text="CẢNH SÁT VIỆT REALM | /vrstatus để kiểm tra config")
    
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
