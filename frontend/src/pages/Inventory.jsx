import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Boxes, Pencil, Plus, SlidersHorizontal } from 'lucide-react';
import { allRecords, api } from '../api';
import { useSession } from '../session';
import {
  DataState,
  ErrorBanner,
  Field,
  FormActions,
  Modal,
  PageHeading,
  Pagination,
  SearchBox,
  useDebounced,
  useList,
  useSave,
} from '../ui';
import { money } from '../utils';

export default function Inventory() {
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get('search') || '');
  const [status, setStatus] = useState('true');
  const [low, setLow] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null);
  const [adjusting, setAdjusting] = useState(null);
  const { canManage, session } = useSession();
  const debounced = useDebounced(search);
  const query = useList('products', { search: debounced, is_active: status, low_stock: low, page });
  function filter(fn, value) {
    fn(value);
    setPage(1);
  }
  return (
    <>
      <PageHeading
        eyebrow="A PLACE FOR EVERY PRODUCT"
        title="Inventory"
        description="Know what’s on hand, what’s reserved, and what needs a refill."
      >
        {canManage && (
          <button className="button primary" onClick={() => setEditing({})}>
            <Plus size={17} />
            Add product
          </button>
        )}
      </PageHeading>
      <section className="panel">
        <div className="toolbar">
          <SearchBox
            value={search}
            onChange={(v) => filter(setSearch, v)}
            placeholder="Search products, SKU, or category…"
          />
          <div className="toolbar-filters">
            <select
              aria-label="Product status"
              value={status}
              onChange={(e) => filter(setStatus, e.target.value)}
            >
              <option value="true">Active products</option>
              <option value="false">Archived products</option>
              <option value="">All products</option>
            </select>
            <select
              aria-label="Stock level"
              value={low}
              onChange={(e) => filter(setLow, e.target.value)}
            >
              <option value="">All stock levels</option>
              <option value="true">Low stock only</option>
            </select>
          </div>
        </div>
        <DataState
          query={query}
          emptyTitle="No products found"
          emptyText={
            search || low
              ? 'Try a different search or stock filter.'
              : 'Add your first product, then record its opening stock with Adjust stock.'
          }
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Category</th>
                  <th className="number">On hand</th>
                  <th className="number">Reserved</th>
                  <th className="number">Available</th>
                  <th className="number">Sale price</th>
                  <th>Status</th>
                  {canManage && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {query.data?.results.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="product-cell">
                        <span className="product-icon">
                          <Boxes size={19} />
                        </span>
                        <div>
                          <strong>{p.name}</strong>
                          <small>{p.sku}</small>
                        </div>
                      </div>
                    </td>
                    <td className="muted">{p.category || '—'}</td>
                    <td className="number">{p.quantity}</td>
                    <td className="number muted">{p.reserved_quantity}</td>
                    <td className={`number strong ${p.is_low_stock ? 'warning-text' : ''}`}>
                      {p.available_quantity}
                    </td>
                    <td className="number">{money(p.sale_price, session.business.currency)}</td>
                    <td>
                      <span
                        className={`badge ${!p.is_active ? 'badge-cancelled' : p.is_low_stock ? 'badge-low' : 'badge-active'}`}
                      >
                        {!p.is_active ? 'Archived' : p.is_low_stock ? 'Low stock' : 'In stock'}
                      </span>
                    </td>
                    {canManage && (
                      <td>
                        <div className="row-actions">
                          <button
                            className="icon-button"
                            aria-label={`Edit ${p.name}`}
                            onClick={() => setEditing(p)}
                          >
                            <Pencil size={16} />
                          </button>
                          <button
                            className="icon-button"
                            disabled={!p.is_active}
                            aria-label={`Adjust stock for ${p.name}`}
                            onClick={() => setAdjusting(p)}
                          >
                            <SlidersHorizontal size={16} />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination data={query.data} page={page} onPage={setPage} disabled={query.isFetching} />
        </DataState>
      </section>
      {editing && <ProductForm product={editing} onClose={() => setEditing(null)} />}
      {adjusting && <AdjustmentForm product={adjusting} onClose={() => setAdjusting(null)} />}
    </>
  );
}
function ProductForm({ product, onClose }) {
  const suppliers = useQuery({
    queryKey: ['supplier-options'],
    queryFn: () => allRecords('suppliers'),
  });
  const save = useSave(
    (data) =>
      api(`/api/products/${product.id ? `${product.id}/` : ''}`, {
        method: product.id ? 'PATCH' : 'POST',
        body: data,
      }),
    product.id
      ? 'Product updated.'
      : 'Product added. Use Adjust stock to record its opening balance.',
    onClose,
  );
  function submit(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget));
    data.supplier = data.supplier || null;
    data.is_active = data.is_active === 'on';
    save.mutate(data);
  }
  return (
    <Modal
      title={product.id ? 'Edit product' : 'Add a product'}
      onClose={() => !save.isPending && onClose()}
    >
      <form onSubmit={submit}>
        <div className="form-body">
          <ErrorBanner error={save.error || suppliers.error} />
          <div className="form-grid">
            <Field label="Product name">
              <input name="name" defaultValue={product.name} required maxLength={180} />
            </Field>
            <Field label="SKU" hint="Unique within your business.">
              <input name="sku" defaultValue={product.sku} required maxLength={64} />
            </Field>
            <Field label="Category">
              <input name="category" defaultValue={product.category} maxLength={100} />
            </Field>
            <Field label="Barcode">
              <input name="barcode" defaultValue={product.barcode} maxLength={80} />
            </Field>
            <Field label="Cost price">
              <input
                name="cost_price"
                type="number"
                min="0"
                max="9999999999.99"
                step="0.01"
                defaultValue={product.cost_price || '0.00'}
                required
              />
            </Field>
            <Field label="Sale price">
              <input
                name="sale_price"
                type="number"
                min="0"
                max="9999999999.99"
                step="0.01"
                defaultValue={product.sale_price || '0.00'}
                required
              />
            </Field>
            <Field label="Reorder level">
              <input
                name="reorder_level"
                type="number"
                min="0"
                max="2147483647"
                step="1"
                defaultValue={product.reorder_level ?? 5}
                required
              />
            </Field>
            <Field label="Supplier">
              <select name="supplier" defaultValue={product.supplier || ''}>
                <option value="">No supplier</option>
                {product.supplier && !suppliers.data?.some((s) => s.id === product.supplier) && (
                  <option value={product.supplier}>{product.supplier_name} (archived)</option>
                )}
                {suppliers.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Description">
            <textarea
              name="description"
              rows={3}
              defaultValue={product.description}
              maxLength={4000}
            />
          </Field>
          <label className="checkbox">
            <input name="is_active" type="checkbox" defaultChecked={product.is_active ?? true} />
            Active product
          </label>
        </div>
        <FormActions
          busy={save.isPending || suppliers.isPending || suppliers.isError}
          onClose={onClose}
          label={product.id ? 'Save changes' : 'Add product'}
        />
      </form>
    </Modal>
  );
}
function AdjustmentForm({ product, onClose }) {
  const save = useSave(
    (data) => api(`/api/products/${product.id}/adjust/`, { method: 'POST', body: data }),
    'Stock adjusted and recorded in activity.',
    onClose,
  );
  return (
    <Modal title="Adjust stock" onClose={() => !save.isPending && onClose()}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(Object.fromEntries(new FormData(e.currentTarget)));
        }}
      >
        <div className="form-body">
          <p>
            <strong>{product.name}</strong> <span className="muted">· {product.sku}</span>
          </p>
          <div className="info-box">
            {product.quantity} on hand · {product.reserved_quantity} reserved ·{' '}
            {product.available_quantity} available
          </div>
          <ErrorBanner error={save.error} />
          <Field
            label="Quantity change"
            hint="Use a positive number to add stock, or a negative number to remove it."
          >
            <input
              name="quantity_delta"
              type="number"
              step="1"
              min="-1000000000"
              max="1000000000"
              required
              placeholder="e.g. 20 or -3"
            />
          </Field>
          <Field label="Reason" hint="This note becomes part of your permanent stock history.">
            <textarea
              name="note"
              rows={3}
              required
              maxLength={500}
              placeholder="Opening balance, damaged stock, physical count…"
            />
          </Field>
        </div>
        <FormActions busy={save.isPending} onClose={onClose} label="Record adjustment" />
      </form>
    </Modal>
  );
}
