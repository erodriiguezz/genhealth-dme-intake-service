"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

type Settled<T> = { key: string; data: T | null; error: ApiError | null };

/** Fetches on mount and whenever `key` changes. `loading` is derived, so no setState runs synchronously in the effect. */
export function useApi<T>(key: string, fetcher: () => Promise<T>) {
  const [nonce, setNonce] = useState(0);
  const fullKey = `${key}#${nonce}`;
  const [settled, setSettled] = useState<Settled<T> | null>(null);

  useEffect(() => {
    let active = true;
    fetcher().then(
      (data) => active && setSettled({ key: fullKey, data, error: null }),
      (e) =>
        active &&
        setSettled({
          key: fullKey,
          data: null,
          error: e instanceof ApiError ? e : new ApiError(0, "unknown_error", "Something went wrong."),
        }),
    );
    return () => {
      active = false;
    };
    // fetcher is recreated on every render; `key` identifies the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullKey]);

  const current = settled !== null && settled.key === fullKey ? settled : null;
  const retry = useCallback(() => setNonce((n) => n + 1), []);
  return {
    loading: current === null,
    data: current === null ? null : current.data,
    error: current === null ? null : current.error,
    retry,
    setData: (data: T) => setSettled({ key: fullKey, data, error: null }),
  };
}
