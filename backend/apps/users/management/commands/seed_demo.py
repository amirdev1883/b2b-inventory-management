import getpass
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inventory.models import Product
from apps.inventory.services import adjust_stock
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem
from apps.orders.services import transition_sales
from apps.suppliers.models import Supplier
from apps.users.models import Tenant, User
from apps.users.serializers import check_password


class Command(BaseCommand):
    help = "Create optional sample data in development. Never modifies an existing account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is disabled outside development settings.")
        email = options["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write("Account already exists; no data changed.")
            return
        password = os.getenv("DEMO_PASSWORD") or getpass.getpass(
            "Choose a demo password (10+ characters): "
        )
        try:
            check_password(password, User(email=email))
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        tenant = Tenant.objects.create(
            name="Northstar Supply Co.",
            currency="CAD",
            address="100 Example Avenue, Toronto, ON",
            email=email,
            phone="416-555-0100",
        )
        user = User.objects.create_user(
            email, password, tenant=tenant, role="ADMIN", first_name="Amir", last_name="Arani"
        )
        supplier = Supplier.objects.create(
            tenant=tenant,
            name="Maple Manufacturing",
            email="orders@example.com",
            phone="416-555-0120",
            address="25 Sample Road, Toronto, ON",
        )
        Supplier.objects.create(
            tenant=tenant, name="Pacific Office Supply", email="supply@example.com"
        )
        products = []
        catalog = [
            ("DESK-001", "Ergonomic desk chair", "Office", "85.00", "159.00", 42, 10),
            ("LIGHT-001", "Studio desk lamp", "Lighting", "18.50", "39.00", 28, 8),
            ("ORG-001", "Modular desk organizer", "Accessories", "9.00", "22.00", 64, 15),
            ("CABLE-001", "USB-C braided cable", "Electronics", "5.00", "16.00", 7, 10),
            ("NOTE-001", "Recycled notebook pack", "Stationery", "4.50", "12.00", 96, 20),
            ("STAND-001", "Aluminum laptop stand", "Accessories", "22.00", "49.00", 4, 8),
        ]
        for sku, name, category, cost, price, quantity, reorder in catalog:
            product = Product.objects.create(
                tenant=tenant,
                supplier=supplier,
                sku=sku,
                name=name,
                category=category,
                cost_price=cost,
                sale_price=price,
                reorder_level=reorder,
            )
            products.append(
                adjust_stock(
                    product_id=product.pk,
                    tenant=tenant,
                    actor=user,
                    quantity_delta=quantity,
                    note="Demo opening balance",
                )
            )
        for index, customer in enumerate(
            ["Cedar Design Studio", "Harbour Workspace", "Evergreen Retail"]
        ):
            order = SalesOrder.objects.create(
                tenant=tenant,
                created_by=user,
                currency=tenant.currency,
                customer_name=customer,
                customer_email="customer@example.com",
                tax_rate="13.00",
            )
            for product in products[:2]:
                SalesOrderItem.objects.create(
                    tenant=tenant,
                    order=order,
                    product=product,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=index + 2,
                    unit_price=product.sale_price,
                )
            if index < 2:
                transition_sales(order_id=order.pk, tenant=tenant, actor=user, action="confirm")
            if index == 0:
                transition_sales(order_id=order.pk, tenant=tenant, actor=user, action="ship")
        purchase = PurchaseOrder.objects.create(
            tenant=tenant,
            created_by=user,
            currency=tenant.currency,
            supplier=supplier,
            supplier_name=supplier.name,
        )
        for product in products[-2:]:
            PurchaseOrderItem.objects.create(
                tenant=tenant,
                order=purchase,
                product=product,
                product_name=product.name,
                sku=product.sku,
                quantity=20,
                unit_price=product.cost_price,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo workspace created for {email}. Sign in using your chosen password."
            )
        )
