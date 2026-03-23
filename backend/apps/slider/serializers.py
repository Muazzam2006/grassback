from rest_framework import serializers

from .models import SliderItem


class SliderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SliderItem
        fields = ("id", "title", "description", "image", "order", "created_at")
