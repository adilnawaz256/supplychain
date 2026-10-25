import {
  BarChart3, Package, Settings2, Tag, Users, ShoppingCart, Truck, LayoutGrid, MapPin,
  Box, TrendingUp, Target, Network, ShieldCheck, AlertTriangle, Layers, Trophy, Database,
  Calendar, Share2, Star, Clock, Crown, Store, Lightbulb, DollarSign,
} from 'lucide-react';

export const INTELLIGENCES = [
  { id: 'demand', number: 1, name: 'Demand Forecasting', icon: BarChart3 },
  { id: 'inventory', number: 2, name: 'Inventory Planning', icon: Package },
  { id: 'policy', number: 3, name: 'Inventory Policy', icon: Settings2 },
  { id: 'pricing', number: 4, name: 'Pricing & Demand', icon: Tag },
  { id: 'customers', number: 5, name: 'Customer Value', icon: Users },
  { id: 'basket', number: 6, name: 'Market Basket', icon: ShoppingCart },
  { id: 'suppliers', number: 7, name: 'Supplier Segmentation', icon: Truck },
  { id: 'assortment', number: 8, name: 'Assortment Planning', icon: LayoutGrid },
  { id: 'trade_area', number: 9, name: 'Trade Area', icon: MapPin },
];

/** KPI icon keys sent by the backend. */
export const KPI_ICONS = {
  box: Box, chart: BarChart3, target: Target, model: Network, trending: TrendingUp, shield: ShieldCheck,
  cart: ShoppingCart, alert: AlertTriangle, layers: Layers, trophy: Trophy, database: Database, users: Users,
  calendar: Calendar, share: Share2, star: Star, truck: Truck, clock: Clock, crown: Crown, store: Store,
  bulb: Lightbulb, money: DollarSign,
};

export const TONES = {
  good: { fg: '#059669', bg: '#ecfdf5', border: '#a7f3d0' },
  info: { fg: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  warn: { fg: '#d97706', bg: '#fffbeb', border: '#fde68a' },
  orange: { fg: '#ea580c', bg: '#fff7ed', border: '#fed7aa' },
  bad: { fg: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  purple: { fg: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  neutral: { fg: '#475569', bg: '#f1f5f9', border: '#e2e8f0' },
};

export const PALETTE = ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#94a3b8'];

const AUTO_TONES = ['info', 'purple', 'good', 'warn', 'orange', 'neutral'];
export function autoTone(value) {
  let h = 0;
  for (const ch of String(value)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return AUTO_TONES[h % AUTO_TONES.length];
}
