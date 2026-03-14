import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import type { Session, Rep, FatigueScore } from '../types/index.ts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const api = axios.create({ baseURL: API_URL });

export function useSession(id: string | undefined) {
  const [session, setSession] = useState<Session | null>(null);
  const [reps, setReps] = useState<Rep[]>([]);
  const [fatigue, setFatigue] = useState<FatigueScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchData = async () => {
      try {
        const [sessionRes, repsRes, fatigueRes] = await Promise.all([
          api.get<Session>(`/api/sessions/${id}`),
          api.get<Rep[]>(`/api/sessions/${id}/reps`),
          api.get<FatigueScore[]>(`/api/sessions/${id}/fatigue`),
        ]);
        setSession(sessionRes.data);
        setReps(repsRes.data);
        setFatigue(fatigueRes.data);
        setLoading(false);

        if (sessionRes.data.status !== 'processing' && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to fetch session data';
        setError(msg);
        setLoading(false);
      }
    };

    fetchData();
    intervalRef.current = setInterval(fetchData, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [id]);

  return { session, reps, fatigue, loading, error };
}

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Session[]>('/api/sessions')
      .then(res => {
        setSessions(res.data);
        setLoading(false);
      })
      .catch(err => {
        const msg = err instanceof Error ? err.message : 'Failed to fetch sessions';
        setError(msg);
        setLoading(false);
      });
  }, []);

  const refetch = () => {
    setLoading(true);
    api.get<Session[]>('/api/sessions')
      .then(res => {
        setSessions(res.data);
        setLoading(false);
      })
      .catch(err => {
        const msg = err instanceof Error ? err.message : 'Failed to fetch sessions';
        setError(msg);
        setLoading(false);
      });
  };

  return { sessions, loading, error, refetch };
}
