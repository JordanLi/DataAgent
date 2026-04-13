/**
 * Shared TypeScript types for DataAgent frontend.
 * Extended in Steps 9 & 10.
 */

export type Role = "admin" | "analyst" | "viewer";

export interface User {
  id: number;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface DataSource {
  id: number;
  name: string;
  db_type: "mysql";
  host: string;
  port: number;
  database: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface TableColumn {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
  comment: string | null;
  alias?: string;
}

export interface TableMeta {
  table_name: string;
  table_comment: string | null;
  columns: TableColumn[];
}

export interface BusinessTerm {
  id: number;
  datasource_id: number;
  term_name: string;
  definition: string;
  sql_expression: string;
}

export interface FieldAlias {
  id: number;
  datasource_id: number;
  table_name: string;
  column_name: string;
  alias_name: string;
  description: string;
}

export interface EnumMapping {
  id: number;
  datasource_id: number;
  table_name: string;
  column_name: string;
  enum_value: string;
  display_label: string;
}

export interface TableRelation {
  id: number;
  datasource_id: number;
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  relation_type: "many_to_one" | "one_to_many" | "one_to_one";
}

// Chat types
export type ChartType = "line" | "bar" | "pie" | "scatter" | "none";

export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  execution_time_ms: number;
  chart_type: ChartType;
  insight: string;
}

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  sql?: string;
  result?: QueryResult;
  error?: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  datasource_id: number | null;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user_id: number;
  username: string;
  action: string;
  datasource_id: number | null;
  datasource_name: string | null;
  sql_executed: string | null;
  row_count: number | null;
  duration_ms: number | null;
  created_at: string;
}

// API response wrappers
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  detail: string;
}
