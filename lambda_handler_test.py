#!/usr/bin/env python3
"""
AWS Lambda handler for Zoom2Youtube web application
Simple test version
"""

def handler(event, context):
    """Simple test handler"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': '<h1>Lambda is working!</h1>'
    }
