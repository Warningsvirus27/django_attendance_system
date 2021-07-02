from .models import LocationTrack
from rest_framework import serializers


class LocationTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationTrack
        fields = '__all__'
