from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def health(request):
    """
    Simple health check endpoint.

    Returns:
      200 OK with JSON {"message": "Server is up!"}
    """
    return Response({"message": "Server is up!"})
