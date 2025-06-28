"""Miss Lisa Telegram Bot - Main bot implementation"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

from gemini_client import GeminiClient
from conversation_manager import ConversationManager
from config import Config

logger = logging.getLogger(__name__)

class MissLisaBot:
    def __init__(self, telegram_token: str, gemini_api_key: str):
        self.telegram_token = telegram_token
        self.gemini_client = GeminiClient(gemini_api_key)
        self.conversation_manager = ConversationManager()
        
        # Initialize Telegram application
        self.application = Application.builder().token(telegram_token).build()
        
        # Add handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup bot command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("memory", self.memory_command))
        
        # Message handler for regular conversations
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "gorgeous"
        
        # Update user profile
        self.conversation_manager.update_user_profile(user_id, user_name)
        
        await update.message.reply_text(
            Config.WELCOME_MESSAGE,
            parse_mode='Markdown'
        )
        
        logger.info(f"User {user_id} ({user_name}) started the bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            Config.HELP_MESSAGE,
            parse_mode='Markdown'
        )
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id
        
        # Clear conversation history
        self.conversation_manager.clear_conversation_history(user_id)
        
        await update.message.reply_text(Config.PROFILE_CLEARED)
        
        logger.info(f"User {user_id} cleared their conversation history")
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        user_id = update.effective_user.id
        
        profile_summary = self.conversation_manager.format_profile_summary(user_id)
        
        await update.message.reply_text(
            profile_summary,
            parse_mode='Markdown'
        )
    
    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory command"""
        user_id = update.effective_user.id
        
        memories_display = self.conversation_manager.format_memories_display(user_id)
        
        await update.message.reply_text(
            memories_display,
            parse_mode='Markdown'
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "gorgeous"
        message_text = update.message.text
        
        try:
            # Check rate limiting
            if not self.conversation_manager.check_rate_limit(user_id):
                await update.message.reply_text(Config.ERROR_MESSAGES['rate_limit'])
                return
            
            # Get conversation context
            conversation_history = self.conversation_manager.get_conversation_history(user_id)
            user_profile = self.conversation_manager.get_user_profile(user_id)
            
            # Generate response using Gemini
            bot_response = await self.gemini_client.generate_response(
                message_text, 
                conversation_history, 
                user_profile
            )
            
            # Send response
            await update.message.reply_text(bot_response)
            
            # Save conversation
            self.conversation_manager.add_conversation_entry(
                user_id, message_text, bot_response, user_name
            )
            
            # Extract and save memories asynchronously
            asyncio.create_task(self._extract_and_save_memories(
                user_id, message_text, bot_response
            ))
            
            # Auto cleanup memories for this user if needed
            self.conversation_manager.auto_cleanup_memories_for_user(user_id)
            
            logger.info(f"Processed message from user {user_id}: {len(message_text)} chars")
            
        except Exception as e:
            logger.error(f"Error handling message from user {user_id}: {e}")
            await update.message.reply_text(Config.ERROR_MESSAGES['general_error'])
    
    async def _extract_and_save_memories(self, user_id: int, user_message: str, bot_response: str):
        """Extract and save memories from conversation (async)"""
        try:
            memories = await self.gemini_client.extract_memories(user_message, bot_response)
            if memories:
                self.conversation_manager.add_memories(user_id, memories)
                logger.info(f"Extracted {len(memories)} memories for user {user_id}")
        except Exception as e:
            logger.error(f"Error extracting memories for user {user_id}: {e}")
    
    async def error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    Config.ERROR_MESSAGES['general_error']
                )
            except TelegramError:
                logger.error("Failed to send error message to user")
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Miss Lisa Bot application...")
        
        # Start cleanup task
        asyncio.create_task(self._periodic_cleanup())
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        logger.info("Miss Lisa Bot is now running...")
        
        # Keep the bot running
        try:
            await self.application.updater.idle()
        except AttributeError:
            # For newer versions of python-telegram-bot
            import signal
            import sys
            
            def signal_handler(sig, frame):
                logger.info("Bot stopped by signal")
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        
        # Cleanup on shutdown
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old conversations"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                self.conversation_manager.cleanup_old_conversations()
                self.conversation_manager.cleanup_old_memories()
                logger.info("Completed periodic cleanup of conversations and memories")
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
