import { useRef, useEffect, useState } from 'react';
import type { RepBoundary } from '../types/index.ts';

interface VideoPlayerProps {
  videoUrl: string;
  repBoundaries: RepBoundary[];
  currentTime?: number;
  onTimeUpdate?: (time: number) => void;
  crossOrigin?: 'anonymous' | 'use-credentials' | '' | undefined;
}

export default function VideoPlayer({
  videoUrl,
  repBoundaries,
  currentTime,
  onTimeUpdate,
  crossOrigin = undefined,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const seekingRef = useRef(false);

  useEffect(() => {
    if (videoRef.current && currentTime !== undefined && !seekingRef.current) {
      const diff = Math.abs(videoRef.current.currentTime - currentTime);
      if (diff > 0.5) {
        videoRef.current.currentTime = currentTime;
      }
    }
  }, [currentTime]);

  const handleTimeUpdate = () => {
    if (videoRef.current && onTimeUpdate) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  const [duration, setDuration] = useState(1);
  
  useEffect(() => {
    if (videoRef.current && videoRef.current.duration) {
      setDuration(videoRef.current.duration);
    }
  }, [videoUrl]);

  return (
    <div className="video-player">
      <video
        ref={videoRef}
        src={videoUrl}
        controls
        crossOrigin={crossOrigin}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onTimeUpdate={handleTimeUpdate}
        onSeeking={() => { seekingRef.current = true; }}
        onSeeked={() => { seekingRef.current = false; }}
      />
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
