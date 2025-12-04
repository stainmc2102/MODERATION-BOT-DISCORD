import discord
from discord.ext import commands
from datetime import datetime
from typing import List
import re
import asyncio

from src.utils import JSONStorage, EmbedBuilder

URL_PATTERN = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*|'
    r'(?:www\.)?[-\w]+\.(?:com|net|org|io|gg|co|ru|site|gift|xyz|info|biz)[^\s]*',
    re.IGNORECASE
)

DISCORD_TOKEN_PATTERN = re.compile(
    r'[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27}',
    re.IGNORECASE
)

SUSPICIOUS_PATTERNS = [
    re.compile(r'free\s*nitro', re.IGNORECASE),
    re.compile(r'discord\s*nitro\s*free', re.IGNORECASE),
    re.compile(r'claim\s*your\s*(?:free\s*)?(?:nitro|gift)', re.IGNORECASE),
    re.compile(r'steam\s*(?:gift|free|giveaway)', re.IGNORECASE),
    re.compile(r'(?:click|get)\s*(?:here|now)\s*(?:for|to)\s*(?:free|nitro)', re.IGNORECASE),
    re.compile(r'airdrop', re.IGNORECASE),
    re.compile(r'crypto\s*giveaway', re.IGNORECASE),
]

class AntiLinkCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def get_guild_config(self, guild_id: int) -> dict:
        config = await JSONStorage.load("config.json")
        return config.get("guilds", {}).get(str(guild_id), {})
    
    async def is_bypassed(self, member: discord.Member, channel: discord.TextChannel) -> bool:
        config = await self.get_guild_config(member.guild.id)
        
        if member.guild_permissions.administrator:
            return True
        
        bypass_users = config.get("bypass_users", [])
        if member.id in bypass_users:
            return True
        
        bypass_channels = config.get("bypass_channels", [])
        if channel.id in bypass_channels:
            return True
        
        bypass_roles = config.get("bypass_roles", [])
        for role in member.roles:
            if role.id in bypass_roles:
                return True
        
        return False
    
    async def send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        config = await self.get_guild_config(guild.id)
        log_channel_id = config.get("log_channel")
        
        if log_channel_id:
            channel = guild.get_channel(int(log_channel_id))
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass
    
    async def get_blocked_links(self) -> List[str]:
        data = await JSONStorage.load("ban-mute-BlockWord.json")
        return data.get("blocked_links", [])
    
    async def get_scam_domains(self) -> List[str]:
        data = await JSONStorage.load("ban-mute-BlockWord.json")
        return data.get("scam_domains", [])
    
    def extract_urls(self, content: str) -> List[str]:
        return URL_PATTERN.findall(content)
    
    def contains_token(self, content: str) -> bool:
        return bool(DISCORD_TOKEN_PATTERN.search(content))
    
    def contains_suspicious_content(self, content: str) -> bool:
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(content):
                return True
        return False
    
    async def check_blocked_links(self, message: discord.Message) -> bool:
        if not message.guild or not message.author or message.author.bot:
            return False
        
        if await self.is_bypassed(message.author, message.channel):
            return False
        
        urls = self.extract_urls(message.content)
        if not urls:
            return False
        
        blocked_links = await self.get_blocked_links()
        
        for url in urls:
            url_lower = url.lower()
            for blocked in blocked_links:
                if blocked.lower() in url_lower:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.NotFound):
                        pass
                    
                    automod = self.bot.get_cog("AutoModCog")
                    if automod:
                        await automod.add_warning(
                            message.author,
                            "🤖 Anti-Link",
                            f"Gửi link bị cấm: {blocked}",
                            auto=True
                        )
                    
                    embed = discord.Embed(
                        title="🔗 Phát Hiện Link Cấm",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="👤 Người dùng", value=f"{message.author.mention}", inline=True)
                    embed.add_field(name="📍 Kênh", value=f"{message.channel.mention}", inline=True)
                    embed.add_field(name="🔗 Link phát hiện", value=f"||{url[:100]}...||" if len(url) > 100 else f"||{url}||", inline=False)
                    embed.add_field(name="⚡ Hành động", value="Xóa tin nhắn + Cảnh cáo", inline=False)
                    
                    await self.send_log(message.guild, embed)
                    return True
        
        return False
    
    async def check_scam_links(self, message: discord.Message) -> bool:
        if not message.guild or not message.author or message.author.bot:
            return False
        
        if await self.is_bypassed(message.author, message.channel):
            return False
        
        if self.contains_token(message.content):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            
            automod = self.bot.get_cog("AutoModCog")
            if automod:
                await automod.auto_ban_user(
                    message.author,
                    None,
                    "Gửi nội dung chứa Discord token - Nghi ngờ token logger"
                )
            
            embed = EmbedBuilder.scam_detection(
                user=message.author,
                content="[Token detected - content hidden for security]",
                action="Ban vĩnh viễn"
            )
            
            await self.send_log(message.guild, embed)
            return True
        
        urls = self.extract_urls(message.content)
        scam_domains = await self.get_scam_domains()
        
        for url in urls:
            url_lower = url.lower()
            for domain in scam_domains:
                if domain.lower() in url_lower:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.NotFound):
                        pass
                    
                    automod = self.bot.get_cog("AutoModCog")
                    if automod:
                        await automod.auto_ban_user(
                            message.author,
                            "7d",
                            f"Gửi link scam: {domain}"
                        )
                    
                    embed = EmbedBuilder.scam_detection(
                        user=message.author,
                        content=f"Link scam phát hiện: {domain}",
                        action="Ban 7 ngày"
                    )
                    
                    await self.send_log(message.guild, embed)
                    return True
        
        if self.contains_suspicious_content(message.content) and urls:
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            
            automod = self.bot.get_cog("AutoModCog")
            if automod:
                await automod.auto_mute_user(
                    message.author,
                    "1h",
                    "Nghi ngờ gửi nội dung lừa đảo"
                )
            
            embed = EmbedBuilder.scam_detection(
                user=message.author,
                content=message.content,
                action="Mute 1 giờ - Đang điều tra"
            )
            
            await self.send_log(message.guild, embed)
            return True
        
        return False

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiLinkCog(bot))
