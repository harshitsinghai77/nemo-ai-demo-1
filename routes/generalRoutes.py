"""
General purpose routes for the application.
This module contains routes that don't fit into other specific categories.
"""

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, Union
import datetime
import json

router = APIRouter()

def get_templates() -> Jinja2Templates:
    """
    Returns a Jinja2Templates instance.
    
    Returns:
        Jinja2Templates: Templates instance for rendering HTML responses.
    """
    return Jinja2Templates(directory="templates")

def create_greeting_message(name: Optional[str] = None) -> str:
    """
    Creates a personalized greeting message.
    
    Args:
        name: Optional name for the greeting.
        
    Returns:
        str: A greeting message.
    """
    return f"Hello {name}" if name else "Hello World"

def get_example_responses() -> Dict[str, Dict[str, str]]:
    """
    Returns example responses for the hello-world endpoint.
    
    Returns:
        Dict[str, Dict[str, str]]: Dictionary containing example responses.
    """
    return {
        "with_name": {"message": "Hello Alice"},
        "without_name": {"message": "Hello World"}
    }

@router.get("/hello-world")
async def hello_world(
    request: Request, 
    name: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates)
) -> Union[JSONResponse, Any]:
    """
    A simple greeting endpoint that returns a personalized message.
    
    Args:
        request: FastAPI Request object.
        name: Optional name for personalized greeting.
        templates: Jinja2Templates instance for HTML rendering.
        
    Returns:
        Union[JSONResponse, Any]: JSON response or HTML template response.
    """
    # Prepare the response message
    message = create_greeting_message(name)
    response_data = {"message": message}
    
    # Check if request is from a browser
    if "text/html" in request.headers.get("accept", ""):
        return render_html_response(request, name, templates)
    
    # Return JSON response
    return JSONResponse(content=response_data)

def render_html_response(
    request: Request, 
    name: Optional[str] = None,
    templates: Jinja2Templates = None
) -> Any:
    """
    Renders an HTML response for browser requests.
    
    Args:
        request: FastAPI Request object.
        name: Optional name parameter from the request.
        templates: Jinja2Templates instance for HTML rendering.
        
    Returns:
        Any: HTML template response.
    """
    current_year = datetime.datetime.now().year
    example_responses = get_example_responses()
    
    return templates.TemplateResponse(
        "route.html",
        {
            "request": request,
            "route_path": "/hello-world",
            "method": "GET",
            "full_path": str(request.url).split("?")[0],
            "description": "A simple greeting endpoint that returns a personalized message.",
            "parameters": [
                {"name": "name", "type": "string", "description": "Optional name for personalized greeting"}
            ],
            "example_query": "",
            "example_response": json.dumps(
                example_responses["with_name"] if name else example_responses["without_name"], 
                indent=2
            ),
            "current_year": current_year
        }
    )