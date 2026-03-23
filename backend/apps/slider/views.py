from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import SliderItem
from .serializers import SliderItemSerializer


class SliderItemListView(generics.ListAPIView):
    """
    Returns a list of active slider items, ordered by 'order' and 'created_at'.
    """
    queryset = SliderItem.objects.filter(is_active=True)
    serializer_class = SliderItemSerializer
    permission_classes = [AllowAny]
