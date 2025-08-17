from .views import logger


# users/middleware.py


class SampleLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("Custome Middleware initializing... Chk-chk-chk-chk… vrrRRRrrr… VROOOOMMM!!")

    def __call__(self, request):
        logger.info(f"[LOG]-mb- {request.method} request to {request.path}")
        
        # Before view
        response = self.get_response(request)

        # After view
        logger.info(f"[LOG]-ma- Response status: {response.status_code}")
        return response
