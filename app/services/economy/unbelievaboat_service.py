"""UnbelievaBoat economy integration service for QuranBot."""

# =============================================================================
# QuranBot - UnbelievaBoat Economy Service
# =============================================================================
# Handles UnbelievaBoat API interactions for economy features
# =============================================================================

import asyncio
import json
from typing import Any, Optional

import aiohttp

from ...config import get_config
from ...core.logger import TreeLogger
from ..core.base_service import BaseService


class UnbelievaBoatService(BaseService):
    """
    UnbelievaBoat economy service for managing virtual currency.

    Features:
    - Add/remove balance via UnbelievaBoat API
    - Check user balance
    - Leaderboard integration
    - Quiz reward distribution
    """

    def __init__(self, bot):
        """Initialize UnbelievaBoat service."""
        super().__init__("UnbelievaBoat")
        self.bot = bot
        self.config = get_config()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API configuration
        self.base_url = "https://unbelievaboat.com/api/v1"
        self.headers = {
            "Authorization": self.config.unbelievaboat_token,
            "Content-Type": "application/json"
        }
        
        TreeLogger.debug(
            "UnbelievaBoat service instance created",
            {"has_token": bool(self.config.unbelievaboat_token)},
            service=self.service_name,
        )

    async def _initialize(self) -> bool:
        """Initialize the UnbelievaBoat service."""
        try:
            TreeLogger.info("Initializing UnbelievaBoat service", service=self.service_name)
            
            # Check if token is configured
            if not self.config.unbelievaboat_token:
                TreeLogger.warning(
                    "UnbelievaBoat token not configured - service disabled",
                    service=self.service_name
                )
                return False
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Test API connection
            test_success = await self._test_connection()
            if not test_success:
                TreeLogger.error(
                    "Failed to connect to UnbelievaBoat API",
                    service=self.service_name
                )
                return False
            
            TreeLogger.info(
                "UnbelievaBoat service initialized",
                {
                    "rewards": {
                        "easy": self.config.quiz_reward_easy,
                        "medium": self.config.quiz_reward_medium,
                        "hard": self.config.quiz_reward_hard,
                    }
                },
                service=self.service_name,
            )
            
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "unbelievaboat_initialization"}
            )
            return False

    async def _start(self) -> bool:
        """Start the UnbelievaBoat service."""
        TreeLogger.info("UnbelievaBoat service started", service=self.service_name)
        return True

    async def _stop(self) -> bool:
        """Stop the UnbelievaBoat service."""
        if self.session:
            await self.session.close()
        TreeLogger.info("UnbelievaBoat service stopped", service=self.service_name)
        return True

    async def _health_check(self) -> dict[str, Any]:
        """Perform health check on UnbelievaBoat service."""
        if not self.config.unbelievaboat_token:
            return {
                "is_healthy": False,
                "has_token": False,
                "api_connected": False,
                "message": "No API token configured"
            }
        
        api_connected = await self._test_connection()
        return {
            "is_healthy": api_connected,
            "has_token": True,
            "api_connected": api_connected,
            "reward_config": {
                "easy": self.config.quiz_reward_easy,
                "medium": self.config.quiz_reward_medium,
                "hard": self.config.quiz_reward_hard,
            }
        }

    async def _test_connection(self) -> bool:
        """Test connection to UnbelievaBoat API."""
        try:
            TreeLogger.debug(
                "Testing UnbelievaBoat API connection",
                {"guild_id": self.config.guild_id},
                service=self.service_name
            )
            
            # Test with guild info endpoint
            url = f"{self.base_url}/guilds/{self.config.guild_id}"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    TreeLogger.debug(
                        "UnbelievaBoat API connection successful",
                        {"status": response.status},
                        service=self.service_name
                    )
                    return True
                else:
                    error_text = await response.text()
                    TreeLogger.warning(
                        "UnbelievaBoat API connection failed",
                        {
                            "status": response.status,
                            "error": error_text[:200],  # Truncate long errors
                            "guild_id": self.config.guild_id
                        },
                        service=self.service_name
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            TreeLogger.error(
                "UnbelievaBoat API network error",
                e,
                {
                    "error_type": type(e).__name__,
                    "guild_id": self.config.guild_id,
                    "traceback": True
                },
                service=self.service_name
            )
            return False
        except Exception as e:
            TreeLogger.error(
                "Unexpected error testing UnbelievaBoat connection",
                e,
                {
                    "error_type": type(e).__name__,
                    "guild_id": self.config.guild_id,
                    "traceback": True
                },
                service=self.service_name
            )
            return False

    async def get_balance(self, user_id: int) -> Optional[dict[str, Any]]:
        """
        Get user's balance from UnbelievaBoat.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Balance info dict or None if error
        """
        try:
            TreeLogger.debug(
                "Fetching user balance from UnbelievaBoat",
                {"user_id": user_id, "guild_id": self.config.guild_id},
                service=self.service_name
            )
            
            url = f"{self.base_url}/guilds/{self.config.guild_id}/users/{user_id}"
            
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    balance_info = {
                        "cash": data.get("cash", 0),
                        "bank": data.get("bank", 0),
                        "total": data.get("total", 0),
                        "rank": data.get("rank")
                    }
                    
                    TreeLogger.debug(
                        "Successfully fetched user balance",
                        {
                            "user_id": user_id,
                            "cash": balance_info["cash"],
                            "bank": balance_info["bank"],
                            "total": balance_info["total"],
                            "rank": balance_info["rank"]
                        },
                        service=self.service_name
                    )
                    
                    return balance_info
                    
                elif response.status == 404:
                    TreeLogger.debug(
                        "User not found in UnbelievaBoat",
                        {"user_id": user_id, "status": response.status},
                        service=self.service_name
                    )
                    # User doesn't exist yet, return default balance
                    return {
                        "cash": 0,
                        "bank": 0,
                        "total": 0,
                        "rank": None
                    }
                    
                else:
                    error_text = await response.text()
                    TreeLogger.warning(
                        "Failed to get balance from UnbelievaBoat",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "error": error_text[:200],
                            "guild_id": self.config.guild_id
                        },
                        service=self.service_name
                    )
                    return None
                    
        except aiohttp.ClientError as e:
            TreeLogger.error(
                "Network error fetching balance",
                e,
                {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "get_balance", "user_id": user_id}
            )
            return None
            
        except json.JSONDecodeError as e:
            TreeLogger.error(
                "Invalid JSON response from UnbelievaBoat",
                e,
                {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "get_balance", "user_id": user_id, "error": "json_decode"}
            )
            return None
            
        except Exception as e:
            TreeLogger.error(
                "Unexpected error getting user balance",
                e,
                {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "get_balance", "user_id": user_id}
            )
            return None

    async def add_balance(self, user_id: int, amount: int, reason: str = "Quiz reward") -> bool:
        """
        Add balance to user's account.
        
        Args:
            user_id: Discord user ID
            amount: Amount to add
            reason: Reason for transaction
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate inputs
            if amount <= 0:
                TreeLogger.warning(
                    "Invalid amount for add_balance",
                    {"user_id": user_id, "amount": amount},
                    service=self.service_name
                )
                return False
                
            url = f"{self.base_url}/guilds/{self.config.guild_id}/users/{user_id}"
            
            data = {
                "cash": amount,
                "reason": reason[:500]  # Truncate reason if too long
            }
            
            TreeLogger.debug(
                "Adding balance to user",
                {
                    "user_id": user_id, 
                    "amount": amount, 
                    "reason": reason,
                    "guild_id": self.config.guild_id
                },
                service=self.service_name
            )
            
            async with self.session.patch(url, headers=self.headers, json=data) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        response_data = json.loads(response_text) if response_text else {}
                        new_balance = response_data.get("cash", "unknown")
                        
                        TreeLogger.info(
                            "Balance added successfully",
                            {
                                "user_id": user_id,
                                "amount": amount,
                                "new_balance": new_balance,
                                "reason": reason[:100]  # Truncate for logging
                            },
                            service=self.service_name
                        )
                    except:
                        # Still successful even if we can't parse response
                        TreeLogger.info(
                            "Balance added successfully (unparseable response)",
                            {"user_id": user_id, "amount": amount},
                            service=self.service_name
                        )
                    return True
                    
                elif response.status == 404:
                    TreeLogger.warning(
                        "User not found in UnbelievaBoat",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "guild_id": self.config.guild_id
                        },
                        service=self.service_name
                    )
                    return False
                    
                elif response.status == 403:
                    TreeLogger.error(
                        "Permission denied for UnbelievaBoat operation",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "error": response_text[:200]
                        },
                        service=self.service_name
                    )
                    return False
                    
                else:
                    TreeLogger.warning(
                        "Failed to add balance",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "error": response_text[:200],
                            "amount": amount
                        },
                        service=self.service_name
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            TreeLogger.error(
                "Network error adding balance",
                e,
                {
                    "user_id": user_id,
                    "amount": amount,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "add_balance", "user_id": user_id, "amount": amount}
            )
            return False
            
        except Exception as e:
            TreeLogger.error(
                "Unexpected error adding balance",
                e,
                {
                    "user_id": user_id,
                    "amount": amount,
                    "reason": reason[:100],
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "add_balance", "user_id": user_id, "amount": amount}
            )
            return False

    async def remove_balance(self, user_id: int, amount: int, reason: str = "Purchase") -> bool:
        """
        Remove balance from user's account.
        
        Args:
            user_id: Discord user ID
            amount: Amount to remove
            reason: Reason for transaction
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate inputs
            if amount <= 0:
                TreeLogger.warning(
                    "Invalid amount for remove_balance",
                    {"user_id": user_id, "amount": amount},
                    service=self.service_name
                )
                return False
                
            # First check if user has enough balance
            current_balance = await self.get_balance(user_id)
            if current_balance and current_balance["cash"] < amount:
                TreeLogger.warning(
                    "Insufficient balance for removal",
                    {
                        "user_id": user_id,
                        "requested_amount": amount,
                        "current_balance": current_balance["cash"]
                    },
                    service=self.service_name
                )
                # Still try to remove (UnbelievaBoat allows negative balance)
                
            url = f"{self.base_url}/guilds/{self.config.guild_id}/users/{user_id}"
            
            data = {
                "cash": -amount,  # Negative amount to remove
                "reason": reason[:500]  # Truncate reason if too long
            }
            
            TreeLogger.debug(
                "Removing balance from user",
                {
                    "user_id": user_id,
                    "amount": amount,
                    "reason": reason,
                    "guild_id": self.config.guild_id
                },
                service=self.service_name
            )
            
            async with self.session.patch(url, headers=self.headers, json=data) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        response_data = json.loads(response_text) if response_text else {}
                        new_balance = response_data.get("cash", "unknown")
                        
                        TreeLogger.info(
                            "Balance removed successfully",
                            {
                                "user_id": user_id,
                                "amount": amount,
                                "new_balance": new_balance,
                                "reason": reason[:100]
                            },
                            service=self.service_name
                        )
                    except:
                        TreeLogger.info(
                            "Balance removed successfully (unparseable response)",
                            {"user_id": user_id, "amount": amount},
                            service=self.service_name
                        )
                    return True
                    
                elif response.status == 404:
                    TreeLogger.warning(
                        "User not found in UnbelievaBoat",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "guild_id": self.config.guild_id
                        },
                        service=self.service_name
                    )
                    return False
                    
                elif response.status == 403:
                    TreeLogger.error(
                        "Permission denied for UnbelievaBoat operation",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "error": response_text[:200]
                        },
                        service=self.service_name
                    )
                    return False
                    
                else:
                    TreeLogger.warning(
                        "Failed to remove balance",
                        {
                            "user_id": user_id,
                            "status": response.status,
                            "error": response_text[:200],
                            "amount": amount
                        },
                        service=self.service_name
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            TreeLogger.error(
                "Network error removing balance",
                e,
                {
                    "user_id": user_id,
                    "amount": amount,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "remove_balance", "user_id": user_id, "amount": amount}
            )
            return False
            
        except Exception as e:
            TreeLogger.error(
                "Unexpected error removing balance",
                e,
                {
                    "user_id": user_id,
                    "amount": amount,
                    "reason": reason[:100],
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "remove_balance", "user_id": user_id, "amount": amount}
            )
            return False

    async def reward_quiz_answer(
        self, 
        user_id: int, 
        difficulty: int, 
        question_text: str,
        response_time: float,
        is_first: bool = False
    ) -> tuple[bool, int]:
        """
        Reward user for correct quiz answer based on difficulty and time.
        
        Args:
            user_id: Discord user ID
            difficulty: Question difficulty (1-5)
            question_text: The question text for transaction reason
            response_time: Time taken to answer in seconds
            is_first: Whether this is the first correct answer
            
        Returns:
            Tuple of (success, reward_amount)
        """
        try:
            # Get base reward amount based on difficulty
            base_reward = self.config.get_quiz_reward(difficulty)
            
            # Calculate time multiplier
            if response_time <= 5:
                time_multiplier = 2.0
                speed_desc = "Lightning Fast"
            elif response_time <= 10:
                time_multiplier = 1.5
                speed_desc = "Quick"
            elif response_time <= 20:
                time_multiplier = 1.0
                speed_desc = "Normal"
            else:
                time_multiplier = 0.75
                speed_desc = "Slow"
            
            # Apply time multiplier
            reward = int(base_reward * time_multiplier)
            
            # Apply first person bonus
            if is_first:
                reward = int(reward * 1.5)
                speed_desc = f"First! {speed_desc}"
            
            # Create descriptive reason
            difficulty_name = "Easy" if difficulty <= 2 else "Medium" if difficulty == 3 else "Hard"
            reason = f"Quiz reward ({difficulty_name} - {difficulty}★) - {speed_desc} ({response_time:.1f}s)"
            
            # Add balance
            success = await self.add_balance(user_id, reward, reason)
            
            if success:
                TreeLogger.info(
                    "Quiz reward distributed",
                    {
                        "user_id": user_id,
                        "difficulty": difficulty,
                        "base_reward": base_reward,
                        "final_reward": reward,
                        "time_multiplier": time_multiplier,
                        "response_time": response_time,
                        "is_first": is_first,
                        "difficulty_name": difficulty_name
                    },
                    service=self.service_name
                )
            
            return success, reward
            
        except ValueError as e:
            TreeLogger.error(
                "Invalid value in reward calculation",
                e,
                {
                    "user_id": user_id,
                    "difficulty": difficulty,
                    "response_time": response_time,
                    "base_reward": base_reward if 'base_reward' in locals() else None,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "reward_quiz_answer", "user_id": user_id, "difficulty": difficulty}
            )
            return False, 0
            
        except Exception as e:
            TreeLogger.error(
                "Unexpected error rewarding quiz answer",
                e,
                {
                    "user_id": user_id,
                    "difficulty": difficulty,
                    "response_time": response_time,
                    "is_first": is_first,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {
                    "operation": "reward_quiz_answer",
                    "user_id": user_id,
                    "difficulty": difficulty,
                    "response_time": response_time,
                    "is_first": is_first
                }
            )
            return False, 0

    async def penalize_wrong_answer(
        self,
        user_id: int,
        difficulty: int,
        response_time: float
    ) -> tuple[bool, int]:
        """
        Penalize user for incorrect quiz answer.
        
        Args:
            user_id: Discord user ID
            difficulty: Question difficulty (1-5)
            response_time: Time taken to answer in seconds
            
        Returns:
            Tuple of (success, penalty_amount)
        """
        try:
            # Get base penalty (50% of reward for that difficulty)
            base_reward = self.config.get_quiz_reward(difficulty)
            base_penalty = int(base_reward * 0.5)
            
            # Calculate time penalty multiplier (opposite of reward)
            if response_time <= 5:
                time_multiplier = 0.5  # Less penalty for quick wrong answers
                speed_desc = "Quick guess"
            elif response_time <= 10:
                time_multiplier = 1.0
                speed_desc = "Wrong answer"
            elif response_time <= 20:
                time_multiplier = 1.5
                speed_desc = "Slow wrong"
            else:
                time_multiplier = 2.0  # More penalty for slow wrong answers
                speed_desc = "Very slow wrong"
            
            # Apply time multiplier
            penalty = int(base_penalty * time_multiplier)
            
            # Create descriptive reason
            difficulty_name = "Easy" if difficulty <= 2 else "Medium" if difficulty == 3 else "Hard"
            reason = f"Quiz penalty ({difficulty_name} - {difficulty}★) - {speed_desc} ({response_time:.1f}s)"
            
            # Remove balance
            success = await self.remove_balance(user_id, penalty, reason)
            
            if success:
                TreeLogger.info(
                    "Quiz penalty applied",
                    {
                        "user_id": user_id,
                        "difficulty": difficulty,
                        "base_penalty": base_penalty,
                        "final_penalty": penalty,
                        "time_multiplier": time_multiplier,
                        "response_time": response_time,
                        "difficulty_name": difficulty_name
                    },
                    service=self.service_name
                )
            
            return success, penalty
            
        except ValueError as e:
            TreeLogger.error(
                "Invalid value in penalty calculation",
                e,
                {
                    "user_id": user_id,
                    "difficulty": difficulty,
                    "response_time": response_time,
                    "base_penalty": base_penalty if 'base_penalty' in locals() else None,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "penalize_wrong_answer", "user_id": user_id, "difficulty": difficulty}
            )
            return False, 0
            
        except Exception as e:
            TreeLogger.error(
                "Unexpected error applying quiz penalty",
                e,
                {
                    "user_id": user_id,
                    "difficulty": difficulty,
                    "response_time": response_time,
                    "error_type": type(e).__name__,
                    "traceback": True
                },
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {
                    "operation": "penalize_wrong_answer",
                    "user_id": user_id,
                    "difficulty": difficulty,
                    "response_time": response_time
                }
            )
            return False, 0

    async def get_leaderboard(self, limit: int = 10) -> Optional[list[dict[str, Any]]]:
        """
        Get economy leaderboard.
        
        Args:
            limit: Number of users to fetch
            
        Returns:
            List of user balance data or None if error
        """
        try:
            url = f"{self.base_url}/guilds/{self.config.guild_id}/users"
            params = {
                "sort": "total",
                "limit": limit
            }
            
            async with self.session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            "user_id": user["user_id"],
                            "rank": user.get("rank", 0),
                            "cash": user.get("cash", 0),
                            "bank": user.get("bank", 0),
                            "total": user.get("total", 0)
                        }
                        for user in data
                    ]
                else:
                    TreeLogger.warning(
                        f"Failed to get leaderboard: {response.status}",
                        service=self.service_name
                    )
                    return None
                    
        except Exception as e:
            TreeLogger.error(
                "Error getting leaderboard",
                e,
                service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "get_leaderboard"}
            )
            return None

    async def _cleanup(self) -> None:
        """Clean up UnbelievaBoat service resources."""
        try:
            TreeLogger.debug(
                "Cleaning up UnbelievaBoat service resources", service=self.service_name
            )
            
            if self.session:
                await self.session.close()
                
            TreeLogger.info(
                "UnbelievaBoat service cleanup completed", service=self.service_name
            )
            
        except Exception as e:
            TreeLogger.error(
                "Error during UnbelievaBoat service cleanup",
                e,
                {"error_type": type(e).__name__},
                service=self.service_name,
            )