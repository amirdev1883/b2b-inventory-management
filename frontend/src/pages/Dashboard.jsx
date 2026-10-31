import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowRight,
  ArrowUpRight,
  Boxes,
  CircleAlert,
  PackageCheck,
  ShoppingBag,
  TrendingUp,
} from 'lucide-react';
import { api } from '../api';
import { useSession } from '../session';
import { Badge, Empty, ErrorBanner, PageHeading, Spinner } from '../ui';
import { date, money } from '../utils';

function RevenueChart({ data, currency }) {
  const max = Math.max(...data.map((d) => Number(d.revenue)), 1);
  const points = data.map(
    (d, i) => `${(i * 720) / (data.length - 1)},${160 - (Number(d.revenue) / max) * 145}`,
  );
  const hasSales = data.some((d) => Number(d.revenue) > 0);
  return (
    <div className="revenue-chart">
      <div className="chart-axis">
        <span>{money(max, currency)}</span>
        <span>{money(max / 2, currency)}</span>
        <span>{money(0, currency)}</span>
      </div>
      <div className="chart-body">
        <svg
          viewBox="0 0 720 175"
          role="img"
          aria-label="Daily pre-tax shipped revenue for the last 30 days"
        >
          <defs>
            <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#167e67" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#167e67" stopOpacity="0.01" />
            </linearGradient>
          </defs>
          {[15, 87.5, 160].map((y) => (
            <line key={y} x1="0" x2="720" y1={y} y2={y} stroke="#e9eceb" strokeDasharray="4 5" />
          ))}
          <polygon points={`0,160 ${points.join(' ')} 720,160`} fill="url(#revenueFill)" />
          <polyline
            points={points.join(' ')}
            fill="none"
            stroke="#167e67"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
          {data.map((d, i) => (
            <circle
              key={d.date}
              cx={(i * 720) / (data.length - 1)}
              cy={160 - (Number(d.revenue) / max) * 145}
              r="5"
              fill="#167e67"
              opacity="0.6"
            >
              <title>
                {date(d.date)}: {money(d.revenue, currency)}
              </title>
            </circle>
          ))}
        </svg>
        <div className="chart-dates">
          <span>{date(data[0].date)}</span>
          <span>{date(data[14].date)}</span>
          <span>{date(data.at(-1).date)}</span>
        </div>
      </div>
      {!hasSales && <p className="chart-empty">Your first shipment will start the story.</p>}
    </div>
  );
}
export default function Dashboard() {
  const { session, canManage } = useSession();
  const query = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api('/api/analytics/dashboard/'),
  });
  return (
    <>
      <PageHeading
        eyebrow="THE BIG PICTURE"
        title={`Hello, ${session.user.first_name || 'there'}.`}
        description="Here’s what’s happening across your business."
      >
        <Link className="button primary" to="/sales">
          <ShoppingBag size={17} />
          New sales order
          <ArrowRight size={16} />
        </Link>
      </PageHeading>
      {query.isPending ? (
        <Spinner />
      ) : query.isError ? (
        <ErrorBanner error={query.error} retry={() => query.refetch()} />
      ) : (
        <DashboardContent data={query.data} canManage={canManage} />
      )}
    </>
  );
}
function DashboardContent({ data, canManage }) {
  const metrics = [
    [
      'Shipped revenue',
      money(data.shipped_revenue, data.currency),
      'All time · before tax',
      TrendingUp,
      'green',
    ],
    [
      'Inventory value',
      money(data.inventory_value, data.currency),
      `${data.units_on_hand.toLocaleString()} units on hand · at cost`,
      Boxes,
      'blue',
    ],
    [
      'Open sales orders',
      data.open_sales_orders,
      'Draft and confirmed orders',
      ShoppingBag,
      'purple',
    ],
    [
      'Low-stock products',
      data.low_stock_count,
      'Available stock at reorder level',
      CircleAlert,
      'amber',
    ],
  ];
  return (
    <>
      <div className="metric-grid">
        {metrics.map(([title, value, hint, Icon, tone]) => (
          <article className="metric-card" key={title}>
            <div>
              <span>{title}</span>
              <span className={`metric-icon ${tone}`}>
                <Icon size={19} />
              </span>
            </div>
            <strong>{value}</strong>
            <p>{hint}</p>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel revenue-panel">
          <div className="panel-heading">
            <div>
              <h2>Sales at a glance</h2>
              <p className="muted">Revenue recognized when orders ship</p>
            </div>
            <span className="period-pill">Last 30 days · UTC</span>
          </div>
          <RevenueChart data={data.daily_sales} currency={data.currency} />
        </section>
        <section className="panel stock-panel">
          <div className="panel-heading">
            <div>
              <h2>Stock to watch</h2>
              <p className="muted">A little attention goes a long way</p>
            </div>
            <span className="count-badge">{data.low_stock_count}</span>
          </div>
          {data.low_stock_products.length ? (
            <div className="stock-watch-list">
              {data.low_stock_products.map((p) => (
                <Link key={p.id} to={`/inventory?search=${encodeURIComponent(p.sku)}`}>
                  <span className="product-icon">
                    <Boxes size={20} />
                  </span>
                  <div>
                    <strong>{p.name}</strong>
                    <small>{p.sku}</small>
                  </div>
                  <span>
                    <strong className="stock-number">{p.available_quantity}</strong>
                    <small>available</small>
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <Empty
              title="Stock is in good shape"
              text="No active products are at their reorder level."
            />
          )}
          <Link className="panel-link" to="/inventory">
            View inventory
            <ArrowRight size={15} />
          </Link>
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Recent sales orders</h2>
            <p className="muted">From the first request to the final shipment</p>
          </div>
          <Link className="text-button" to="/sales">
            View all orders
            <ArrowUpRight size={16} />
          </Link>
        </div>
        {data.recent_orders.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th className="number">Total</th>
                  <th aria-label="Open order" />
                </tr>
              </thead>
              <tbody>
                {data.recent_orders.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <Link className="record-link" to={`/sales?order=${order.id}`}>
                        {order.number}
                      </Link>
                    </td>
                    <td>{order.customer_name}</td>
                    <td className="muted">{date(order.created_at)}</td>
                    <td>
                      <Badge value={order.status} />
                    </td>
                    <td className="number strong">{money(order.total, order.currency)}</td>
                    <td>
                      <Link
                        aria-label={`Open ${order.number}`}
                        className="icon-button"
                        to={`/sales?order=${order.id}`}
                      >
                        <ArrowUpRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="Ready for your first order"
            text="Add products to your inventory, then create a sales order."
          >
            <Link to="/inventory" className="button secondary">
              Go to inventory
              <ArrowRight size={15} />
            </Link>
          </Empty>
        )}
      </section>
      <div className="dashboard-note">
        <PackageCheck size={19} />
        <span>
          {data.product_count} active products · {data.units_reserved} units reserved for confirmed
          orders.
        </span>
        {canManage && (
          <Link to="/purchases">
            Manage purchasing
            <ArrowRight size={14} />
          </Link>
        )}
      </div>
    </>
  );
}
