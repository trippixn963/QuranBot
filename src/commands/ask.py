# =============================================================================
# QuranBot - Islamic AI Assistant
# =============================================================================
# AI-powered Islamic Q&A with proper disclaimers and safeguards
# =============================================================================

import os
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_config_service
from src.utils.tree_log import log_perfect_tree_section, log_error_with_traceback

# Islamic AI Assistant Configuration
ISLAMIC_SYSTEM_PROMPT = """You are an Islamic AI assistant helping Muslims with questions about Islam. 

IMPORTANT GUIDELINES:
1. Always provide authentic Islamic information based on Quran and authentic Hadith
2. When unsure, clearly state "I'm not certain" and suggest consulting scholars
3. Never issue fatwas or religious rulings - direct users to qualified scholars
4. Be respectful of all Islamic schools of thought (madhabs)
5. Include relevant Quranic verses or Hadith references when possible
6. If asked about non-Islamic topics, politely redirect to Islamic matters
7. Always emphasize the importance of seeking knowledge from qualified scholars

DISCLAIMER TO INCLUDE:
"⚠️ This is AI-generated information. For important religious matters, please consult qualified Islamic scholars."

Format your responses clearly and include Islamic greetings when appropriate."""


class IslamicAIAssistant:
    """Handles AI-powered Islamic Q&A"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            log_perfect_tree_section(
                "Islamic AI Assistant - Configuration",
                [
                    ("status", "⚠️ OpenAI API key not found"),
                    ("feature", "Disabled"),
                    ("action", "Set OPENAI_API_KEY to enable")
                ],
                "🤖"
            )
    
    async def get_islamic_response(self, question: str, user_name: str) -> str:
        """Get AI response to Islamic question"""
        if not self.enabled:
            return ("🤖 **AI Assistant Currently Unavailable**\n\n"
                   "The Islamic AI assistant requires OpenAI API configuration. "
                   "Please contact the administrator.\n\n"
                   "⚠️ For Islamic guidance, please consult qualified scholars.")
        
        try:
            # This is a placeholder for OpenAI integration
            # You'll need to install: pip install openai
            # And implement the actual OpenAI API call here
            
            """
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": ISLAMIC_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Assalamu alaikum. My name is {user_name}. {question}"}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            """
            
            # Placeholder response for now
            return (f"🤖 **AI Assistant Response** (Demo Mode)\n\n"
                   f"Wa alaikum assalam, {user_name}!\n\n"
                   f"Thank you for your question: *{question}*\n\n"
                   f"**This feature is currently in development.** Once configured with OpenAI API, "
                   f"this will provide authentic Islamic guidance based on Quran and Sunnah.\n\n"
                   f"⚠️ **Important**: This is AI-generated information. For important religious "
                   f"matters, please consult qualified Islamic scholars.\n\n"
                   f"🔗 **Recommended**: Contact your local mosque or Islamic center for guidance.")
            
        except Exception as e:
            log_error_with_traceback("Error in Islamic AI assistant", e)
            return ("❌ **Error Processing Question**\n\n"
                   "There was an error processing your question. Please try again later.\n\n"
                   "⚠️ For Islamic guidance, please consult qualified scholars.")


class AskCog(commands.Cog):
    """Islamic AI Assistant commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ai_assistant = IslamicAIAssistant()
    
    @app_commands.command(
        name="ask",
        description="Ask the Islamic AI assistant a question about Islam"
    )
    @app_commands.describe(
        question="Your Islamic question (about Quran, Hadith, Islamic practices, etc.)"
    )
    async def ask(
        self,
        interaction: discord.Interaction,
        question: str
    ):
        """Ask the Islamic AI assistant"""
        
        # Basic question validation
        if len(question.strip()) < 5:
            embed = discord.Embed(
                title="❌ Question Too Short",
                description="Please provide a more detailed question about Islam.",
                color=0xFF6B6B
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if len(question) > 500:
            embed = discord.Embed(
                title="❌ Question Too Long",
                description="Please keep your question under 500 characters.",
                color=0xFF6B6B
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        log_perfect_tree_section(
            "Islamic AI Assistant - Question",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("question_length", str(len(question))),
                ("channel", f"#{interaction.channel.name}"),
                ("guild", interaction.guild.name if interaction.guild else "DM")
            ],
            "🤖"
        )
        
        # Acknowledge the question (AI responses can take time)
        await interaction.response.defer()
        
        try:
            # Get AI response
            response = await self.ai_assistant.get_islamic_response(
                question, 
                interaction.user.display_name
            )
            
            # Create response embed
            embed = discord.Embed(
                title="🤖 Islamic AI Assistant",
                description=response,
                color=0x1ABC9C,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="❓ Your Question",
                value=f"```{question}```",
                inline=False
            )
            
            # Set bot thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            
            # Set footer with admin profile picture
            try:
                config = get_config_service().config
                admin_user = await self.bot.fetch_user(config.DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا • AI Assistant",
                        icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا • AI Assistant")
            except:
                embed.set_footer(text="Created by حَـــــنَـــــا • AI Assistant")
            
            # Send response
            await interaction.followup.send(embed=embed)
            
            # Add thinking emoji reaction
            try:
                message = await interaction.original_response()
                await message.add_reaction("🤔")
            except:
                pass
            
            log_perfect_tree_section(
                "Islamic AI Assistant - Response Sent",
                [
                    ("user", interaction.user.display_name),
                    ("response_length", str(len(response))),
                    ("status", "✅ Response delivered")
                ],
                "🤖"
            )
            
        except Exception as e:
            log_error_with_traceback("Error in ask command", e)
            
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while processing your question. Please try again later.\n\n"
                           "⚠️ For Islamic guidance, please consult qualified scholars.",
                color=0xFF6B6B
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Set up the ask cog"""
    await bot.add_cog(AskCog(bot)) 