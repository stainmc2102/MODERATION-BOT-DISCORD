import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional, Union
import asyncio

from src.utils import (
    JSONStorage, EmbedBuilder, parse_duration, 
    format_duration, get_expiry_time, delete_user_messages
)

class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def is_authorized(self, user_id: int) -> bool:
        data = await JSONStorage.load("authorized_users.json")
        authorized_users = data.get("authorized_users", [])
        return user_id in authorized_users
    
    async def get_guild_config(self, guild_id: int) -> dict:
        config = await JSONStorage.load("config.json")
        return config.get("guilds", {}).get(str(guild_id), {})
    
    async def save_guild_config(self, guild_id: int, guild_config: dict) -> None:
        config = await JSONStorage.load("config.json")
        if "guilds" not in config:
            config["guilds"] = {}
        config["guilds"][str(guild_id)] = guild_config
        await JSONStorage.save("config.json", config)
    
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
                    await member.add_roles(role, reason="Muted by CẢNH SÁT VIỆT REALM")
                    return True
                except discord.Forbidden:
                    return False
        return False
    
    async def remove_muted_role(self, member: discord.Member) -> bool:
        config = await self.get_guild_config(member.guild.id)
        muted_role_id = config.get("muted_role")
        
        if muted_role_id:
            role = member.guild.get_role(int(muted_role_id))
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Unmuted by CẢNH SÁT VIỆT REALM")
                    return True
                except discord.Forbidden:
                    return False
        return False
    
    async def record_ban(self, guild_id: int, user_id: int, moderator_id: int, reason: str, duration: Optional[str], expiry: Optional[datetime]) -> None:
        data = await JSONStorage.load("ban-mute.json")
        if "bans" not in data:
            data["bans"] = {}
        
        if str(guild_id) not in data["bans"]:
            data["bans"][str(guild_id)] = {}
        
        data["bans"][str(guild_id)][str(user_id)] = {
            "moderator_id": moderator_id,
            "reason": reason,
            "duration": duration,
            "expiry": expiry.isoformat() if expiry else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await JSONStorage.save("ban-mute.json", data)
    
    async def record_mute(self, guild_id: int, user_id: int, moderator_id: int, reason: str, duration: Optional[str], expiry: Optional[datetime]) -> None:
        data = await JSONStorage.load("ban-mute.json")
        if "mutes" not in data:
            data["mutes"] = {}
        
        if str(guild_id) not in data["mutes"]:
            data["mutes"][str(guild_id)] = {}
        
        data["mutes"][str(guild_id)][str(user_id)] = {
            "moderator_id": moderator_id,
            "reason": reason,
            "duration": duration,
            "expiry": expiry.isoformat() if expiry else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await JSONStorage.save("ban-mute.json", data)
    
    async def remove_mute_record(self, guild_id: int, user_id: int) -> None:
        data = await JSONStorage.load("ban-mute.json")
        if "mutes" in data and str(guild_id) in data["mutes"]:
            if str(user_id) in data["mutes"][str(guild_id)]:
                del data["mutes"][str(guild_id)][str(user_id)]
                await JSONStorage.save("ban-mute.json", data)
    
    @app_commands.command(name="vrban", description="Cấm một người dùng khỏi server")
    @app_commands.describe(
        user="Người dùng cần cấm",
        duration="Thời hạn (s/m/h/d/w/mo) - để trống nếu vĩnh viễn",
        reason="Lý do cấm (tùy chọn)"
    )
    async def vrban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: Optional[str] = None,
        reason: Optional[str] = None
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        if duration and not parse_duration(duration):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Định dạng thời hạn không hợp lệ. Sử dụng: s, m, h, d, w, mo"),
                ephemeral=True
            )
            return
        
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không thể cấm người dùng có role cao hơn hoặc bằng bạn."),
                ephemeral=True
            )
            return
        
        expiry = get_expiry_time(duration)
        
        try:
            await user.ban(reason=reason or "Không có lý do")
            
            await self.record_ban(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                reason or "Không có lý do",
                duration,
                expiry
            )
            
            asyncio.create_task(delete_user_messages(interaction.guild, user.id))
            
            embed = EmbedBuilder.moderation(
                action="ban",
                user=user,
                moderator=interaction.user,
                reason=reason,
                duration=duration
            )
            
            await interaction.response.send_message(
                embed=EmbedBuilder.success(f"Đã ban {user.mention}"),
                ephemeral=True
            )
            await self.send_log(interaction.guild, embed)
            
            if expiry:
                await self.schedule_unban(interaction.guild, user.id, expiry)
                
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Tôi không có quyền cấm người dùng này."),
                ephemeral=True
            )
    
    async def schedule_unban(self, guild: discord.Guild, user_id: int, expiry: datetime):
        delay = (expiry - datetime.utcnow()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            try:
                await guild.unban(discord.Object(id=user_id), reason="Hết thời hạn cấm")
            except discord.NotFound:
                pass
    
    @app_commands.command(name="vrmute", description="Tắt tiếng một người dùng")
    @app_commands.describe(
        user="Người dùng cần tắt tiếng",
        duration="Thời hạn (s/m/h/d/w/mo) - để trống nếu vĩnh viễn",
        reason="Lý do tắt tiếng (tùy chọn)"
    )
    async def vrmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: Optional[str] = None,
        reason: Optional[str] = None
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        if duration and not parse_duration(duration):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Định dạng thời hạn không hợp lệ. Sử dụng: s, m, h, d, w, mo"),
                ephemeral=True
            )
            return
        
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không thể mute người dùng có role cao hơn hoặc bằng bạn."),
                ephemeral=True
            )
            return
        
        expiry = get_expiry_time(duration)
        
        try:
            await self.apply_muted_role(user)
            
            timeout_duration = parse_duration(duration) if duration else 2419200
            timeout_until = discord.utils.utcnow() + timedelta(seconds=min(timeout_duration, 2419200))
            await user.timeout(timeout_until, reason=reason or "Không có lý do")
            
            await self.record_mute(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                reason or "Không có lý do",
                duration,
                expiry
            )
            
            embed = EmbedBuilder.moderation(
                action="mute",
                user=user,
                moderator=interaction.user,
                reason=reason,
                duration=duration
            )
            
            await interaction.response.send_message(
                embed=EmbedBuilder.success(f"Đã mute {user.mention}"),
                ephemeral=True
            )
            await self.send_log(interaction.guild, embed)
            
            if expiry:
                await self.schedule_unmute(interaction.guild, user, expiry)
                
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Tôi không có quyền mute người dùng này."),
                ephemeral=True
            )
    
    async def schedule_unmute(self, guild: discord.Guild, user: discord.Member, expiry: datetime):
        delay = (expiry - datetime.utcnow()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            try:
                member = guild.get_member(user.id)
                if member:
                    await self.remove_muted_role(member)
                    await member.timeout(None, reason="Hết thời hạn mute")
                await self.remove_mute_record(guild.id, user.id)
            except (discord.NotFound, discord.Forbidden):
                pass
    
    @app_commands.command(name="vrwarn", description="Cảnh cáo một người dùng")
    @app_commands.describe(
        user="Người dùng cần cảnh cáo",
        reason="Lý do cảnh cáo (tùy chọn)"
    )
    async def vrwarn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        from src.automod import AutoModCog
        automod = self.bot.get_cog("AutoModCog")
        if automod:
            await automod.add_warning(
                user,
                interaction.user,
                reason or "Không có lý do",
                interaction,
                send_to_log=False
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Không thể thêm cảnh cáo."),
                ephemeral=True
            )
    
    async def remove_ban_record(self, guild_id: int, user_id: int) -> None:
        data = await JSONStorage.load("ban-mute.json")
        if "bans" in data and str(guild_id) in data["bans"]:
            if str(user_id) in data["bans"][str(guild_id)]:
                del data["bans"][str(guild_id)][str(user_id)]
                await JSONStorage.save("ban-mute.json", data)
    
    @app_commands.command(name="vrunban", description="Gỡ cấm một người dùng")
    @app_commands.describe(
        user_id="ID của người dùng cần gỡ cấm",
        reason="Lý do gỡ cấm (tùy chọn)"
    )
    async def vrunban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: Optional[str] = None
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        try:
            uid = int(user_id.strip())
        except ValueError:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("ID người dùng không hợp lệ."),
                ephemeral=True
            )
            return
        
        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=reason or "Không có lý do")
            
            await self.remove_ban_record(interaction.guild.id, uid)
            
            embed = discord.Embed(
                title="🔓 UnBan",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="👤 Người dùng", value=f"{user.name} (ID: {uid})", inline=True)
            embed.add_field(name="🛡️ Người thực hiện", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 Lý do", value=reason or "Không có lý do", inline=False)
            
            await interaction.response.send_message(
                embed=EmbedBuilder.success(f"Đã unban {user.name}"),
                ephemeral=True
            )
            await self.send_log(interaction.guild, embed)
            
        except discord.NotFound:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Người dùng không tìm thấy hoặc chưa bị cấm."),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Tôi không có quyền gỡ cấm người dùng này."),
                ephemeral=True
            )
    
    @app_commands.command(name="vrunmute", description="Gỡ tắt tiếng một người dùng")
    @app_commands.describe(
        user="Người dùng cần gỡ tắt tiếng",
        reason="Lý do gỡ tắt tiếng (tùy chọn)"
    )
    async def vrunmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        try:
            await self.remove_muted_role(user)
            await user.timeout(None, reason=reason or "Không có lý do")
            
            await self.remove_mute_record(interaction.guild.id, user.id)
            
            embed = discord.Embed(
                title="🔊 UnMute",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="👤 Người dùng", value=f"{user.mention} ({user.name})", inline=True)
            embed.add_field(name="🛡️ Người thực hiện", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 Lý do", value=reason or "Không có lý do", inline=False)
            embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
            
            await interaction.response.send_message(
                embed=EmbedBuilder.success(f"Đã unmute {user.mention}"),
                ephemeral=True
            )
            await self.send_log(interaction.guild, embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Tôi không có quyền gỡ mute người dùng này."),
                ephemeral=True
            )
    
    @app_commands.command(name="vrunwarn", description="Giảm 1 cảnh cáo của người dùng")
    @app_commands.describe(
        user="Người dùng cần giảm cảnh cáo",
        reason="Lý do giảm cảnh cáo (tùy chọn)"
    )
    async def vrunwarn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        data = await JSONStorage.load("warn.json")
        
        guild_id = str(interaction.guild.id)
        user_id = str(user.id)
        
        if "warnings" not in data:
            data["warnings"] = {}
        
        if guild_id not in data["warnings"] or user_id not in data["warnings"][guild_id]:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Người dùng này không có cảnh cáo nào."),
                ephemeral=True
            )
            return
        
        warnings = data["warnings"][guild_id][user_id]
        if not warnings:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Người dùng này không có cảnh cáo nào."),
                ephemeral=True
            )
            return
        
        removed_warn = warnings.pop()
        
        if not warnings:
            del data["warnings"][guild_id][user_id]
        
        await JSONStorage.save("warn.json", data)
        
        remaining = len(warnings)
        
        embed = discord.Embed(
            title="✅ UnWarn",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="👤 Người dùng", value=f"{user.mention}", inline=True)
        embed.add_field(name="📊 Cảnh cáo còn lại", value=str(remaining), inline=True)
        embed.add_field(name="🛡️ Người thực hiện", value=interaction.user.mention, inline=True)
        embed.add_field(name="📝 Lý do", value=reason or "Không có lý do", inline=False)
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="vrbypass", description="Thêm/xóa bypass cho role/user/channel")
    @app_commands.describe(
        target_type="Loại đối tượng bypass",
        target="Role, User hoặc Channel ID"
    )
    @app_commands.choices(target_type=[
        app_commands.Choice(name="Role", value="role"),
        app_commands.Choice(name="User", value="user"),
        app_commands.Choice(name="Channel", value="channel")
    ])
    async def vrbypass(
        self,
        interaction: discord.Interaction,
        target_type: str,
        target: str
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        try:
            target_id = int(target.strip("<@&#>"))
        except ValueError:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("ID không hợp lệ."),
                ephemeral=True
            )
            return
        
        config = await self.get_guild_config(interaction.guild.id)
        bypass_key = f"bypass_{target_type}s"
        
        if bypass_key not in config:
            config[bypass_key] = []
        
        if target_id in config[bypass_key]:
            config[bypass_key].remove(target_id)
            action = "xóa khỏi"
        else:
            config[bypass_key].append(target_id)
            action = "thêm vào"
        
        await self.save_guild_config(interaction.guild.id, config)
        
        type_names = {"role": "Role", "user": "User", "channel": "Channel"}
        embed = EmbedBuilder.config_update(
            f"Bypass {type_names[target_type]}",
            f"Đã {action} danh sách bypass: {target_id}",
            interaction.user
        )
        
        await interaction.response.send_message(embed=embed)
        await self.send_log(interaction.guild, embed)
    
    @app_commands.command(name="vrsetlog", description="Thiết lập channel log")
    @app_commands.describe(channel="Channel để gửi log")
    async def vrsetlog(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        config = await self.get_guild_config(interaction.guild.id)
        config["log_channel"] = channel.id
        await self.save_guild_config(interaction.guild.id, config)
        
        embed = EmbedBuilder.config_update(
            "Log Channel",
            f"{channel.mention}",
            interaction.user
        )
        
        await interaction.response.send_message(embed=embed)
        await self.send_log(interaction.guild, embed)
    
    @app_commands.command(name="vrsetmutedrole", description="Thiết lập role muted")
    @app_commands.describe(role="Role để gán khi mute")
    async def vrsetmutedrole(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        if not await self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bạn không có quyền sử dụng lệnh này."),
                ephemeral=True
            )
            return
        
        config = await self.get_guild_config(interaction.guild.id)
        config["muted_role"] = role.id
        await self.save_guild_config(interaction.guild.id, config)
        
        embed = EmbedBuilder.config_update(
            "Muted Role",
            f"{role.mention}",
            interaction.user
        )
        
        await interaction.response.send_message(embed=embed)
        await self.send_log(interaction.guild, embed)
    
    @vrban.error
    @vrunban.error
    @vrmute.error
    @vrunmute.error
    @vrwarn.error
    @vrunwarn.error
    @vrbypass.error
    @vrsetlog.error
    @vrsetmutedrole.error
    async def command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                embed=EmbedBuilder.error(f"Đã xảy ra lỗi: {str(error)}"),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
