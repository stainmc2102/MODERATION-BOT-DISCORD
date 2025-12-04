import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional, Union
import asyncio
import re

from src.utils import (
    JSONStorage, EmbedBuilder, parse_duration, 
    get_expiry_time, delete_user_messages
)

class AutoModCog(commands.Cog):
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
    
    async def apply_muted_role(self, member: discord.Member) -> bool:
        config = await self.get_guild_config(member.guild.id)
        muted_role_id = config.get("muted_role")
        
        if muted_role_id:
            role = member.guild.get_role(int(muted_role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Auto Muted by CẢNH SÁT VIỆT REALM")
                    return True
                except discord.Forbidden:
                    return False
        return False
    
    async def get_user_warnings(self, guild_id: int, user_id: int) -> list:
        data = await JSONStorage.load("warn.json")
        warnings = data.get("warnings", {})
        guild_warnings = warnings.get(str(guild_id), {})
        return guild_warnings.get(str(user_id), [])
    
    async def add_warning(
        self,
        user: discord.Member,
        moderator: Union[discord.Member, str],
        reason: str,
        interaction: Optional[discord.Interaction] = None,
        auto: bool = False,
        send_to_log: bool = True
    ) -> int:
        data = await JSONStorage.load("warn.json")
        
        if "warnings" not in data:
            data["warnings"] = {}
        
        guild_id = str(user.guild.id)
        user_id = str(user.id)
        
        if guild_id not in data["warnings"]:
            data["warnings"][guild_id] = {}
        
        if user_id not in data["warnings"][guild_id]:
            data["warnings"][guild_id][user_id] = []
        
        mod_id = moderator if isinstance(moderator, str) else moderator.id
        
        warning = {
            "reason": reason,
            "moderator_id": mod_id,
            "timestamp": datetime.utcnow().isoformat(),
            "auto": auto
        }
        
        data["warnings"][guild_id][user_id].append(warning)
        await JSONStorage.save("warn.json", data)
        
        total_warns = len(data["warnings"][guild_id][user_id])
        current_level = ((total_warns - 1) % 3) + 1
        
        embed = EmbedBuilder.warning_level(user, current_level, total_warns)
        embed.add_field(name="📝 Lý do", value=reason, inline=False)
        
        if isinstance(moderator, str):
            embed.add_field(name="🛡️ Người thực hiện", value=moderator, inline=True)
        else:
            embed.add_field(name="🛡️ Người thực hiện", value=moderator.mention, inline=True)
        
        if interaction:
            await interaction.response.send_message(embed=embed)
        
        if send_to_log:
            await self.send_log(user.guild, embed)
        
        if current_level == 2:
            success = await self.auto_mute_user(user, "10m", f"Cảnh cáo lần 2: {reason}")
            if not success and interaction:
                try:
                    await interaction.followup.send(
                        embed=EmbedBuilder.error(f"Không thể tự động mute {user.mention} - kiểm tra quyền bot."),
                        ephemeral=True
                    )
                except discord.HTTPException:
                    pass
        elif current_level == 3:
            success = await self.auto_ban_user(user, "1d", f"Cảnh cáo lần 3: {reason}")
            if not success and interaction:
                try:
                    await interaction.followup.send(
                        embed=EmbedBuilder.error(f"Không thể tự động ban {user.mention} - kiểm tra quyền bot."),
                        ephemeral=True
                    )
                except discord.HTTPException:
                    pass
        
        return current_level
    
    async def auto_mute_user(self, user: discord.Member, duration: str, reason: str) -> bool:
        try:
            await self.apply_muted_role(user)
            
            timeout_seconds = parse_duration(duration) if duration else 2419200
            timeout_until = discord.utils.utcnow() + timedelta(seconds=min(timeout_seconds or 2419200, 2419200))
            await user.timeout(timeout_until, reason=reason)
            
            ban_mute_data = await JSONStorage.load("ban-mute.json")
            if "mutes" not in ban_mute_data:
                ban_mute_data["mutes"] = {}
            if str(user.guild.id) not in ban_mute_data["mutes"]:
                ban_mute_data["mutes"][str(user.guild.id)] = {}
            
            expiry = get_expiry_time(duration)
            ban_mute_data["mutes"][str(user.guild.id)][str(user.id)] = {
                "moderator_id": "Auto",
                "reason": reason,
                "duration": duration,
                "expiry": expiry.isoformat() if expiry else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            await JSONStorage.save("ban-mute.json", ban_mute_data)
            
            embed = EmbedBuilder.moderation(
                action="mute",
                user=user,
                moderator="🤖 CẢNH SÁT VIỆT REALM",
                reason=reason,
                duration=duration,
                auto=True
            )
            
            await self.send_log(user.guild, embed)
            return True
            
        except discord.Forbidden:
            error_embed = EmbedBuilder.error(f"Không thể mute {user.mention} - Thiếu quyền hoặc role cao hơn bot.")
            await self.send_log(user.guild, error_embed)
            return False
        except Exception as e:
            error_embed = EmbedBuilder.error(f"Lỗi khi mute {user.mention}: {str(e)}")
            await self.send_log(user.guild, error_embed)
            return False
    
    async def auto_ban_user(self, user: discord.Member, duration: Optional[str], reason: str) -> bool:
        try:
            await user.ban(reason=reason, delete_message_days=1)
            
            asyncio.create_task(delete_user_messages(user.guild, user.id))
            
            ban_mute_data = await JSONStorage.load("ban-mute.json")
            if "bans" not in ban_mute_data:
                ban_mute_data["bans"] = {}
            if str(user.guild.id) not in ban_mute_data["bans"]:
                ban_mute_data["bans"][str(user.guild.id)] = {}
            
            expiry = get_expiry_time(duration) if duration else None
            ban_mute_data["bans"][str(user.guild.id)][str(user.id)] = {
                "moderator_id": "Auto",
                "reason": reason,
                "duration": duration,
                "expiry": expiry.isoformat() if expiry else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            await JSONStorage.save("ban-mute.json", ban_mute_data)
            
            embed = EmbedBuilder.moderation(
                action="ban",
                user=user,
                moderator="🤖 CẢNH SÁT VIỆT REALM",
                reason=reason,
                duration=duration,
                auto=True
            )
            
            await self.send_log(user.guild, embed)
            
            if expiry:
                delay = (expiry - datetime.utcnow()).total_seconds()
                if delay > 0:
                    asyncio.create_task(self._schedule_unban(user.guild, user.id, delay))
            
            return True
                        
        except discord.Forbidden:
            error_embed = EmbedBuilder.error(f"Không thể ban {user.mention} - Thiếu quyền hoặc role cao hơn bot.")
            await self.send_log(user.guild, error_embed)
            return False
        except Exception as e:
            error_embed = EmbedBuilder.error(f"Lỗi khi ban {user.mention}: {str(e)}")
            await self.send_log(user.guild, error_embed)
            return False
    
    async def _schedule_unban(self, guild: discord.Guild, user_id: int, delay: float):
        await asyncio.sleep(delay)
        try:
            await guild.unban(discord.Object(id=user_id), reason="Hết thời hạn cấm")
        except discord.NotFound:
            pass
    
    async def check_blocked_words(self, message: discord.Message) -> bool:
        if not message.guild or not message.author or message.author.bot:
            return False
        
        if await self.is_bypassed(message.author, message.channel):
            return False
        
        block_data = await JSONStorage.load("ban-mute-BlockWord.json")
        blocked_words = block_data.get("blocked_words", {})
        
        content_lower = message.content.lower()
        
        for word, config in blocked_words.items():
            if word.lower() in content_lower:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                
                action = config.get("action", "warn")
                duration = config.get("time")
                reason = f"Sử dụng từ cấm: {word}"
                
                if action == "ban":
                    await self.auto_ban_user(message.author, duration, reason)
                elif action == "mute":
                    await self.auto_mute_user(message.author, duration, reason)
                else:
                    await self.add_warning(message.author, "🤖 CẢNH SÁT VIỆT REALM", reason, auto=True)
                
                return True
        
        return False

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModCog(bot))
