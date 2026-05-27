from rest_framework import serializers
from .models import PrimeraConsultaLead


class PrimeraConsultaLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrimeraConsultaLead
        fields = "__all__"