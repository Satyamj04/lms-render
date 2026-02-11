"""
Custom middleware to handle frame options for media files
"""

class DisableXFrameOptionsMiddleware:
    """
    Middleware to remove X-Frame-Options header from all responses
    This allows PDFs and other media to be displayed in iframes
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Remove X-Frame-Options header if it exists
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        
        return response
