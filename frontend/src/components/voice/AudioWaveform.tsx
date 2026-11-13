"use client";

import React, { useEffect, useRef } from "react";

interface AudioWaveformProps {
  isRecording: boolean;
  analyser?: AnalyserNode | null;
  className?: string;
}

export function AudioWaveform({ isRecording, analyser, className = "h-20" }: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      if (isRecording && analyser) {
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyser.getByteTimeDomainData(dataArray);

        ctx.lineWidth = 2;
        ctx.strokeStyle = "#38bdf8"; // Cyber sky blue
        ctx.beginPath();

        const sliceWidth = (width * 1.0) / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 128.0;
          const y = (v * height) / 2;

          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }

          x += sliceWidth;
        }

        ctx.lineTo(width, height / 2);
        ctx.stroke();
      } else if (isRecording) {
        // Fallback animated wave if no AnalyserNode
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#38bdf8";
        ctx.beginPath();
        const time = Date.now() / 200;
        for (let x = 0; x < width; x++) {
          const y = height / 2 + Math.sin(x * 0.05 + time) * 15 * Math.sin(x * 0.01);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      } else {
        // Idle baseline flatline
        ctx.lineWidth = 1;
        ctx.strokeStyle = "#334155";
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isRecording, analyser]);

  return (
    <div className={`w-full rounded-xl bg-slate-950/80 border border-slate-800 p-2 flex items-center justify-center overflow-hidden ${className}`}>
      <canvas ref={canvasRef} width={600} height={80} className="w-full h-full" />
    </div>
  );
}

