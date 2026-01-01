/**
 * Client-side Git cache hook
 *
 * Prevents redundant API calls when switching tabs by caching data in memory
 * Works alongside Redis server-side cache for optimal performance
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  projectId: number;
}

// Global cache shared across all component instances
const cache = {
  commits: null as CacheEntry<any[]> | null,
  graph: null as CacheEntry<any> | null,
  status: null as CacheEntry<any> | null,
  branches: null as CacheEntry<any> | null,
};

// Cache TTLs (in milliseconds)
const CACHE_TTL = {
  commits: 60000, // 1 minute
  graph: 60000,   // 1 minute
  status: 10000,  // 10 seconds (status changes frequently)
  branches: 30000, // 30 seconds
};

export function useGitCommits(projectId: number, limit: number = 50) {
  const [commits, setCommits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const loadCommits = useCallback(async (force: boolean = false) => {
    // Check cache first
    const now = Date.now();
    if (
      !force &&
      cache.commits &&
      cache.commits.projectId === projectId &&
      now - cache.commits.timestamp < CACHE_TTL.commits
    ) {
      // Use cached data
      setCommits(cache.commits.data);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/commits`, {
        params: { limit },
      });

      if (!isMountedRef.current) return;

      const data = response.data as any[];

      // Update cache
      cache.commits = {
        data,
        timestamp: now,
        projectId,
      };

      setCommits(data);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      console.error('Failed to load commits:', err);
      setError(err.message || 'Failed to load commits');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId, limit]);

  useEffect(() => {
    isMountedRef.current = true;
    loadCommits();

    return () => {
      isMountedRef.current = false;
    };
  }, [loadCommits]);

  const invalidate = useCallback(() => {
    cache.commits = null;
    loadCommits(true);
  }, [loadCommits]);

  return { commits, loading, error, reload: loadCommits, invalidate };
}

export function useGitStatus(projectId: number) {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const loadStatus = useCallback(async (force: boolean = false) => {
    // Check cache first
    const now = Date.now();
    if (
      !force &&
      cache.status &&
      cache.status.projectId === projectId &&
      now - cache.status.timestamp < CACHE_TTL.status
    ) {
      // Use cached data
      setStatus(cache.status.data);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/status`);

      if (!isMountedRef.current) return;

      const data = response.data as any;

      // Update cache
      cache.status = {
        data,
        timestamp: now,
        projectId,
      };

      setStatus(data);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      console.error('Failed to load status:', err);
      setError(err.message || 'Failed to load status');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId]);

  useEffect(() => {
    isMountedRef.current = true;
    loadStatus();

    return () => {
      isMountedRef.current = false;
    };
  }, [loadStatus]);

  const invalidate = useCallback(() => {
    cache.status = null;
    loadStatus(true);
  }, [loadStatus]);

  return { status, loading, error, reload: loadStatus, invalidate };
}

export function useGitBranches(projectId: number) {
  const [branches, setBranches] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const loadBranches = useCallback(async (force: boolean = false) => {
    // Check cache first
    const now = Date.now();
    if (
      !force &&
      cache.branches &&
      cache.branches.projectId === projectId &&
      now - cache.branches.timestamp < CACHE_TTL.branches
    ) {
      // Use cached data
      setBranches(cache.branches.data);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/branches`);

      if (!isMountedRef.current) return;

      const data = response.data as any;

      // Update cache
      cache.branches = {
        data,
        timestamp: now,
        projectId,
      };

      setBranches(data);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      console.error('Failed to load branches:', err);
      setError(err.message || 'Failed to load branches');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId]);

  useEffect(() => {
    isMountedRef.current = true;
    loadBranches();

    return () => {
      isMountedRef.current = false;
    };
  }, [loadBranches]);

  const invalidate = useCallback(() => {
    cache.branches = null;
    loadBranches(true);
  }, [loadBranches]);

  return { branches, loading, error, reload: loadBranches, invalidate };
}

export function useGitGraph(projectId: number, limit: number = 100) {
  const [graph, setGraph] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const loadGraph = useCallback(async (force: boolean = false) => {
    // Check cache first
    const now = Date.now();
    if (
      !force &&
      cache.graph &&
      cache.graph.projectId === projectId &&
      now - cache.graph.timestamp < CACHE_TTL.graph
    ) {
      // Use cached data
      setGraph(cache.graph.data);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/graph`, {
        params: { limit, all_branches: true },
      });

      if (!isMountedRef.current) return;

      const data = response.data as any;

      // Update cache
      cache.graph = {
        data,
        timestamp: now,
        projectId,
      };

      setGraph(data);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      console.error('Failed to load git graph:', err);
      setError(err.message || 'Failed to load git graph');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId, limit]);

  useEffect(() => {
    isMountedRef.current = true;
    loadGraph();

    return () => {
      isMountedRef.current = false;
    };
  }, [loadGraph]);

  const invalidate = useCallback(() => {
    cache.graph = null;
    loadGraph(true);
  }, [loadGraph]);

  return { graph, loading, error, reload: loadGraph, invalidate };
}

// Global invalidation function for use after git operations
export function invalidateAllGitCache() {
  cache.commits = null;
  cache.graph = null;
  cache.status = null;
  cache.branches = null;
}
