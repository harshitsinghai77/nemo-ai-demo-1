from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, Tuple, Callable
import json
import datetime
from utils.calculator_utils import CalculatorUtils

templates = Jinja2Templates(directory="templates")

async def handle_calculator_request(
    request: Request, 
    route_path: str,
    operation_name: str,
    num1: Optional[str] = None, 
    num2: Optional[str] = None,
    calculation_func: Callable[[float, float], float] = CalculatorUtils.calculate_sum
) -> HTMLResponse | JSONResponse:
    """
    Generic handler for calculator endpoints to reduce code duplication.
    
    Args:
        request: The FastAPI request object
        route_path: The path of the route (e.g., "/calc/add")
        operation_name: Description of the operation (e.g., "Add")
        num1: First number as a string
        num2: Second number as a string
        calculation_func: Function to perform the calculation (defaults to sum)
        
    Returns:
        JSONResponse with num1, num2, and result
        HTMLResponse for browser requests with documentation
    """
    # Check if request is from a browser
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        current_year = datetime.datetime.now().year
        # Use utility to generate dynamic example response
        example_response = CalculatorUtils.get_example_response()
        
        return templates.TemplateResponse(
            "route.html",
            {
                "request": request,
                "route_path": route_path,
                "method": "GET",
                "full_path": str(request.url).split("?")[0],
                "description": f"{operation_name} two numbers provided as query parameters and return JSON result.",
                "parameters": [
                    {"name": "num1", "type": "number", "description": "First number for calculation"},
                    {"name": "num2", "type": "number", "description": "Second number for calculation"}
                ],
                "example_query": "?num1=5&num2=7",
                "example_response": json.dumps(example_response, indent=2),
                "current_year": current_year
            }
        )
    
    # Handle regular API calls - validate parameters are provided
    if num1 is None or num2 is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Both num1 and num2 query parameters are required"}
        )
    
    # Validate and convert first number
    float_num1, error1 = CalculatorUtils.validate_and_convert_number(num1)
    if error1:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid num1: {error1}"}
        )
    
    # Validate and convert second number
    float_num2, error2 = CalculatorUtils.validate_and_convert_number(num2)
    if error2:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid num2: {error2}"}
        )
    
    try:
        # Use provided calculation function
        total = calculation_func(float_num1, float_num2)
        
        # Prepare response
        response_data = {
            "num1": float_num1,
            "num2": float_num2,
            "total": total
        }
        
        return JSONResponse(content=response_data)
    
    except ValueError as ve:
        return JSONResponse(
            status_code=400,
            content={"error": str(ve)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )