from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, ErrorDetail

def custom_exception_handler(exc, context):
    """
    Customized formatting for validation error 
    """
    # Use DRF's default exception handler as a fallback
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(exc, ValidationError):
            # Handle ValidationError specifically
            if isinstance(response.data, dict):
                error_count = len(response.data.keys())
                errors = {}

                for field, value in response.data.items():
                    if isinstance(value, list) and value:    
                        errors[field] = {
                            'message': str(value[0]),
                            'code': value[0].code if hasattr(value[0], 'code') else 'error'
                        }

                response.data = {
                    "errors": errors,
                    "error_count": error_count
                }
                
        else:
            error_count = len(response.data.keys())

            for field, value in response.data.items():
                if isinstance(value, ErrorDetail) and value:
                    response.data[field] = {
                        'message': str(value),
                        'code': value.code if hasattr(value, 'code') else 'error'
                    }
             
            response.data['error_count'] = error_count
    
    return response
                                  

        
      