import os
import datetime
import json
import requests
import re
from fastapi import FastAPI, APIRouter, Request, Query, Depends, HTTPException, Security, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyHeader
from agno.agent import RunResponse, Agent
from agno.models.nebius import Nebius
from controllers.agents import multi_ai
import dotenv
from controllers.ask import chat_agent
from controllers.grokAI import grok_chat, grok_multi_ai
from typing import Optional, Dict, Any, Union

router = APIRouter()

dotenv.load_dotenv()
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
API_KEY = os.getenv("API_KEY", "")  # API key for endpoint security
templates = Jinja2Templates(directory="templates")

# Security - API key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate the API key for protected endpoints.
    
    Args:
        api_key: The API key from the X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If authentication fails
    """
    if not API_KEY:
        # If no API key is set in environment, don't enforce authentication
        return api_key
    
    if api_key == API_KEY:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
        headers={"WWW-Authenticate": "APIKey"},
    )

def sanitize_query(query: Optional[str] = None) -> str:
    """
    Sanitize and validate the query parameter.
    
    Args:
        query: The query string to sanitize
        
    Returns:
        Sanitized query string
        
    Raises:
        HTTPException: If validation fails
    """
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Query parameter is required"
        )
    
    # Remove potentially malicious patterns
    sanitized = re.sub(r'<script.*?>.*?</script>', '', query, flags=re.DOTALL | re.IGNORECASE)
    
    # Additional sanitization if needed
    
    return sanitized

@router.get("/health", response_class=HTMLResponse)
async def health_check(request: Request):
    """Health check endpoint to verify the API server status and connections."""
    try:
        response_data = {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "uptime": "OK",
            "api": {
                "nebius_api": "connected" if NEBIUS_API_KEY else "not configured",
                "grok_api": "connected" if GROK_API_KEY else "not configured",
                "api_security": "enabled" if API_KEY else "disabled"
            },
            "ip": requests.get('https://api.ipify.org').text,
            "services": {
                "chat": router.url_path_for("chat"),
                "agent": router.url_path_for("ask"),
                "ask-grok": router.url_path_for("ask_grok"),
            },
        }

        # Check if request is from a browser or format is explicitly set to html
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            current_year = datetime.datetime.now().year
            return templates.TemplateResponse(
                "route.html",
                {
                    "request": request,
                    "route_path": "/health",
                    "method": "GET",
                    "full_path": str(request.url).split("?")[0],
                    "description": "Health check endpoint to verify the API server status and connections.",
                    "parameters": [
                        {"name": "format", "type": "string", "description": "Response format (html or json)"}
                    ],
                    "example_query": "",
                    "example_response": json.dumps(response_data, indent=2),
                    "current_year": current_year
                }
            )
        
        return JSONResponse(content=response_data)

    except Exception as e:
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(e)
        }
        
        # Check if request is from a browser or format is explicitly set to html
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            current_year = datetime.datetime.now().year
            return templates.TemplateResponse(
                "route.html",
                {
                    "request": request,
                    "route_path": "/health",
                    "method": "GET",
                    "full_path": str(request.url).split("?")[0],
                    "description": "Health check endpoint to verify the API server status and connections.",
                    "parameters": [
                        {"name": "format", "type": "string", "description": "Response format (html or json)"}
                    ],
                    "example_query": "",
                    "example_response": json.dumps(error_response, indent=2),
                    "current_year": current_year
                }
            )
            
        return JSONResponse(content=error_response)

@router.get("/chat", response_class=HTMLResponse)
def chat(request: Request, query: str = None):
    """
    API endpoint to handle user investment-related questions and return AI-generated insights.
    """
    # Check if request is from a browser or format is explicitly set to html
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        current_year = datetime.datetime.now().year
        example_response = {
            "question": "What are good tech stocks to invest in?",
            "answer": "Some popular tech stocks to consider include Apple (AAPL), Microsoft (MSFT), Google (GOOGL), and Amazon (AMZN). However, you should always do your own research and consider your investment goals and risk tolerance before investing."
        }
        
        return templates.TemplateResponse(
            "route.html",
            {
                "request": request,
                "route_path": "/chat",
                "method": "GET",
                "full_path": str(request.url).split("?")[0],
                "description": "Chat endpoint that uses Nebius's LLaMa model to answer investment questions.",
                "parameters": [
                    {"name": "query", "type": "string", "description": "The investment question to ask"},
                    {"name": "format", "type": "string", "description": "Response format (html or json)"}
                ],
                "example_query": "What are good tech stocks to invest in?",
                "example_response": json.dumps(example_response, indent=2),
                "current_year": current_year
            }
        )
    
    # Handle regular API calls
    if not query:
        return JSONResponse(content={"error": "Query parameter is required"})
    
    try:
        response = chat_agent.run(query)
        answer = response.content
        return JSONResponse(content={"question": query, "answer": answer})
    
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )

@router.get("/ask-grok", response_class=HTMLResponse)
async def ask_grok(
    request: Request, 
    query: Optional[str] = None,
    api_key: str = Depends(validate_api_key)
) -> Union[JSONResponse, HTMLResponse]:
    """
    API endpoint to handle user investment-related questions using Grok AI with integrated financial tools.
    
    Args:
        request: The FastAPI request object
        query: The investment question to ask
        api_key: Validated API key from the request header
        
    Returns:
        Either HTML or JSON response based on the request's Accept header
    """
    # Check if request is from a browser or format is explicitly set to html
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        current_year = datetime.datetime.now().year
        example_response = {
            "question": "What's the best way to invest in the current market?",
            "answer": "In the current market conditions, a diversified approach is recommended. Consider allocating your investments across different asset classes including index funds, blue-chip stocks, and some bond exposure for stability. Keep some cash reserves for opportunities that may arise during market corrections. Always align your investment strategy with your personal goals, time horizon, and risk tolerance."
        }
        
        return templates.TemplateResponse(
            "route.html",
            {
                "request": request,
                "route_path": "/ask-grok",
                "method": "GET",
                "full_path": str(request.url).split("?")[0],
                "description": "Grok AI endpoint that uses Grok's advanced AI capabilities combined with financial tools to provide detailed investment advice.",
                "parameters": [
                    {"name": "query", "type": "string", "description": "The investment question to ask"},
                    {"name": "format", "type": "string", "description": "Response format (html or json)"}
                ],
                "example_query": "What's the best way to invest in the current market?",
                "example_response": json.dumps(example_response, indent=2),
                "current_year": current_year
            }
        )
    
    # Handle regular API calls
    try:
        # Sanitize and validate query
        if query:
            sanitized_query = sanitize_query(query)
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Query parameter is required"}
            )
        
        response: RunResponse = grok_multi_ai.run(sanitized_query)
        answer = response.content

        return JSONResponse(content={"question": sanitized_query, "answer": answer})
    
    except HTTPException as http_ex:
        return JSONResponse(
            status_code=http_ex.status_code,
            content={"error": http_ex.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )

@router.get("/agent", response_class=HTMLResponse)
def ask(request: Request, query: str = None):
    """
    API endpoint to handle user investment-related questions and return AI-generated insights.
    """
    # Check if request is from a browser or format is explicitly set to html
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        current_year = datetime.datetime.now().year
        example_response = {
            "question": "Should I invest in index funds?",
            "answer": "Index funds are often a good choice for passive investors looking for broad market exposure with low fees. They offer diversification and typically outperform actively managed funds in the long term. However, the suitability depends on your investment goals, time horizon, and risk tolerance."
        }
        
        return templates.TemplateResponse(
            "route.html",
            {
                "request": request,
                "route_path": "/agent",
                "method": "GET",
                "full_path": str(request.url).split("?")[0],
                "description": "Agent endpoint that uses a multi-AI system to provide sophisticated investment advice.",
                "parameters": [
                    {"name": "query", "type": "string", "description": "The investment question to ask"},
                    {"name": "format", "type": "string", "description": "Response format (html or json)"}
                ],
                "example_query": "Should I invest in index funds?",
                "example_response": json.dumps(example_response, indent=2),
                "current_year": current_year
            }
        )
    
    # Handle regular API calls
    if not query:
        return JSONResponse(content={"error": "Query parameter is required"})
    
    try:
        response: RunResponse = multi_ai.run(query)
        answer = response.content

        return JSONResponse(content={"question": query, "answer": answer})
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)})
