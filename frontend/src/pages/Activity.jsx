import { useState } from 'react';
import { Badge, DataState, PageHeading, Pagination, SearchBox, useDebounced, useList } from '../ui';
import { date } from '../utils';

export default function Activity() {
  const [search, setSearch] = useState('');
  const [kind, setKind] = useState('');
  const [page, setPage] = useState(1);
  const query = useList('stock-movements', { search: useDebounced(search), kind, page });
  return (
    <>
      <PageHeading
        eyebrow="EVERY CHANGE, ACCOUNTED FOR"
        title="Stock activity"
        description="The permanent record of receipts, reservations, shipments, and adjustments."
      />
      <section className="panel">
        <div className="toolbar">
          <SearchBox
            value={search}
            onChange={(value) => {
              setSearch(value);
              setPage(1);
            }}
            placeholder="Search products, references, or notes…"
          />
          <select
            aria-label="Movement type"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All movements</option>
            {['ADJUSTMENT', 'PURCHASE', 'RESERVE', 'RELEASE', 'SALE'].map((type) => (
              <option key={type}>{type}</option>
            ))}
          </select>
        </div>
        <DataState
          query={query}
          emptyTitle="No stock activity yet"
          emptyText="Record an opening stock adjustment, receive a purchase, or confirm a sales order to start your ledger."
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Movement</th>
                  <th className="number">Stock change</th>
                  <th className="number">Reserved change</th>
                  <th className="number">Stock after</th>
                  <th>Reference / note</th>
                  <th>Recorded by</th>
                </tr>
              </thead>
              <tbody>
                {query.data?.results.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <strong>{m.product_name}</strong>
                      <small className="cell-secondary">{m.sku}</small>
                    </td>
                    <td>
                      <Badge value={m.kind} />
                      <small className="cell-secondary">{date(m.created_at)}</small>
                    </td>
                    <td className={`number strong ${m.quantity_delta > 0 ? 'positive-text' : ''}`}>
                      {m.quantity_delta > 0 ? '+' : ''}
                      {m.quantity_delta}
                    </td>
                    <td className="number">
                      {m.reserved_delta > 0 ? '+' : ''}
                      {m.reserved_delta}
                    </td>
                    <td className="number">
                      {m.balance_after}
                      <small className="cell-secondary">{m.reserved_after} reserved</small>
                    </td>
                    <td>
                      <span>{m.reference || 'Manual adjustment'}</span>
                      <small className="cell-secondary">{m.note}</small>
                    </td>
                    <td className="muted">{m.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination data={query.data} page={page} onPage={setPage} disabled={query.isFetching} />
        </DataState>
      </section>
    </>
  );
}
