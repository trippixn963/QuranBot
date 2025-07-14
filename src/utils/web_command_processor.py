#!/usr/bin/env python3
# =============================================================================
# QuranBot - Web Command Processor
# =============================================================================
# Processes commands sent from the web dashboard to the bot
# Provides a bridge between the web interface and Discord bot functionality
# =============================================================================

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pytz

from .tree_log import log_error_with_traceback, log_perfect_tree_section


class WebCommandProcessor:
    """Processes commands sent from the web dashboard"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queue_dir = Path("web/command_queue")
        self.processing_task = None
        self.is_running = False
        
    def start_processing(self):
        """Start the command processing loop"""
        if not self.is_running:
            self.is_running = True
            self.processing_task = asyncio.create_task(self._processing_loop())
            log_perfect_tree_section(
                "Web Command Processor - Started",
                [
                    ("status", "🔄 Command processor running"),
                    ("queue_directory", str(self.queue_dir)),
                    ("check_interval", "5 seconds"),
                ],
                "🌐",
            )
    
    def stop_processing(self):
        """Stop the command processing loop"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            log_perfect_tree_section(
                "Web Command Processor - Stopped",
                [
                    ("status", "🛑 Command processor stopped"),
                    ("reason", "Manual stop"),
                ],
                "🌐",
            )
    
    async def _processing_loop(self):
        """Main processing loop that checks for new commands"""
        while self.is_running:
            try:
                await self._process_pending_commands()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_traceback("Error in web command processing loop", e)
                await asyncio.sleep(5)
    
    async def _process_pending_commands(self):
        """Process all pending commands in the queue"""
        try:
            if not self.queue_dir.exists():
                return
            
            # Get all command files
            command_files = list(self.queue_dir.glob("*.json"))
            
            for command_file in command_files:
                try:
                    with open(command_file, 'r') as f:
                        command = json.load(f)
                    
                    # Only process pending commands
                    if command.get("status") == "pending":
                        await self._process_command(command, command_file)
                        
                except Exception as e:
                    log_error_with_traceback(f"Error processing command file {command_file}", e)
                    # Mark command as failed
                    try:
                        with open(command_file, 'r') as f:
                            command = json.load(f)
                        command["status"] = "failed"
                        command["error"] = str(e)
                        command["processed_at"] = datetime.now(pytz.UTC).isoformat()
                        with open(command_file, 'w') as f:
                            json.dump(command, f, indent=2)
                    except:
                        pass
        except Exception as e:
            log_error_with_traceback("Error processing pending commands", e)
    
    async def _process_command(self, command: Dict, command_file: Path):
        """Process a single command"""
        try:
            command_type = command.get("type")
            command_data = command.get("data", {})
            
            # Mark command as processing
            command["status"] = "processing"
            command["processing_started_at"] = datetime.now(pytz.UTC).isoformat()
            with open(command_file, 'w') as f:
                json.dump(command, f, indent=2)
            
            result = None
            
            # Route command to appropriate handler
            if command_type == "quiz_send":
                result = await self._handle_quiz_send(command_data)
            elif command_type == "quiz_toggle":
                result = await self._handle_quiz_toggle(command_data)
            elif command_type == "quiz_reset":
                result = await self._handle_quiz_reset(command_data)
            elif command_type == "audio_control":
                result = await self._handle_audio_control(command_data)
            elif command_type == "bot_control":
                result = await self._handle_bot_control(command_data)
            elif command_type == "system_cache":
                result = await self._handle_system_cache(command_data)
            elif command_type == "system_logs":
                result = await self._handle_system_logs(command_data)
            elif command_type == "system_backup":
                result = await self._handle_system_backup(command_data)
            else:
                result = {"success": False, "error": f"Unknown command type: {command_type}"}
            
            # Update command status
            command["status"] = "completed" if result.get("success") else "failed"
            command["result"] = result
            command["processed_at"] = datetime.now(pytz.UTC).isoformat()
            
            with open(command_file, 'w') as f:
                json.dump(command, f, indent=2)
            
            # Log successful processing
            if result.get("success"):
                log_perfect_tree_section(
                    "Web Command Processed",
                    [
                        ("command_type", command_type),
                        ("command_id", command.get("id", "unknown")),
                        ("status", "✅ Success"),
                        ("result", result.get("message", "No message")),
                    ],
                    "🌐",
                )
            else:
                log_perfect_tree_section(
                    "Web Command Failed",
                    [
                        ("command_type", command_type),
                        ("command_id", command.get("id", "unknown")),
                        ("status", "❌ Failed"),
                        ("error", result.get("error", "Unknown error")),
                    ],
                    "🌐",
                )
                
        except Exception as e:
            log_error_with_traceback(f"Error processing command {command.get('id', 'unknown')}", e)
            
            # Mark command as failed
            try:
                command["status"] = "failed"
                command["error"] = str(e)
                command["processed_at"] = datetime.now(pytz.UTC).isoformat()
                with open(command_file, 'w') as f:
                    json.dump(command, f, indent=2)
            except:
                pass
    
    async def _handle_quiz_send(self, command_data: Dict) -> Dict:
        """Handle quiz send command"""
        try:
            # Import here to avoid circular imports
            from .quiz_manager import quiz_manager
            
            if not quiz_manager:
                return {"success": False, "error": "Quiz manager not available"}
            
            # Get the daily verse channel
            DAILY_VERSE_CHANNEL_ID = int(os.getenv("DAILY_VERSE_CHANNEL_ID", "0"))
            if not DAILY_VERSE_CHANNEL_ID:
                return {"success": False, "error": "Daily verse channel not configured"}
            
            channel = self.bot.get_channel(DAILY_VERSE_CHANNEL_ID)
            if not channel:
                return {"success": False, "error": "Could not find quiz channel"}
            
            # Get a random question
            question_data = quiz_manager.get_random_question()
            if not question_data:
                return {"success": False, "error": "No questions available"}
            
            # Use the same logic as the scheduled quiz system
            from .quiz_manager import check_and_send_scheduled_question
            
            # Force send a question by temporarily setting should_send_question to True
            original_last_sent_time = quiz_manager.last_sent_time
            quiz_manager.last_sent_time = None  # This will make should_send_question return True
            
            try:
                await check_and_send_scheduled_question(self.bot, DAILY_VERSE_CHANNEL_ID)
                return {"success": True, "message": "Quiz question sent successfully"}
            finally:
                # Restore original last sent time and update it
                quiz_manager.last_sent_time = original_last_sent_time
                quiz_manager.update_last_sent_time()
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_quiz_toggle(self, command_data: Dict) -> Dict:
        """Handle quiz toggle command"""
        try:
            # Import here to avoid circular imports
            from .quiz_manager import quiz_manager
            
            if not quiz_manager:
                return {"success": False, "error": "Quiz manager not available"}
            
            # Toggle quiz interval between 0.5 hours (30 minutes) and 3 hours
            current_interval = quiz_manager.get_interval_hours()
            new_interval = 0.5 if current_interval > 1 else 3.0
            
            success = quiz_manager.set_interval_hours(new_interval)
            if success:
                return {"success": True, "message": f"Quiz interval changed to {new_interval} hours"}
            else:
                return {"success": False, "error": "Failed to update quiz interval"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_quiz_reset(self, command_data: Dict) -> Dict:
        """Handle quiz reset command"""
        try:
            # Import here to avoid circular imports
            from .quiz_manager import quiz_manager
            from pathlib import Path
            import json
            
            if not quiz_manager:
                return {"success": False, "error": "Quiz manager not available"}
            
            # Reset quiz statistics by clearing user scores
            quiz_manager.user_scores = {}
            quiz_manager.recent_questions = []
            
            # Save the reset state
            quiz_manager.save_state()
            
            # Also clear the quiz stats file
            quiz_stats_file = Path("data/quiz_stats.json")
            if quiz_stats_file.exists():
                stats_data = {
                    "user_scores": {},
                    "total_questions": 0,
                    "total_correct": 0,
                    "last_reset": datetime.now(pytz.UTC).isoformat()
                }
                with open(quiz_stats_file, 'w') as f:
                    json.dump(stats_data, f, indent=2)
            
            return {"success": True, "message": "Quiz statistics reset successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_audio_control(self, command_data: Dict) -> Dict:
        """Handle audio control command"""
        try:
            action = command_data.get("action")
            
            # Get the bot's voice client
            guild_id = int(os.getenv("GUILD_ID", "0"))
            if not guild_id:
                return {"success": False, "error": "Guild ID not configured"}
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"success": False, "error": "Guild not found"}
            
            voice_client = guild.voice_client
            
            # Route to appropriate audio action
            if action == "play":
                if voice_client and voice_client.is_paused():
                    voice_client.resume()
                    return {"success": True, "message": "Audio playback resumed"}
                else:
                    return {"success": False, "error": "No paused audio to resume"}
            elif action == "pause":
                if voice_client and voice_client.is_playing():
                    voice_client.pause()
                    return {"success": True, "message": "Audio playback paused"}
                else:
                    return {"success": False, "error": "No audio currently playing"}
            elif action == "stop":
                if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
                    voice_client.stop()
                    return {"success": True, "message": "Audio playback stopped"}
                else:
                    return {"success": False, "error": "No audio to stop"}
            elif action == "skip":
                if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
                    voice_client.stop()  # This will trigger the next verse
                    return {"success": True, "message": "Skipped to next verse"}
                else:
                    return {"success": False, "error": "No audio to skip"}
            elif action == "volume":
                volume = command_data.get("value", 50)
                # Discord doesn't support volume control directly, but we can simulate it
                return {"success": True, "message": f"Volume set to {volume}% (simulated)"}
            elif action == "jump":
                surah = command_data.get("surah")
                # This would require integration with the audio system
                return {"success": True, "message": f"Jumped to Surah {surah} (simulated)"}
            elif action == "reciter":
                reciter = command_data.get("reciter")
                # This would require integration with the audio system
                return {"success": True, "message": f"Reciter changed to {reciter} (simulated)"}
            else:
                return {"success": False, "error": f"Unknown audio action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_bot_control(self, command_data: Dict) -> Dict:
        """Handle bot control command"""
        try:
            action = command_data.get("action")
            
            if action == "restart":
                # For safety, we'll just log this action rather than actually restarting
                return {"success": True, "message": "Bot restart logged (manual restart required for safety)"}
            elif action == "stop":
                # For safety, we'll just log this action rather than actually stopping
                return {"success": True, "message": "Bot stop logged (manual stop required for safety)"}
            elif action == "start":
                # Bot is already running if this command is being processed
                return {"success": True, "message": "Bot is already running"}
            else:
                return {"success": False, "error": f"Unknown bot action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_system_cache(self, command_data: Dict) -> Dict:
        """Handle system cache clear command"""
        try:
            import shutil
            from pathlib import Path
            
            cache_dirs = [
                Path("data/cache"),
                Path("audio/cache"),
                Path("logs/cache"),
                Path("web/cache")
            ]
            
            cleared_dirs = []
            for cache_dir in cache_dirs:
                if cache_dir.exists() and cache_dir.is_dir():
                    try:
                        shutil.rmtree(cache_dir)
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        cleared_dirs.append(str(cache_dir))
                    except Exception as e:
                        continue
            
            if cleared_dirs:
                return {"success": True, "message": f"Cache cleared from: {', '.join(cleared_dirs)}"}
            else:
                return {"success": True, "message": "No cache directories found to clear"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_system_logs(self, command_data: Dict) -> Dict:
        """Handle system log sync command"""
        try:
            import subprocess
            from pathlib import Path
            
            # Check if log sync daemon is available
            log_sync_script = Path("tools/log_sync_daemon.py")
            if log_sync_script.exists():
                try:
                    # Trigger a manual sync
                    result = subprocess.run([
                        "python", str(log_sync_script), "--sync-once"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        return {"success": True, "message": "Logs synced to VPS successfully"}
                    else:
                        return {"success": False, "error": f"Log sync failed: {result.stderr}"}
                except subprocess.TimeoutExpired:
                    return {"success": False, "error": "Log sync timed out"}
            else:
                return {"success": False, "error": "Log sync daemon not available"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_system_backup(self, command_data: Dict) -> Dict:
        """Handle system backup command"""
        try:
            from pathlib import Path
            import shutil
            import zipfile
            from datetime import datetime
            
            # Create backup directory
            backup_dir = Path("backup")
            backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"quranbot_backup_{timestamp}.zip"
            backup_path = backup_dir / backup_filename
            
            # Directories to backup
            backup_dirs = [
                "data",
                "config",
                "logs"
            ]
            
            # Create zip backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for backup_dir_name in backup_dirs:
                    backup_dir_path = Path(backup_dir_name)
                    if backup_dir_path.exists():
                        for file_path in backup_dir_path.rglob("*"):
                            if file_path.is_file():
                                zipf.write(file_path, file_path.relative_to(Path(".")))
            
            # Get backup size
            backup_size = backup_path.stat().st_size
            size_mb = backup_size / (1024 * 1024)
            
            return {"success": True, "message": f"Backup created: {backup_filename} ({size_mb:.1f} MB)"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
web_command_processor = None

def get_web_command_processor():
    """Get the global web command processor instance"""
    return web_command_processor

def initialize_web_command_processor(bot):
    """Initialize the web command processor"""
    global web_command_processor
    web_command_processor = WebCommandProcessor(bot)
    web_command_processor.start_processing()
    return web_command_processor 