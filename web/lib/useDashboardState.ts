"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";
import { parseState, serializeState, type DashboardState } from "./state";
import type { Report } from "./types";

// Query string adalah sumber state. Saat build (prerender) query dianggap kosong sehingga
// HTML statis berisi tampilan bawaan; setelah hidrasi nilai dari URL langsung dipakai.
const URL_EVENT = "biotrace:urlchange";

function subscribe(onChange: () => void) {
  window.addEventListener("popstate", onChange);
  window.addEventListener(URL_EVENT, onChange);
  return () => {
    window.removeEventListener("popstate", onChange);
    window.removeEventListener(URL_EVENT, onChange);
  };
}

const getSearch = () => window.location.search;
const getServerSearch = () => "";

export function useDashboardState(report: Report) {
  const search = useSyncExternalStore(subscribe, getSearch, getServerSearch);
  const state = useMemo(() => parseState(search, report), [search, report]);

  const update = useCallback(
    (patch: Partial<DashboardState>) => {
      const next = { ...parseState(window.location.search, report), ...patch };
      // replaceState bawaan browser terintegrasi dengan router Next.js
      window.history.replaceState(null, "", `${window.location.pathname}${serializeState(next, report)}`);
      window.dispatchEvent(new Event(URL_EVENT));
    },
    [report],
  );

  return [state, update] as const;
}
