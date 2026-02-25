import { describe, expect, it, vi } from "vitest";
import { createTypingCallbacks } from "./typing.js";

const flushMicrotasks = async () => {
  await Promise.resolve();
  await Promise.resolve();
};

describe("createTypingCallbacks", () => {
  it("invokes start on reply start", async () => {
    const start = vi.fn().mockResolvedValue(undefined);
    const onStartError = vi.fn();
    const callbacks = createTypingCallbacks({ start, onStartError });

    await callbacks.onReplyStart();

    expect(start).toHaveBeenCalledTimes(1);
    expect(onStartError).not.toHaveBeenCalled();
  });

  it("reports start errors", async () => {
    const start = vi.fn().mockRejectedValue(new Error("fail"));
    const onStartError = vi.fn();
    const callbacks = createTypingCallbacks({ start, onStartError });

    await callbacks.onReplyStart();

    expect(onStartError).toHaveBeenCalledTimes(1);
  });

  it("invokes stop on idle and reports stop errors", async () => {
    const start = vi.fn().mockResolvedValue(undefined);
    const stop = vi.fn().mockRejectedValue(new Error("stop"));
    const onStartError = vi.fn();
    const onStopError = vi.fn();
    const callbacks = createTypingCallbacks({ start, stop, onStartError, onStopError });

    callbacks.onIdle?.();
    await flushMicrotasks();

    expect(stop).toHaveBeenCalledTimes(1);
    expect(onStopError).toHaveBeenCalledTimes(1);
  });

  it("sends typing keepalive pings until idle cleanup", async () => {
    vi.useFakeTimers();
    try {
      const start = vi.fn().mockResolvedValue(undefined);
      const stop = vi.fn().mockResolvedValue(undefined);
      const onStartError = vi.fn();
      const callbacks = createTypingCallbacks({ start, stop, onStartError });

      await callbacks.onReplyStart();
      expect(start).toHaveBeenCalledTimes(1);

      await vi.advanceTimersByTimeAsync(2_999);
      expect(start).toHaveBeenCalledTimes(1);

      await vi.advanceTimersByTimeAsync(1);
      expect(start).toHaveBeenCalledTimes(2);

      await vi.advanceTimersByTimeAsync(3_000);
      expect(start).toHaveBeenCalledTimes(3);

      callbacks.onIdle?.();
      await flushMicrotasks();
      expect(stop).toHaveBeenCalledTimes(1);

      await vi.advanceTimersByTimeAsync(9_000);
      expect(start).toHaveBeenCalledTimes(3);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not re-arm keepalive when idle fires during an in-flight start", async () => {
    vi.useFakeTimers();
    try {
      let resolveStart: (() => void) | undefined;
      const start = vi.fn().mockImplementation(
        () =>
          new Promise<void>((resolve) => {
            resolveStart = resolve;
          }),
      );
      const stop = vi.fn().mockResolvedValue(undefined);
      const onStartError = vi.fn();
      const callbacks = createTypingCallbacks({ start, stop, onStartError });

      const inFlightStart = callbacks.onReplyStart();
      expect(start).toHaveBeenCalledTimes(1);

      callbacks.onIdle?.();
      await flushMicrotasks();
      expect(stop).toHaveBeenCalledTimes(1);

      resolveStart?.();
      await inFlightStart;

      await vi.advanceTimersByTimeAsync(9_000);
      expect(start).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("deduplicates stop across idle and cleanup", async () => {
    const start = vi.fn().mockResolvedValue(undefined);
    const stop = vi.fn().mockResolvedValue(undefined);
    const onStartError = vi.fn();
    const callbacks = createTypingCallbacks({ start, stop, onStartError });

    callbacks.onIdle?.();
    callbacks.onCleanup?.();
    await flushMicrotasks();

    expect(stop).toHaveBeenCalledTimes(1);
  });

  it("does not restart keepalive after idle cleanup", async () => {
    vi.useFakeTimers();
    try {
      const start = vi.fn().mockResolvedValue(undefined);
      const stop = vi.fn().mockResolvedValue(undefined);
      const onStartError = vi.fn();
      const callbacks = createTypingCallbacks({ start, stop, onStartError });

      await callbacks.onReplyStart();
      expect(start).toHaveBeenCalledTimes(1);

      callbacks.onIdle?.();
      await flushMicrotasks();

      await callbacks.onReplyStart();
      await vi.advanceTimersByTimeAsync(9_000);

      expect(start).toHaveBeenCalledTimes(1);
      expect(stop).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });
});
