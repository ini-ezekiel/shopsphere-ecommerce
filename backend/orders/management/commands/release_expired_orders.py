from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from orders.models import Order
from orders.services import (
    OrderCancellationError,
    expire_pending_order,
)


class Command(BaseCommand):
    help = (
        "Reconcile payments, cancel unpaid expired " "orders, and release their reserved inventory"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help=(
                "Number of expired order IDs fetched " "from the database at a time."
            ),
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]

        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1.")

        current_time = timezone.now()

        expired_order_ids = (
            Order.objects.filter(
                status=Order.Status.PENDING_PAYMENT,
                inventory_status=(Order.InventoryStatus.RESERVED),
                reservation_expires_at__isnull=False,
                reservation_expires_at__lte=current_time,
            )
            .order_by("reservation_expires_at")
            .values_list("id", flat=True)
            .iterator(chunk_size=batch_size)
        )

        expired_count = 0
        skipped_count = 0
        failed_count = 0

        for order_id in expired_order_ids:
            try:
                order, expired = expire_pending_order(
                    order_id=order_id,
                    current_time=current_time,
                )
            except OrderCancellationError as error:
                failed_count += 1

                self.stderr.write(
                    self.style.ERROR(f"Order ID {order_id} failed: " f"{error.message}")
                )

                continue

            if expired:
                expired_count += 1

                self.stdout.write(f"Expired {order.order_number}")
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {expired_count} order(s); "
                f"skipped {skipped_count}; "
                f"failed {failed_count}."
            )
        )
