# Migration & Schema Consistency Checklist

- [ ] Migration uses real entity fields (no stub): all columns from `entities` present with correct types/defaults.
- [ ] Alembic upgrade test passes (no `UndefinedColumnError`).
- [ ] `*Create` schemas do NOT require `id/created_at`.
- [ ] `items` fields allow empty list on create (no `min_items` enforced there).
- [ ] Status/payment_status defaults are string literals; enums always quoted.
- [ ] Add-item endpoints use `CartItem/OrderItem` payload, not container schemas.
- [ ] Rutas llaman métodos existentes en services (`get_by_id` et al.).
- [ ] Smoke QA (create product + customer + cart empty + add item + checkout + pay) succeeds in-container.
