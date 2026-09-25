from rest_framework import serializers
from .models import Monitor


class MonitorSerializer(serializers.ModelSerializer):

    class Meta:

        model = Monitor

        fields = '__all__'

        read_only_fields = [
            'owner',
            'heartbeat_token',
            'created_at',
        ]


    def validate_name(self, value):

        if not value.strip():
            raise serializers.ValidationError(
                "Monitor name is required."
            )

        return value


    def validate_url(self, value):

        if not value:
            return value

        if not (
            value.startswith("http://")
            or value.startswith("https://")
        ):
            raise serializers.ValidationError(
                "URL must start with http:// or https://."
            )

        return value


    def validate(self, data):

        monitor_type = data.get(
            "monitor_type"
        )

        url = data.get("url")

        if monitor_type == "http" and not url:

            raise serializers.ValidationError({
                "url": "URL is required for HTTP monitors."
            })

        return data