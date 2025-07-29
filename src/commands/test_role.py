#!/usr/bin/env python3
# =============================================================================
# QuranBot - Test Role Management Command
# =============================================================================
# A developer command to test and verify role management functionality.
# This command helps debug role assignment and removal issues.
# =============================================================================

import discord
from discord.ext import commands
from src.core.structured_logger import StructuredLogger
from src.config.config_service import ConfigService


class TestRoleCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = StructuredLogger(name="test_role")

    @commands.slash_command(
        name="test_role",
        description="[DEV] Test role management system consistency"
    )
    @commands.has_permissions(administrator=True)
    async def test_role(self, ctx):
        """Test and verify role management system."""
        try:
            await ctx.defer()

            # Get configuration
            config_service = ConfigService()
            
            # Get guild-specific settings
            target_channel_id = config_service.get_target_channel_id(ctx.guild.id)
            panel_access_role_id = config_service.get_panel_access_role_id()
            
            if not target_channel_id:
                await ctx.followup.send("❌ Target voice channel not configured for this guild.")
                return
                
            if not panel_access_role_id:
                await ctx.followup.send("❌ Panel access role not configured.")
                return

            # Get the role
            panel_role = ctx.guild.get_role(panel_access_role_id)
            if not panel_role:
                await ctx.followup.send(f"❌ Panel access role not found (ID: {panel_access_role_id}).")
                return

            # Get the target voice channel
            target_channel = ctx.guild.get_channel(target_channel_id)
            if not target_channel:
                await ctx.followup.send(f"❌ Target voice channel not found (ID: {target_channel_id}).")
                return

            # Check all guild members for role consistency
            inconsistent_users = []
            users_in_channel = []
            users_with_role = []
            
            for member in ctx.guild.members:
                if member.bot:
                    continue
                    
                has_role = panel_role in member.roles
                in_quran_vc = (member.voice and 
                             member.voice.channel and 
                             member.voice.channel.id == target_channel_id)
                
                if has_role:
                    users_with_role.append(member.display_name)
                    
                if in_quran_vc:
                    users_in_channel.append(member.display_name)
                
                # Check for inconsistency
                if has_role and not in_quran_vc:
                    inconsistent_users.append({
                        'user': member.display_name,
                        'user_id': member.id,
                        'has_role': has_role,
                        'in_channel': in_quran_vc,
                        'current_channel': member.voice.channel.name if member.voice else "None"
                    })

            # Create detailed report
            embed = discord.Embed(
                title="🔧 Role Management System Test",
                description=f"Testing role consistency for **{panel_role.name}**",
                color=0x00ff00 if not inconsistent_users else 0xff9900
            )
            
            embed.add_field(
                name="📊 Statistics",
                value=f"• Users in {target_channel.name}: **{len(users_in_channel)}**\n"
                      f"• Users with role: **{len(users_with_role)}**\n"
                      f"• Inconsistent users: **{len(inconsistent_users)}**",
                inline=False
            )
            
            if users_in_channel:
                embed.add_field(
                    name=f"👥 Users in {target_channel.name}",
                    value="\n".join([f"• {user}" for user in users_in_channel[:10]]) + 
                          (f"\n• ... and {len(users_in_channel) - 10} more" if len(users_in_channel) > 10 else ""),
                    inline=True
                )
            
            if users_with_role:
                embed.add_field(
                    name=f"🎭 Users with {panel_role.name}",
                    value="\n".join([f"• {user}" for user in users_with_role[:10]]) + 
                          (f"\n• ... and {len(users_with_role) - 10} more" if len(users_with_role) > 10 else ""),
                    inline=True
                )

            if inconsistent_users:
                embed.add_field(
                    name="⚠️ Inconsistent Users",
                    value="\n".join([
                        f"• **{user['user']}** - Has role but in: `{user['current_channel']}`"
                        for user in inconsistent_users[:5]
                    ]) + (f"\n• ... and {len(inconsistent_users) - 5} more" if len(inconsistent_users) > 5 else ""),
                    inline=False
                )
                
                embed.add_field(
                    name="🔧 Cleanup Action",
                    value="The system will automatically remove roles from inconsistent users within 30 minutes via the periodic cleanup task.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="All roles are consistent! No cleanup needed.",
                    inline=False
                )

            embed.set_footer(text=f"Test performed by {ctx.author.display_name}")
            await ctx.followup.send(embed=embed)
            
            # Log the test
            await self.logger.info(
                "Role management system test performed",
                {
                    "guild_id": ctx.guild.id,
                    "tester": ctx.author.display_name,
                    "users_in_channel": len(users_in_channel),
                    "users_with_role": len(users_with_role),
                    "inconsistent_users": len(inconsistent_users)
                }
            )

        except Exception as e:
            await self.logger.error("Error in test role command", {"error": str(e)})
            await ctx.followup.send(f"❌ Error testing role system: {str(e)}")


def setup(bot):
    bot.add_cog(TestRoleCommand(bot)) 