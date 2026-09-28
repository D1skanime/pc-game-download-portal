export type BackgroundAudioTrack = {
  id: number;
  url: string;
};

export function useBackgroundAudio(random = Math.random): {
  playRandom: (tracks: BackgroundAudioTrack[]) => void;
  stop: () => void;
} {
  let audio: HTMLAudioElement | null = null;

  function stop() {
    if (!audio) return;
    audio.pause();
    audio.src = "";
    audio.load();
    audio = null;
  }

  function playRandom(tracks: BackgroundAudioTrack[]) {
    stop();
    if (!tracks.length) return;
    const index = Math.min(
      tracks.length - 1,
      Math.max(0, Math.floor(random() * tracks.length)),
    );
    audio = new Audio(tracks[index].url);
    audio.preload = "none";
    void audio.play().catch(() => stop());
  }

  return { playRandom, stop };
}
