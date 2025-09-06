import os
from dotenv import load_dotenv
from agno.agent import Agent, RunResponse
from typing import Dict, Any, Optional, List, Union
import requests
import html
import re

# Load environment variables
load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")

if not GROK_API_KEY:
    raise ValueError("Please provide a GROK API key in the .env file")

class GrokAPIClient:
    """
    Client for handling secure communication with the Grok AI API.
    This class is responsible for making secure API calls to the Grok AI service.
    """
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Grok API Client with API key.
        
        Args:
            api_key: Optional API key to use, defaults to environment variable
        """
        self.api_key = api_key or GROK_API_KEY
        self.api_base_url = "https://api.grok.x/v1"  # Ensure HTTPS for secure communication
        
        if not self.api_key:
            raise ValueError("Grok API key is required")
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model_id: str = "grok-2",
                       temperature: float = 0.7,
                       max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Make a secure chat completion API call to Grok AI.
        
        Args:
            messages: List of message dictionaries with role and content
            model_id: The Grok AI model identifier to use
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Dict containing the response from Grok AI
        
        Raises:
            Exception: If the API call fails or returns an error
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/chat/completions", 
                json=data, 
                headers=headers,
                timeout=30  # Set timeout for security
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error calling Grok AI API: {str(e)}")


class GrokModel:
    """
    Model adapter for Grok AI that provides an interface compatible with the 
    application's agent architecture.
    """
    def __init__(self, model_id: str = "grok-2", api_key: Optional[str] = None):
        """
        Initialize the Grok AI model adapter.
        
        Args:
            model_id: The Grok AI model identifier to use, defaults to "grok-2"
            api_key: Optional API key to use, defaults to environment variable
        """
        self.model_id = model_id
        self.api_client = GrokAPIClient(api_key)
    
    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize input text to prevent injection attacks.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized text string
        """
        # Escape HTML entities
        text = html.escape(text)
        
        # Remove any potential script or injection patterns
        text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text
    
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Generate a response from Grok AI using the chat completions API.
        
        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to provide context
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Dict containing the response from Grok AI
        """
        # Sanitize inputs
        sanitized_prompt = self._sanitize_input(prompt)
        
        messages = []
        
        if system_prompt:
            sanitized_system_prompt = self._sanitize_input(system_prompt)
            messages.append({"role": "system", "content": sanitized_system_prompt})
        
        messages.append({"role": "user", "content": sanitized_prompt})
        
        return self.api_client.chat_completion(
            messages=messages,
            model_id=self.model_id,
            temperature=temperature,
            max_tokens=max_tokens
        )


# Create Grok AI-powered agent for basic chat functionality
grok_chat_agent = Agent(
    model=GrokModel(model_id="grok-2"),
    instructions=[
        "You are an AI investment assistant powered by Grok AI.",
        "You are here to help users with investment-related questions.",
        "Provide clear, helpful, and accurate financial advice."
    ],
    markdown=True
)


def grok_chat(query: str) -> Dict[str, Any]:
    """
    Process a financial query using the Grok AI chat agent.
    
    Args:
        query: The user's financial question (sanitized before processing)
        
    Returns:
        Dict containing the question and answer, or an error message
    """
    if not query or not isinstance(query, str):
        return {"error": "Query parameter is required and must be a string"}
    
    # Additional input validation
    if len(query.strip()) == 0:
        return {"error": "Query cannot be empty"}
    
    try:
        # Sanitize the query (already done in the GrokModel class)
        response = grok_chat_agent.run(query)
        answer = response.content
        return {"question": query, "answer": answer}
    
    except Exception as e:
        return {"error": str(e)}


# Import the existing agents to combine with Grok AI
from controllers.agents import web_search_agent, financial_agent

# Create a multi-AI agent powered by Grok instead of meta-llama
grok_multi_ai = Agent(
    name="grok_finance_agent",
    team=[web_search_agent, financial_agent],
    model=GrokModel(model_id="grok-2"),
    markdown=True,
    instructions=[
        "You are an advanced investment assistant powered by Grok AI.",
        "You have access to real-time financial data tools and web search capabilities.",
        "Use these tools to provide comprehensive financial advice and market insights.",
        "Always cite your sources and explain your reasoning."
    ]
)