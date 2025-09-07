import os
import datetime
import json
import requests
from dataclasses import dataclass
from functools import wraps
from typing import Literal, Optional, Union, Dict, Any, TypeVar, Callable, cast, Protocol, Type
from enum import Enum
from abc import ABC, abstractmethod

from fastapi import FastAPI, APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from agno.agent import RunResponse, Agent
from agno.models.nebius import Nebius
from controllers.agents import multi_ai
import dotenv
from controllers.ask import chat_agent

router = APIRouter()

dotenv.load_dotenv()
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
templates = Jinja2Templates(directory="templates")

# Calculator operation classes
class Operation(str, Enum):
    """Enum for calculator operations."""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"

@dataclass(frozen=True)
class CalculationResult:
    """Immutable dataclass for calculator operation results."""
    operation: str
    num1: Union[float, int]
    num2: Union[float, int]
    res: Union[float, int]

class OperationStrategy(ABC):
    """Abstract base class for calculator operation strategies."""
    
    @abstractmethod
    def execute(self, num1: Union[float, int], num2: Union[float, int]) -> Union[float, int]:
        """Execute the operation on two numbers."""
        pass

class AddOperation(OperationStrategy):
    """Addition operation strategy."""
    
    def execute(self, num1: Union[float, int], num2: Union[float, int]) -> Union[float, int]:
        """Add two numbers."""
        return num1 + num2

class SubtractOperation(OperationStrategy):
    """Subtraction operation strategy."""
    
    def execute(self, num1: Union[float, int], num2: Union[float, int]) -> Union[float, int]:
        """Subtract second number from first number."""
        return num1 - num2

class MultiplyOperation(OperationStrategy):
    """Multiplication operation strategy."""
    
    def execute(self, num1: Union[float, int], num2: Union[float, int]) -> Union[float, int]:
        """Multiply two numbers."""
        return num1 * num2

class DivideOperation(OperationStrategy):
    """Division operation strategy."""
    
    def execute(self, num1: Union[float, int], num2: Union[float, int]) -> Union[float, int]:
        """Divide first number by second number."""
        if num2 == 0:
            raise ValueError("Cannot divide by zero")
        return num1 / num2

class Calculator:
    """Calculator class that uses different operation strategies."""
    
    def __init__(self) -> None:
        """Initialize the calculator with operation strategies."""
        self._operations: Dict[Operation, OperationStrategy] = {
            Operation.ADD: AddOperation(),
            Operation.SUBTRACT: SubtractOperation(),
            Operation.MULTIPLY: MultiplyOperation(),
            Operation.DIVIDE: DivideOperation()
        }
    
    def calculate(self, 
                 operation: Operation, 
                 num1: Union[float, int], 
                 num2: Union[float, int]) -> CalculationResult:
        """
        Perform the calculation using the appropriate operation strategy.
        
        Args:
            operation: The operation to perform
            num1: First number for calculation
            num2: Second number for calculation
            
        Returns:
            CalculationResult object containing operation details and result
            
        Raises:
            ValueError: If an invalid operation is provided or division by zero is attempted
        """
        if operation not in self._operations:
            raise ValueError(f"Invalid operation: {operation}")
        
        result = self._operations[operation].execute(num1, num2)
        
        return CalculationResult(
            operation=operation.value,
            num1=num1,
            num2=num2,
            res=result
        )

# Parameter validation decorator
T = TypeVar("T", bound=Callable[..., Any])

