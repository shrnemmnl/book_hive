# users/middleware.py

class SampleLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print("Middleware initialized...")

    def __call__(self, request):
        print(f"[LOG] {request.method} request to {request.path}")

        # Before view
        response = self.get_response(request)

        # After view
        print(f"[LOG] Response status: {response.status_code}")
        return response
