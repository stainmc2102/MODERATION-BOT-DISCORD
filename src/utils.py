import json
import asyncio
import aiofiles
import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import re
import os

DATA_DIR = "data"

DURATION_REGEX = re.compile(r'^(\d+)(s|m|h|d|w|mo)$')

DURATION_MULTIPLIERS = {
    's': 1,
    'm': 60,
    'h': 3600,
    'd': 86400,
    'w': 604800,
    'mo': 2592000
}

DURATION_NAMES = {
    's': 'giây',
    'm': 'phút',
    'h': 'giờ',
    'd': 'ngày',
    'w': 'tuần',
    'mo': 'tháng'
}

def parse_duration(duration_str: Optional[str]) -> Optional[int]:
    if not duration_str:
        return None
    
    match = DURATION_REGEX.match(duration_str.lower().strip())
    if not match:
        return None
    
    value = int(match.group(1))
    unit = match.group(2)
    
    return value * DURATION_MULTIPLIERS[unit]

def format_duration(duration_str: Optional[str]) -> str:
    if not duration_str:
        return "Vĩnh viễn"
    
    match = DURATION_REGEX.match(duration_str.lower().strip())
    if not match:
        return duration_str
    
    value = int(match.group(1))
    unit = match.group(2)
    
    return f"{value} {DURATION_NAMES[unit]}"

def get_expiry_time(duration_str: Optional[str]) -> Optional[datetime]:
    seconds = parse_duration(duration_str)
    if seconds is None:
        return None
    return datetime.utcnow() + timedelta(seconds=seconds)

class JSONStorage:
    _locks: Dict[str, asyncio.Lock] = {}
    
    @classmethod
    def _get_lock(cls, filename: str) -> asyncio.Lock:
        if filename not in cls._locks:
            cls._locks[filename] = asyncio.Lock()
        return cls._locks[filename]
    
    @classmethod
    async def load(cls, filename: str) -> Dict[str, Any]:
        filepath = os.path.join(DATA_DIR, filename)
        lock = cls._get_lock(filename)
        
        async with lock:
            try:
                async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            except FileNotFoundError:
                return {}
            except json.JSONDecodeError:
                return {}
    
    @classmethod
    async def save(cls, filename: str, data: Dict[str, Any]) -> None:
        filepath = os.path.join(DATA_DIR, filename)
        lock = cls._get_lock(filename)
        
        async with lock:
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    
    @classmethod
    async def update(cls, filename: str, key: str, value: Any) -> None:
        data = await cls.load(filename)
        data[key] = value
        await cls.save(filename, data)

