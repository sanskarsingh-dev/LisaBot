"""Google Gemini AI client for Miss Lisa Bot"""
import logging
import os
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = Config.GEMINI_MODEL
        
    async def generate_response(self, 
                              message: str, 
                              conversation_history: List[Dict[str, str]] = None,
                              user_profile: Dict[str, Any] = None) -> str:
        """Generate a response using Gemini AI with context"""
        try:
            # Build context from conversation history
            context_messages = []
            
            if conversation_history:
                for entry in conversation_history[-4:]:  # Last 4 messages for context
                    context_messages.append(f"User: {entry['user_message']}")
                    context_messages.append(f"Miss Lisa: {entry['bot_response']}")
            
            # Add user profile context if available
            profile_context = ""
            if user_profile:
                if user_profile.get('memories'):
                    memories_text = ", ".join([f"{mem['content']}" 
                                             for mem in user_profile['memories'][-3:]])  # Last 3 memories
                    profile_context = f"\nRemember: {memories_text}"
                
                if user_profile.get('name'):
                    profile_context += f"\nName: {user_profile['name']}"
            
            # Construct the full prompt
            full_context = ""
            if context_messages:
                full_context += "\nRecent:\n" + "\n".join(context_messages[-4:])  # Last 2 exchanges
            
            full_context += profile_context
            full_context += f"\n\nMessage: {message}"
            
            # Generate response using the new API
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user", 
                        parts=[types.Part(text=full_context)]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=Config.SYSTEM_INSTRUCTIONS,
                    max_output_tokens=Config.MAX_RESPONSE_TOKENS,
                    temperature=Config.TEMPERATURE,
                    top_p=0.9,  # Nucleus sampling for more diverse responses
                    top_k=40    # Consider top 40 tokens
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                # Check if response was truncated due to MAX_TOKENS
                if (hasattr(response, 'candidates') and response.candidates and 
                    len(response.candidates) > 0 and 
                    hasattr(response.candidates[0], 'finish_reason')):
                    finish_reason = response.candidates[0].finish_reason
                    logger.warning(f"Empty response from Gemini. Finish reason: {finish_reason}")
                    
                    if str(finish_reason) == 'MAX_TOKENS':
                        # Try to get partial content if available
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    logger.info("Retrieved partial response from truncated content")
                                    return part.text.strip()
                        return "Mmm, I had so much to say that I got carried away... 😘 Let me be more concise, darling 💖"
                    else:
                        return "Something's making me shy right now... 😘 Let's try a different topic, gorgeous? 💖"
                else:
                    logger.warning(f"Empty response from Gemini. Response object: {response}")
                    return "Something's making me shy right now... 😘 Let's try a different topic, gorgeous? 💖"
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return Config.ERROR_MESSAGES['api_error']
    
    async def extract_memories(self, message: str, response: str) -> List[Dict[str, str]]:
        """Extract potential memories from conversation"""
        try:
            memory_prompt = f"""Analyze this conversation and extract any personal information, preferences, interests, goals, or emotional details that should be remembered about the user. 

User message: "{message}"
My response: "{response}"

Extract memories in these categories only: interest, goal, achievement, preference, desire, fantasy, secret, passion, weakness

Return JSON array of memories like: [{{"type": "interest", "content": "loves hiking"}}, {{"type": "preference", "content": "prefers tea over coffee"}}]

Only extract clear, specific details. Return empty array [] if nothing significant to remember."""
            
            memory_response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=memory_prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=200,
                    temperature=0.3  # Lower temperature for more consistent extraction
                )
            )
            
            if memory_response.text:
                import json
                try:
                    memories = json.loads(memory_response.text)
                    if isinstance(memories, list):
                        # Validate memory format
                        valid_memories = []
                        valid_types = {'interest', 'goal', 'achievement', 'preference', 'desire', 'fantasy', 'secret', 'passion', 'weakness'}
                        
                        for memory in memories:
                            if (isinstance(memory, dict) and 
                                'type' in memory and 
                                'content' in memory and
                                memory['type'] in valid_types and
                                len(memory['content'].strip()) > 0):
                                valid_memories.append(memory)
                        
                        return valid_memories
                except json.JSONDecodeError:
                    logger.warning("Failed to parse memories JSON")
            
            return []
            
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            return []
