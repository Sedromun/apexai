"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch, apiJson } from "./api";
import type {
  CoachReport,
  LapCompare,
  LapDetail,
  LapListItem,
  LapSummary,
  LapTrace,
  Plan,
  ReferenceCompare,
  SessionSummary,
  TrackInfo,
  TrackReferenceResponse,
} from "./types";

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: () => apiFetch<SessionSummary[]>("/sessions"),
  });
}

export function useAllLaps() {
  return useQuery({ queryKey: ["all-laps"], queryFn: () => apiFetch<LapListItem[]>("/laps") });
}

export function useSessionLaps(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["session-laps", sessionId],
    queryFn: () => apiFetch<LapSummary[]>(`/sessions/${sessionId}/laps`),
    enabled: Boolean(sessionId),
  });
}

export function useLap(lapId: string | undefined) {
  return useQuery({
    queryKey: ["lap", lapId],
    queryFn: () => apiFetch<LapDetail>(`/laps/${lapId}`),
    enabled: Boolean(lapId),
  });
}

export function useLapTrace(lapId: string | undefined) {
  return useQuery({
    queryKey: ["trace", lapId],
    queryFn: () => apiFetch<LapTrace>(`/laps/${lapId}/trace`),
    enabled: Boolean(lapId),
  });
}

export function useCompare(a: string | undefined, b: string | undefined) {
  return useQuery({
    queryKey: ["compare", a, b],
    queryFn: () => apiFetch<LapCompare>(`/laps/compare?a=${a}&b=${b}`),
    enabled: Boolean(a) && Boolean(b),
  });
}

export function useTrack(track: string | null | undefined) {
  return useQuery({
    queryKey: ["track", track],
    queryFn: () => apiFetch<TrackInfo>(`/tracks/${encodeURIComponent(track!)}`),
    enabled: Boolean(track),
  });
}

export function useTrackReference(track: string | null | undefined) {
  return useQuery({
    queryKey: ["track-reference", track],
    queryFn: () => apiFetch<TrackReferenceResponse>(`/tracks/${encodeURIComponent(track!)}/reference`),
    enabled: Boolean(track),
  });
}

export function useReferenceCompare(lapId: string | undefined) {
  return useQuery({
    queryKey: ["reference-compare", lapId],
    queryFn: () => apiFetch<ReferenceCompare>(`/laps/${lapId}/reference-compare`),
    enabled: Boolean(lapId),
  });
}

export function useCoachReport(lapId: string | undefined) {
  return useQuery({
    queryKey: ["coach", lapId],
    queryFn: async () => {
      try {
        return await apiFetch<CoachReport>(`/laps/${lapId}/coach`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    enabled: Boolean(lapId),
  });
}

export function useAnalyzeLap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (lapId: string) => apiJson<CoachReport>("/coach/analyze", "POST", { lap_id: lapId }),
    onSuccess: (report) => {
      qc.setQueryData(["coach", report.lap_id], report);
    },
  });
}

export function usePlans() {
  return useQuery({ queryKey: ["plans"], queryFn: () => apiFetch<Plan[]>("/billing/plans") });
}

export function useSubscribe() {
  return useMutation({
    mutationFn: (plan: string) =>
      apiJson<{ checkout_url: string; subscription_id: string; provider: string }>(
        "/billing/subscribe",
        "POST",
        { plan },
      ),
  });
}
