from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """
    Simple health check endpoint.

    Returns:
      200 OK with JSON {"message": "Server is up!"}
    """
    return Response({"message": "Server is up!"})
