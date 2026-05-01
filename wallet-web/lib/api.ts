export const walletApiBaseUrl =
  process.env.NEXT_PUBLIC_WALLET_API_BASE_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8007";

export const franceConnectLoginUrl =
  process.env.NEXT_PUBLIC_FRANCECONNECT_LOGIN_URL || "http://127.0.0.1:8001/auth/login";

