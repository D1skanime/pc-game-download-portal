<script setup lang="ts">
// PersonalTab — read-only "your stats" section. Interactive editing lives
// in the Edit dialog (emitter event) for now; when we build a v2-native
// editor it replaces the static rows here.
import type { RomUserSchema } from "@/__generated__";

defineOptions({ inheritAttrs: false });

defineProps<{
  romUser: RomUserSchema | null;
  statusDisplay: { emoji: string; text: string } | null;
  lastPlayed: string | null;
}>();
</script>

<template>
  <section class="r-v2-det-personal">
    <div class="r-v2-det-personal__row">
      <div class="r-v2-det-personal__label">Status</div>
      <div>
        <span v-if="statusDisplay" class="r-v2-det-personal__status">
          <span>{{ statusDisplay.emoji }}</span>
          {{ statusDisplay.text }}
        </span>
        <span v-else class="r-v2-det-personal__muted">Not set</span>
      </div>
    </div>
    <div class="r-v2-det-personal__row">
      <div class="r-v2-det-personal__label">Rating</div>
      <div>
        <span v-if="romUser?.rating">
          {{ "★".repeat(romUser.rating)
          }}{{ "☆".repeat(Math.max(0, 5 - romUser.rating)) }}
        </span>
        <span v-else class="r-v2-det-personal__muted">Unrated</span>
      </div>
    </div>
    <div v-if="romUser?.difficulty" class="r-v2-det-personal__row">
      <div class="r-v2-det-personal__label">Difficulty</div>
      <div>{{ romUser.difficulty }}/10</div>
    </div>
    <div v-if="romUser?.completion" class="r-v2-det-personal__row">
      <div class="r-v2-det-personal__label">Completion</div>
      <div class="r-v2-det-personal__completion">
        <div class="r-v2-det-personal__progress">
          <div
            class="r-v2-det-personal__progress-fill"
            :style="{ width: `${romUser.completion}%` }"
          />
        </div>
        <span>{{ romUser.completion }}%</span>
      </div>
    </div>
    <div class="r-v2-det-personal__row">
      <div class="r-v2-det-personal__label">Last played</div>
      <div>
        <span v-if="lastPlayed">{{ lastPlayed }}</span>
        <span v-else class="r-v2-det-personal__muted">Never</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.r-v2-det-personal {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 520px;
}

.r-v2-det-personal__row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.r-v2-det-personal__label {
  width: 120px;
  flex-shrink: 0;
  font-size: 10.5px;
  font-weight: var(--r-font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.28);
}

.r-v2-det-personal__muted {
  color: rgba(255, 255, 255, 0.3);
  font-style: italic;
}

.r-v2-det-personal__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: #fff;
  font-size: 12.5px;
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-det-personal__completion {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}
.r-v2-det-personal__progress {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}
.r-v2-det-personal__progress-fill {
  height: 100%;
  background: #fff;
  border-radius: 3px;
}
</style>
