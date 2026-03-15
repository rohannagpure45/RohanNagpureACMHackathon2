import { useRef, useEffect, useState, useCallback } from 'react';
import type { RepBoundary, LandmarkFrame } from '../types/index.ts';

// MediaPipe Pose connections (35 pairs)
const POSE_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10],
  [11, 12],
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 29], [29, 31], [27, 31],
  [24, 26], [26, 28], [28, 30], [30, 32], [28, 32],
];

interface VideoPlayerProps {
  videoUrl: string;
  repBoundaries: RepBoundary[];
  currentTime?: number;
  onTimeUpdate?: (time: number) => void;
  crossOrigin?: 'anonymous' | 'use-credentials' | '' | undefined;
  landmarkFrames?: LandmarkFrame[];
}

// Interpolate between the two bracketing frames for smooth rendering
function interpolateFrame(frames: LandmarkFrame[], t: number): LandmarkFrame | null {
  if (!frames.length) return null;
  if (frames.length === 1) return frames[0];

  // Binary search for first frame with t >= query
  let lo = 0, hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].t < t) lo = mid + 1;
    else hi = mid;
  }

  // Edge cases: before first or after last frame
  if (lo === 0) return frames[0];
  if (lo >= frames.length) return frames[frames.length - 1];
  // Exact match or very close
  if (Math.abs(frames[lo].t - t) < 0.001) return frames[lo];

  const before = frames[lo - 1];
  const after = frames[lo];
  const span = after.t - before.t;
  if (span <= 0) return before;

  const alpha = (t - before.t) / span;

  const lm: [number, number, number][] = before.lm.map((bLm, i) => {
    const aLm = after.lm[i];
    if (!aLm) return bLm;
    return [
      bLm[0] * (1 - alpha) + aLm[0] * alpha,
      bLm[1] * (1 - alpha) + aLm[1] * alpha,
      Math.min(bLm[2], aLm[2]), // conservative visibility
    ] as [number, number, number];
  });

  return { t, lm };
}

export default function VideoPlayer({
  videoUrl,
  repBoundaries,
  currentTime,
  onTimeUpdate,
  crossOrigin = undefined,
  landmarkFrames = [],
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const seekingRef = useRef(false);
  const rafRef = useRef<number>(0);
  const smoothedLmRef = useRef<[number, number, number][] | null>(null);
  const [showSkeleton, setShowSkeleton] = useState(true);
  const [duration, setDuration] = useState(1);

  useEffect(() => {
    if (videoRef.current && currentTime !== undefined && !seekingRef.current) {
      const diff = Math.abs(videoRef.current.currentTime - currentTime);
      if (diff > 0.5) {
        videoRef.current.currentTime = currentTime;
      }
    }
  }, [currentTime]);

  useEffect(() => {
    if (videoRef.current && videoRef.current.duration) {
      setDuration(videoRef.current.duration);
    }
  }, [videoUrl]);

  // Keep canvas size synced to video element
  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const sync = () => {
      canvas.width = video.clientWidth;
      canvas.height = video.clientHeight;
    };
    sync();

    const observer = new ResizeObserver(sync);
    observer.observe(video);
    return () => observer.disconnect();
  }, []);

  const drawPose = useCallback((t: number, resetSmoothing = false) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !showSkeleton || !landmarkFrames.length) {
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx?.clearRect(0, 0, canvas.width, canvas.height);
      }
      smoothedLmRef.current = null;
      return;
    }

    const frame = interpolateFrame(landmarkFrames, t);
    if (!frame) return;

    // EMA smoothing: blend with previous rendered positions
    const SMOOTHING = 0.6;
    let lm = frame.lm;
    if (resetSmoothing) {
      smoothedLmRef.current = null;
    }
    const prev = smoothedLmRef.current;
    if (prev && prev.length === lm.length) {
      lm = lm.map((cur, i) => [
        prev[i][0] * (1 - SMOOTHING) + cur[0] * SMOOTHING,
        prev[i][1] * (1 - SMOOTHING) + cur[1] * SMOOTHING,
        cur[2], // keep raw visibility for threshold check
      ] as [number, number, number]);
    }
    smoothedLmRef.current = lm;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cW = canvas.width;
    const cH = canvas.height;
    ctx.clearRect(0, 0, cW, cH);

    // Video content occupies full width; height determined by aspect ratio
    const videoContentH = video.videoWidth > 0
      ? cW * (video.videoHeight / video.videoWidth)
      : cH;

    const toScreen = (pt: [number, number, number]): [number, number] => [
      pt[0] * cW,
      pt[1] * videoContentH,
    ];

    // Draw connections
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.lineWidth = 2;
    for (const [a, b] of POSE_CONNECTIONS) {
      const lmA = lm[a];
      const lmB = lm[b];
      if (!lmA || !lmB || lmA[2] < 0.65 || lmB[2] < 0.65) continue;
      const [ax, ay] = toScreen(lmA);
      const [bx, by] = toScreen(lmB);
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.stroke();
    }

    // Draw joints
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    for (const pt of lm) {
      if (pt[2] < 0.65) continue;
      const [sx, sy] = toScreen(pt);
      ctx.beginPath();
      ctx.arc(sx, sy, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [landmarkFrames, showSkeleton]);

  const handleTimeUpdate = () => {
    if (videoRef.current && onTimeUpdate) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  // RAF loop for smooth skeleton rendering
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const loop = () => {
      if (video.paused || video.ended) return;
      drawPose(video.currentTime);
      rafRef.current = requestAnimationFrame(loop);
    };

    const onPlay = () => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(loop);
    };

    const onPauseOrEnd = () => {
      cancelAnimationFrame(rafRef.current);
      drawPose(video.currentTime);
    };

    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPauseOrEnd);
    video.addEventListener('ended', onPauseOrEnd);

    // If already playing when effect runs (e.g. skeleton toggled on mid-play)
    if (!video.paused && !video.ended) {
      rafRef.current = requestAnimationFrame(loop);
    } else {
      drawPose(video.currentTime, true);
    }

    return () => {
      cancelAnimationFrame(rafRef.current);
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPauseOrEnd);
      video.removeEventListener('ended', onPauseOrEnd);
    };
  }, [drawPose]);

  return (
    <div className="video-player">
      {landmarkFrames.length > 0 && (
        <button
          className="skeleton-toggle"
          onClick={() => setShowSkeleton((v) => !v)}
        >
          {showSkeleton ? 'Hide Skeleton' : 'Show Skeleton'}
        </button>
      )}
      <div className="video-wrapper">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          crossOrigin={crossOrigin}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          onTimeUpdate={handleTimeUpdate}
          onSeeking={() => { seekingRef.current = true; }}
          onSeeked={() => {
            seekingRef.current = false;
            if (videoRef.current) drawPose(videoRef.current.currentTime, true);
          }}
        />
        <canvas ref={canvasRef} className="pose-canvas" />
      </div>
      {repBoundaries.length > 0 && (
        <div className="rep-markers">
          {repBoundaries.map((rb) => {
            const left = (rb.start_time / duration) * 100;
            const width = ((rb.end_time - rb.start_time) / duration) * 100;
            return (
              <div
                key={rb.rep_number}
                className="rep-marker"
                style={{ left: `${left}%`, width: `${width}%` }}
                title={`Rep ${rb.rep_number}`}
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = rb.start_time;
                  }
                }}
              >
                <span className="rep-marker-label">{rb.rep_number}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
