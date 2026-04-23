<script setup lang="ts">
// GlobalDialogs — the stack of emitter-driven dialogs + notification
// mount-points that need to live at the layout level so they overlay
// every route. v1 dialogs are reused directly; when a v2-native replacement
// is built it drops in here.
import AddRomsToCollectionDialog from "@/components/common/Collection/Dialog/AddRoms.vue";
import DeleteManualDialog from "@/components/common/Game/Dialog/DeleteManual.vue";
import DeleteRomDialog from "@/components/common/Game/Dialog/DeleteRom.vue";
import EditRomDialog from "@/components/common/Game/Dialog/EditRom.vue";
import ManualUploadTargetDialog from "@/components/common/Game/Dialog/ManualUploadTarget.vue";
import MatchRomDialog from "@/components/common/Game/Dialog/MatchRom.vue";
import RefreshMetadataDialog from "@/components/common/Game/Dialog/RefreshMetadata.vue";
import ShowQRCodeDialog from "@/components/common/Game/Dialog/ShowQRCode.vue";
import Notification from "@/components/common/Notifications/Notification.vue";
import UploadProgress from "@/components/common/Notifications/UploadProgress.vue";

defineOptions({ inheritAttrs: false });
</script>

<template>
  <Notification />
  <UploadProgress />
  <ManualUploadTargetDialog />
  <DeleteManualDialog />
  <EditRomDialog />
  <DeleteRomDialog />
  <MatchRomDialog />
  <RefreshMetadataDialog />
  <ShowQRCodeDialog />
  <AddRomsToCollectionDialog />
</template>
