"""QuranBot - Backup Manager Command.

Provides Discord slash commands for managing data backups and integrity.
Allows creating backups, restoring from backups, and checking data integrity.

This module provides commands for:
- Creating manual backups
- Listing available backups
- Restoring from backups
- Checking data integrity
- Viewing backup statistics

Commands:
    /backup create - Create a new backup
    /backup list - List available backups
    /backup restore - Restore from a backup
    /backup integrity - Check data integrity
    /backup stats - View backup statistics
"""

from datetime import datetime
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from ..core.logger import StructuredLogger
from ..services.data_manager import HybridDataManager


class BackupManagerCog(commands.Cog):
    """Backup management commands."""

    def __init__(
        self,
        bot: commands.Bot,
        data_manager: HybridDataManager,
        logger: StructuredLogger,
    ):
        self.bot = bot
        self.data_manager = data_manager
        self.logger = logger

    @app_commands.command(name="backup", description="Manage data backups")
    @app_commands.describe(
        action="Action to perform (create, list, restore, integrity, stats)",
        backup_id="Backup ID for restore operation",
    )
    async def backup_command(
        self,
        interaction: discord.Interaction,
        action: str,
        backup_id: str | None = None,
    ):
        """Main backup management command."""

        # Check permissions (only bot owner can manage backups)
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message(
                "❌ Only the bot owner can manage backups.", ephemeral=True
            )
            return

        try:
            if action.lower() == "create":
                await self._create_backup(interaction)
            elif action.lower() == "list":
                await self._list_backups(interaction)
            elif action.lower() == "restore":
                await self._restore_backup(interaction, backup_id)
            elif action.lower() == "integrity":
                await self._check_integrity(interaction)
            elif action.lower() == "stats":
                await self._backup_stats(interaction)
            else:
                await interaction.response.send_message(
                    f"❌ Unknown action: {action}. Use: create, list, restore, integrity, stats",
                    ephemeral=True,
                )

        except Exception as e:
            await self.logger.error(
                "Backup command error", {"error": str(e), "action": action}
            )
            await interaction.response.send_message(f"❌ Error: {e!s}", ephemeral=True)

    async def _create_backup(self, interaction: discord.Interaction):
        """Create a new backup."""
        await interaction.response.defer(thinking=True)

        try:
            backup_path = await self.data_manager.create_backup()

            if backup_path:
                # Get backup info
                manifest_path = backup_path / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)

                embed = discord.Embed(
                    title="✅ Backup Created Successfully",
                    description=f"**Backup ID:** `{backup_path.name}`",
                    color=0x00FF00,
                )
                embed.add_field(
                    name="Timestamp",
                    value=manifest.get("backup_timestamp", "Unknown"),
                    inline=True,
                )
                embed.add_field(
                    name="SQLite Size",
                    value=f"{manifest.get('sqlite_size', 0):,} bytes",
                    inline=True,
                )
                embed.add_field(
                    name="JSON Files",
                    value=str(manifest.get("total_files", 0)),
                    inline=True,
                )
                embed.add_field(
                    name="Backup Path", value=str(backup_path), inline=False
                )

                await interaction.followup.send(embed=embed)

                await self.logger.info(
                    "Backup created",
                    {
                        "backup_id": backup_path.name,
                        "created_by": interaction.user.display_name,
                        "sqlite_size": manifest.get("sqlite_size", 0),
                        "json_files": manifest.get("total_files", 0),
                    },
                )
            else:
                await interaction.followup.send("❌ Failed to create backup")

        except Exception as e:
            await interaction.followup.send(f"❌ Backup creation failed: {e!s}")

    async def _list_backups(self, interaction: discord.Interaction):
        """List available backups."""
        backup_dir = Path("data/backups")

        if not backup_dir.exists():
            await interaction.response.send_message("No backups found.", ephemeral=True)
            return

        backups = []
        for backup_path in backup_dir.glob("backup_*"):
            if backup_path.is_dir():
                manifest_path = backup_path / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)

                        backups.append(
                            {
                                "id": backup_path.name,
                                "timestamp": manifest.get(
                                    "backup_timestamp", "Unknown"
                                ),
                                "sqlite_size": manifest.get("sqlite_size", 0),
                                "json_files": manifest.get("total_files", 0),
                                "path": backup_path,
                            }
                        )
                    except Exception:
                        # Skip corrupted manifests
                        continue

        if not backups:
            await interaction.response.send_message(
                "No valid backups found.", ephemeral=True
            )
            return

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)

        embed = discord.Embed(
            title=f"📁 Available Backups ({len(backups)})",
            description="List of all available backups",
            color=0x0099FF,
        )

        for backup in backups[:10]:  # Show latest 10
            timestamp = backup["timestamp"]
            if timestamp != "Unknown":
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass

            embed.add_field(
                name=f"🔹 {backup['id']}",
                value=f"**Time:** {timestamp}\n"
                f"**SQLite:** {backup['sqlite_size']:,} bytes\n"
                f"**Files:** {backup['json_files']}",
                inline=False,
            )

        if len(backups) > 10:
            embed.add_field(
                name="More Backups",
                value=f"... and {len(backups) - 10} more backups",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    async def _restore_backup(
        self, interaction: discord.Interaction, backup_id: str | None
    ):
        """Restore from a backup."""
        if not backup_id:
            await interaction.response.send_message(
                "❌ Please provide a backup ID to restore from.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            backup_path = Path("data/backups") / backup_id

            if not backup_path.exists():
                await interaction.followup.send(f"❌ Backup `{backup_id}` not found.")
                return

            # Confirm restoration
            embed = discord.Embed(
                title="⚠️ Confirm Backup Restoration",
                description=f"Are you sure you want to restore from backup `{backup_id}`?\n\n"
                f"**This will overwrite all current data!**\n\n"
                f"React with ✅ to confirm or ❌ to cancel.",
                color=0xFF9900,
            )

            message = await interaction.followup.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            # Wait for confirmation (30 seconds)
            def check(reaction, user):
                return (
                    user == interaction.user
                    and reaction.message.id == message.id
                    and str(reaction.emoji) in ["✅", "❌"]
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                if str(reaction.emoji) == "✅":
                    # Perform restoration
                    success = await self.data_manager.restore_backup(backup_path)

                    if success:
                        await interaction.followup.send(
                            f"✅ Successfully restored from backup `{backup_id}`\n"
                            f"**Please restart the bot to apply changes.**"
                        )

                        await self.logger.info(
                            "Backup restored",
                            {
                                "backup_id": backup_id,
                                "restored_by": interaction.user.display_name,
                            },
                        )
                    else:
                        await interaction.followup.send(
                            f"❌ Failed to restore from backup `{backup_id}`"
                        )
                else:
                    await interaction.followup.send("❌ Backup restoration cancelled.")

            except TimeoutError:
                await interaction.followup.send("⏰ Backup restoration timed out.")

        except Exception as e:
            await interaction.followup.send(f"❌ Restoration failed: {e!s}")

    async def _check_integrity(self, interaction: discord.Interaction):
        """Check data integrity."""
        await interaction.response.defer(thinking=True)

        try:
            integrity_report = await self.data_manager.verify_data_integrity()

            embed = discord.Embed(
                title="🔍 Data Integrity Report",
                description=f"**Overall Status:** {integrity_report['overall_status'].upper()}",
                color=self._get_integrity_color(integrity_report["overall_status"]),
            )

            # SQLite status
            sqlite_status = (
                "✅ Healthy" if integrity_report["sqlite_integrity"] else "❌ Corrupted"
            )
            embed.add_field(name="🗄️ SQLite Database", value=sqlite_status, inline=True)

            # JSON files status
            json_files = integrity_report["json_files"]
            healthy_files = sum(
                1 for f in json_files.values() if f.get("valid_json", False)
            )
            total_files = len(json_files)

            json_status = f"✅ {healthy_files}/{total_files} Healthy"
            if healthy_files < total_files:
                json_status = f"⚠️ {healthy_files}/{total_files} Healthy"

            embed.add_field(name="📄 JSON Files", value=json_status, inline=True)

            # Detailed JSON status
            for content_type, status in json_files.items():
                if not status.get("valid_json", False):
                    embed.add_field(
                        name=f"❌ {content_type}",
                        value="Corrupted or missing",
                        inline=False,
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Integrity check failed: {e!s}")

    async def _backup_stats(self, interaction: discord.Interaction):
        """View backup statistics."""
        backup_dir = Path("data/backups")

        if not backup_dir.exists():
            await interaction.response.send_message(
                "No backup statistics available.", ephemeral=True
            )
            return

        backups = []
        total_size = 0

        for backup_path in backup_dir.glob("backup_*"):
            if backup_path.is_dir():
                manifest_path = backup_path / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)

                        size = manifest.get("sqlite_size", 0)
                        total_size += size

                        backups.append(
                            {
                                "timestamp": manifest.get(
                                    "backup_timestamp", "Unknown"
                                ),
                                "size": size,
                            }
                        )
                    except Exception:
                        continue

        if not backups:
            await interaction.response.send_message(
                "No backup statistics available.", ephemeral=True
            )
            return

        # Calculate stats
        oldest_backup = min(backups, key=lambda x: x["timestamp"])
        newest_backup = max(backups, key=lambda x: x["timestamp"])
        avg_size = total_size / len(backups)

        embed = discord.Embed(
            title="📊 Backup Statistics",
            description=f"Statistics for {len(backups)} backups",
            color=0x0099FF,
        )

        embed.add_field(name="Total Backups", value=str(len(backups)), inline=True)
        embed.add_field(name="Total Size", value=f"{total_size:,} bytes", inline=True)
        embed.add_field(
            name="Average Size", value=f"{avg_size:,.0f} bytes", inline=True
        )
        embed.add_field(
            name="Oldest Backup", value=oldest_backup["timestamp"][:10], inline=True
        )
        embed.add_field(
            name="Newest Backup", value=newest_backup["timestamp"][:10], inline=True
        )
        embed.add_field(name="Backup Frequency", value="Manual", inline=True)

        await interaction.response.send_message(embed=embed)

    def _get_integrity_color(self, status: str) -> int:
        """Get embed color based on integrity status."""
        colors = {
            "healthy": 0x00FF00,  # Green
            "degraded": 0xFFAA00,  # Orange
            "corrupted": 0xFF0000,  # Red
            "error": 0xFF0000,  # Red
        }
        return colors.get(status.lower(), 0x999999)


async def setup(bot, container=None):
    """Setup the backup manager cog."""
    try:
        # Get data manager from container
        data_manager = container.get("HybridDataManager") if container else None
        logger = container.get("StructuredLogger") if container else None
        
        await bot.add_cog(BackupManagerCog(bot, data_manager, logger))
    except Exception as e:
        # Fallback if container or services not available
        await bot.add_cog(BackupManagerCog(bot, None, None))
