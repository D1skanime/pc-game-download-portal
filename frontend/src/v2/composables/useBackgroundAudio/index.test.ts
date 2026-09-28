import { afterEach, describe, expect, it, vi } from "vitest";
import { useBackgroundAudio } from ".";

describe("useBackgroundAudio", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("chooses a supplied selected track and clears audio on stop", () => {
    const createdAudio = {
      load: vi.fn(),
      pause: vi.fn(),
      play: vi.fn().mockResolvedValue(undefined),
      preload: "",
      src: "",
    };
    function AudioMock(url: string) {
      createdAudio.src = url;
      return createdAudio;
    }
    vi.stubGlobal("Audio", AudioMock);
    const audio = useBackgroundAudio(() => 0.5);

    audio.playRandom([
      { id: 1, url: "/one.mp3" },
      { id: 2, url: "/two.mp3" },
    ]);

    expect(createdAudio.src).toContain("/two.mp3");
    expect(createdAudio.preload).toBe("none");
    audio.stop();
    expect(createdAudio.pause).toHaveBeenCalledOnce();
    expect(createdAudio.load).toHaveBeenCalledOnce();
    expect(createdAudio.src).toBe("");
  });

  it("stays silent when autoplay is rejected", async () => {
    const createdAudio = {
      load: vi.fn(),
      pause: vi.fn(),
      play: vi.fn().mockRejectedValue(new Error("Autoplay blocked")),
      preload: "",
      src: "",
    };
    function AudioMock(url: string) {
      createdAudio.src = url;
      return createdAudio;
    }
    vi.stubGlobal("Audio", AudioMock);
    const audio = useBackgroundAudio();

    audio.playRandom([{ id: 1, url: "/one.mp3" }]);
    await Promise.resolve();

    expect(createdAudio.pause).toHaveBeenCalledOnce();
    expect(createdAudio.src).toBe("");
  });
});
