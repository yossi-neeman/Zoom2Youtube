#!/usr/bin/env python3
"""
AWS Lambda handler for Zoom2Youtube web application
"""

import sys
import os
import traceback
import json

# Set UTF-8 as default encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

# Ensure Lambda paths are in Python path
lambda_task_root = os.environ.get('LAMBDA_TASK_ROOT', '/var/task')
if lambda_task_root not in sys.path:
    sys.path.insert(0, lambda_task_root)

# Import after path is set
from mangum import Mangum
from asgiref.wsgi import WsgiToAsgi
from web_app import app as flask_app

# Wrap Flask (WSGI) as ASGI for Mangum
asgi_app = WsgiToAsgi(flask_app)

# Create the base handler
base_handler = Mangum(asgi_app, lifespan="off")

def handler(event, context):
    """Lambda handler with comprehensive error handling"""
    try:
        # Log the incoming event (without sensitive data)
        method = event.get('requestContext', {}).get('http', {}).get('method')
        path = event.get('rawPath')
        print(f"Lambda invoked - HTTP Method: {method}")
        print(f"Path: {path}")
        
        # Call the base handler
        result = base_handler(event, context)
        
        # Ensure all response headers are Latin-1 safe (HTTP requirement)
        if isinstance(result, dict) and 'headers' in result:
            safe_headers = {}
            for key, value in result.get('headers', {}).items():
                if isinstance(value, str):
                    try:
                        # HTTP headers must be Latin-1 (ISO-8859-1)
                        value.encode('latin-1')
                        safe_headers[key] = value
                    except UnicodeEncodeError:
                        # If header contains non-Latin-1 characters, drop or escape them
                        print(f"Warning: Header '{key}' contains non-Latin-1 characters, escaping")
                        safe_headers[key] = value.encode('ascii', errors='ignore').decode('ascii')
                else:
                    safe_headers[key] = value
            result['headers'] = safe_headers
        
        # Ensure body is properly encoded if it's a dict
        if isinstance(result, dict) and 'body' in result:
            body = result['body']
            if isinstance(body, dict):
                result['body'] = json.dumps(body, ensure_ascii=False).encode('utf-8').decode('utf-8')
            elif isinstance(body, str):
                # Ensure it's UTF-8
                result['body'] = body
        
        return result
        
    except UnicodeEncodeError as e:
        print(f"Unicode encoding error: {e}")
        print(f"Error details: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json; charset=utf-8'},
            'body': json.dumps({
                'success': False,
                'error': 'Unicode encoding error. Please check that all text fields contain valid characters.'
            }, ensure_ascii=False)
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Error details: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json; charset=utf-8'},
            'body': json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, ensure_ascii=False)
        }
