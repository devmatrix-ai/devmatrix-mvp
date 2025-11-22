import uuid
import httpx
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ClientJourney")

BASE_URL = "http://localhost:8002"

# ... imports ...

async def run_journey():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        logger.info("🚀 Starting Client Journey Test")

        # 1. Health Check
        logger.info("1️⃣  Checking Health...")
        resp = await client.get("/health/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        logger.info("   ✅ System is healthy")

        # 2. Create a Product
        logger.info("2️⃣  Creating a Product...")
        product_id = str(uuid.uuid4())
        product_payload = {
            "id": product_id,
            "name": "Gaming Laptop",
            "description": "High performance laptop",
            "price": 1500.00,
            "stock": 10,
            "is_active": True
        }
        resp = await client.post("/products/", json=product_payload)
        if resp.status_code != 200:
            logger.error(f"Failed to create product: {resp.text}")
            return
        product = resp.json()
        logger.info(f"   ✅ Product created: {product['name']} (ID: {product['id']})")

        # 3. Create a Customer
        logger.info("3️⃣  Creating a Customer...")
        customer_id = str(uuid.uuid4())
        customer_payload = {
            "id": customer_id,
            "full_name": "John Doe",
            "email": "john.doe@example.com"
        }
        resp = await client.post("/customers/", json=customer_payload)
        if resp.status_code != 200:
            logger.error(f"Failed to create customer: {resp.text}")
            return
        customer = resp.json()
        logger.info(f"   ✅ Customer created: {customer['full_name']} (ID: {customer['id']})")

        # 4. Create a Cart
        logger.info("4️⃣  Creating a Cart...")
        cart_id = str(uuid.uuid4())
        cart_payload = {
            "id": cart_id,
            "customer_id": customer_id,
            "status": "OPEN",
            "items": []
        }
        resp = await client.post("/carts/", json=cart_payload)
        if resp.status_code != 200:
            logger.error(f"Failed to create cart: {resp.text}")
            return
        cart = resp.json()
        logger.info(f"   ✅ Cart created (ID: {cart['id']})")

        # 5. Add Item to Cart
        logger.info("5️⃣  Adding Item to Cart...")
        item_payload = {
            "cart_id": cart_id,
            "product_id": product_id,
            "quantity": 1,
            "unit_price": 1500.00
        }
        # Try standard generated endpoint name with trailing slash
        resp = await client.post("/cart_items/", json=item_payload) 
        
        if resp.status_code == 404:
             # Try alternative path
             resp = await client.post(f"/carts/{cart_id}/items/", json=item_payload)

        if resp.status_code not in [200, 201]:
            logger.warning(f"   ⚠️  Could not add item via standard paths. Status: {resp.status_code}")
            logger.info("   🔍 Fetching OpenAPI schema to find correct endpoint...")
            schema_resp = await client.get("/openapi.json")
            if schema_resp.status_code == 200:
                paths = schema_resp.json().get("paths", {}).keys()
                logger.info(f"   Available paths: {list(paths)}")
            return

        item = resp.json()
        logger.info(f"   ✅ Item added to cart: {item}")

        # 6. Checkout (Create Order)
        logger.info("6️⃣  Checking Out (Creating Order)...")
        order_id = str(uuid.uuid4())
        order_payload = {
            "id": order_id,
            "customer_id": customer_id,
            "status": "PENDING_PAYMENT",
            "payment_status": "PENDING",
            "total_amount": 1500.00,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 1,
                    "unit_price": 1500.00
                }
            ]
        }
        resp = await client.post("/orders/", json=order_payload)
        if resp.status_code != 200:
            logger.error(f"Failed to create order: {resp.text}")
            return
        order = resp.json()
        order_id = order["id"]
        logger.info(f"   ✅ Order created successfully (ID: {order_id})")
        
        # 7. Verify Order
        logger.info("7️⃣  Verifying Order Details...")
        resp = await client.get(f"/orders/{order_id}")
        assert resp.status_code == 200
        final_order = resp.json()
        assert final_order["total_amount"] == 1500.00
        assert final_order["status"] == "PENDING_PAYMENT"
        logger.info("   ✅ Order details verified")

        logger.info("🎉 Client Journey Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(run_journey())
