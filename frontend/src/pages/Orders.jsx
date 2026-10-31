import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  ArrowUpRight,
  Check,
  CreditCard,
  Download,
  PackageCheck,
  Pencil,
  Plus,
  Trash2,
  Truck,
  X,
} from 'lucide-react';
import Decimal from 'decimal.js';
import { allRecords, api, downloadInvoice } from '../api';
import { useSession } from '../session';
import {
  Badge,
  DataState,
  Empty,
  ErrorBanner,
  Field,
  FormActions,
  Modal,
  PageHeading,
  Pagination,
  SearchBox,
  Spinner,
  useDebounced,
  useList,
  useSave,
  useToast,
} from '../ui';
import { date, money, totals } from '../utils';

export default function Orders({ kind }) {
  const sales = kind === 'sales';
  const resource = sales ? 'sales-orders' : 'purchase-orders';
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState(params.get('order'));
  const [editing, setEditing] = useState(params.has('new') ? {} : null);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const { canManage } = useSession();
  const query = useList(resource, { search: useDebounced(search), status, page });
  function closeDetail() {
    setSelected(null);
    setParams({});
  }
  return (
    <>
      <PageHeading
        eyebrow={sales ? 'FROM REQUEST TO DELIVERY' : 'KEEP THE SHELVES READY'}
        title={sales ? 'Sales orders' : 'Purchase orders'}
        description={
          sales
            ? 'A clear path from the first draft to the final shipment.'
            : 'Manage supplier orders and receive stock with confidence.'
        }
      >
        {(sales || canManage) && (
          <button className="button primary" onClick={() => setEditing({})}>
            <Plus size={17} />
            {sales ? 'New sales order' : 'New purchase order'}
          </button>
        )}
      </PageHeading>
      <section className="panel">
        <div className="toolbar">
          <SearchBox
            value={search}
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
            placeholder={sales ? 'Search orders or customers…' : 'Search orders or suppliers…'}
          />
          <select
            aria-label="Order status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {(sales
              ? ['DRAFT', 'CONFIRMED', 'SHIPPED', 'CANCELLED']
              : ['DRAFT', 'RECEIVED', 'CANCELLED']
            ).map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <DataState
          query={query}
          emptyTitle="No orders found"
          emptyText={
            search || status
              ? 'Try another search or status filter.'
              : sales
                ? 'Your first sales order starts with a customer and a product.'
                : 'Add a supplier and products, then create a purchase order.'
          }
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>{sales ? 'Customer' : 'Supplier'}</th>
                  <th>Date</th>
                  <th>Status</th>
                  {sales && <th>Payment</th>}
                  <th className="number">Total</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {query.data?.results.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <button className="record-link" onClick={() => setSelected(o.id)}>
                        {o.number}
                      </button>
                      <small className="cell-secondary">
                        {o.items.length} {o.items.length === 1 ? 'product' : 'products'}
                      </small>
                    </td>
                    <td>{sales ? o.customer_name : o.supplier_name}</td>
                    <td className="muted">{date(o.created_at)}</td>
                    <td>
                      <Badge value={o.status} />
                    </td>
                    {sales && (
                      <td>
                        <Badge value={o.payment_status} />
                      </td>
                    )}
                    <td className="number strong">{money(o.total, o.currency)}</td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Open ${o.number}`}
                        onClick={() => setSelected(o.id)}
                      >
                        <ArrowUpRight size={17} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination data={query.data} page={page} onPage={setPage} disabled={query.isFetching} />
        </DataState>
      </section>
      {selected && (
        <OrderDetail
          id={selected}
          resource={resource}
          sales={sales}
          onClose={closeDetail}
          onEdit={(order) => {
            closeDetail();
            setEditing(order);
          }}
        />
      )}
      {editing && (
        <OrderForm
          order={editing}
          resource={resource}
          sales={sales}
          onClose={() => {
            setEditing(null);
            setParams({});
          }}
          onSaved={(order) => {
            setEditing(null);
            setSelected(order.id);
          }}
        />
      )}
    </>
  );
}
function OrderDetail({ id, resource, sales, onClose, onEdit }) {
  const { canManage } = useSession();
  const [pending, setPending] = useState(null);
  const toast = useToast();
  const query = useQuery({
    queryKey: [resource, id],
    queryFn: () => api(`/api/${resource}/${id}/`),
  });
  const save = useSave(
    ({ action, body = {} }) => api(`/api/${resource}/${id}/${action}/`, { method: 'POST', body }),
    'Order updated.',
    () => setPending(null),
  );
  const invoice = useMutation({
    mutationFn: downloadInvoice,
    onSuccess: () => toast('Invoice downloaded.'),
  });
  const order = query.data;
  const descriptions = {
    confirm:
      'Confirming reserves every product on this order. Product prices and billing details are preserved for the invoice.',
    ship: 'Shipping removes these units from on-hand stock and closes the reservation. This action cannot be reversed.',
    cancel:
      'Cancel this order? Any sales reservations will be released. Paid orders must be marked unpaid after a refund is arranged.',
    receive:
      'Receiving adds every line to on-hand stock. Verify the full delivery first. This action cannot be reversed.',
    payment:
      'This records a payment status only. Payments and refunds are handled outside Stockroom.',
  };
  return (
    <>
      <Modal title={order?.number || 'Order details'} onClose={onClose} wide>
        {query.isPending ? (
          <Spinner />
        ) : query.isError ? (
          <div className="form-body">
            <ErrorBanner error={query.error} retry={() => query.refetch()} />
          </div>
        ) : (
          <>
            <div className="order-detail">
              <div className="order-summary">
                <div>
                  <p className="eyebrow">{sales ? 'CUSTOMER' : 'SUPPLIER'}</p>
                  <h3>{sales ? order.customer_name : order.supplier_name}</h3>
                  {sales && (
                    <>
                      <p>{order.customer_email}</p>
                      <p className="pre-line">{order.customer_address}</p>
                    </>
                  )}
                </div>
                <div className="order-meta">
                  <Badge value={order.status} />
                  {sales && <Badge value={order.payment_status} />}
                  <small>Created {date(order.created_at)}</small>
                  <small>By {order.created_by_name || 'Team member'}</small>
                </div>
              </div>
              <ErrorBanner error={save.error || invoice.error} />
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th className="number">Quantity</th>
                      <th className="number">Unit price</th>
                      <th className="number">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.items.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <strong>{item.product_name}</strong>
                          <small className="cell-secondary">{item.sku}</small>
                        </td>
                        <td className="number">{item.quantity}</td>
                        <td className="number">{money(item.unit_price, order.currency)}</td>
                        <td className="number strong">{money(item.line_total, order.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="order-totals">
                <span>
                  Subtotal<strong>{money(order.subtotal, order.currency)}</strong>
                </span>
                <span>
                  Tax ({order.tax_rate}%)<strong>{money(order.tax_amount, order.currency)}</strong>
                </span>
                <span className="total-line">
                  Total<strong>{money(order.total, order.currency)}</strong>
                </span>
              </div>
              {order.notes && (
                <div className="order-notes">
                  <strong>Notes</strong>
                  <p className="pre-line">{order.notes}</p>
                </div>
              )}
              <div className="detail-timeline">
                {order.confirmed_at && (
                  <span>
                    <Check size={15} />
                    Confirmed {date(order.confirmed_at)}
                  </span>
                )}
                {order.shipped_at && (
                  <span>
                    <Truck size={15} />
                    Shipped {date(order.shipped_at)}
                  </span>
                )}
                {order.received_at && (
                  <span>
                    <PackageCheck size={15} />
                    Received {date(order.received_at)}
                  </span>
                )}
              </div>
            </div>
            <div className="detail-actions">
              {order.status === 'DRAFT' && (sales || canManage) && (
                <button className="button secondary" onClick={() => onEdit(order)}>
                  <Pencil size={15} />
                  Edit draft
                </button>
              )}
              {sales && ['CONFIRMED', 'SHIPPED'].includes(order.status) && (
                <button
                  className="button secondary"
                  disabled={invoice.isPending}
                  onClick={() => invoice.mutate(order)}
                >
                  <Download size={15} />
                  {invoice.isPending ? 'Preparing…' : 'Download invoice'}
                </button>
              )}
              {canManage && (
                <>
                  {sales && order.status === 'DRAFT' && (
                    <button
                      className="button primary"
                      onClick={() => setPending({ action: 'confirm', title: 'Confirm order' })}
                    >
                      <Check size={16} />
                      Confirm order
                    </button>
                  )}
                  {sales && order.status === 'CONFIRMED' && (
                    <button
                      className="button primary"
                      onClick={() => setPending({ action: 'ship', title: 'Ship order' })}
                    >
                      <Truck size={16} />
                      Ship order
                    </button>
                  )}
                  {!sales && order.status === 'DRAFT' && (
                    <button
                      className="button primary"
                      onClick={() => setPending({ action: 'receive', title: 'Receive stock' })}
                    >
                      <PackageCheck size={16} />
                      Receive stock
                    </button>
                  )}
                  {sales && ['CONFIRMED', 'SHIPPED'].includes(order.status) && (
                    <button
                      className="button secondary"
                      onClick={() =>
                        setPending({
                          action: 'payment',
                          body: {
                            payment_status: order.payment_status === 'PAID' ? 'UNPAID' : 'PAID',
                          },
                          title: order.payment_status === 'PAID' ? 'Mark unpaid' : 'Mark paid',
                        })
                      }
                    >
                      <CreditCard size={15} />
                      {order.payment_status === 'PAID' ? 'Mark unpaid' : 'Mark paid'}
                    </button>
                  )}
                  {['DRAFT', 'CONFIRMED'].includes(order.status) && (
                    <button
                      className="button danger-quiet"
                      onClick={() => setPending({ action: 'cancel', title: 'Cancel order' })}
                    >
                      <X size={15} />
                      Cancel order
                    </button>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </Modal>
      {pending && (
        <Modal title={pending.title} onClose={() => !save.isPending && setPending(null)}>
          <div className="form-body">
            <p>{descriptions[pending.action]}</p>
            <ErrorBanner error={save.error} />
          </div>
          <div className="form-actions">
            <button
              className="button secondary"
              disabled={save.isPending}
              onClick={() => setPending(null)}
            >
              Go back
            </button>
            <button
              className={`button ${pending.action === 'cancel' ? 'danger' : 'primary'}`}
              disabled={save.isPending}
              onClick={() => save.mutate(pending)}
            >
              {save.isPending ? 'Updating…' : pending.title}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
function newLine() {
  return { key: crypto.randomUUID(), product: '', quantity: '1', unit_price: '0.00' };
}
function OrderForm({ order, resource, sales, onClose, onSaved }) {
  const { session } = useSession();
  const [key] = useState(() => crypto.randomUUID());
  const [lines, setLines] = useState(
    () =>
      order.items?.map((item) => ({ ...item, key: item.id, product: String(item.product) })) || [
        newLine(),
      ],
  );
  const [taxRate, setTaxRate] = useState(order.tax_rate || '0');
  const products = useQuery({
    queryKey: ['product-options'],
    queryFn: () => allRecords('products'),
  });
  const suppliers = useQuery({
    queryKey: ['supplier-options'],
    queryFn: () => allRecords('suppliers'),
    enabled: !sales,
  });
  const save = useSave(
    (data) =>
      api(`/api/${resource}/${order.id ? `${order.id}/` : ''}`, {
        method: order.id ? 'PATCH' : 'POST',
        body: data,
        headers: order.id ? {} : { 'Idempotency-Key': key },
      }),
    order.id ? 'Draft updated.' : 'Draft order created.',
    onSaved,
  );
  const amount = totals(lines, taxRate);
  const currency = order.currency || session.business.currency;
  function updateLine(index, field, value) {
    setLines((current) =>
      current.map((line, i) => {
        if (i !== index) return line;
        if (field !== 'product') return { ...line, [field]: value };
        const product = products.data?.find((p) => p.id === value);
        return {
          ...line,
          product: value,
          unit_price: product ? (sales ? product.sale_price : product.cost_price) : '0.00',
        };
      }),
    );
  }
  function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    body.items = lines.map((line) => ({
      product: line.product,
      quantity: Number(line.quantity),
      unit_price: line.unit_price,
    }));
    body.tax_rate = taxRate;
    save.mutate(body);
  }
  const loading = products.isPending || (!sales && suppliers.isPending);
  const optionError = products.error || (!sales && suppliers.error);
  return (
    <Modal
      title={`${order.id ? 'Edit' : 'New'} ${sales ? 'sales' : 'purchase'} order`}
      wide
      onClose={() => !save.isPending && onClose()}
    >
      <form onSubmit={submit}>
        <div className="form-body">
          <ErrorBanner error={save.error || optionError} />
          {loading ? (
            <Spinner text="Loading your catalog…" />
          ) : !products.data?.length || (!sales && !suppliers.data?.length) ? (
            <Empty
              title="Set up your catalog first"
              text={
                sales
                  ? 'Add at least one active product in Inventory.'
                  : 'Add at least one active product and supplier before creating a purchase order.'
              }
            />
          ) : (
            <>
              <div className="form-grid">
                {sales ? (
                  <>
                    <Field label="Customer name">
                      <input
                        name="customer_name"
                        defaultValue={order.customer_name}
                        required
                        maxLength={180}
                        autoComplete="organization"
                      />
                    </Field>
                    <Field label="Customer email">
                      <input
                        name="customer_email"
                        type="email"
                        defaultValue={order.customer_email}
                        maxLength={254}
                        autoComplete="email"
                      />
                    </Field>
                    <Field label="Billing address" className="full">
                      <textarea
                        name="customer_address"
                        rows={2}
                        maxLength={1000}
                        defaultValue={order.customer_address}
                      />
                    </Field>
                  </>
                ) : (
                  <Field label="Supplier" className="full">
                    <select name="supplier" defaultValue={order.supplier || ''} required>
                      <option value="">Select a supplier</option>
                      {suppliers.data?.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                )}
              </div>
              <div className="line-heading">
                <h3>Order items</h3>
                <span className="muted">Prices in {currency}</span>
              </div>
              <div className="order-lines">
                {lines.map((line, index) => (
                  <div className="order-line" key={line.key}>
                    <Field label={`Product ${index + 1}`}>
                      <select
                        aria-label={`Product ${index + 1}`}
                        required
                        value={line.product}
                        onChange={(e) => updateLine(index, 'product', e.target.value)}
                      >
                        <option value="">Select a product</option>
                        {line.product && !products.data?.some((p) => p.id === line.product) && (
                          <option value={line.product}>{line.product_name} (archived)</option>
                        )}
                        {products.data?.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.sku} · {p.name} ({p.available_quantity} available)
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Quantity">
                      <input
                        aria-label={`Quantity ${index + 1}`}
                        type="number"
                        min="1"
                        max="1000000"
                        step="1"
                        required
                        value={line.quantity}
                        onChange={(e) => updateLine(index, 'quantity', e.target.value)}
                      />
                    </Field>
                    <Field label="Unit price">
                      <input
                        aria-label={`Unit price ${index + 1}`}
                        type="number"
                        min="0"
                        max="9999999999.99"
                        step="0.01"
                        required
                        value={line.unit_price}
                        onChange={(e) => updateLine(index, 'unit_price', e.target.value)}
                      />
                    </Field>
                    <div className="line-total">
                      <small>Amount</small>
                      <strong>
                        {money(
                          new Decimal(line.quantity || 0).times(line.unit_price || 0),
                          currency,
                        )}
                      </strong>
                    </div>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Remove item ${index + 1}`}
                      disabled={lines.length === 1}
                      onClick={() => setLines((current) => current.filter((_, i) => i !== index))}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="text-button"
                disabled={lines.length >= 100}
                onClick={() => setLines((current) => [...current, newLine()])}
              >
                <Plus size={16} />
                Add another item
              </button>
              <div className="order-form-bottom">
                <div>
                  <Field label="Tax rate (%)">
                    <input
                      name="tax_rate"
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      required
                      value={taxRate}
                      onChange={(e) => setTaxRate(e.target.value)}
                    />
                  </Field>
                  <Field label="Notes">
                    <textarea
                      name="notes"
                      rows={3}
                      maxLength={2000}
                      defaultValue={order.notes}
                      placeholder="Delivery details, payment terms, or an internal note…"
                    />
                  </Field>
                </div>
                <div className="order-totals">
                  <span>
                    Subtotal<strong>{money(amount.subtotal, currency)}</strong>
                  </span>
                  <span>
                    Tax<strong>{money(amount.tax, currency)}</strong>
                  </span>
                  <span className="total-line">
                    Total<strong>{money(amount.total, currency)}</strong>
                  </span>
                  <small className="muted">Final totals are calculated when saved.</small>
                </div>
              </div>
              <div className="info-box">
                {sales
                  ? 'Saving a draft does not change stock. An admin or manager confirms the order to reserve inventory.'
                  : 'Saving a draft does not change stock. Use Receive stock after the full delivery arrives.'}
              </div>
            </>
          )}
        </div>
        <FormActions
          busy={
            save.isPending ||
            loading ||
            !!optionError ||
            !products.data?.length ||
            (!sales && !suppliers.data?.length)
          }
          onClose={onClose}
          label={order.id ? 'Save draft' : 'Create draft order'}
        />
      </form>
    </Modal>
  );
}
