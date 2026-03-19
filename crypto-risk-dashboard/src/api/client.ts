import type {
  AssetOptionsResponse,
  CryptoReturnServiceRequest,
  CryptoReturnServiceResponse,
  HorizonRequest,
  HorizonResponse,
  MultiHorizonRequest,
  MultiHorizonResponse,
  PortfolioRequest,
  PortfolioResponse
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function readJson<T>(res: Response): Promise<T> {
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText} - ${text}`);
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON response: ${text}`);
  }
}

async function postJson<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return readJson<TRes>(res);
}

async function getJson<TRes>(path: string): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`);
  return readJson<TRes>(res);
}

export const api = {
  forecastHorizon: (req: HorizonRequest) =>
    postJson<HorizonRequest, HorizonResponse>("/forecast/horizon", req),

  forecastHorizonMulti: (req: MultiHorizonRequest) =>
    postJson<MultiHorizonRequest, MultiHorizonResponse>("/forecast/horizon/multi", req),

  portfolioRecommend: (req: PortfolioRequest) =>
    postJson<PortfolioRequest, PortfolioResponse>("/portfolio/recommend", req),

  getAssetOptions: () =>
    getJson<AssetOptionsResponse>("/assets/options"),

  cryptoReturnService: (req: CryptoReturnServiceRequest) =>
    postJson<CryptoReturnServiceRequest, CryptoReturnServiceResponse>("/crypto_return_service", req)
};