def validate_calculator_params(func: T) -> T:
    """
    Decorator for validating calculator endpoint parameters.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function with parameter validation
    """
    @wraps(func)
    async def wrapper(
        request: Request,
        num1: Optional[Union[float, int]] = None,
        num2: Optional[Union[float, int]] = None,
        operation: Optional[str] = None,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        # Check if request is from a browser and parameters are missing
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and (num1 is None or num2 is None or operation is None):
            # Return HTML documentation
            current_year = datetime.datetime.now().year
            example_response = {
                "operation": "add",
                "num1": 5,
                "num2": 3,
                "res": 8
            }
            
            return templates.TemplateResponse(
                "route.html",
                {
                    "request": request,
                    "route_path": "/calc",
                    "method": "GET",
                    "full_path": str(request.url).split("?")[0],
                    "description": "Calculator endpoint that performs basic arithmetic operations on two numbers.",
                    "parameters": [
                        {"name": "num1", "type": "number", "description": "First number for calculation"},
                        {"name": "num2", "type": "number", "description": "Second number for calculation"},
                        {"name": "operation", "type": "string", "description": "One of 'add', 'subtract', 'multiply', or 'divide'"}
                    ],
                    "example_query": "?num1=5&num2=3&operation=add",
                    "example_response": json.dumps(example_response, indent=2),
                    "current_year": current_year
                }
            )
        
        # Consolidated parameter validation
        errors = []
        if num1 is None:
            errors.append("Missing required parameter 'num1'")
        if num2 is None:
            errors.append("Missing required parameter 'num2'")
        if operation is None:
            errors.append("Missing required parameter 'operation'")
        
        if errors:
            return JSONResponse(
                status_code=400, 
                content={"error": "; ".join(errors)}
            )
            
        # Validate operation value
        try:
            operation_enum = Operation(operation)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid operation: {operation}. Must be one of: {', '.join([op.value for op in Operation])}"}
            )
            
        return await func(request, num1, num2, operation_enum, *args, **kwargs)
    
    return cast(T, wrapper)

def create_response(data: Any) -> JSONResponse:
    """
    Create a standardized JSON response.
    
    Args:
        data: Response data to include in the JSON
    
    Returns:
        JSONResponse with the provided data
    """
    return JSONResponse(content=data)

def create_error_response(message: str, status_code: int = 400) -> JSONResponse:
    """
    Create a standardized error JSON response.
    
    Args:
        message: Error message
        status_code: HTTP status code, defaults to 400
        
    Returns:
        JSONResponse with the error message and status code
    """
    return JSONResponse(
        status_code=status_code,
        content={"error": message}
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
                "calc": router.url_path_for("calc"),
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

@router.get("/calc", response_class=HTMLResponse)
async def calc(
    request: Request,
    num1: Optional[Union[float, int]] = None,
    num2: Optional[Union[float, int]] = None,
    operation: Optional[str] = None
) -> JSONResponse:
    """
    Calculator endpoint that performs basic arithmetic operations on two numbers.
    
    Args:
        request: The FastAPI request object
        num1: First number for calculation
        num2: Second number for calculation
        operation: Operation to perform (add, subtract, multiply, divide)
        
    Returns:
        JSON response with operation details and result
    """
    # Check if request is from a browser
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and (num1 is None or num2 is None or operation is None):
        # Return HTML documentation
        current_year = datetime.datetime.now().year
        example_response = {
            "operation": "add",
            "num1": 5,
            "num2": 3,
            "res": 8
        }
        
        return templates.TemplateResponse(
            "route.html",
            {
                "request": request,
                "route_path": "/calc",
                "method": "GET",
                "full_path": str(request.url).split("?")[0],
                "description": "Calculator endpoint that performs basic arithmetic operations on two numbers.",
                "parameters": [
                    {"name": "num1", "type": "number", "description": "First number for calculation"},
                    {"name": "num2", "type": "number", "description": "Second number for calculation"},
                    {"name": "operation", "type": "string", "description": "One of 'add', 'subtract', 'multiply', or 'divide'"}
                ],
                "example_query": "?num1=5&num2=3&operation=add",
                "example_response": json.dumps(example_response, indent=2),
                "current_year": current_year
            }
        )
    
    # Validate parameters
    errors = []
    if num1 is None:
        errors.append("Missing required parameter 'num1'")
    if num2 is None:
        errors.append("Missing required parameter 'num2'")
    if operation is None:
        errors.append("Missing required parameter 'operation'")
    
    if errors:
        return JSONResponse(
            status_code=400, 
            content={"error": "; ".join(errors)}
        )
    
    # Validate operation type
    valid_operations = ["add", "subtract", "multiply", "divide"]
    if operation not in valid_operations:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}"}
        )
    
    # Perform the calculation
    try:
        result = None
        if operation == "add":
            result = num1 + num2
        elif operation == "subtract":
            result = num1 - num2
        elif operation == "multiply":
            result = num1 * num2
        elif operation == "divide":
            if num2 == 0:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Cannot divide by zero"}
                )
            result = num1 / num2
        
        # Return the result
        return JSONResponse(content={
            "operation": operation,
            "num1": num1,
            "num2": num2,
            "res": result
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred during calculation: {str(e)}"}
        )