import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import asyncio
import re

from src.utils import JSONStorage, EmbedBuilder

class SpamTracker:
    def __init__(self):
        self.message_cache: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.content_cache: Dict[int, Dict[int, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.channel_cache: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        self.emoji_cache: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.mention_cache: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.slowmode_users: Dict[int, Dict[int, datetime]] = defaultdict(dict)
        
        self.SPAM_THRESHOLD = 5
        self.SPAM_INTERVAL = 5
        self.EMOJI_THRESHOLD = 10
        self.MENTION_THRESHOLD = 5
        self.CHANNEL_HOP_THRESHOLD = 5
        self.CHANNEL_HOP_INTERVAL = 10
        self.DUPLICATE_THRESHOLD = 3
        self.MAX_MESSAGE_LENGTH = 2000
        self.RATE_LIMIT_MESSAGES = 10
        self.RATE_LIMIT_INTERVAL = 5
    
    def cleanup_old_entries(self, guild_id: int, user_id: int):
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=30)
        
        self.message_cache[guild_id][user_id] = [
            ts for ts in self.message_cache[guild_id][user_id] if ts > cutoff
        ]
        
        if len(self.content_cache[guild_id][user_id]) > 10:
            self.content_cache[guild_id][user_id] = self.content_cache[guild_id][user_id][-10:]
        
        if len(self.channel_cache[guild_id][user_id]) > 10:
            self.channel_cache[guild_id][user_id] = self.channel_cache[guild_id][user_id][-10:]
    
    def track_message(self, message: discord.Message) -> dict:
        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.utcnow()
        
        self.cleanup_old_entries(guild_id, user_id)
        
        self.message_cache[guild_id][user_id].append(now)
        self.content_cache[guild_id][user_id].append(message.content)
        self.channel_cache[guild_id][user_id].append(message.channel.id)
        
        emoji_count = len(re.findall(r'<a?:\w+:\d+>|[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', message.content))
        self.emoji_cache[guild_id][user_id] = emoji_count
        
        mention_count = len(message.mentions) + len(message.role_mentions)
        self.mention_cache[guild_id][user_id] = mention_count
        
        results = {
            "message_spam": False,
            "emoji_spam": False,
            "mention_spam": False,
            "channel_hop": False,
            "duplicate_spam": False,
            "long_message": False,
            "rate_limit": False,
            "details": []
        }
        
        recent_messages = [
            ts for ts in self.message_cache[guild_id][user_id]
            if (now - ts).total_seconds() <= self.SPAM_INTERVAL
        ]
        
        if len(recent_messages) >= self.SPAM_THRESHOLD:
            results["message_spam"] = True
            results["details"].append(f"{len(recent_messages)} tin nhắn trong {self.SPAM_INTERVAL}s")
        
        if len(recent_messages) >= self.RATE_LIMIT_MESSAGES:
            results["rate_limit"] = True
            results["details"].append(f"Vượt giới hạn: {len(recent_messages)} tin nhắn trong {self.RATE_LIMIT_INTERVAL}s")
        
        if emoji_count >= self.EMOJI_THRESHOLD:
            results["emoji_spam"] = True
            results["details"].append(f"{emoji_count} emoji trong tin nhắn")
        
        if mention_count >= self.MENTION_THRESHOLD:
            results["mention_spam"] = True
            results["details"].append(f"{mention_count} mentions trong tin nhắn")
        
        recent_channels = self.channel_cache[guild_id][user_id][-self.CHANNEL_HOP_THRESHOLD:]
        if len(set(recent_channels)) >= self.CHANNEL_HOP_THRESHOLD:
            results["channel_hop"] = True
            results["details"].append(f"Nhảy {len(set(recent_channels))} kênh liên tục")
        
        recent_content = self.content_cache[guild_id][user_id][-self.DUPLICATE_THRESHOLD:]
        if len(recent_content) >= self.DUPLICATE_THRESHOLD:
            if len(set(recent_content)) == 1 and recent_content[0]:
                results["duplicate_spam"] = True
                results["details"].append("Gửi tin nhắn trùng lặp")
        
        if len(message.content) > self.MAX_MESSAGE_LENGTH:
            results["long_message"] = True
            results["details"].append(f"Tin nhắn quá dài: {len(message.content)} ký tự")
        
        return results
    
    def is_rate_limited(self, guild_id: int, user_id: int) -> bool:
        if user_id in self.slowmode_users.get(guild_id, {}):
            expiry = self.slowmode_users[guild_id][user_id]
            if datetime.utcnow() < expiry:
                return True
            else:
                del self.slowmode_users[guild_id][user_id]
        return False
    
    def set_rate_limit(self, guild_id: int, user_id: int, duration_seconds: int = 60):
        self.slowmode_users[guild_id][user_id] = datetime.utcnow() + timedelta(seconds=duration_seconds)

class AntiSpamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tracker = SpamTracker()
    
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
    
    async def send_dm_warning(self, user: discord.Member, reason: str):
        try:
            embed = discord.Embed(
                title="⚠️ Cảnh báo từ Server",
                description=f"Bạn đã bị phát hiện spam trong **{user.guild.name}**",
                color=discord.Color.orange()
            )
            embed.add_field(name="Lý do", value=reason, inline=False)
            embed.add_field(name="Lưu ý", value="Tiếp tục spam có thể dẫn đến mute hoặc ban.", inline=False)
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
    
    async def check_spam(self, message: discord.Message) -> bool:
        if not message.guild or not message.author or message.author.bot:
            return False
        
        if await self.is_bypassed(message.author, message.channel):
            return False
        
        if self.tracker.is_rate_limited(message.guild.id, message.author.id):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            return True
        
        results = self.tracker.track_message(message)
        
        has_spam = any([
            results["message_spam"],
            results["emoji_spam"],
            results["mention_spam"],
            results["channel_hop"],
            results["duplicate_spam"],
            results["long_message"]
        ])
        
        if not has_spam and not results["rate_limit"]:
            return False
        
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        
        spam_types = []
        if results["message_spam"]:
            spam_types.append("Spam tin nhắn")
        if results["emoji_spam"]:
            spam_types.append("Spam emoji")
        if results["mention_spam"]:
            spam_types.append("Spam mention")
        if results["channel_hop"]:
            spam_types.append("Nhảy kênh liên tục")
        if results["duplicate_spam"]:
            spam_types.append("Tin nhắn trùng lặp")
        if results["long_message"]:
            spam_types.append("Tin nhắn quá dài")
        
        spam_type_str = ", ".join(spam_types) if spam_types else "Vượt giới hạn tin nhắn"
        details_str = "\n".join(results["details"])
        
        if results["rate_limit"]:
            self.tracker.set_rate_limit(message.guild.id, message.author.id, 60)
            await self.send_dm_warning(message.author, f"Bạn đang gửi tin nhắn quá nhanh. Vui lòng đợi 1 phút.")
            
            embed = EmbedBuilder.spam_detection(
                user=message.author,
                spam_type=spam_type_str,
                action="Bật slowmode cá nhân 1 phút",
                details=details_str
            )
            await self.send_log(message.guild, embed)
        elif results["mention_spam"] or results["message_spam"]:
            automod = self.bot.get_cog("AutoModCog")
            if automod:
                await automod.auto_mute_user(message.author, "5m", f"Auto spam detection: {spam_type_str}")
        else:
            automod = self.bot.get_cog("AutoModCog")
            if automod:
                await automod.add_warning(message.author, "🤖 CẢNH SÁT VIỆT REALM", f"{spam_type_str}", auto=True)
        
        return True

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpamCog(bot))
