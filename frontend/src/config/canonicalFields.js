// Canonical Database Field Definitions for Manual Schema Mapping
// Organizes all database columns across core tables for select box dropdowns

export const CANONICAL_DB_GROUPS = [
  {
    group: 'Product Master',
    options: [
      { value: 'product_sku', label: 'Product SKU (products.sku)' },
      { value: 'product_name', label: 'Product Name (products.name)' },
      { value: 'unit_cost', label: 'Unit Cost (products.unit_cost)' },
      { value: 'selling_price', label: 'Selling Price (products.selling_price)' },
      { value: 'lead_time_days', label: 'Lead Time Days (products.lead_time_days)' },
      { value: 'safety_stock_min', label: 'Safety Stock Min (products.safety_stock_min)' },
      { value: 'reorder_point', label: 'Reorder Point (products.reorder_point)' },
      { value: 'category_name', label: 'Product Category (product_categories.name)' }
    ]
  },
  {
    group: 'Inventory & Warehousing',
    options: [
      { value: 'warehouse_code', label: 'Warehouse Code (warehouses.code)' },
      { value: 'warehouse_name', label: 'Warehouse Name (warehouses.name)' },
      { value: 'current_stock', label: 'Current Stock Qty (inventory.current_stock)' },
      { value: 'reserved_stock', label: 'Reserved / Allocated Stock (inventory.reserved_stock)' },
      { value: 'in_transit_stock', label: 'In-Transit Stock (inventory.in_transit_stock)' }
    ]
  },
  {
    group: 'Sales & Transactions',
    options: [
      { value: 'transaction_date', label: 'Transaction Date (sales_history.date)' },
      { value: 'quantity_sold', label: 'Quantity Sold (sales_history.quantity_sold)' },
      { value: 'sales_revenue', label: 'Sales Revenue / Amount (sales_history.revenue)' }
    ]
  },
  {
    group: 'Suppliers & Vendors',
    options: [
      { value: 'supplier_code', label: 'Supplier Code (suppliers.code)' },
      { value: 'supplier_name', label: 'Supplier Name (suppliers.name)' }
    ]
  },
  {
    group: 'Customers & Orders',
    options: [
      { value: 'customer_code', label: 'Customer Code (customers.customer_code)' },
      { value: 'customer_name', label: 'Customer Name (customers.name)' },
      { value: 'order_number', label: 'Order Number (orders.order_number)' }
    ]
  },
  {
    group: 'Store & Space',
    options: [
      { value: 'shelf_space_sqm', label: 'Shelf Space Sqm (retail_spaces.allocated_space_sqm)' }
    ]
  },
  {
    group: 'Exclude',
    options: [
      { value: 'ignore', label: '🚫 Do Not Map (Ignore Column)' }
    ]
  }
];

export const CANONICAL_FIELD_LABEL_MAP = CANONICAL_DB_GROUPS.reduce((acc, grp) => {
  grp.options.forEach(opt => {
    acc[opt.value] = opt.label;
  });
  return acc;
}, {});
