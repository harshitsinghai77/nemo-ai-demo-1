import math
from typing import Optional, Dict, Union, Tuple

class CalculatorUtils:
    """
    Utility class for calculator operations with enhanced validation and error handling.
    """
    # Constants for validation
    MAX_NUMBER_VALUE = 1e100
    MIN_NUMBER_VALUE = -1e100
    
    @staticmethod
    def validate_and_convert_number(value: str) -> Tuple[float, Optional[str]]:
        """
        Validates and converts a string to a float with comprehensive error handling.
        
        Args:
            value: String representation of a number
            
        Returns:
            Tuple containing (converted_number, error_message)
            If successful, error_message will be None
        """
        if not value or not isinstance(value, str):
            return (0, "Value must be a non-empty string")
        
        try:
            num = float(value)
            
            # Check for special values
            if math.isnan(num):
                return (0, "Value is not a number (NaN)")
                
            if math.isinf(num):
                return (0, "Value cannot be infinity")
                
            # Check range constraints
            if abs(num) > CalculatorUtils.MAX_NUMBER_VALUE:
                return (0, f"Value exceeds maximum allowed magnitude ({CalculatorUtils.MAX_NUMBER_VALUE})")
                
            # Success case
            return (num, None)
            
        except ValueError:
            return (0, "Invalid number format")
        except Exception as e:
            return (0, f"Unexpected error: {str(e)}")
    
    @staticmethod
    def calculate_sum(num1: float, num2: float) -> float:
        """
        Calculates the sum of two numbers with overflow checking.
        
        Args:
            num1: First number
            num2: Second number
            
        Returns:
            The sum of num1 and num2
            
        Raises:
            ValueError: If the result would overflow
        """
        result = num1 + num2
        
        # Check for overflow
        if math.isinf(result):
            raise ValueError("Calculation resulted in overflow")
            
        # Check for underflow (result too close to zero)
        if abs(result) > 0 and abs(result) < float.epsilon if hasattr(float, 'epsilon') else 2.2204460492503131e-16:
            raise ValueError("Calculation resulted in underflow")
            
        return result
    
    @staticmethod
    def get_example_response(num1: float = 5, num2: float = 7) -> Dict[str, Union[float, int]]:
        """
        Generates a dynamic example response for documentation.
        
        Args:
            num1: Example first number
            num2: Example second number
            
        Returns:
            Dictionary with example values
        """
        return {
            "num1": num1,
            "num2": num2,
            "total": num1 + num2
        }