import os
import datetime
import json
import requests
from fastapi import FastAPI, APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from agno.agent import RunResponse, Agent
from agno.models.nebius import Nebius
from controllers.agents import multi_ai
import dotenv
from controllers.ask import chat_agent
from typing import Optional, Union, Dict, Any, Tuple

# Pre-computed example response for sum endpoint
SUM_EXAMPLE_RESPONSE = json.dumps({"num1": 5, "num2": 7, "total": 12}, indent=2)

router = APIRouter()

dotenv.load_dotenv()
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
templates = Jinja2Templates(directory="templates")

def convert_to_number(value: str) -> Union[int, float]:
    """
    Convert a string to either an int or float based on its content.
    
    Args:
        value: String representation of a number
        
    Returns:
        The number as int if it's an integer, otherwise as float
        
    Raises:
        ValueError: If the string cannot be converted to a number
    """
    try:
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        return float(value)
    except ValueError:
        raise ValueError(f"Cannot convert '{value}' to a number")


async def validate_number_params(
    request: Request,
    num1: Optional[str] = Query(None, description="First number to add"),
    num2: Optional[str] = Query(None, description="Second number to add")
) -> Tuple[Union[int, float], Union[int, float]]:
    """
    Validate and convert query parameters to numbers.
    
    Args:
        request: FastAPI request object
        num1: First number as string
        num2: Second number as string
        
    Returns:
        Tuple of converted numbers (num1, num2)
        
    Raises:
        HTTPException: If parameters are missing or invalid
    """
    # Check if parameters are provided
    if num1 is None or num2 is None:
        raise HTTPException(
            status_code=400, 
            detail="Both 'num1' and 'num2' query parameters are required"
        )
    
    # Convert parameters to numbers
    try:
        n1 = convert_to_number(num1)
        n2 = convert_to_number(num2)
        return n1, n2
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Parameters 'num1' and 'num2' must be valid numbers"
        )

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
            },
            "ip": requests.get('https://api.ipify.org').text,
            "services": {
                "chat": router.url_path_for("chat"),
                "agent": router.url_path_for("ask"),
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
        return JSONResponse(content={"error": str(e)})

@router.get("/sum", response_class=HTMLResponse)
async def calculate_sum(
    request: Request,
    params: Tuple[Union[int, float], Union[int, float]] = Depends(validate_number_params)
) -> Union[HTMLResponse, JSONResponse]:
    """
    API endpoint that calculates the sum of two numbers provided as query parameters.
    Returns the result in JSON format with keys num1, num2, and total.
    
    Args:
        request: FastAPI request object
        params: Tuple of validated number parameters (num1, num2)
        
    Returns:
        HTML response for browser requests, or JSON response with calculation results
    """
    # Check if request is from a browser with no parameters
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and not request.query_params.get("num1"):
        current_year = datetime.datetime.now().year
        return templates.TemplateResponse(
            "route.html",
            {
                "request": request,
                "route_path": "/sum",
                "method": "GET",
                "full_path": str(request.url).split("?")[0],
                "description": "Endpoint that calculates the sum of two numbers.",
                "parameters": [
                    {"name": "num1", "type": "number", "description": "First number to add"},
                    {"name": "num2", "type": "number", "description": "Second number to add"},
                ],
                "example_query": "?num1=5&num2=7",
                "example_response": SUM_EXAMPLE_RESPONSE,
                "current_year": current_year
            }
        )
    
    # Unpack parameters and calculate sum
    num1, num2 = params
    total = num1 + num2
    
    # Return the result
    return JSONResponse(content={
        "num1": num1,
        "num2": num2,
        "total": total
    })

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