export type DownloadTransferResponse = {
  schema_version: number;
  id: string;
  manifest_id: string;
  parent_session_id: string | null;
  attempt_no: number;
  rom_id: number;
  mode: string;
  status: string;
  result?: string | null;
  selected_items: number;
  selected_bytes: number;
  observed_bytes: number;
  started_at: string;
  last_activity_at: string;
  ended_at: string | null;
  items: Array<{
    id: number;
    manifest_member_id: string;
    destination: string;
    expected_bytes: number;
    observed_bytes: number;
    status: string;
    started_at: string | null;
    last_activity_at: string | null;
    ended_at: string | null;
  }>;
  events: Array<{
    ordinal: number;
    event_type: string;
    observed_bytes: number;
    error_code: string | null;
    occurred_at: string;
  }>;
};
