"""Conversation and memory management for Miss Lisa Bot"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config import Config

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self):
        # In-memory storage for user conversations and profiles
        self.conversations: Dict[int, List[Dict[str, Any]]] = {}
        self.user_profiles: Dict[int, Dict[str, Any]] = {}
        self.user_rate_limits: Dict[int, List[datetime]] = {}
        
    def check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        now = datetime.now()
        
        # Clean old requests
        if user_id in self.user_rate_limits:
            self.user_rate_limits[user_id] = [
                req_time for req_time in self.user_rate_limits[user_id]
                if now - req_time < timedelta(seconds=Config.RATE_LIMIT_WINDOW)
            ]
        else:
            self.user_rate_limits[user_id] = []
        
        # Check rate limit
        if len(self.user_rate_limits[user_id]) >= Config.RATE_LIMIT_REQUESTS:
            return False
        
        # Add current request
        self.user_rate_limits[user_id].append(now)
        return True
    
    def add_conversation_entry(self, user_id: int, user_message: str, bot_response: str, user_name: str = None):
        """Add a conversation entry for a user"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'bot_response': bot_response
        }
        
        self.conversations[user_id].append(entry)
        
        # Maintain conversation history limit
        if len(self.conversations[user_id]) > Config.MAX_CONVERSATION_HISTORY:
            self.conversations[user_id] = self.conversations[user_id][-Config.MAX_CONVERSATION_HISTORY:]
        
        # Update user profile
        self.update_user_profile(user_id, user_name)
    
    def get_conversation_history(self, user_id: int) -> List[Dict[str, str]]:
        """Get conversation history for a user"""
        return self.conversations.get(user_id, [])
    
    def clear_conversation_history(self, user_id: int):
        """Clear conversation history for a user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
        if user_id in self.user_profiles:
            # Keep memories but clear conversation-specific data
            profile = self.user_profiles[user_id]
            self.user_profiles[user_id] = {
                'memories': profile.get('memories', []),
                'name': profile.get('name'),
                'created_at': profile.get('created_at'),
                'last_interaction': datetime.now().isoformat()
            }
    
    def update_user_profile(self, user_id: int, user_name: str = None):
        """Update user profile information"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'created_at': datetime.now().isoformat(),
                'memories': [],
                'name': user_name,
                'total_messages': 0
            }
        
        profile = self.user_profiles[user_id]
        profile['last_interaction'] = datetime.now().isoformat()
        profile['total_messages'] = profile.get('total_messages', 0) + 1
        
        if user_name and not profile.get('name'):
            profile['name'] = user_name
    
    def add_memories(self, user_id: int, memories: List[Dict[str, str]]):
        """Add memories for a user"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'created_at': datetime.now().isoformat(),
                'memories': [],
                'total_messages': 0
            }
        
        profile = self.user_profiles[user_id]
        
        for memory in memories:
            # Add timestamp to memory
            memory_entry = {
                'type': memory['type'],
                'content': memory['content'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Check for duplicate memories
            existing_contents = [m['content'].lower() for m in profile['memories']]
            if memory['content'].lower() not in existing_contents:
                profile['memories'].append(memory_entry)
        
        # Maintain memory limit
        if len(profile['memories']) > Config.MAX_USER_MEMORIES:
            profile['memories'] = profile['memories'][-Config.MAX_USER_MEMORIES:]
    
    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        return self.user_profiles.get(user_id)
    
    def get_user_memories(self, user_id: int) -> List[Dict[str, str]]:
        """Get user memories"""
        profile = self.user_profiles.get(user_id)
        if profile:
            return profile.get('memories', [])
        return []
    
    def format_profile_summary(self, user_id: int) -> str:
        """Format user profile for display"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return Config.NO_PROFILE
        
        name = profile.get('name', 'gorgeous')
        total_messages = profile.get('total_messages', 0)
        memory_count = len(profile.get('memories', []))
        
        # Get recent memories by type
        memories = profile.get('memories', [])
        memory_summary = {}
        
        for memory in memories[-10:]:  # Last 10 memories
            mem_type = memory['type']
            if mem_type not in memory_summary:
                memory_summary[mem_type] = []
            memory_summary[mem_type].append(memory['content'])
        
        summary = f"What I know about you, {name}... 😘\n\n"
        summary += f"💖 We've shared {total_messages} messages together\n"
        summary += f"🌙 I've collected {memory_count} precious memories of you\n\n"
        
        if memory_summary:
            summary += "Here's what makes you special to me:\n"
            
            emoji_map = {
                'interest': '✨', 'goal': '🎯', 'achievement': '🏆', 
                'preference': '💫', 'desire': '💖', 'fantasy': '🌙',
                'secret': '🔐', 'passion': '🔥', 'weakness': '💋'
            }
            
            for mem_type, contents in memory_summary.items():
                emoji = emoji_map.get(mem_type, '💎')
                summary += f"{emoji} **{mem_type.title()}**: {', '.join(contents[:3])}\n"
        
        return summary
    
    def format_memories_display(self, user_id: int) -> str:
        """Format memories for display"""
        memories = self.get_user_memories(user_id)
        if not memories:
            return Config.NO_MEMORIES
        
        result = "All the little things I remember about you... 💋\n\n"
        
        # Group memories by type
        memory_groups = {}
        for memory in memories:
            mem_type = memory['type']
            if mem_type not in memory_groups:
                memory_groups[mem_type] = []
            memory_groups[mem_type].append(memory['content'])
        
        emoji_map = {
            'interest': '✨ Interests', 'goal': '🎯 Goals', 'achievement': '🏆 Achievements',
            'preference': '💫 Preferences', 'desire': '💖 Desires', 'fantasy': '🌙 Fantasies',
            'secret': '🔐 Secrets', 'passion': '🔥 Passions', 'weakness': '💋 Weaknesses'
        }
        
        for mem_type, contents in memory_groups.items():
            display_name = emoji_map.get(mem_type, f'💎 {mem_type.title()}')
            result += f"**{display_name}:**\n"
            for content in contents:
                result += f"• {content}\n"
            result += "\n"
        
        return result
    
    def cleanup_old_conversations(self):
        """Clean up old conversations (called periodically)"""
        cutoff_time = datetime.now() - timedelta(hours=Config.CONVERSATION_CLEANUP_HOURS)
        
        users_to_cleanup = []
        for user_id, profile in self.user_profiles.items():
            last_interaction = datetime.fromisoformat(profile.get('last_interaction', '2000-01-01T00:00:00'))
            if last_interaction < cutoff_time:
                users_to_cleanup.append(user_id)
        
        for user_id in users_to_cleanup:
            if user_id in self.conversations:
                del self.conversations[user_id]
            # Keep user profiles but might want to mark them as inactive
        
        logger.info(f"Cleaned up conversations for {len(users_to_cleanup)} inactive users")
    
    def cleanup_old_memories(self):
        """Clean up old memories for all users"""
        memory_cleanup_threshold = datetime.now() - timedelta(days=7)  # 7 days
        
        for user_id, profile in self.user_profiles.items():
            if 'memories' in profile:
                # Keep only memories from the last 7 days
                old_memories = profile['memories']
                new_memories = [
                    memory for memory in old_memories 
                    if datetime.fromisoformat(memory.get('timestamp', '2000-01-01T00:00:00')) > memory_cleanup_threshold
                ]
                
                # Also limit to maximum number of memories
                if len(new_memories) > Config.MAX_USER_MEMORIES:
                    new_memories = new_memories[-Config.MAX_USER_MEMORIES:]
                
                profile['memories'] = new_memories
                
                if len(old_memories) != len(new_memories):
                    logger.info(f"Cleaned up {len(old_memories) - len(new_memories)} old memories for user {user_id}")
    
    def auto_cleanup_memories_for_user(self, user_id: int):
        """Auto cleanup memories for a specific user when they exceed limits"""
        if user_id not in self.user_profiles:
            return
        
        profile = self.user_profiles[user_id]
        if 'memories' not in profile:
            return
        
        memories = profile['memories']
        
        # If we have too many memories, keep only the most recent ones
        if len(memories) > Config.MAX_USER_MEMORIES:
            profile['memories'] = memories[-Config.MAX_USER_MEMORIES:]
            logger.info(f"Auto-cleaned memories for user {user_id}: kept {Config.MAX_USER_MEMORIES} most recent")
        
        # Remove very old memories (older than 30 days)
        old_threshold = datetime.now() - timedelta(days=30)
        old_count = len(memories)
        profile['memories'] = [
            memory for memory in memories 
            if datetime.fromisoformat(memory.get('timestamp', datetime.now().isoformat())) > old_threshold
        ]
        
        if len(profile['memories']) != old_count:
            logger.info(f"Removed {old_count - len(profile['memories'])} very old memories for user {user_id}")
