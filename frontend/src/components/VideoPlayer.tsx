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

function binarySearchNearest(frames: LandmarkFrame[], t: number): LandmarkFrame | null {
  if (!frames.length) return null;
  let lo = 0, hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].t < t) lo = mid + 1;
    else hi = mid;
  }
  if (lo > 0 && Math.abs(frames[lo - 1].t - t) < Math.abs(frames[lo].t - t)) {
    return frames[lo - 1];
  }
  return frames[lo];
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

  const drawPose = useCallback((t: number) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !showSkeleton || !landmarkFrames.length) {
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx?.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    const frame = binarySearchNearest(landmarkFrames, t);
    if (!frame) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cW = canvas.width;
    const cH = canvas.height;
    ctx.clearRect(0, 0, cW, cH);

    // Video content occupies full width; height determined by aspect ratio
    const videoContentH = video.videoWidth > 0
      ? cW * (video.videoHeight / video.videoWidth)
      : cH;

    const toScreen = (lm: [number, number, number]): [number, number] => [
      lm[0] * cW,
      lm[1] * videoContentH,
    ];

    // Draw connections
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.lineWidth = 2;
    for (const [a, b] of POSE_CONNECTIONS) {
      const lmA = frame.lm[a];
      const lmB = frame.lm[b];
      if (!lmA || !lmB || lmA[2] < 0.5 || lmB[2] < 0.5) continue;
      const [ax, ay] = toScreen(lmA);
      const [bx, by] = toScreen(lmB);
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.stroke();
    }

    // Draw joints
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    for (const lm of frame.lm) {
      if (lm[2] < 0.5) continue;
      const [sx, sy] = toScreen(lm);
      ctx.beginPath();
      ctx.arc(sx, sy, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [landmarkFrames, showSkeleton]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      if (onTimeUpdate) onTimeUpdate(videoRef.current.currentTime);
      drawPose(videoRef.current.currentTime);
    }
  };

  // Redraw when skeleton toggle changes
  useEffect(() => {
    if (videoRef.current) {
      drawPose(videoRef.current.currentTime);
    }
  }, [showSkeleton, drawPose]);

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
            if (videoRef.current) drawPose(videoRef.current.currentTime);
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
