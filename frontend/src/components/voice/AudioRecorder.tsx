"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { AudioWaveform } from "./AudioWaveform";
import { convertBlobTo16kMonoWav } from "@/lib/audio/wav-encoder";
import {
  AlertCircle,
  CheckCircle2,
  Mic,
  Pause,
  Play,
  RotateCcw,
  Square,
  Trash2,
  Volume2,
} from "lucide-react";

export type RecorderState =
  | "IDLE"
  | "REQUESTING_PERMISSION"
  | "READY"
  | "RECORDING"
  | "PAUSED"
  | "PROCESSING"
  | "COMPLETED"
  | "ERROR";

interface AudioRecorderProps {
  onRecordingComplete: (file: File) => void;
  onRecordingReset?: () => void;
  sampleLabel?: string;
  minDurationSec?: number;
  maxDurationSec?: number;
}

export function AudioRecorder({
  onRecordingComplete,
  onRecordingReset,
  sampleLabel = "Sample Recording",
  minDurationSec = 1.0,
  maxDurationSec = 60.0,
}: AudioRecorderProps) {
  const [state, setState] = useState<RecorderState>("IDLE");
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const cleanupResources = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setAnalyser(null);
  }, [audioUrl]);

  // Cleanup temporary audio URLs and active microphone streams on unmount
  useEffect(() => {
    return () => {
      cleanupResources();
    };
  }, [cleanupResources]);

  const requestMicrophoneAccess = async (): Promise<MediaStream> => {
    setState("REQUESTING_PERMISSION");
    setErrorMessage(null);

    if (typeof window === "undefined" || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Microphone capture is not supported by your browser or environment.");
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          sampleRate: 16000,
        },
      });
      return stream;
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        throw new Error(
          "Microphone permission was denied. Please allow microphone access in your browser settings to continue."
        );
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        throw new Error("No operational microphone detected. Please connect an audio input device.");
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        throw new Error("Microphone is currently occupied or blocked by another application.");
      } else {
        throw new Error(err.message || "Failed to initialize microphone.");
      }
    }
  };

  const startRecording = async () => {
    setErrorMessage(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setCapturedFile(null);
    chunksRef.current = [];

    try {
      const stream = await requestMicrophoneAccess();
      streamRef.current = stream;

      // Initialize Web Audio API for live waveform visualizer
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

      // Determine best browser supported MIME type
      let selectedMimeType = "";
      const candidates = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ];
      for (const candidate of candidates) {
        if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(candidate)) {
          selectedMimeType = candidate;
          break;
        }
      }

      const mediaRecorder = selectedMimeType
        ? new MediaRecorder(stream, { mimeType: selectedMimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setState("PROCESSING");
        try {
          const rawBlob = new Blob(chunksRef.current, {
            type: selectedMimeType || "audio/webm",
          });

          // Convert recorded buffer to 16kHz mono PCM WAV with RIFF header
          const { wavBlob, durationSec } = await convertBlobTo16kMonoWav(rawBlob, 16000);

          if (durationSec < minDurationSec) {
            throw new Error(
              `Recording duration (${durationSec.toFixed(1)}s) is shorter than the minimum required ${minDurationSec} seconds.`
            );
          }

          if (durationSec > maxDurationSec) {
            throw new Error(
              `Recording duration (${durationSec.toFixed(1)}s) exceeds maximum allowed ${maxDurationSec} seconds.`
            );
          }

          const wavUrl = URL.createObjectURL(wavBlob);
          setAudioUrl(wavUrl);

          const wavFile = new File([wavBlob], `utterance_${Date.now()}.wav`, {
            type: "audio/wav",
          });
          setCapturedFile(wavFile);
          setState("COMPLETED");
          onRecordingComplete(wavFile);
        } catch (convErr: any) {
          setState("ERROR");
          setErrorMessage(convErr.message || "Failed to process audio recording into WAV format.");
        } finally {
          // Disconnect stream tracks to turn off recording indicator
          if (streamRef.current) {
            streamRef.current.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
          }
          if (audioContextRef.current && audioContextRef.current.state !== "closed") {
            audioContextRef.current.close().catch(() => {});
            audioContextRef.current = null;
          }
          setAnalyser(null);
        }
      };

      mediaRecorder.start(100);
      setState("RECORDING");
      setDuration(0);

      timerRef.current = setInterval(() => {
        setDuration((prev) => {
          const next = prev + 0.1;
          if (next >= maxDurationSec) {
            stopRecording();
          }
          return next;
        });
      }, 100);
    } catch (err: any) {
      setState("ERROR");
      setErrorMessage(err.message || "Microphone initialization error.");
      cleanupResources();
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && state === "RECORDING") {
      mediaRecorderRef.current.pause();
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setState("PAUSED");
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && state === "PAUSED") {
      mediaRecorderRef.current.resume();
      setState("RECORDING");
      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 0.1);
      }, 100);
    }
  };

  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && (state === "RECORDING" || state === "PAUSED")) {
      mediaRecorderRef.current.stop();
    }
  };

  const resetRecording = () => {
    cleanupResources();
    setAudioUrl(null);
    setCapturedFile(null);
    setDuration(0);
    setErrorMessage(null);
    setState("IDLE");
    if (onRecordingReset) {
      onRecordingReset();
    }
  };

  const isRecordingActive = state === "RECORDING";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-white flex items-center gap-2">
          <Volume2 className="w-4 h-4 text-blue-400" />
          {sampleLabel}
        </span>

        <div className="flex items-center gap-2">
          {state === "REQUESTING_PERMISSION" && (
            <span className="text-xs text-amber-400 font-mono animate-pulse">
              Requesting mic permission...
            </span>
          )}

          {isRecordingActive && (
            <span className="flex items-center gap-1.5 text-xs text-red-400 font-mono animate-pulse">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-sm" />
              REC {duration.toFixed(1)}s / {minDurationSec}s min
            </span>
          )}

          {state === "PAUSED" && (
            <span className="text-xs text-amber-400 font-mono">
              PAUSED {duration.toFixed(1)}s
            </span>
          )}

          {state === "PROCESSING" && (
            <span className="text-xs text-blue-400 font-mono animate-pulse">
              Encoding 16kHz WAV...
            </span>
          )}

          {state === "COMPLETED" && capturedFile && (
            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {duration.toFixed(1)}s 16kHz WAV
            </span>
          )}
        </div>
      </div>

      {/* Real-time Waveform Canvas */}
      <AudioWaveform isRecording={isRecordingActive} analyser={analyser} />

      {/* Error Feedback */}
      {errorMessage && (
        <div className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Playback preview if recorded */}
      {audioUrl && state === "COMPLETED" && (
        <div className="pt-1">
          <audio controls src={audioUrl} className="w-full h-8 rounded" />
        </div>
      )}

      {/* Controls Bar */}
      <div className="flex items-center justify-between pt-1">
        <div className="text-[11px] text-slate-400">
          {state === "IDLE" && "Click 'Record' and speak into your microphone."}
          {state === "RECORDING" && `Speak continuously for at least ${minDurationSec}s.`}
          {state === "COMPLETED" && "Audio captured. Review playback or re-record."}
        </div>

        <div className="flex items-center gap-2">
          {state === "IDLE" || state === "ERROR" ? (
            <Button
              type="button"
              onClick={startRecording}
              className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record</span>
            </Button>
          ) : null}

          {state === "RECORDING" ? (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={pauseRecording}
                className="text-xs gap-1.5"
              >
                <Pause className="w-3.5 h-3.5" />
                <span>Pause</span>
              </Button>
              <Button
                type="button"
                onClick={stopRecording}
                className="bg-red-600 hover:bg-red-500 text-white gap-2 text-xs"
              >
                <Square className="w-3.5 h-3.5 fill-white" />
                <span>Stop</span>
              </Button>
            </>
          ) : null}

          {state === "PAUSED" ? (
            <>
              <Button
                type="button"
                onClick={resumeRecording}
                className="bg-blue-600 hover:bg-blue-500 text-white gap-1.5 text-xs"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>Resume</span>
              </Button>
              <Button
                type="button"
                onClick={stopRecording}
                className="bg-red-600 hover:bg-red-500 text-white gap-2 text-xs"
              >
                <Square className="w-3.5 h-3.5 fill-white" />
                <span>Finish</span>
              </Button>
            </>
          ) : null}

          {state === "COMPLETED" ? (
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={resetRecording}
                className="text-xs gap-1.5 text-slate-300 hover:text-white"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Re-record</span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={resetRecording}
                className="text-xs text-red-400 hover:text-red-300 p-2"
                title="Discard audio"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
