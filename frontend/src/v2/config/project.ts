// Dependency-free display metadata shared by browser startup and build tooling.
// Persistence, authentication and service-worker identities are separate contracts.
export const PROJECT_NAME = "ZockArchive";
export const PROJECT_SHORT_NAME = "ZA";
export const PROJECT_DESCRIPTION = "A self-hosted PC and console game archive";
export const PROJECT_REPOSITORY = "D1skanime/zockarchive";
export const PROJECT_GITHUB_URL = "https://github.com/" + PROJECT_REPOSITORY;
export const PROJECT_DOCS_URL = PROJECT_GITHUB_URL + "/tree/main/docs";
export const PROJECT_RELEASES_URL = PROJECT_GITHUB_URL + "/releases";
export const PROJECT_RELEASE_API_URL =
  "https://api.github.com/repos/" + PROJECT_REPOSITORY + "/releases";

export function projectReleaseTagUrl(tag: string): string {
  return PROJECT_RELEASES_URL + "/tag/" + tag;
}
