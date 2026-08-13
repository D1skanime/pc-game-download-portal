<script setup lang="ts">
import type { Emitter } from "mitt";
import { storeToRefs } from "pinia";
import { inject, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useDisplay } from "vuetify";
import type { FirmwareSchema } from "@/__generated__";
import RDialog from "@/components/common/RDialog.vue";
import firmwareApi from "@/services/api/firmware";
import storeRoms from "@/stores/roms";
import type { Events } from "@/types/emitter";
import { formatBytes } from "@/utils";

const { t } = useI18n();
const { mdAndUp, lgAndUp, xs } = useDisplay();
const show = ref(false);
const firmwares = ref<FirmwareSchema[]>([]);
const romsStore = storeRoms();
const { currentPlatform } = storeToRefs(romsStore);
const emitter = inject<Emitter<Events>>("emitter");
emitter?.on("showDeleteFirmwareDialog", (firmwaresToDelete) => {
  firmwares.value = firmwaresToDelete;
  show.value = true;
});
const HEADERS = [
  {
    title: "Firmware",
    align: "start",
    sortable: true,
    key: "name",
  },
  { title: "", align: "end", key: "actions", sortable: false },
] as const;

async function deleteFirmware() {
  await firmwareApi
    .deleteFirmware({
      firmware: firmwares.value,
    })
    .then(() => {
      if (currentPlatform.value?.firmware) {
        currentPlatform.value.firmware = currentPlatform.value.firmware.filter(
          (firm) => !firmwares.value.includes(firm),
        );
      }
      emitter?.emit("snackbarShow", {
        msg: t("platform.firmware-deleted-successfully", {
          count: firmwares.value.length,
        }),
        icon: "mdi-check-circle",
        color: "green",
        timeout: 4000,
      });
    })
    .catch((error) => {
      console.error(error);
      emitter?.emit("snackbarShow", {
        msg: error.response.data.detail,
        icon: "mdi-close-circle",
        color: "red",
      });
      return;
    });
  closeDialog();
}

function closeDialog() {
  show.value = false;
  firmwares.value = [];
}
</script>

<template>
  <RDialog
    v-model="show"
    icon="mdi-delete"
    scroll-content
    :width="mdAndUp ? '60vw' : '95vw'"
    @close="closeDialog"
  >
    <template #header>
      <v-row no-gutters class="justify-center">
        <span>{{ t("platform.removing-firmware", firmwares.length) }}</span>
      </v-row>
    </template>
    <template #content>
      <v-data-table-virtual
        :item-value="(item) => item.id"
        :items="firmwares"
        :width="mdAndUp ? '60vw' : '95vw'"
        :headers="HEADERS"
      >
        <template #item.name="{ item }">
          <v-list-item class="px-0">
            <v-row no-gutters>
              <v-col>
                {{ item.file_name }}
              </v-col>
            </v-row>
            <v-row v-if="!lgAndUp" no-gutters>
              <v-col>
                <v-chip size="x-small" label>
                  {{ formatBytes(item.file_size_bytes) }}
                </v-chip>
                <v-chip
                  color="blue"
                  size="x-small"
                  label
                  :class="{ 'ml-1': !xs }"
                >
                  <span class="text-truncate"> {{ item.md5_hash }}</span>
                </v-chip>
              </v-col>
            </v-row>
            <template #append>
              <template v-if="lgAndUp">
                <v-chip size="x-small" label>
                  {{ formatBytes(item.file_size_bytes) }}
                </v-chip>
                <v-chip class="ml-1" color="blue" size="x-small" label>
                  <span class="text-truncate">{{ item.md5_hash }}</span>
                </v-chip>
              </template>
            </template>
          </v-list-item>
        </template>
      </v-data-table-virtual>
    </template>
    <template #append>
      <v-row class="justify-center my-2">
        <v-btn-group divided density="compact">
          <v-btn class="bg-toplayer" variant="flat" @click="closeDialog">
            {{ t("common.cancel") }}
          </v-btn>
          <v-btn
            class="text-romm-red bg-toplayer"
            variant="flat"
            @click="deleteFirmware"
          >
            {{ t("common.confirm") }}
          </v-btn>
        </v-btn-group>
      </v-row>
    </template>
  </RDialog>
</template>
