"""
API Integration Tests

End-to-end tests for all CRUD endpoints with real HTTP requests.
Coverage target: 75%+ for api/routes/
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
{% for entity in entities %}
from tests.factories import {{ entity.name }}Factory
{% endfor %}

{% for entity in entities %}
class Test{{ entity.name }}API:
    """Integration tests for {{ entity.name }} CRUD endpoints."""

    BASE_URL = "/api/{{ entity.table_name }}"

    @pytest.mark.asyncio
    async def test_create_{{ entity.snake_name }}_success(self, client: AsyncClient):
        """Test POST {{ BASE_URL }} creates {{ entity.snake_name }} successfully."""
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()

        response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        {% for field in entity.fields %}
        {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
        {% if field.type in ["str", "bool", "int"] %}
        assert data["{{ field.name }}"] == {{ entity.snake_name }}_data.{{ field.name }}
        {% endif %}
        {% endif %}
        {% endfor %}
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_{{ entity.snake_name }}_validation_error(self, client: AsyncClient):
        """Test POST {{ BASE_URL }} with invalid data returns 422."""
        invalid_data = {}  # Missing required fields

        response = await client.post(self.BASE_URL, json=invalid_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    {% for field in entity.fields %}
    {% if field.required and not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
    @pytest.mark.asyncio
    async def test_create_{{ entity.snake_name }}_missing_{{ field.name }}(self, client: AsyncClient):
        """Test POST {{ BASE_URL }} without required {{ field.name }} returns 422."""
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create().model_dump(mode='json')
        del {{ entity.snake_name }}_data["{{ field.name }}"]

        response = await client.post(self.BASE_URL, json={{ entity.snake_name }}_data)

        assert response.status_code == 422

    {% endif %}
    {% endfor %}

    {% for field in entity.fields %}
    {% if field.constraints and field.type == "str" and not field.primary_key %}
    {% if field.constraints.get('max_length') %}
    @pytest.mark.asyncio
    async def test_create_{{ entity.snake_name }}_{{ field.name }}_too_long(self, client: AsyncClient):
        """Test POST {{ BASE_URL }} with {{ field.name }} exceeding max_length returns 422."""
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        {{ entity.snake_name }}_data.{{ field.name }} = "a" * ({{ field.constraints.get('max_length') }} + 1)

        response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )

        assert response.status_code == 422

    {% endif %}
    {% endif %}
    {% endfor %}

    @pytest.mark.asyncio
    async def test_get_existing_{{ entity.snake_name }}(self, client: AsyncClient):
        """Test GET {{ BASE_URL }}/{id} returns existing {{ entity.snake_name }}."""
        # Create {{ entity.snake_name }} first
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        create_response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )
        created = create_response.json()

        # Get {{ entity.snake_name }}
        response = await client.get(f"{self.BASE_URL}/{created['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        {% for field in entity.fields %}
        {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
        {% if field.type in ["str", "bool", "int"] %}
        assert data["{{ field.name }}"] == created["{{ field.name }}"]
        {% endif %}
        {% endif %}
        {% endfor %}

    @pytest.mark.asyncio
    async def test_get_nonexistent_{{ entity.snake_name }}(self, client: AsyncClient):
        """Test GET {{ BASE_URL }}/{id} with nonexistent ID returns 404."""
        fake_id = str(uuid4())

        response = await client.get(f"{self.BASE_URL}/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_{{ entity.snake_name }}_invalid_uuid(self, client: AsyncClient):
        """Test GET {{ BASE_URL }}/{id} with invalid UUID returns 422."""
        response = await client.get(f"{self.BASE_URL}/not-a-valid-uuid")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_{{ entity.table_name }}_empty(self, client: AsyncClient):
        """Test GET {{ BASE_URL }} returns empty list when no {{ entity.table_name }} exist."""
        response = await client.get(self.BASE_URL)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 10

    @pytest.mark.asyncio
    async def test_list_{{ entity.table_name }}_with_data(self, client: AsyncClient):
        """Test GET {{ BASE_URL }} returns all {{ entity.table_name }}."""
        # Create 3 {{ entity.table_name }}
        for _ in range(3):
            {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
            await client.post(
                self.BASE_URL,
                json={{ entity.snake_name }}_data.model_dump(mode='json')
            )

        response = await client.get(self.BASE_URL)

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_{{ entity.table_name }}_pagination(self, client: AsyncClient):
        """Test GET {{ BASE_URL }} with pagination parameters."""
        # Create 5 {{ entity.table_name }}
        for _ in range(5):
            {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
            await client.post(
                self.BASE_URL,
                json={{ entity.snake_name }}_data.model_dump(mode='json')
            )

        # Get page 2 with size 2
        response = await client.get(f"{self.BASE_URL}?page=2&size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["size"] == 2
        assert data["pages"] == 3  # ceil(5/2) = 3

    @pytest.mark.asyncio
    async def test_list_{{ entity.table_name }}_invalid_pagination(self, client: AsyncClient):
        """Test GET {{ BASE_URL }} with invalid pagination parameters."""
        response = await client.get(f"{self.BASE_URL}?page=-1&size=0")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_existing_{{ entity.snake_name }}(self, client: AsyncClient):
        """Test PUT {{ BASE_URL }}/{id} updates {{ entity.snake_name }} successfully."""
        # Create {{ entity.snake_name }} first
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        create_response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )
        created = create_response.json()

        # Update {{ entity.snake_name }}
        update_data = {
            {% for field in entity.fields %}
            {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
            {% if field.type == "str" %}
            "{{ field.name }}": "updated_{{ field.name }}",
            
            {% endif %}
            {% endif %}
            {% endfor %}
        }
        response = await client.put(
            f"{self.BASE_URL}/{created['id']}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        {% for field in entity.fields %}
        {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
        {% if field.type == "str" %}
        assert data["{{ field.name }}"] == "updated_{{ field.name }}"
        
        {% endif %}
        {% endif %}
        {% endfor %}

    @pytest.mark.asyncio
    async def test_update_nonexistent_{{ entity.snake_name }}(self, client: AsyncClient):
        """Test PUT {{ BASE_URL }}/{id} with nonexistent ID returns 404."""
        fake_id = str(uuid4())
        update_data = {
            {% for field in entity.fields %}
            {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
            {% if field.type == "str" %}
            "{{ field.name }}": "updated_value"
            
            {% endif %}
            {% endif %}
            {% endfor %}
        }

        response = await client.put(f"{self.BASE_URL}/{fake_id}", json=update_data)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_{{ entity.snake_name }}_partial_update(self, client: AsyncClient):
        """Test PUT {{ BASE_URL }}/{id} with partial data updates only specified fields."""
        # Create {{ entity.snake_name }} first
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        create_response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )
        created = create_response.json()

        # Update only one field
        update_data = {
            {% for field in entity.fields %}
            {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
            {% if field.type == "str" %}
            "{{ field.name }}": "partially_updated"
            
            {% endif %}
            {% endif %}
            {% endfor %}
        }
        response = await client.put(
            f"{self.BASE_URL}/{created['id']}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        {% for field in entity.fields %}
        {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
        {% if field.type == "str" %}
        assert data["{{ field.name }}"] == "partially_updated"
        
        {% endif %}
        {% endif %}
        {% endfor %}

        # Other fields should remain unchanged
        {% set updated_field_found = namespace(value=False) %}
        {% for field in entity.fields %}
        {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
        {% if not updated_field_found.value %}
        {% if field.type == "str" %}
        {% set updated_field_found.value = True %}
        {% endif %}
        {% else %}
        {% if field.type in ["str", "bool", "int"] %}
        assert data["{{ field.name }}"] == created["{{ field.name }}"]
        {% endif %}
        {% endif %}
        {% endif %}
        {% endfor %}

    @pytest.mark.asyncio
    async def test_update_{{ entity.snake_name }}_validation_error(self, client: AsyncClient):
        """Test PUT {{ BASE_URL }}/{id} with invalid data returns 422."""
        # Create {{ entity.snake_name }} first
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        create_response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )
        created = create_response.json()

        # Update with invalid data
        {% for field in entity.fields %}
        {% if field.constraints and field.type == "str" and not field.primary_key %}
        {% if field.constraints.get('max_length') %}
        invalid_data = {
            "{{ field.name }}": "a" * ({{ field.constraints.get('max_length') }} + 1)
        }
        
        {% endif %}
        {% endif %}
        {% endfor %}

        response = await client.put(
            f"{self.BASE_URL}/{created['id']}",
            json=invalid_data
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_existing_{{ entity.snake_name }}(self, client: AsyncClient):
        """Test DELETE {{ BASE_URL }}/{id} deletes {{ entity.snake_name }} successfully."""
        # Create {{ entity.snake_name }} first
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        create_response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )
        created = create_response.json()

        # Delete {{ entity.snake_name }}
        response = await client.delete(f"{self.BASE_URL}/{created['id']}")

        assert response.status_code == 204

        # Verify it's actually deleted
        get_response = await client.get(f"{self.BASE_URL}/{created['id']}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_{{ entity.snake_name }}(self, client: AsyncClient):
        """Test DELETE {{ BASE_URL }}/{id} with nonexistent ID returns 404."""
        fake_id = str(uuid4())

        response = await client.delete(f"{self.BASE_URL}/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_{{ entity.snake_name }}_invalid_uuid(self, client: AsyncClient):
        """Test DELETE {{ BASE_URL }}/{id} with invalid UUID returns 422."""
        response = await client.delete(f"{self.BASE_URL}/not-a-valid-uuid")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, client: AsyncClient):
        """Test complete CRUD workflow: create → get → update → delete."""
        # 1. Create
        {{ entity.snake_name }}_data = {{ entity.name }}Factory.create()
        create_response = await client.post(
            self.BASE_URL,
            json={{ entity.snake_name }}_data.model_dump(mode='json')
        )
        assert create_response.status_code == 201
        created = create_response.json()
        {{ entity.snake_name }}_id = created["id"]

        # 2. Get
        get_response = await client.get(f"{self.BASE_URL}/{{{ entity.snake_name }}_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == {{ entity.snake_name }}_id

        # 3. Update
        update_data = {
            {% for field in entity.fields %}
            {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
            {% if field.type == "str" %}
            "{{ field.name }}": "workflow_updated"
            
            {% endif %}
            {% endif %}
            {% endfor %}
        }
        update_response = await client.put(
            f"{self.BASE_URL}/{{{ entity.snake_name }}_id}",
            json=update_data
        )
        assert update_response.status_code == 200
        {% for field in entity.fields %}
        {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
        {% if field.type == "str" %}
        assert update_response.json()["{{ field.name }}"] == "workflow_updated"
        
        {% endif %}
        {% endif %}
        {% endfor %}

        # 4. List (should contain our {{ entity.snake_name }})
        list_response = await client.get(self.BASE_URL)
        assert list_response.status_code == 200
        assert any(item["id"] == {{ entity.snake_name }}_id for item in list_response.json()["items"])

        # 5. Delete
        delete_response = await client.delete(f"{self.BASE_URL}/{{{ entity.snake_name }}_id}")
        assert delete_response.status_code == 204

        # 6. Verify deletion
        final_get = await client.get(f"{self.BASE_URL}/{{{ entity.snake_name }}_id}")
        assert final_get.status_code == 404

{% endfor %}