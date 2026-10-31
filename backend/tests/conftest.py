import pytest
from apps.inventory.models import Product
from apps.inventory.services import adjust_stock
from apps.suppliers.models import Supplier
from apps.users.models import Tenant, User
from rest_framework.test import APIClient


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Northstar Supply", currency="CAD")


@pytest.fixture
def admin(tenant):
    return User.objects.create_user(
        "owner@example.com", "A-real-password-832!", tenant=tenant, role="ADMIN", first_name="Amir"
    )


@pytest.fixture
def manager(tenant):
    return User.objects.create_user(
        "manager@example.com", "A-real-password-832!", tenant=tenant, role="MANAGER"
    )


@pytest.fixture
def staff(tenant):
    return User.objects.create_user(
        "staff@example.com", "A-real-password-832!", tenant=tenant, role="STAFF"
    )


@pytest.fixture
def client(admin):
    client = APIClient()
    client.force_authenticate(admin)
    return client


@pytest.fixture
def supplier(tenant):
    return Supplier.objects.create(tenant=tenant, name="Maple Works")


@pytest.fixture
def product(tenant, admin, supplier):
    product = Product.objects.create(
        tenant=tenant,
        supplier=supplier,
        name="Desk Lamp",
        sku="LIGHT-01",
        cost_price="10.10",
        sale_price="25.25",
        reorder_level=5,
    )
    return adjust_stock(
        product_id=product.pk, tenant=tenant, actor=admin, quantity_delta=20, note="Opening balance"
    )


@pytest.fixture
def outsider(db):
    other = Tenant.objects.create(name="Other business")
    return User.objects.create_user(
        "other@example.com", "A-real-password-832!", tenant=other, role="ADMIN"
    )


@pytest.fixture
def sale_payload(product):
    return {
        "customer_name": "Cedar Studio",
        "customer_email": "cedar@example.com",
        "tax_rate": "13.00",
        "items": [{"product": str(product.pk), "quantity": 3}],
    }


@pytest.fixture
def purchase_payload(product, supplier):
    return {
        "supplier": str(supplier.pk),
        "items": [{"product": str(product.pk), "quantity": 10, "unit_price": "9.50"}],
    }
