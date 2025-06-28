#!/usr/bin/env python3
"""
Main entry point for Miss Lisa Telegram Bot
"""
import asyncio
import logging
import os
import sys
from bot import MissLisaBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    try:
        # Validate environment variables
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
            sys.exit(1)
            
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY environment variable is required")
            sys.exit(1)
        
        logger.info("Starting Miss Lisa Bot...")
        
        # Initialize and start the bot
        bot = MissLisaBot(telegram_token, gemini_api_key)
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
