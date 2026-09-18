/** Validate a server-provided destination before it is used for local traversal. */
export function validateDownloadDestination(
  destination: string,
): string[] | null {
  if (
    !destination ||
    destination.includes("\\") ||
    destination.startsWith("/") ||
    destination.startsWith("//") ||
    /^[A-Za-z]:\//.test(destination)
  ) {
    return null;
  }
  const segments = destination.split("/");
  if (
    segments.some(
      (segment) =>
        !segment ||
        segment === "." ||
        segment === ".." ||
        [...segment].some((character) => character.charCodeAt(0) < 0x20),
    )
  ) {
    return null;
  }
  return segments;
}
