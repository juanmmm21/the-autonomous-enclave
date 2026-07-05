/**
 * Contrato compartido con el backend (`backend/src/enclave/models.py`).
 * Los campos `Decimal` del backend se serializan como `string` en JSON
 * (ver `MoneyModel`), así que aquí también son `string`.
 */

export type Personality =
  | "ambitious"
  | "cautious"
  | "cooperative"
  | "altruistic"
  | "machiavellian";

export type AgentStatus = "alive" | "sleeping" | "bankrupt" | "terminated";

export type AssetType =
  | "inference_quota"
  | "vector_pack"
  | "alpha_signal"
  | "code_script"
  | "financial_derivative";

export type ContractStatus = "pending" | "fulfilled" | "disputed" | "breached";

export interface Position {
  x: number;
  y: number;
}

export interface AgentState {
  agent_id: string;
  display_name: string;
  personality: Personality[];
  balance: string;
  inventory: Partial<Record<AssetType, number>>;
  inference_quota: number;
  position: Position;
  status: AgentStatus;
  trust_links: Record<string, number>;
  last_reasoning: string | null;
}

export interface MarketOffer {
  offer_id: string;
  seller_id: string;
  asset_type: AssetType;
  quantity: number;
  unit_price: string;
  created_at_tick: number;
}

export interface Contract {
  contract_id: string;
  party_a: string;
  party_b: string;
  terms: string;
  amount: string;
  status: ContractStatus;
  created_at_tick: number;
}

export interface Transaction {
  transaction_id: string;
  from_agent: string;
  to_agent: string;
  amount: string;
  reason: string;
  tick: number;
  timestamp: string;
}

export interface JudgeRuling {
  ruling_id: string;
  contract_id: string;
  at_fault_agent: string;
  verdict: string;
  penalty: string;
  ruled_at_tick: number;
}

export interface EconomicIndicators {
  gini_index: number;
  inflation_rate: number;
  virtual_gdp: number;
  transactions_per_minute: number;
}

export interface TickEvent {
  tick: number;
  timestamp: string;
  agents: AgentState[];
  indicators: EconomicIndicators;
}
