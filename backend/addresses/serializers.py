from django.db import transaction
from rest_framework import serializers

from .models import DeliveryLocation, ShippingAddress


class DeliveryLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLocation
        fields = [
            "id",
            "state",
            "city",
            "shipping_fee",
            "estimated_delivery_days",
        ]


class ShippingAddressSerializer(serializers.ModelSerializer):
    delivery_location = DeliveryLocationSerializer(
        read_only=True,
    )

    delivery_location_id = serializers.PrimaryKeyRelatedField(
        source="delivery_location",
        queryset=DeliveryLocation.objects.filter(is_active=True),
        write_only=True,
    )

    class Meta:
        model = ShippingAddress
        fields = [
            "id",
            "label",
            "recipient_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "landmark",
            "postal_code",
            "country",
            "delivery_location",
            "delivery_location_id",
            "is_default",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "country",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance
        requested_default = attrs.get("is_default")

        if instance is not None and instance.is_default and requested_default is False:
            raise serializers.ValidationError(
                {
                    "is_default": (
                        "Set another address as default before "
                        "removing this address as the default."
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        requested_default = validated_data.get(
            "is_default",
            False,
        )

        with transaction.atomic():
            existing_addresses = ShippingAddress.objects.select_for_update().filter(
                user=user
            )

            existing_ids = list(
                existing_addresses.values_list(
                    "id",
                    flat=True,
                )
            )

            if not existing_ids:
                validated_data["is_default"] = True

            elif requested_default:
                ShippingAddress.objects.filter(
                    id__in=existing_ids,
                ).update(is_default=False)

            return ShippingAddress.objects.create(
                user=user,
                **validated_data,
            )

    def update(self, instance, validated_data):
        user = self.context["request"].user
        requested_default = validated_data.get(
            "is_default",
            instance.is_default,
        )

        with transaction.atomic():
            address = ShippingAddress.objects.select_for_update().get(
                pk=instance.pk,
                user=user,
            )

            if requested_default:
                other_addresses = (
                    ShippingAddress.objects.select_for_update()
                    .filter(user=user)
                    .exclude(pk=address.pk)
                )

                other_ids = list(
                    other_addresses.values_list(
                        "id",
                        flat=True,
                    )
                )

                ShippingAddress.objects.filter(
                    id__in=other_ids,
                ).update(is_default=False)

            for field, value in validated_data.items():
                setattr(address, field, value)

            address.save()

        return address
