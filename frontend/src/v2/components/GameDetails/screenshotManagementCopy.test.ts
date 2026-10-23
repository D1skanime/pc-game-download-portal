import { describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import applicationI18n from "@/locales";

const catalogs = import.meta.glob<{ default: Record<string, string> }>(
  "../../../locales/*/rom.json",
  { eager: true },
);
const locales = Object.entries(catalogs).map(([path, module]) => ({
  locale: path.split("/").at(-2)!,
  messages: module.default,
}));
const requiredKeys = [
  "upload-screenshots",
  "add-to-overview",
  "remove-from-overview",
  "add-as-background",
  "remove-as-background",
  "screenshot-public",
  "screenshot-make-public",
  "screenshot-make-private",
  "screenshots-upload-hint",
  "screenshots-source-provider",
  "screenshots-section-mine",
  "screenshots-section-community",
  "screenshots-overview-position",
  "screenshots-background-position",
  "provider-screenshot-remove-title",
  "provider-screenshot-remove-body",
  "provider-screenshot-remove-confirm",
  "provider-screenshot-delete-note",
  "delete-screenshot-title",
  "delete-screenshot-body",
  "screenshots-uploaded-n",
  "screenshots-upload-partial",
  "no-screenshots-uploaded",
  "screenshots-preview-unavailable",
  "screenshots-update-error",
  "screenshots-placement-conflict",
];
const english = locales.find(({ locale }) => locale === "en_US")!.messages;

describe("screenshot management message contract", () => {
  it("loads every supported locale", () => {
    expect(locales).toHaveLength(18);
  });

  describe.each(locales)("$locale", ({ locale, messages }) => {
    const missing = vi.fn();
    const i18n = createI18n({
      legacy: false,
      locale,
      fallbackLocale: false,
      missing,
      missingWarn: false,
      fallbackWarn: false,
      pluralRules: applicationI18n.global.pluralRules,
      messages: { [locale]: { rom: messages } },
    });
    const { t, te } = i18n.global;

    it("resolves required messages locally with no English fallback", () => {
      missing.mockClear();
      for (const key of requiredKeys) {
        expect(te("rom." + key, locale), key).toBe(true);
        const rendered = t("rom." + key, {
          n: 2,
          position: 0,
          uploaded: 3,
          failed: 7,
        });
        expect(rendered, key).not.toBe("rom." + key);
        expect(rendered, key).not.toMatch(/\{\w+\}/);
      }
      expect(missing).not.toHaveBeenCalled();
    });

    it("preserves the named parameter contract for every required message", () => {
      for (const key of requiredKeys) {
        const parameters = (message: string) =>
          [...new Set(message.match(/\{\w+\}/g) ?? [])].sort();
        expect(parameters(messages[key]), key).toEqual(
          parameters(english[key]),
        );
      }
    });

    it.each([0, 1, 2, 17])(
      "retains placement position %i on both surfaces",
      (position) => {
        for (const surface of ["overview", "background"]) {
          const rendered = t("rom.screenshots-" + surface + "-position", {
            position,
          });
          expect(rendered).toContain(String(position));
          expect(rendered).not.toMatch(/\{\w+\}/);
        }
      },
    );

    it.each([0, 1, 2, 5, 21])(
      "renders complete upload count %i through real plural rules",
      (n) => {
        const rendered = t("rom.screenshots-uploaded-n", { n }, n);
        expect(rendered).toContain(String(n));
        expect(rendered).not.toMatch(/[|{}]/);
        const branches = messages["screenshots-uploaded-n"]
          .split("|")
          .map((value) => value.trim());
        const branch =
          locale === "cs_CZ"
            ? n === 0
              ? 0
              : n === 1
                ? 1
                : n <= 4
                  ? 2
                  : 3
            : branches.length === 3
              ? Math.min(n, 2)
              : n === 1
                ? 0
                : 1;
        expect(rendered).toBe(branches[branch].replaceAll("{n}", String(n)));
      },
    );

    it.each([
      [1, 2],
      [3, 7],
      [0, 9],
      [21, 1],
    ])(
      "renders %i uploaded and %i failed without losing either outcome",
      (uploaded, failed) => {
        const rendered = t(
          "rom.screenshots-upload-partial",
          { uploaded, failed },
          uploaded,
        );
        expect(rendered).toContain(String(uploaded));
        expect(rendered).toContain(String(failed));
        expect(rendered).not.toMatch(/[|{}]/);
        expect(rendered).not.toBe(t("rom.no-screenshots-uploaded"));
      },
    );
  });

  it("explains durable provider deletion across scans and manual refreshes", () => {
    expect(english["provider-screenshot-remove-title"]).toBe(
      "Remove provider screenshot",
    );
    expect(english["provider-screenshot-remove-confirm"]).toBe(
      "Remove screenshot",
    );
    expect(english["provider-screenshot-remove-body"]).toBe(
      "This removes the managed screenshot copy and its overview/background placements. Deleted provider screenshots stay excluded from scans and manual provider refreshes.",
    );
    expect(english["provider-screenshot-delete-note"]).toBe(
      english["provider-screenshot-remove-body"],
    );
    expect(english["delete-screenshot-body"]).toBe(
      "This permanently deletes your uploaded screenshot.",
    );
    expect(english["no-screenshots-uploaded"]).toBe(
      "No screenshots uploaded. Check upload progress and try again.",
    );
  });

  it("uses the approved German primary action", () => {
    expect(
      locales.find(({ locale }) => locale === "de_DE")!.messages[
        "upload-screenshots"
      ],
    ).toBe("Screenshots hochladen");
  });
});
