from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)

    return (
        Cart.objects.select_related("user")
        .prefetch_related(
            "items__variant__inventory",
            "items__variant__product__images",
        )
        .get(pk=cart.pk)
    )


# CartDetailView retrieves the current user’s cart and totals.


class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_user_cart(request.user)

        serializer = CartSerializer(
            cart,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# CartItemCreateView adds a variant or increases its existing quantity.


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_user_cart(request.user)

        serializer = AddCartItemSerializer(
            data=request.data,
            context={
                "request": request,
                "cart": cart,
            },
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        response_serializer = CartItemSerializer(
            item,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED if serializer.created else status.HTTP_200_OK
            ),
        )


# CartItemDetailView updates or removes only items belonging to the authenticated user.


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(
            CartItem.objects.select_related(
                "cart",
                "variant__product",
                "variant__inventory",
            ),
            pk=pk,
            cart__user=request.user,
        )

    def patch(self, request, pk):
        item = self.get_object(request, pk)

        serializer = UpdateCartItemSerializer(
            item,
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        response_serializer = CartItemSerializer(
            item,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        item = self.get_object(request, pk)
        item.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


# CartClearView removes every item from the current user’s cart.


class CartClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        CartItem.objects.filter(
            cart__user=request.user,
        ).delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
