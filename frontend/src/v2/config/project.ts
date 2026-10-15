export const PROJECT_REPOSITORY = "D1skanime/pc-game-download-portal";
export const PROJECT_GITHUB_URL = "https://github.com/" + PROJECT_REPOSITORY;
export const PROJECT_RELEASES_URL = PROJECT_GITHUB_URL + "/releases";
export const PROJECT_RELEASE_API_URL =
  "https://api.github.com/repos/" + PROJECT_REPOSITORY + "/releases";

export function projectReleaseTagUrl(tag: string): string {
  return PROJECT_RELEASES_URL + "/tag/" + tag;
}
