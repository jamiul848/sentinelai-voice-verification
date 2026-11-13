import { describe, expect, it } from "vitest";
import { encodePcmWav, validateAudioRecording } from "@/lib/audio/wav-encoder";

describe("Phase 8C - Audio Normalization & WAV Header Encoding", () => {
  it("encodes Float32Array into standard 16-bit PCM RIFF/WAVE header", () => {
    // Generate 1 second of 16kHz mono audio (16,000 samples)
    const sampleRate = 16000;
    const numSamples = sampleRate;
    const samples = new Float32Array(numSamples);

    // Populate with 440 Hz sinusoidal test tone
    for (let i = 0; i < numSamples; i++) {
      samples[i] = Math.sin((2 * Math.PI * 440 * i) / sampleRate) * 0.5;
    }

    const wavBuffer = encodePcmWav(samples, sampleRate);
    expect(wavBuffer.byteLength).toBe(44 + numSamples * 2); // 44 bytes header + 32,000 bytes data

    const view = new DataView(wavBuffer);

    // Check RIFF header
    const riff = String.fromCharCode(
      view.getUint8(0),
      view.getUint8(1),
      view.getUint8(2),
      view.getUint8(3)
    );
    expect(riff).toBe("RIFF");

    // Check WAVE identifier
    const wave = String.fromCharCode(
      view.getUint8(8),
      view.getUint8(9),
      view.getUint8(10),
      view.getUint8(11)
    );
    expect(wave).toBe("WAVE");

    // Check "fmt " sub-chunk
    const fmt = String.fromCharCode(
      view.getUint8(12),
      view.getUint8(13),
      view.getUint8(14),
      view.getUint8(15)
    );
    expect(fmt).toBe("fmt ");
    expect(view.getUint32(16, true)).toBe(16); // Subchunk1Size
    expect(view.getUint16(20, true)).toBe(1); // AudioFormat: 1 (PCM)
    expect(view.getUint16(22, true)).toBe(1); // NumChannels: 1 (Mono)
    expect(view.getUint32(24, true)).toBe(16000); // SampleRate: 16000
    expect(view.getUint32(28, true)).toBe(32000); // ByteRate: 16000 * 1 * 2
    expect(view.getUint16(32, true)).toBe(2); // BlockAlign: 2
    expect(view.getUint16(34, true)).toBe(16); // BitsPerSample: 16

    // Check "data" sub-chunk
    const dataChunk = String.fromCharCode(
      view.getUint8(36),
      view.getUint8(37),
      view.getUint8(38),
      view.getUint8(39)
    );
    expect(dataChunk).toBe("data");
    expect(view.getUint32(40, true)).toBe(numSamples * 2);
  });

  it("validates recording constraints (size and non-emptiness)", () => {
    // Empty file validation
    const emptyFile = new File([], "empty.wav", { type: "audio/wav" });
    const emptyValidation = validateAudioRecording(emptyFile);
    expect(emptyValidation.valid).toBe(false);
    expect(emptyValidation.error).toContain("empty");

    // Oversized file validation (> 10MB)
    const largeBuffer = new Uint8Array(11 * 1024 * 1024);
    const oversizedFile = new File([largeBuffer], "large.wav", { type: "audio/wav" });
    const oversizedValidation = validateAudioRecording(oversizedFile);
    expect(oversizedValidation.valid).toBe(false);
    expect(oversizedValidation.error).toContain("exceeds maximum allowed limit");

    // Valid file validation
    const validBuffer = new Uint8Array(32044); // ~1 sec of 16kHz WAV
    const validFile = new File([validBuffer], "valid.wav", { type: "audio/wav" });
    const validValidation = validateAudioRecording(validFile);
    expect(validValidation.valid).toBe(true);
    expect(validValidation.error).toBeUndefined();
  });
});

