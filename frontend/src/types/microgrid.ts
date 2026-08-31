export interface MicrogridSummary {
  id: string;
  name: string;
  location: string;
  status: "ACTIVE" | "INACTIVE" | "MAINTENANCE";
  created_at: string;
}

export interface DemoSeedResponse {
  microgrid: MicrogridSummary;
  already_existed: boolean;
  readings_backfilled: number;
  message: string;
}
