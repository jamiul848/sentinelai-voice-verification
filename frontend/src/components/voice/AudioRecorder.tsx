p"use client";

import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { AudioWaveform } from "./AudioWaveform";
import { AlertCircle, CheckCircle2, Mic, RotateCcw, Square, Volume2 } from "lucide-react";

interface AudioRecorderProps {
  onRecordingComplete: (file: File) => void;
  sampleLabel?: string;
  minDurationSec?: number;
}

export function AudioRecorder({
  onRecordingComplete,
  sampleLabel = "Sample Recording",
  minDurationSec = 3,
}: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [micError, setMicError] = useState<string | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Cleanup temporary audio URLs on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        audioContextRef.current.close();
      }
    };
  }, [audioUrl]);

  const startRecording = async () => {
    setMicError(null);
    setRecordedBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    chunksRef.current = [];

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone API not supported by this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

      // Initialize Web Audio API for waveform analysis
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioContext = new AudioContextClass();
      const analyserNode = audioContext.createAnalyser();
      analyserNode.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyserNode);

      audioContextRef.current = audioContext;
      setAnalyser(analyserNode);

      // Initialize MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const fullBlob = new Blob(chunksRef.current, { type: mimeType });
        setRecordedBlob(fullBlob);
        const url = URL.createObjectURL(fullBlob);
        setAudioUrl(url);
        setAnalyser(null);

        // Convert to File for backend upload
        const extension = mimeType.includes("webm") ? "webm" : "wav";
        const file = new File([fullBlob], `utterance_${Date.now()}.${extension}`, {
          type: mimeType,
        });
        onRecordingComplete(file);

        // Stop stream tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        if (audioContextRef.current && audioContextRef.current.state !== "closed") {
          audioContextRef.current.close();
        }
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setDuration(0);

      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 0.1);
      }, 100);
    } catch (err: any) {
      setMicError(
        err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
          ? "Microphone access was denied. Please grant microphone permissions in browser settings."
          : err.message || "Failed to initialize audio capture device."
      );
    }
  };

  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const resetRecording = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setRecordedBlob(null);
    setDuration(0);
    setMicError(null);
    setAnalyser(null);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-white flex items-center gap-2">
          <Volume2 className="w-4 h-4 text-blue-400" />
          {sampleLabel}
        </span>
        <div className="flex items-center gap-2">
          {isRecording && (
            <span className="flex items-center gap-1.5 text-xs text-red-400 font-mono animate-pulse">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              REC {duration.toFixed(1)}s
            </span>
          )}
          {!isRecording && recordedBlob && (
            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {duration.toFixed(1)}s captured
            </span>
          )}
        </div>
      </div>

      {/* Real-time Waveform Canvas */}
      <AudioWaveform isRecording={isRecording} analyser={analyser} />

      {/* Error Feedback */}
      {micError && (
        <div className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{micError}</span>
        </div>
      )}

      {/* Playback preview if recorded */}
      {audioUrl && !isRecording && (
        <div className="pt-1">
          <audio controls src={audioUrl} className="w-full h-8 rounded" />
        </div>
      )}

      {/* Controls Bar */}
      <div className="flex items-center justify-between pt-2">
        <div className="text-xs text-slate-400">
          {!recordedBlob && !isRecording && (
            <span>Minimum sample length: {minDurationSec} seconds</span>
          )}
          {isRecording && (
            <span className={duration < minDurationSec ? "text-amber-400" : "text-emerald-400"}>
              {duration < minDurationSec
                ? `Record at least ${(minDurationSec - duration).toFixed(1)}s more...`
                : "Sufficient acoustic length captured. You may stop."}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {!isRecording && !recordedBlob && (
            <Button onClick={startRecording} size="sm" className="bg-blue-600 hover:bg-blue-500 text-white gap-1.5">
              <Mic className="w-4 h-4" />
              <span>Start Recording</span>
            </Button>
          )}

          {isRecording && (
            <Button
              onClick={stopRecording}
              size="sm"
              variant="destructive"
              className="gap-1.5 animate-pulse"
            >
              <Square className="w-4 h-4" />
              <span>Stop Capture</span>
            </Button>
          )}

          {!isRecording && recordedBlob && (
            <Button
              onClick={resetRecording}
              size="sm"
              variant="outline"
              className="text-slate-300 gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Re-record</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}