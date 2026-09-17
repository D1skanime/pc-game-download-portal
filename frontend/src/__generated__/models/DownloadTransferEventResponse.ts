export type DownloadTransferEventResponse = {
  ordinal: number;
  event_type: string;
  observed_bytes: number;
  error_code: string | null;
  occurred_at: string;
};