class EmbedBuilder:
    COLORS = {
        'ban': discord.Color.red(),
        'mute': discord.Color.orange(),
        'warn': discord.Color.gold(),
        'kick': discord.Color.dark_red(),
        'unban': discord.Color.green(),
        'unmute': discord.Color.green(),
        'info': discord.Color.blue(),
        'success': discord.Color.green(),
        'error': discord.Color.red(),
        'spam': discord.Color.purple(),
        'scam': discord.Color.dark_red(),
        'link': discord.Color.dark_orange()
    }
    
    @classmethod
    def moderation(
        cls,
        action: str,
        user: discord.Member,
        moderator: Union[discord.Member, discord.User, str],
        reason: Optional[str] = None,
        duration: Optional[str] = None,
        auto: bool = False
    ) -> discord.Embed:
        color = cls.COLORS.get(action.lower(), discord.Color.blurple())
        
        action_names = {
            'ban': 'Ban',
            'mute': 'Mute',
            'warn': 'Warn',
            'kick': 'Kick',
            'unban': 'UnBan',
            'unmute': 'UnMute'
        }
        
        title = f"{'🤖 Auto ' if auto else '🔨 '}{action_names.get(action.lower(), action.title())}"
        
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Người dùng",
            value=f"{user.mention} ({user.name}#{user.discriminator})\nID: {user.id}",
            inline=True
        )
        
        if isinstance(moderator, str):
            mod_value = moderator
        else:
            mod_value = f"{moderator.mention} ({moderator.name})"
        
        embed.add_field(
            name="🛡️ Người thực hiện",
            value=mod_value,
            inline=True
        )
        
        if duration:
            embed.add_field(
                name="⏱️ Thời hạn",
                value=format_duration(duration),
                inline=True
            )
        
        embed.add_field(
            name="📝 Lý do",
            value=reason or "Không có lý do",
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.set_footer(text=f"User ID: {user.id}")
        
        return embed
    
    @classmethod
    def warning_level(cls, user: discord.Member, level: int, total_warns: int) -> discord.Embed:
        embed = discord.Embed(
            title="⚠️ Warn",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Người dùng",
            value=f"{user.mention}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Mức cảnh cáo",
            value=f"{level}/3",
            inline=True
        )
        
        embed.add_field(
            name="📈 Tổng cảnh cáo",
            value=str(total_warns),
            inline=True
        )
        
        consequences = {
            1: "Cảnh cáo lần 1 - Không có hình phạt",
            2: "Cảnh cáo lần 2 - Tự động mute 10 phút",
            3: "Cảnh cáo lần 3 - Tự động ban 1 ngày"
        }
        
        embed.add_field(
            name="⚡ Hậu quả",
            value=consequences.get(level, "Không xác định"),
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        
        return embed
    
    @classmethod
    def spam_detection(
        cls,
        user: discord.Member,
        spam_type: str,
        action: str,
        details: str
    ) -> discord.Embed:
        embed = discord.Embed(
            title="🚫 Phát Hiện Spam",
            color=cls.COLORS['spam'],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Người dùng",
            value=f"{user.mention}",
            inline=True
        )
        
        embed.add_field(
            name="📛 Loại spam",
            value=spam_type,
            inline=True
        )
        
        embed.add_field(
            name="⚡ Hành động",
            value=action,
            inline=True
        )
        
        embed.add_field(
            name="📋 Chi tiết",
            value=details,
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        
        return embed
    
    @classmethod
    def scam_detection(
        cls,
        user: discord.Member,
        content: str,
        action: str
    ) -> discord.Embed:
        embed = discord.Embed(
            title="🔴 Phát Hiện Scam/Token Logger",
            color=cls.COLORS['scam'],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Người dùng",
            value=f"{user.mention} (ID: {user.id})",
            inline=False
        )
        
        truncated_content = content[:500] + "..." if len(content) > 500 else content
        embed.add_field(
            name="📜 Nội dung",
            value=f"```{truncated_content}```",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Hành động",
            value=action,
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        
        return embed
    
    @classmethod
    def config_update(cls, setting: str, value: str, moderator: discord.Member) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Cập Nhật Cấu Hình",
            color=cls.COLORS['info'],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📝 Thiết lập",
            value=setting,
            inline=True
        )
        
        embed.add_field(
            name="📌 Giá trị",
            value=value,
            inline=True
        )
        
        embed.add_field(
            name="👤 Người thực hiện",
            value=f"{moderator.mention}",
            inline=True
        )
        
        return embed
    
    @classmethod
    def error(cls, message: str) -> discord.Embed:
        return discord.Embed(
            title="❌ Lỗi",
            description=message,
            color=cls.COLORS['error']
        )
    
    @classmethod
    def success(cls, message: str) -> discord.Embed:
        return discord.Embed(
            title="✅ Thành công",
            description=message,
            color=cls.COLORS['success']
        )

async def delete_messages_safely(channel: discord.TextChannel, messages: list, delay: float = 0.5):
    for msg in messages:
        try:
            await msg.delete()
            await asyncio.sleep(delay)
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            await asyncio.sleep(2)

async def delete_user_messages(guild: discord.Guild, user_id: int, delay: float = 1.0):
    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=100):
                if message.author.id == user_id:
                    try:
                        await message.delete()
                        await asyncio.sleep(delay)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        continue
        except discord.Forbidden:
            continue
