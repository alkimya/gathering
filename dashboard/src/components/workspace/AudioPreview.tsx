import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, RotateCcw, Music } from 'lucide-react';

interface AudioPreviewProps {
  filePath: string;
  projectId: number;
}

export function AudioPreview({ filePath, projectId }: AudioPreviewProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);

  // Use /file/raw endpoint to get binary audio data with correct MIME type
  const audioUrl = `/api/workspace/${projectId}/file/raw?path=${encodeURIComponent(filePath)}`;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);
    const handleError = (e: Event) => {
      const target = e.target as HTMLAudioElement;
      if (target.error) {
        console.error('Audio playback error:', {
          code: target.error.code,
          message: target.error.message,
          url: audioUrl
        });
      }
    };

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [audioUrl]);

  const togglePlay = async () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        try {
          await audioRef.current.play();
          setIsPlaying(true);
        } catch (error) {
          console.error('Audio play failed:', {
            error: (error as Error).message,
            url: audioUrl
          });
          setIsPlaying(false);
        }
      }
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
      if (newVolume === 0) {
        setIsMuted(true);
        audioRef.current.muted = true;
      } else if (isMuted) {
        setIsMuted(false);
        audioRef.current.muted = false;
      }
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const handleRestart = async () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      setCurrentTime(0);
      try {
        await audioRef.current.play();
        setIsPlaying(true);
      } catch (error) {
        console.error('Audio restart failed:', error);
        setIsPlaying(false);
      }
    }
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const fileName = filePath.split('/').pop() || '';
  const fileExtension = fileName.split('.').pop()?.toUpperCase() || 'AUDIO';

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-purple-900/10 to-slate-900">
      {/* Header */}
      <div className="glass-card border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Music className="w-5 h-5 text-cyan-400" />
          <span className="text-sm text-white/70 font-mono">{fileName}</span>
        </div>
        <div className="text-xs text-white/50">
          Audio Player
        </div>
      </div>

      {/* Audio Visualizer/Display */}
      <div className="flex-1 overflow-hidden flex flex-col items-center justify-center p-8 bg-black/20">
        {/* Album Art Placeholder */}
        <div className="w-64 h-64 rounded-2xl bg-gradient-to-br from-purple-500/20 via-cyan-500/20 to-purple-500/20
                      border-2 border-white/10 flex items-center justify-center mb-8 shadow-2xl
                      backdrop-blur-sm">
          <Music className="w-32 h-32 text-white/30" />
        </div>

        {/* Track Info */}
        <div className="text-center mb-6">
          <h3 className="text-xl font-semibold text-white/90 mb-2">{fileName}</h3>
          <div className="flex items-center gap-2 justify-center">
            <span className="px-3 py-1 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 text-xs font-mono">
              {fileExtension}
            </span>
            <span className="text-sm text-white/50">
              {formatTime(duration)}
            </span>
          </div>
        </div>

        {/* Hidden Audio Element */}
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="metadata"
          crossOrigin="anonymous"
        />
      </div>

      {/* Controls */}
      <div className="glass-card border-t border-white/5 p-6 space-y-4">
        {/* Progress Bar */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-white/60 font-mono min-w-[45px] text-right">
            {formatTime(currentTime)}
          </span>
          <div className="flex-1 relative">
            <input
              type="range"
              min="0"
              max={duration || 0}
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-cyan-500
                       [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-webkit-slider-thumb]:hover:bg-cyan-400
                       [&::-webkit-slider-thumb]:transition-colors
                       [&::-webkit-slider-thumb]:shadow-lg
                       [&::-webkit-slider-thumb]:shadow-cyan-500/50"
            />
            {/* Progress Fill */}
            <div
              className="absolute top-1/2 -translate-y-1/2 left-0 h-2 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-lg pointer-events-none"
              style={{ width: `${(currentTime / (duration || 1)) * 100}%` }}
            />
          </div>
          <span className="text-xs text-white/60 font-mono min-w-[45px]">
            {formatTime(duration)}
          </span>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-center gap-3">
          {/* Restart */}
          <button
            onClick={handleRestart}
            className="p-3 rounded-lg bg-white/5 hover:bg-white/10
                     border border-white/10 text-white/70 transition-all
                     hover:text-cyan-400 hover:border-cyan-500/30"
            title="Restart"
          >
            <RotateCcw className="w-5 h-5" />
          </button>

          {/* Play/Pause */}
          <button
            onClick={togglePlay}
            className="p-4 rounded-full bg-gradient-to-br from-cyan-500 to-purple-500
                     hover:from-cyan-400 hover:to-purple-400
                     border border-white/20 text-white transition-all
                     shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50
                     hover:scale-105"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-6 h-6" />
            ) : (
              <Play className="w-6 h-6 ml-1" />
            )}
          </button>

          {/* Volume */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleMute}
              className="p-3 rounded-lg bg-white/5 hover:bg-white/10
                       border border-white/10 text-white/70 transition-all
                       hover:text-purple-400 hover:border-purple-500/30"
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="w-5 h-5" />
              ) : (
                <Volume2 className="w-5 h-5" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={volume}
              onChange={handleVolumeChange}
              className="w-24 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-3
                       [&::-webkit-slider-thumb]:h-3
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-purple-500
                       [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-webkit-slider-thumb]:hover:bg-purple-400
                       [&::-webkit-slider-thumb]:transition-colors
                       [&::-webkit-slider-thumb]:shadow-md
                       [&::-webkit-slider-thumb]:shadow-purple-500/50"
            />
            <span className="text-xs text-white/50 font-mono min-w-[35px]">
              {Math.round(volume * 100)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
